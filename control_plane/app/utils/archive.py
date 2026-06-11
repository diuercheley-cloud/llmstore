import os
import tarfile
import zipfile
from pathlib import Path
from typing import Union

def is_relative_to(path: Path, base: Path) -> bool:
    """Check if 'path' is relative to 'base'."""
    try:
        path.relative_to(base)
        return True
    except ValueError:
        return False

def safe_extract_tar(tar: tarfile.TarFile, path: Union[str, Path]) -> None:
    """
    Safely extract a tar archive to the specified directory, blocking:
    - Absolute paths
    - Directory traversal via '..'
    - Symlinks or hardlinks pointing outside the destination directory
    - Special files (devices, FIFOs, sockets, etc.)
    """
    dest = Path(path).resolve()
    
    # First, validate all members
    for m in tar.getmembers():
        # 1. Block absolute paths and '..'
        name = m.name
        if name.startswith('/') or Path(name).is_absolute():
            raise ValueError(f"Absolute path not allowed in tar member: {name}")
        
        if '..' in Path(name).parts:
            raise ValueError(f"Directory traversal sequence ('..') not allowed in tar member: {name}")
            
        # 2. Block special files
        if not (m.isreg() or m.isdir() or m.issym() or m.islnk()):
            raise ValueError(f"Special files are not allowed in tar: {name}")
            
        # 3. Ensure target is within destination
        dest_path = (dest / name).resolve()
        if not is_relative_to(dest_path, dest):
            raise ValueError(f"Tar member extracts outside of destination: {name}")
            
        # 4. Check symlink / hardlink targets
        if m.issym() or m.islnk():
            link_target = Path(m.linkname)
            if link_target.is_absolute():
                raise ValueError(f"Link points to absolute path: {m.linkname}")
            
            link_dir = (dest / name).parent
            resolved_target = (link_dir / link_target).resolve()
            if not is_relative_to(resolved_target, dest):
                raise ValueError(f"Link points outside destination: {m.linkname}")
                
    # If all members are valid, extract
    tar.extractall(str(dest))

def safe_extract_zip(zf: zipfile.ZipFile, path: Union[str, Path]) -> None:
    """
    Safely extract a zip archive to the specified directory, blocking:
    - Absolute paths
    - Directory traversal via '..'
    - Symlinks pointing outside the destination directory
    - Special files (devices, FIFOs, sockets, etc.)
    """
    dest = Path(path).resolve()
    
    # First, validate all members
    for zinfo in zf.infolist():
        # 1. Block absolute paths and '..'
        name = zinfo.filename
        if name.startswith('/') or Path(name).is_absolute():
            raise ValueError(f"Absolute path not allowed in zip member: {name}")
            
        if '..' in Path(name).parts:
            raise ValueError(f"Directory traversal sequence ('..') not allowed in zip member: {name}")
            
        # 2. Block special files (Unix attributes if available)
        if zinfo.create_system == 3:  # Unix
            file_type = (zinfo.external_attr >> 16) & 0o170000
            # Allowed types: regular file (S_IFREG), directory (S_IFDIR), symlink (S_IFLNK), or 0
            if file_type not in (0, 0o100000, 0o040000, 0o120000):
                raise ValueError(f"Special files are not allowed in zip: {name}")
                
        # 3. Ensure target is within destination
        dest_path = (dest / name).resolve()
        if not is_relative_to(dest_path, dest):
            raise ValueError(f"Zip member extracts outside of destination: {name}")
            
        # 4. Check symlink targets
        is_symlink = (zinfo.external_attr >> 16) & 0o170000 == 0o120000
        if is_symlink:
            # zip stores symlink target as the file contents
            link_target = zf.read(zinfo).decode('utf-8', errors='ignore').strip()
            link_target_path = Path(link_target)
            if link_target_path.is_absolute():
                raise ValueError(f"Link points to absolute path: {link_target}")
                
            link_dir = (dest / name).parent
            resolved_target = (link_dir / link_target_path).resolve()
            if not is_relative_to(resolved_target, dest):
                raise ValueError(f"Link points outside destination: {link_target}")
                
    # If all members are valid, extract
    zf.extractall(str(dest))
