# Platform Operational Profiles

To reduce configuration complexity, the platform supports pre-defined operational profiles. Instead of managing hundreds of individual feature flags, operators choose a profile that best matches their environment.

## Official Profiles
1. **appliance**: Safe local-only mode with minimal features enabled.
2. **agentic-pilot**: Development/Pilot mode with agentic runtime enabled but limited external impact.
3. **agentic-production**: Production-ready environment with full auditing, isolation, and attestation required.
4. **enterprise-distributed**: Full enterprise deployment support with multi-cluster federation and managed control plane.

## Usage
Set the `PLATFORM_PROFILE` environment variable:
```bash
export PLATFORM_PROFILE=agentic-production
```

## Internal Flags
Individual flags are still supported as overrides, but the core operation is driven by the profile. Internal flags are derived from the profile settings.
