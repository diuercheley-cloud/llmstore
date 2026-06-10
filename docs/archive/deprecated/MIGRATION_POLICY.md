# Alembic Migration Policy

## Policy Choice: Consolidated Baseline (Option B)
We utilize a consolidated baseline approach to migration management. This provides a stable, repeatable path for new environments while keeping the migration history clean.

## Principles
1. **Consolidated History**: We do not maintain an infinite replay of every atomic schema change since project inception.
2. **Snapshots**: Periodic snapshots are taken to consolidate history.
3. **Single Head**: The repository must always have exactly one `alembic head`.

## Standard Procedures

### Creating a New Migration
1. Use `alembic revision --autogenerate -m "description"`.
2. Review the generated script to ensure correctness.
3. Commit both the migration script and the updated schema state.

### Updating New Environments
1. Run `alembic upgrade head` on a fresh database instance.

### Updating Existing Environments
1. Standard Alembic upgrade procedure: `alembic upgrade head`.

### SQLite vs PostgreSQL
1. Always test migrations on both SQLite (for local dev) and PostgreSQL (for CI/Prod). Use `alembic downgrade -1` and `upgrade` to verify reversibility.
