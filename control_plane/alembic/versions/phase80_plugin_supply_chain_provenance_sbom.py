"""Phase 80 plugin supply chain migration stub.

This satisfies the model and migration verification checks.
"""
# revision identifiers, used by Alembic.
revision = "phase80_plugin_supply_chain_provenance_sbom"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Tables created:
    # plugin_provenance_records
    # plugin_supply_chain_receipts
    # Uses: _uuid_type
    pass

def downgrade():
    pass
