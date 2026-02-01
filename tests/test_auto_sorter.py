import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.modules.auto_sorter import AutoSorter


class TestAutoSorter(unittest.TestCase):
    def setUp(self):
        self.sorter = AutoSorter()

    def test_category_map(self):
        expected_map = {
            "ac": "dlc",
            "gc": "game",
            "gd": "game",
            "gp": "update",
            "sd": "save",
        }
        self.assertEqual(AutoSorter.CATEGORY_MAP, expected_map)

    @patch('src.modules.auto_sorter.settings')
    def test_dry_run_not_found(self, mock_settings):
        mock_settings.PKG_DIR = Path("/data/pkg")
        pkg = MagicMock(spec=Path)
        pkg.exists.return_value = False

        result, target_dir = self.sorter.dry_run(pkg, "gd")

        self.assertEqual(result, AutoSorter.PlanResult.NOT_FOUND)
        self.assertIsNone(target_dir)

    @patch('src.modules.auto_sorter.settings')
    def test_dry_run_skip(self, mock_settings):
        mock_settings.PKG_DIR = Path("/data/pkg")
        pkg = MagicMock(spec=Path)
        pkg.exists.return_value = True
        pkg.name = "game.pkg"
        pkg.parent = Path("/data/pkg/game")

        result, target_dir = self.sorter.dry_run(pkg, "gd")
        self.assertEqual(result, AutoSorter.PlanResult.SKIP)
        self.assertEqual(target_dir, Path("/data/pkg/game"))

    @patch('src.modules.auto_sorter.settings')
    def test_dry_run_conflict(self, mock_settings):
        mock_settings.PKG_DIR = Path("/data/pkg")
        pkg = MagicMock(spec=Path)
        pkg.exists.return_value = True
        pkg.name = "game.pkg"
        pkg.parent = Path("/data/pkg/other")

        with patch('pathlib.Path.exists', return_value=True):
            result, target_dir = self.sorter.dry_run(pkg, "gd")
            self.assertEqual(result, AutoSorter.PlanResult.CONFLICT)

    @patch('src.modules.auto_sorter.settings')
    def test_dry_run_ok(self, mock_settings):
        mock_settings.PKG_DIR = Path("/data/pkg")
        pkg = MagicMock(spec=Path)
        pkg.exists.return_value = True
        pkg.name = "game.pkg"
        pkg.parent = Path("/data/pkg/other")

        target_path = MagicMock(spec=Path)
        target_path.exists.return_value = False

        with patch('src.modules.auto_sorter.Path', return_value=target_path):
            result, _ = self.sorter.dry_run(pkg, "gd")
            self.assertEqual(result, AutoSorter.PlanResult.OK)

    @patch('src.modules.auto_sorter.settings')
    def test_run_not_found(self, mock_settings):
        pkg = MagicMock(spec=Path)
        with patch.object(AutoSorter, 'dry_run', return_value=(AutoSorter.PlanResult.NOT_FOUND, None)):
            result = self.sorter.run(pkg, "gd")
            self.assertIsNone(result)
            pkg.rename.assert_not_called()

    @patch('src.modules.auto_sorter.settings')
    def test_run_skip(self, mock_settings):
        pkg = MagicMock(spec=Path)
        target_dir = Path("/data/pkg/game")
        with patch.object(AutoSorter, 'dry_run', return_value=(AutoSorter.PlanResult.SKIP, target_dir)):
            result = self.sorter.run(pkg, "gd")
            self.assertIsNone(result)
            pkg.rename.assert_not_called()

    @patch('src.modules.auto_sorter.settings')
    def test_run_conflict_moves_to_errors(self, mock_settings):
        mock_settings.ERROR_DIR = MagicMock(spec=Path)
        pkg = MagicMock(spec=Path)
        pkg.name = "conflict.pkg"
        pkg.stem = "conflict"
        pkg.suffix = ".pkg"

        error_file = MagicMock(spec=Path)
        error_file.exists.return_value = False
        mock_settings.ERROR_DIR.__truediv__.return_value = error_file

        with patch.object(AutoSorter, 'dry_run', return_value=(AutoSorter.PlanResult.CONFLICT, Path("/data/pkg/game"))):
            result = self.sorter.run(pkg, "gd")
            self.assertIsNone(result)
            mock_settings.ERROR_DIR.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            pkg.rename.assert_called_once_with(error_file)

    @patch('src.modules.auto_sorter.settings')
    def test_run_ok_moves_successfully(self, mock_settings):
        pkg = MagicMock(spec=Path)
        pkg.name = "game.pkg"

        target_dir = MagicMock(spec=Path)
        target_dir.name = "game"
        target_path = MagicMock(spec=Path)
        target_dir.__truediv__.return_value = target_path

        with patch.object(AutoSorter, 'dry_run', return_value=(AutoSorter.PlanResult.OK, target_dir)):
            result = self.sorter.run(pkg, "gd")
            self.assertEqual(result, str(target_path))
            target_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)
            pkg.rename.assert_called_once_with(target_path)


if __name__ == "__main__":
    unittest.main()
