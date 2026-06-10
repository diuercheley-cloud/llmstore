import hashlib
import json
import logging
from datetime import datetime, UTC
from typing import Any, Dict, List, Optional, Tuple

from app.models.core.federation_mesh import ClusterNode, ConflictRecord, FederationPeer, MeshMergePolicy, SyncCommit
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class MeshSyncService:
    def __init__(self, db: AsyncSession, node_id: str):
        self.db = db
        self.node_id = node_id

    async def create_commit(self, payload: Dict[str, Any], parent_hash: Optional[str] = None) -> SyncCommit:
        """Generates a git-like commit for a set of changes."""
        # 1. Increment logical clock
        stmt = update(ClusterNode).where(ClusterNode.id == self.node_id).values(
            logical_clock=ClusterNode.logical_clock + 1
        ).returning(ClusterNode.logical_clock)
        res = await self.db.execute(stmt)
        logical_clock = res.scalar_one()

        # 2. Compute hash
        content = f"{parent_hash}|{self.node_id}|{logical_clock}|{json.dumps(payload, sort_keys=True)}"
        commit_hash = hashlib.sha256(content.encode()).hexdigest()

        commit = SyncCommit(
            hash=commit_hash,
            parent_hash=parent_hash,
            author_node_id=self.node_id,
            payload=payload,
            logical_clock=logical_clock,
            signature="MOCKED_SIGNATURE"
        )
        self.db.add(commit)
        return commit

    async def export_bundle(self, since_hash: Optional[str] = None) -> Dict[str, Any]:
        """Exports a bundle of commits for synchronization."""
        stmt = select(SyncCommit).order_by(SyncCommit.logical_clock.asc())
        # In a real impl, we would filter by since_hash and walk the graph
        res = await self.db.execute(stmt)
        commits = res.scalars().all()

        return {
            "schema_version": "1.0.0",
            "source_node": self.node_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "commits": [
                {
                    "hash": c.hash,
                    "parent_hash": c.parent_hash,
                    "author": c.author_node_id,
                    "payload": c.payload,
                    "clock": c.logical_clock,
                    "signature": c.signature
                } for c in commits
            ]
        }

    async def import_bundle(self, bundle: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        """Imports and merges commits from a bundle."""
        results = {"imported": 0, "conflicts": 0, "merged": 0}
        
        # Validation
        if bundle.get("schema_version") != "1.0.0":
            raise ValueError("Unsupported bundle schema version")

        for commit_data in bundle.get("commits", []):
            commit_hash = commit_data["hash"]
            
            # Check if exists
            existing = await self.db.get(SyncCommit, commit_hash)
            if existing:
                continue

            if dry_run:
                results["imported"] += 1
                continue

            # CRDT-ready Merge Logic: Last Write Wins based on logical clock
            # Here we simulate conflict detection
            conflict = await self._check_conflict(commit_data)
            if conflict:
                results["conflicts"] += 1
                await self._record_conflict(commit_data)
            else:
                new_commit = SyncCommit(
                    hash=commit_hash,
                    parent_hash=commit_data.get("parent_hash"),
                    author_node_id=commit_data["author"],
                    payload=commit_data["payload"],
                    logical_clock=commit_data["clock"],
                    signature=commit_data["signature"]
                )
                self.db.add(new_commit)
                results["imported"] += 1

        if not dry_run:
            await self.db.commit()
            
        return results

    async def _check_conflict(self, commit_data: Dict[str, Any]) -> bool:
        # Simple placeholder logic for conflict: same parent, different hash
        parent = commit_data.get("parent_hash")
        if not parent: return False
        
        stmt = select(SyncCommit).where(SyncCommit.parent_hash == parent, SyncCommit.hash != commit_data["hash"])
        res = await self.db.execute(stmt)
        return res.first() is not None

    async def _record_conflict(self, commit_data: Dict[str, Any]):
        conflict = ConflictRecord(
            commit_hash=commit_data["hash"],
            peer_node_id=commit_data["author"],
            conflicting_payload=commit_data["payload"]
        )
        self.db.add(conflict)
