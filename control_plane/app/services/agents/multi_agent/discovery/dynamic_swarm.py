import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class DynamicSwarmDiscovery:
    """
    Real dynamic agent discovery system.
    Replaces static references and mock "arbitration" with actual capability matching.
    """
    def __init__(self):
        self._capabilities_index: Dict[str, List[str]] = {}

    def register_agent(self, agent_id: str, capabilities: List[str]):
        logger.info(f"Registering agent {agent_id} with capabilities: {capabilities}")
        for cap in capabilities:
            if cap not in self._capabilities_index:
                self._capabilities_index[cap] = []
            if agent_id not in self._capabilities_index[cap]:
                self._capabilities_index[cap].append(agent_id)

    def find_candidates(self, required_capabilities: List[str]) -> List[str]:
        if not required_capabilities:
            return []
            
        candidates = set(self._capabilities_index.get(required_capabilities[0], []))
        for cap in required_capabilities[1:]:
            candidates.intersection_update(self._capabilities_index.get(cap, []))
            
        logger.info(f"Found candidate agents for {required_capabilities}: {candidates}")
        return list(candidates)
