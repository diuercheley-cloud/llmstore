from app.core.time import utc_now

class ClusterHeartbeatService:
    def process_heartbeat(self, cluster_id: str, data: dict):
        # Update cluster health score
        pass