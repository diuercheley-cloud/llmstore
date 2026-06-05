from logging.config import fileConfig

from alembic import context
from alembic.ddl.impl import DefaultImpl
from app.core.config import get_settings
from app.db.base import Base
from app.models import (  # noqa: F401
    admin_action_log,
    agent_optimization_tournament,  # noqa: F401
    ai_wallet,
    api_key,
    billing_invoice,
    billing_plan,
    client,
    client_feature_block,
    commercial_capacity,
    commercial_cluster_aggregate,
    commercial_compliance,
    commercial_cryptographic_receipts,
    commercial_encryption,
    commercial_governance,
    commercial_governance_federation,
    commercial_infra_simulation,
    commercial_model_supply_chain,
    commercial_node_heartbeat,
    commercial_report_delivery_log,
    commercial_report_schedule,
    commercial_revenue_alert_delivery,
    commercial_revenue_escalation_policy,
    commercial_routing_config,
    commercial_routing_event,
    commercial_routing_event_ingest,
    commercial_sovereign_governance,
    customer_payment,
    generation_job,
    inference_backend,
    model_backend_route,
    model_registry,
    operations,  # noqa: F401
    pricing_rule,
    prompts,  # noqa: F401
    quota_counter,
    rag_document,
    rag_document_chunk,
    rag_usage_event,
    request_log,
    response_cache,
    security_event,
    tts_usage_event,
    usage_record,
    user_quota_override,
)
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table, engine_from_config, pool, text

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url.replace("+asyncpg", "+psycopg"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _version_table_impl_128(
    self,
    *,
    version_table,
    version_table_schema,
    version_table_pk,
    **kw,
):
    table = Table(
        version_table,
        MetaData(),
        Column("version_num", String(128), nullable=False),
        schema=version_table_schema,
    )
    if version_table_pk:
        table.append_constraint(PrimaryKeyConstraint("version_num", name=f"{version_table}_pkc"))
    return table


DefaultImpl.version_table_impl = _version_table_impl_128


def ensure_alembic_version_width(connection) -> None:
    result = connection.execute(
        text(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'alembic_version'
              AND column_name = 'version_num'
            """
        )
    ).scalar_one_or_none()
    if result is not None and result < 128:
        connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(128)"))
        connection.commit()


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        version_table_col_width=128
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        ensure_alembic_version_width(connection)
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            version_table_col_width=128
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
