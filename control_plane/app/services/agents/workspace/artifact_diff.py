import difflib
from typing import Any, Dict

from app.models.agents.agent_workspace import AgentArtifactVersion
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


class ArtifactDiffManager:
    @staticmethod
    def compute_diff(content_a: str, content_b: str) -> Dict[str, Any]:
        """Computes diff between content_a (old) and content_b (new) and returns unified and structured diff."""
        lines_a = content_a.splitlines(keepends=True)
        lines_b = content_b.splitlines(keepends=True)
        
        diff_lines = list(difflib.unified_diff(
            lines_a, 
            lines_b, 
            fromfile='version_a', 
            tofile='version_b'
        ))
        
        # Also build a structured line-by-line diff for the UI
        structured = []
        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                for line in lines_a[i1:i2]:
                    structured.append({"type": "equal", "value": line.rstrip('\r\n')})
            elif tag == 'replace':
                for line in lines_a[i1:i2]:
                    structured.append({"type": "delete", "value": line.rstrip('\r\n')})
                for line in lines_b[j1:j2]:
                    structured.append({"type": "insert", "value": line.rstrip('\r\n')})
            elif tag == 'delete':
                for line in lines_a[i1:i2]:
                    structured.append({"type": "delete", "value": line.rstrip('\r\n')})
            elif tag == 'insert':
                for line in lines_b[j1:j2]:
                    structured.append({"type": "insert", "value": line.rstrip('\r\n')})
                    
        return {
            "raw_diff": "".join(diff_lines),
            "structured": structured
        }

    @staticmethod
    async def get_version_by_number(db: AsyncSession, artifact_id: Any, version_number: int) -> AgentArtifactVersion:
        stmt = select(AgentArtifactVersion).where(
            AgentArtifactVersion.artifact_id == artifact_id,
            AgentArtifactVersion.version_number == version_number
        )
        result = await db.execute(stmt)
        version = result.scalar_one_or_none()
        if not version:
            raise ValueError(f"Version {version_number} not found for artifact {artifact_id}.")
        return version
