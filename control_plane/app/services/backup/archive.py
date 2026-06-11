import io
import tarfile
import json
import hashlib
from datetime import UTC, datetime
from typing import Any, Dict
from .errors import BackupArchiveError
from .contracts import ArchiveProvider

class ArchiveService:
    def create(self, payload_parts: Dict[str, bytes]) -> bytes:
        try:
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
                for file_name, payload in payload_parts.items():
                    info = tarfile.TarInfo(name=file_name)
                    info.size = len(payload)
                    info.mtime = int(datetime.now(UTC).timestamp())
                    tar.addfile(info, io.BytesIO(payload))
            return buffer.getvalue()
        except Exception as e:
            raise BackupArchiveError(f"Failed to create archive: {e}")

    def extract(self, archive_bytes: bytes) -> Dict[str, Any]:
        try:
            extracted: Dict[str, Any] = {}
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
                for member in tar.getmembers():
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    content = f.read()
                    if member.name.endswith(".json"):
                        extracted[member.name] = json.loads(content.decode("utf-8"))
                    else:
                        extracted[member.name] = content
            return extracted
        except Exception as e:
            raise BackupArchiveError(f"Failed to extract archive: {e}")

# Maintain backward compatibility for now if needed, 
# but new code should use ArchiveService
class ArchiveWriter:
    @staticmethod
    def create(payload_parts: Dict[str, bytes]) -> bytes:
        return ArchiveService().create(payload_parts)

class ArchiveReader:
    @staticmethod
    def extract(archive_bytes: bytes) -> Dict[str, Any]:
        return ArchiveService().extract(archive_bytes)
    
    @staticmethod
    def get_member_content(archive_bytes: bytes, file_name: str) -> bytes:
        try:
            with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
                member = tar.extractfile(file_name)
                if member is None:
                    raise FileNotFoundError(f"Member {file_name} not found in archive")
                return member.read()
        except Exception as e:
            raise BackupArchiveError(f"Failed to read archive member {file_name}: {e}")
