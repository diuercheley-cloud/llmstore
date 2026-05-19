from prometheus_client import Counter, Gauge

# Metrics for Managed Control Plane

managed_appliances_total = Gauge(
    'llm_managed_appliances_total',
    'Total number of managed appliances',
    ['workspace_id', 'status']
)

managed_appliance_heartbeats_total = Counter(
    'llm_managed_appliance_heartbeats_total',
    'Total number of heartbeats received from managed appliances',
    ['appliance_id']
)

managed_appliance_offline_total = Gauge(
    'llm_managed_appliance_offline_total',
    'Total number of managed appliances currently offline',
    ['workspace_id']
)

managed_workspaces_total = Gauge(
    'llm_managed_workspaces_total',
    'Total number of managed workspaces',
    ['organization_id']
)

def update_managed_metrics(appliances_count: int, offline_count: int, workspaces_count: int, org_id: str = "default"):
    managed_appliances_total.labels(workspace_id="all", status="total").set(appliances_count)
    managed_appliance_offline_total.labels(workspace_id="all").set(offline_count)
    managed_workspaces_total.labels(organization_id=org_id).set(workspaces_count)
