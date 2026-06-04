import pytest
from app.models.commercial_cluster_registry import CommercialClusterRegistry
from app.services.routing.commercial_geo_router import CommercialGeoRouter


@pytest.fixture
def geo_router():
    return CommercialGeoRouter()

def test_calculate_geo_distance(geo_router):
    # New York to London roughly
    lat1, lon1 = 40.7128, -74.0060
    lat2, lon2 = 51.5074, -0.1278
    
    dist = geo_router.calculate_geo_distance_km(lat1, lon1, lat2, lon2)
    assert 5500 < dist < 5600

def test_detect_cross_ocean(geo_router):
    c1 = CommercialClusterRegistry(cluster_id="us", continent="North America")
    c2 = CommercialClusterRegistry(cluster_id="eu", continent="Europe")
    c3 = CommercialClusterRegistry(cluster_id="us-west", continent="North America")
    
    assert geo_router.detect_cross_ocean(c1, c2) is True
    assert geo_router.detect_cross_ocean(c1, c3) is False

def test_score_geo_candidate_local(geo_router):
    source = CommercialClusterRegistry(cluster_id="local", latitude=0, longitude=0)
    candidate = CommercialClusterRegistry(cluster_id="local", latitude=0, longitude=0)
    
    # Enable geo routing for test
    geo_router.settings.commercial_geo_routing_enabled = True
    
    result = geo_router.score_geo_candidate(source, candidate, candidate_margin=30.0, candidate_health=1.0)
    assert result["score"] == 1.0
    assert result["eligible"] is True

def test_score_geo_candidate_far(geo_router):
    source = CommercialClusterRegistry(cluster_id="ny", latitude=40.7, longitude=-74.0)
    candidate = CommercialClusterRegistry(cluster_id="tokyo", latitude=35.6, longitude=139.6)
    
    geo_router.settings.commercial_geo_routing_enabled = True
    geo_router.settings.commercial_geo_routing_allow_cross_ocean = True
    geo_router.settings.commercial_geo_routing_max_region_distance_km = 5000
    
    result = geo_router.score_geo_candidate(source, candidate, candidate_margin=30.0, candidate_health=1.0)
    assert result["eligible"] is False
    assert result["reason"] == "max_distance_exceeded"
