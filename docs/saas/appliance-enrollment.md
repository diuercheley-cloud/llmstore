# Appliance Enrollment Flow

## Process
1. **Token Generation**: An administrator on the Managed Control Plane generates an enrollment token for a specific Workspace.
2. **Token Delivery**: The token is provided to the local appliance administrator.
3. **Appliance Registration**: The appliance calls the `/managed/appliances/enroll` endpoint with the token, its own external ID, and a display name.
4. **Validation**: The Control Plane validates the token and ensures it hasn't expired or been used.
5. **Establishment**: If valid, the appliance is registered in the Control Plane database, and the token is marked as used.
6. **Confirmation**: The appliance receives its `appliance_id`, `workspace_id`, and initial configuration.

## Security
- Tokens are high-entropy secrets (`secrets.token_urlsafe(32)`).
- Tokens have a configurable expiration time (default 24h).
- Each token is single-use.
- Appliances can be revoked at any time by the central administrator.
