import io
import tarfile
import zipfile
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.utils.archive import safe_extract_tar, safe_extract_zip

def test_safe_extract_tar_valid():
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        # Normal file
        tinfo1 = tarfile.TarInfo(name="good.txt")
        tinfo1.size = 12
        tinfo1.mode = 0o644
        tar.addfile(tinfo1, io.BytesIO(b"Hello World!"))
        
        # Directory
        tinfo2 = tarfile.TarInfo(name="subdir")
        tinfo2.type = tarfile.DIRTYPE
        tinfo2.mode = 0o755
        tar.addfile(tinfo2)
        
        # Internal symlink (relative, staying inside)
        tinfo3 = tarfile.TarInfo(name="subdir/link.txt")
        tinfo3.type = tarfile.SYMTYPE
        tinfo3.mode = 0o777
        tinfo3.linkname = "../good.txt"
        tar.addfile(tinfo3)

    tar_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
            safe_extract_tar(tar, tmpdir)
        
        assert Path(tmpdir, "good.txt").exists()
        assert Path(tmpdir, "good.txt").read_text() == "Hello World!"
        assert Path(tmpdir, "subdir").is_dir()
        assert Path(tmpdir, "subdir/link.txt").is_symlink()

def test_safe_extract_tar_absolute():
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        tinfo = tarfile.TarInfo(name="/etc/passwd")
        tinfo.size = 0
        tar.addfile(tinfo, io.BytesIO())
        
    tar_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
            with pytest.raises(ValueError, match="Absolute path not allowed"):
                safe_extract_tar(tar, tmpdir)

def test_safe_extract_tar_traversal():
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        tinfo = tarfile.TarInfo(name="../../evil.txt")
        tinfo.size = 0
        tar.addfile(tinfo, io.BytesIO())
        
    tar_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
            with pytest.raises(ValueError, match="Directory traversal sequence"):
                safe_extract_tar(tar, tmpdir)

def test_safe_extract_tar_symlink_escape():
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        tinfo = tarfile.TarInfo(name="evil_link")
        tinfo.type = tarfile.SYMTYPE
        tinfo.linkname = "../../etc/passwd"
        tar.addfile(tinfo)
        
    tar_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
            with pytest.raises(ValueError, match="Link points outside destination"):
                safe_extract_tar(tar, tmpdir)

def test_safe_extract_tar_hardlink_escape():
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        tinfo = tarfile.TarInfo(name="evil_hardlink")
        tinfo.type = tarfile.LNKTYPE
        tinfo.linkname = "/etc/passwd"
        tar.addfile(tinfo)
        
    tar_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
            with pytest.raises(ValueError, match="Link points to absolute path"):
                safe_extract_tar(tar, tmpdir)

def test_safe_extract_tar_special_file():
    tar_io = io.BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w:gz") as tar:
        tinfo = tarfile.TarInfo(name="device_file")
        tinfo.type = tarfile.CHRTYPE
        tar.addfile(tinfo)
        
    tar_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with tarfile.open(fileobj=tar_io, mode="r:gz") as tar:
            with pytest.raises(ValueError, match="Special files are not allowed"):
                safe_extract_tar(tar, tmpdir)


def test_safe_extract_zip_valid():
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as zf:
        zf.writestr("good.txt", "Hello World!")
        zf.writestr("subdir/", "")
        
        # Internal symlink (staying inside)
        zinfo = zipfile.ZipInfo("subdir/link.txt")
        zinfo.create_system = 3
        zinfo.external_attr = 0o120777 << 16
        zf.writestr(zinfo, "../good.txt")

    zip_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_io) as zf:
            safe_extract_zip(zf, tmpdir)
            
        assert Path(tmpdir, "good.txt").exists()
        assert Path(tmpdir, "good.txt").read_text() == "Hello World!"
        assert Path(tmpdir, "subdir").is_dir()

def test_safe_extract_zip_absolute():
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as zf:
        zf.writestr("/etc/passwd", "evil")
        
    zip_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_io) as zf:
            with pytest.raises(ValueError, match="Absolute path not allowed"):
                safe_extract_zip(zf, tmpdir)

def test_safe_extract_zip_traversal():
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as zf:
        zf.writestr("../../evil.txt", "evil")
        
    zip_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_io) as zf:
            with pytest.raises(ValueError, match="Directory traversal sequence"):
                safe_extract_zip(zf, tmpdir)

def test_safe_extract_zip_symlink_escape():
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as zf:
        zinfo = zipfile.ZipInfo("evil_link")
        zinfo.create_system = 3
        zinfo.external_attr = 0o120777 << 16
        zf.writestr(zinfo, "../../etc/passwd")
        
    zip_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_io) as zf:
            with pytest.raises(ValueError, match="Link points outside destination"):
                safe_extract_zip(zf, tmpdir)

def test_safe_extract_zip_special_file():
    zip_io = io.BytesIO()
    with zipfile.ZipFile(zip_io, "w") as zf:
        zinfo = zipfile.ZipInfo("fifo_file")
        zinfo.create_system = 3
        zinfo.external_attr = 0o010600 << 16
        zf.writestr(zinfo, "")
        
    zip_io.seek(0)
    with TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_io) as zf:
            with pytest.raises(ValueError, match="Special files are not allowed"):
                safe_extract_zip(zf, tmpdir)
