from app.schemas.backup import BackupManifest, BackupComponent
from app.services.backup.planner import RestorePlanner

def test_restore_planner():
    manifest = BackupManifest(
        backup_id="test",
        scope="partial",
        components=[
            BackupComponent(name="db", description="db", item_count=1, data_hash="h1", file_name="db.json"),
            BackupComponent(name="conf", description="conf", item_count=1, data_hash="h2", file_name="conf.json")
        ],
        archive_checksum="c1",
        payload_file="p",
        payload_signature="s"
    )
    plan = RestorePlanner.create_plan(manifest)
    assert len(plan) == 2
    assert "Restore db from db.json" in plan
    assert "Restore conf from conf.json" in plan
