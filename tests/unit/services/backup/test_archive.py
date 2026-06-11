import json
from app.services.backup.archive import ArchiveWriter, ArchiveReader

def test_archive_writer_reader():
    payload_parts = {
        "file1.json": json.dumps({"key": "val"}).encode("utf-8"),
        "file2.txt": b"plain text"
    }
    
    archive_bytes = ArchiveWriter.create(payload_parts)
    assert isinstance(archive_bytes, bytes)
    
    extracted = ArchiveReader.extract(archive_bytes)
    assert extracted["file1.json"] == {"key": "val"}
    assert extracted["file2.txt"] == b"plain text"

def test_archive_reader_get_member():
    payload_parts = {"test.json": b'{"a": 1}'}
    archive_bytes = ArchiveWriter.create(payload_parts)
    
    content = ArchiveReader.get_member_content(archive_bytes, "test.json")
    assert content == b'{"a": 1}'
