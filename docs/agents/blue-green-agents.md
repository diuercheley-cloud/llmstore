# Blue-Green Deployment for Agents

Blue-green deployment is a technique that reduces risk and downtime by running two identical production environments, only one of which serves live traffic.

## Workflow

1. **Blue Version**: The current production version serving all traffic.
2. **Green Version**: The new version deployed and ready for testing.
3. **Traffic Switch**: Gradually move traffic from Blue to Green (e.g., 10%, 50%, 100%).
4. **Health Monitoring**: Monitor metrics (latency, error rate, eval score) during the switch.
5. **Instant Rollback**: If Green shows issues, switch traffic back to Blue immediately.

## Implementation Details

The `BlueGreenDeploymentService` manages the traffic weights and version tracking in the `agent_deployments` table. Traffic routing logic in the Gateway uses these weights to select the appropriate agent version for each request.
