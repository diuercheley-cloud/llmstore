import math
from typing import Any

from app.core.config import get_settings
from app.models.commercial_cluster_registry import CommercialClusterRegistry


class CommercialGeoRouter:
    def __init__(self):
        self.settings = get_settings()

    def calculate_geo_distance_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the great circle distance between two points on the earth."""
        if any(x is None for x in [lat1, lon1, lat2, lon2]):
            return -1.0
            
        # Haversine formula
        r = 6371  # Earth radius in kilometers
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi / 2.0) ** 2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2.0) ** 2
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = r * c
        return distance

    def detect_cross_ocean(self, cluster1: CommercialClusterRegistry, cluster2: CommercialClusterRegistry) -> bool:
        """Detect if routing between two clusters involves crossing an ocean."""
        # Simple heuristic based on continents, or if not available, bounding boxes
        c1 = cluster1.continent
        c2 = cluster2.continent
        if c1 and c2 and c1 != c2:
            # Not all continent crossings are ocean crossings (e.g., Europe/Asia),
            # but for latency purposes, we treat them as significant boundaries.
            # Americas vs others is a definite ocean crossing.
            americas = ["North America", "South America"]
            c1_americas = c1 in americas
            c2_americas = c2 in americas
            if c1_americas != c2_americas:
                return True
                
        # Fallback to distance
        dist = self.calculate_geo_distance_km(
            cluster1.latitude or 0, cluster1.longitude or 0,
            cluster2.latitude or 0, cluster2.longitude or 0
        )
        if dist > 6000: # Rough approximation
            return True
            
        return False

    def calculate_latency_penalty(self, distance_km: float, avg_latency: int) -> float:
        """Calculate a penalty score based on distance and known latency."""
        penalty = 0.0
        if distance_km > 0:
            # Roughly 1ms per 100km theoretical minimum in fiber, but real world is higher
            penalty += min(1.0, distance_km / self.settings.commercial_geo_routing_max_region_distance_km)
            
        if avg_latency is not None and avg_latency > 0:
            penalty += min(1.0, avg_latency / 500.0) # Penalty caps at 500ms
            
        return penalty / 2.0 if penalty > 0 else 0.0

    def score_geo_candidate(self, 
                            source_cluster: CommercialClusterRegistry, 
                            candidate: CommercialClusterRegistry,
                            candidate_margin: float,
                            candidate_health: float,
                            qos_tier: Any | None = None) -> dict[str, Any]:
        """Score a candidate cluster based on geo properties, margin, and health."""
        if not self.settings.commercial_geo_routing_enabled:
            return {"score": 0.0, "eligible": True, "reason": "disabled"}
            
        if source_cluster.cluster_id == candidate.cluster_id:
            return {"score": 1.0, "eligible": True, "reason": "local"}

        # Phase 20: QoS Tier Enforcement
        if qos_tier:
            if not qos_tier.allow_cross_cluster:
                 return {"score": 0.0, "eligible": False, "reason": "qos_cross_cluster_blocked"}
            
            # Check if candidate health violates QoS tier
            if candidate_health < 0.5 and not qos_tier.allow_degraded_cluster:
                 return {"score": 0.0, "eligible": False, "reason": "qos_degraded_cluster_blocked"}

        # 1. Cross Ocean Check
        is_cross_ocean = self.detect_cross_ocean(source_cluster, candidate)
        if is_cross_ocean and not self.settings.commercial_geo_routing_allow_cross_ocean:
            return {"score": 0.0, "eligible": False, "reason": "cross_ocean_blocked"}
            
        # 2. Distance Calculation
        dist_km = -1.0
        if source_cluster.latitude and candidate.latitude:
            dist_km = self.calculate_geo_distance_km(
                source_cluster.latitude, source_cluster.longitude,
                candidate.latitude, candidate.longitude
            )
            
        if dist_km > self.settings.commercial_geo_routing_max_region_distance_km:
            return {"score": 0.0, "eligible": False, "reason": "max_distance_exceeded"}

        # 3. Latency Penalty
        latency_penalty = self.calculate_latency_penalty(dist_km, candidate.avg_public_latency_ms or 0)
        
        # 4. Same Region Group Bonus
        region_bonus = 0.0
        if source_cluster.region_group and candidate.region_group and source_cluster.region_group == candidate.region_group:
            region_bonus = 1.0

        # Calculate final score
        # Base score starts high, subtract penalties, add bonuses
        base = 1.0
        
        w_lat = self.settings.commercial_geo_routing_latency_penalty_weight
        w_margin = self.settings.commercial_geo_routing_margin_weight
        w_health = self.settings.commercial_geo_routing_health_weight
        w_reg = self.settings.commercial_geo_routing_region_weight
        
        # Normalize margin to 0-1 (assuming -100 to +100 range roughly)
        norm_margin = max(0.0, min(1.0, (candidate_margin + 50) / 150))
        
        score = base - (latency_penalty * w_lat) + (norm_margin * w_margin) + (candidate_health * w_health) + (region_bonus * w_reg)
        
        return {
            "score": score,
            "eligible": True,
            "reason": "scored",
            "distance_km": dist_km,
            "is_cross_ocean": is_cross_ocean,
            "latency_penalty": latency_penalty,
            "margin_score": norm_margin,
            "region_bonus": region_bonus
        }

    def rank_geo_clusters(self, source_cluster: CommercialClusterRegistry, candidates_info: list[dict], qos_tier: Any | None = None) -> list[dict]:
        """Rank a list of candidates based on geo scores."""
        ranked = []
        for info in candidates_info:
            candidate = info["cluster"]
            margin = info.get("margin", 0.0)
            health = info.get("health", 1.0)
            
            score_result = self.score_geo_candidate(source_cluster, candidate, margin, health, qos_tier=qos_tier)
            if score_result["eligible"]:
                info.update(score_result)
                ranked.append(info)
                
        # Sort descending by score
        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked

    def explain_geo_selection(self, ranked_candidates: list[dict]) -> dict[str, Any]:
        """Generate a summary explanation of why a candidate would be selected."""
        if not ranked_candidates:
            return {"status": "no_candidates"}
            
        top = ranked_candidates[0]
        return {
            "status": "success",
            "selected_cluster": top["cluster"].cluster_id,
            "score": top["score"],
            "distance_km": top.get("distance_km"),
            "latency_penalty": top.get("latency_penalty"),
            "margin_score": top.get("margin_score"),
            "mode": self.settings.commercial_geo_routing_mode
        }
