# Owner: agent-platform
from .sab_manifest import AgentSABManifest

class SABCompatibility:
    def check(self, manifest: AgentSABManifest, current_platform_version: str) -> bool:
        """
        Simple version prefix match for compatibility.
        """
        # manifest version: v2.0.0, current: v2.1.0 -> compatible
        # manifest version: v3.0.0, current: v2.1.0 -> incompatible
        m_major = manifest.supported_platform_version.split('.')[0]
        p_major = current_platform_version.split('.')[0]
        
        return m_major == p_major
