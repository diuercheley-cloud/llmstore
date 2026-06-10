import os

import pytest

from scripts.llm_harness.workspace import Workspace


class TestWorkspace:
    @pytest.mark.asyncio
    async def test_creates_temp_dir(self, tmp_path):
        async with Workspace(base_path=str(tmp_path)) as ws:
            assert os.path.isdir(ws.path)

    @pytest.mark.asyncio
    async def test_write_and_read_file(self, tmp_path):
        async with Workspace(base_path=str(tmp_path)) as ws:
            ws.write_file("test.txt", "hello world")
            content = ws.read_file("test.txt")
            assert content == "hello world"

    @pytest.mark.asyncio
    async def test_get_path_blocks_traversal(self, tmp_path):
        async with Workspace(base_path=str(tmp_path)) as ws:
            with pytest.raises(PermissionError, match="escapes"):
                ws.get_path("../../etc/passwd")

    @pytest.mark.asyncio
    async def test_get_path_blocks_absolute(self, tmp_path):
        async with Workspace(base_path=str(tmp_path)) as ws:
            with pytest.raises(PermissionError, match="escapes"):
                ws.get_path("/etc/passwd")

    @pytest.mark.asyncio
    async def test_get_path_allows_valid_subpath(self, tmp_path):
        async with Workspace(base_path=str(tmp_path)) as ws:
            path = ws.get_path("src/main.py")
            assert path.startswith(ws.path)

    @pytest.mark.asyncio
    async def test_write_creates_subdirs(self, tmp_path):
        async with Workspace(base_path=str(tmp_path)) as ws:
            ws.write_file("deep/nested/file.txt", "content")
            content = ws.read_file("deep/nested/file.txt")
            assert content == "content"

    @pytest.mark.asyncio
    async def test_cleanup_on_exit(self):
        """Workspace without base_path should create and cleanup temp dir."""
        ws = Workspace()
        async with ws:
            temp_path = ws.path
            assert os.path.isdir(temp_path)
        # After exit, temp dir should be cleaned up
        assert not os.path.exists(temp_path)

    @pytest.mark.asyncio
    async def test_no_cleanup_with_base_path(self, tmp_path):
        """Workspace with base_path should NOT cleanup on exit."""
        ws_path = str(tmp_path)
        async with Workspace(base_path=ws_path) as ws:
            ws.write_file("test.txt", "hello")
        # Directory should still exist
        assert os.path.isdir(ws_path)
