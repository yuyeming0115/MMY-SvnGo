import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.file_comparator import FileComparator
from src.core.file_scanner import FileScanner
from src.core.svn_manager import SVNManager
from src.models.file_info import FileInfo, FileStatus


class CoreLogicTest(unittest.TestCase):
    def test_svn_newer_wins_over_size_difference(self):
        local = FileInfo(
            path="local/a.png",
            name="a.png",
            size=10,
            modify_time=datetime(2026, 1, 1),
            relative_path="a.png",
        )
        svn = FileInfo(
            path="svn/a.png",
            name="a.png",
            size=20,
            modify_time=datetime(2026, 1, 2),
            relative_path="a.png",
        )

        self.assertEqual(FileComparator().compare_file(local, svn), FileStatus.SVN_NEWER)

    def test_image_dimension_cache_uses_file_identity(self):
        FileScanner._dimension_cache.clear()
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "a.png"
            Image.new("RGBA", (8, 6), (0, 0, 0, 0)).save(image_path)

            scanner = FileScanner()
            self.assertEqual(scanner.get_image_dimensions(image_path), (8, 6))
            self.assertGreaterEqual(len(FileScanner._dimension_cache), 1)
            self.assertEqual(scanner.get_image_dimensions(image_path), (8, 6))

    def test_svn_add_uses_parents(self):
        calls = []

        def fake_run(cmd, **kwargs):
            calls.append(cmd)
            return SimpleNamespace(returncode=0, stderr="")

        with patch("src.core.svn_manager.subprocess.run", fake_run):
            self.assertTrue(SVNManager().add_files([Path("folder/new_file.png")]))

        self.assertIn("--parents", calls[0])

    def test_svn_tool_status_reports_cli_and_tortoise(self):
        manager = SVNManager()
        manager.tortoise_available = True

        with patch("src.core.svn_manager.shutil.which", return_value="C:/svn/svn.exe"):
            status = manager.get_tool_status()

        self.assertTrue(status["svn_cli"])
        self.assertTrue(status["tortoise"])
        self.assertIn("tortoise_path", status)


if __name__ == "__main__":
    unittest.main()
