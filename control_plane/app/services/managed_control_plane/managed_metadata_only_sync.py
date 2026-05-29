from app.services.distributed_runtime.data_boundary_policy import DataBoundaryPolicy

class ManagedMetadataOnlySync:
    def sync(self, payload: dict):
        safe_payload = DataBoundaryPolicy.sanitize_payload(payload)
        # Proceed with sync
        return safe_payload