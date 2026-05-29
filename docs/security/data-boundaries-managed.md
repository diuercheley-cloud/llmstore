# Data Boundaries for Managed Control Plane

Security and privacy are the highest priority when connecting to the Managed Control Plane.

## Data Sanitization
The `DataBoundaryPolicy` strictly sanitizes outgoing heartbeats and synchronization events.
- **Prompts**: Stripped.
- **Documents**: Stripped.
- **Raw Memory**: Stripped.

## Validation
Any sync attempt that contains restricted keys will fail or have those keys removed before transmission.
