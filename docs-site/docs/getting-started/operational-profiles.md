<!-- synced_from: docs/PROFILES.md -->

> Source of truth: `docs/PROFILES.md`

# Operational Profiles

Operational profiles provide supported starting points for progressively enabling the
platform. The default profile is `lite`.

Select a profile with:

```bash
OPERATIONAL_PROFILE=lite uvicorn app.main:app --app-dir control_plane
```

`DEPLOYMENT_PROFILE` remains supported as a compatibility fallback. When both variables
are set, `OPERATIONAL_PROFILE` wins. Environment variables and `.env` values override
settings from the selected profile.

## Official Profiles

| Capability | lite | standard | agentic | enterprise |
| --- | --- | --- | --- | --- |
| Database | SQLite | PostgreSQL | PostgreSQL | PostgreSQL |
| Inference proxy and basic RAG | Enabled | Enabled | Enabled | Enabled |
| Multi-model inference | Disabled | Enabled | Enabled | Enabled |
| Basic observability and Prometheus | Optional/disabled | Enabled | Enabled | Enabled |
| Loki and Tempo | Disabled | Disabled | Disabled | Enabled |
| Memory, tools, workflows, and agents | Disabled | Disabled | Enabled | Enabled |
| Multi-tenant, federation, and marketplace | Disabled | Disabled | Disabled | Enabled |

The `enterprise` profile enables every enterprise capability represented by the catalog;
PostgreSQL replaces SQLite as its storage backend. Individual low-level feature flags can
still be overridden by operators.

## Profile Files

Profiles live in `config/profiles/<name>.yaml` and contain:

- `settings`: defaults applied to `BaseAppConfig`.
- `features`: the stable capability catalog shown by the API and dashboard.

The active posture is available at:

```text
GET /api/system/profile
```

The admin dashboard displays it at `/admin-dashboard/operations/profile`.

## Startup Examples

```bash
OPERATIONAL_PROFILE=lite uvicorn app.main:app --app-dir control_plane
OPERATIONAL_PROFILE=standard uvicorn app.main:app --app-dir control_plane
OPERATIONAL_PROFILE=agentic uvicorn app.main:app --app-dir control_plane
OPERATIONAL_PROFILE=enterprise uvicorn app.main:app --app-dir control_plane
```

For `standard`, `agentic`, and `enterprise`, set `DATABASE_URL` to the target PostgreSQL
instance. The values in the profile files are local development defaults.
