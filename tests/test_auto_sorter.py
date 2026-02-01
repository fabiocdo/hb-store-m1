import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.modules.auto_sorter import AutoSorter
from tests.fixtures import SFO_GAME, SFO_DLC, SFO_UPDATE, SFO_SAVE, SFO_UNKNOWN

class TestAutoSorter(unittest.TestCase):
    def setUp(self):
        self.default_sorter = AutoSorter()

    def test_init_defaults(self):
        sorter = AutoSorter()
        expected_map = {
            "ac": "dlc",
            "gc": "game",
            "gd": "game",
            "gp": "update",
            "sd": "save",
        }
        self.assertEqual(sorter.category_map, expected_map)

    def test_init_custom(self):
        custom_map = {"gd": "juegos"}
        sorter = AutoSorter(category_map=custom_map)
        self.assertEqual(sorter.category_map, custom_map)

    def test_dry_run_basic(self):
        pkg_path = Path("/data/pkg/game.pkg")
        category = "gd"
        expected = Path("/data/pkg/game/game.pkg")
        self.assertEqual(self.default_sorter.dry_run(pkg_path, category), expected)

    def test_dry_run_all_fixtures(self):
        pkg_path = Path("/data/pkg/file.pkg")
        fixtures = [
            (SFO_GAME["category"], Path("/data/pkg/game/file.pkg")),
            (SFO_DLC["category"], Path("/data/pkg/dlc/file.pkg")),
            (SFO_UPDATE["category"], Path("/data/pkg/update/file.pkg")),
            (SFO_SAVE["category"], Path("/data/pkg/save/file.pkg")),
            (SFO_UNKNOWN["category"], Path("/data/pkg/_unknown/file.pkg")),
        ]
        for category, expected in fixtures:
            with self.subTest(category=category):
                self.assertEqual(self.default_sorter.dry_run(pkg_path, category), expected)

    @patch("src.modules.auto_sorter.auto_sorter.Path.mkdir")
    @patch("src.modules.auto_sorter.auto_sorter.Path.rename")
    def test_run_moves_file(self, mock_rename, mock_mkdir):
        pkg_path = MagicMock(spec=Path)
        pkg_path.name = "my_game.pkg"
        pkg_path.parent = Path("/data/pkg")
        pkg_path.__eq__.side_effect = lambda other: str(pkg_path) == str(other)
        
        target_path = Path("/data/pkg/game/my_game.pkg")
        
        # We need to mock dry_run to return our controlled target_path
        with patch.object(AutoSorter, 'dry_run', return_value=target_path):
            result = self.default_sorter.run(pkg_path, "gd")
            
            self.assertEqual(result, str(target_path))
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
            pkg_path.rename.assert_called_once_with(target_path)

    def test_run_no_move_needed(self):
        # File is already in the correct folder
        pkg_path = Path("/data/pkg/game/my_game.pkg")
        result = self.default_sorter.run(pkg_path, "gd")
        
        self.assertIsNone(result)

    @patch("src.modules.auto_sorter.auto_sorter.Path.mkdir")
    def test_run_error_handling(self, mock_mkdir):
        pkg_path = MagicMock(spec=Path)
        pkg_path.name = "error.pkg"
        pkg_path.parent = Path("/data/pkg")
        pkg_path.__eq__.return_value = False
        
        # Ensure exists() returns False so it doesn't trigger conflict logic
        pkg_path.exists.return_value = False
        
        mock_mkdir.side_effect = Exception("Permission Denied")
        
        # Mock dry_run to return a path
        target_path = Path("/data/pkg/game/error.pkg")
        with patch.object(AutoSorter, 'dry_run', return_value=target_path):
            # Mock error_path
            mock_error_path = MagicMock(spec=Path)
            with patch("src.modules.auto_sorter.auto_sorter.Path", return_value=mock_error_path):
                sorter = AutoSorter(error_path="/data/_errors")
                result = sorter.run(pkg_path, "gd")
                
                self.assertIsNone(result)
                mock_error_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                # Should have been moved to errors folder due to exception
                pkg_path.rename.assert_called_with(mock_error_path / "error.pkg")

    def test_run_conflict_handling(self):
        pkg_path = MagicMock(spec=Path)
        pkg_path.name = "conflict.pkg"
        pkg_path.parent = Path("/data/pkg")
        pkg_path.__eq__.return_value = False
        
        # Conflict is now detected in dry_run
        with patch.object(AutoSorter, 'dry_run', return_value=None):
            result = self.default_sorter.run(pkg_path, "gd")
            
            self.assertIsNone(result)
            pkg_path.rename.assert_not_called()

if __name__ == "__main__":
    unittest.main()
