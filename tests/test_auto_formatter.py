import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.modules.auto_formatter.auto_formatter import AutoFormatter
from tests.fixtures import SFO_GAME, SFO_DLC, SFO_UPDATE, SFO_SAVE, SFO_UNKNOWN

class TestAutoFormatter(unittest.TestCase):
    def setUp(self):
        self.default_formatter = AutoFormatter()

    def test_init_defaults(self):
        formatter = AutoFormatter()
        self.assertEqual(formatter.template, "{title} {title_id} {app_type}")
        self.assertIsNone(formatter.mode)

    def test_init_custom(self):
        formatter = AutoFormatter(template="{title}", mode="uppercase")
        self.assertEqual(formatter.template, "{title}")
        self.assertEqual(formatter.mode, "uppercase")

    def test_normalize_value_title_uppercase(self):
        formatter = AutoFormatter(mode="uppercase")
        self.assertEqual(formatter._normalize_value("title", "My Game"), "MY GAME")

    def test_normalize_value_title_lowercase(self):
        formatter = AutoFormatter(mode="lowercase")
        self.assertEqual(formatter._normalize_value("title", "My Game"), "my game")

    def test_normalize_value_title_capitalize(self):
        formatter = AutoFormatter(mode="capitalize")
        self.assertEqual(formatter._normalize_value("title", "my game"), "My Game")
        
    def test_normalize_value_title_capitalize_roman_numerals(self):
        formatter = AutoFormatter(mode="capitalize")
        # Test case provided in the issue description
        self.assertEqual(
            formatter._normalize_value("title", "final fantasy XII the zodiac age"),
            "Final Fantasy XII The Zodiac Age"
        )
        # Additional cases
        self.assertEqual(formatter._normalize_value("title", "resident evil III"), "Resident Evil III")
        self.assertEqual(formatter._normalize_value("title", "vincit omnia veritas"), "Vincit Omnia Veritas")

    def test_normalize_value_none(self):
        self.assertEqual(self.default_formatter._normalize_value("any", None), "")

    def test_normalize_value_other_key(self):
        self.assertEqual(self.default_formatter._normalize_value("title_id", "CUSA12345"), "CUSA12345")

    def test_dry_run_basic(self):
        sfo_data = SFO_GAME
        pkg_path = Path("Horizon.pkg")
        expected = "Horizon Zero Dawn CUSA01021 app.pkg"
        self.assertEqual(self.default_formatter.dry_run(pkg_path, sfo_data), expected)

    def test_dry_run_full_template(self):
        formatter = AutoFormatter(template="{title} [{title_id}] [{region}] [{app_type}] [{version}] [{category}] [{content_id}]")
        sfo_data = SFO_GAME
        pkg_path = Path("Horizon.pkg")
        expected = "Horizon Zero Dawn [CUSA01021] [US] [app] [01.00] [gd] [UP9000-CUSA01021_00-HORIZONZERODAWN1].pkg"
        self.assertEqual(formatter.dry_run(pkg_path, sfo_data), expected)

    def test_dry_run_missing_keys(self):
        # Template has {title} {title_id} {app_type}
        sfo_data = {"title": "My Game"}
        pkg_path = Path("old.pkg")
        # _SafeDict should return "" for missing keys
        # Template is "{title} {title_id} {app_type}"
        # Result of format_map: "My Game  "
        # .strip() -> "My Game"
        # .pkg -> "My Game.pkg"
        expected = "My Game.pkg"
        self.assertEqual(self.default_formatter.dry_run(pkg_path, sfo_data), expected)

    def test_dry_run_extra_keys(self):
        # Template doesn't use {version} or {category}
        sfo_data = {
            "title": "My Game",
            "title_id": "CUSA12345",
            "app_type": "app",
            "version": "1.00",
            "category": "gd"
        }
        pkg_path = Path("old.pkg")
        expected = "My Game CUSA12345 app.pkg"
        self.assertEqual(self.default_formatter.dry_run(pkg_path, sfo_data), expected)

    def test_dry_run_all_fixtures(self):
        # Test with all types of fixtures
        fixtures = [
            (SFO_GAME, "Horizon Zero Dawn CUSA01021 app.pkg"),
            (SFO_DLC, "The Frozen Wilds CUSA01021 addon.pkg"),
            (SFO_UPDATE, "Horizon Zero Dawn Update CUSA01021 patch.pkg"),
            (SFO_SAVE, "Horizon Zero Dawn Save Data CUSA01021 save.pkg"),
            (SFO_UNKNOWN, "Unknown Title XXXX00000 unknown.pkg"),
        ]
        pkg_path = Path("old.pkg")
        for sfo, expected in fixtures:
            with self.subTest(sfo=sfo):
                self.assertEqual(self.default_formatter.dry_run(pkg_path, sfo), expected)

    def test_dry_run_various_templates(self):
        sfo = SFO_GAME
        pkg_path = Path("old.pkg")
        templates = [
            ("{title_id}", "CUSA01021.pkg"),
            ("GAME_{title_id}_{region}", "GAME_CUSA01021_US.pkg"),
            ("[{category}] {title} v{version}", "[gd] Horizon Zero Dawn v01.00.pkg"),
            ("{content_id}", "UP9000-CUSA01021_00-HORIZONZERODAWN1.pkg"),
        ]
        for template, expected in templates:
            with self.subTest(template=template):
                formatter = AutoFormatter(template=template)
                self.assertEqual(formatter.dry_run(pkg_path, sfo), expected)

    def test_dry_run_template_with_special_chars(self):
        formatter = AutoFormatter(template="{title} @ {title_id} # {app_type}!")
        sfo = {"title": "Game", "title_id": "ID", "app_type": "app"}
        pkg_path = Path("old.pkg")
        # "Game @ ID # app!" + ".pkg"
        self.assertEqual(formatter.dry_run(pkg_path, sfo), "Game @ ID # app!.pkg")

    def test_normalize_value_numeric(self):
        # Ensure numbers are converted to string and don't crash the formatter
        self.assertEqual(self.default_formatter._normalize_value("version", 1.0), "1.0")
        self.assertEqual(self.default_formatter._normalize_value("title", 123), "123")
        
        # Test capitalize with numeric title (should still work as string)
        formatter = AutoFormatter(mode="capitalize")
        self.assertEqual(formatter._normalize_value("title", 123), "123")

    def test_dry_run_only_missing_keys(self):
        # If all keys in template are missing, it should return None after strip if empty
        formatter = AutoFormatter(template="{non_existent}")
        pkg_path = Path("old.pkg")
        self.assertIsNone(formatter.dry_run(pkg_path, {"title": "Something"}))

    def test_dry_run_stripping(self):
        formatter = AutoFormatter(template="  {title}  ")
        sfo_data = {"title": "My Game"}
        pkg_path = Path("old.pkg")
        self.assertEqual(formatter.dry_run(pkg_path, sfo_data), "My Game.pkg")

    def test_dry_run_no_data(self):
        pkg_path = Path("old.pkg")
        self.assertIsNone(self.default_formatter.dry_run(pkg_path, {}))
        self.assertIsNone(self.default_formatter.dry_run(pkg_path, None))

    def test_dry_run_custom_template(self):
        formatter = AutoFormatter(template="{title_id}-{title}")
        sfo_data = {"title": "My Game", "title_id": "CUSA12345"}
        pkg_path = Path("old.pkg")
        self.assertEqual(formatter.dry_run(pkg_path, sfo_data), "CUSA12345-My Game.pkg")

    def test_run_renames_file(self):
        sfo_data = {"title": "New Name", "title_id": "ID", "app_type": "type"}
        mock_pkg = MagicMock(spec=Path)
        mock_pkg.name = "old.pkg"
        
        mock_target = MagicMock(spec=Path)
        mock_target.exists.return_value = False
        mock_pkg.with_name.return_value = mock_target

        planned_name = "New Name ID type.pkg"
        # Since dry_run now calls exists(), we must patch it or use the mock_target's existence
        with patch.object(AutoFormatter, 'dry_run', return_value=planned_name):
            result = self.default_formatter.run(mock_pkg, sfo_data)

            self.assertEqual(result, planned_name)
            mock_pkg.rename.assert_called_once_with(mock_target)
            mock_pkg.with_name.assert_called_once_with(planned_name)

    def test_run_no_rename_needed(self):
        sfo_data = {"title": "Same", "title_id": "ID", "app_type": "type"}
        planned_name = "Same ID type.pkg"
        
        mock_pkg = MagicMock(spec=Path)
        mock_pkg.name = planned_name
        
        with patch.object(AutoFormatter, 'dry_run', return_value=planned_name):
            result = self.default_formatter.run(mock_pkg, sfo_data)

            self.assertIsNone(result)
            mock_pkg.rename.assert_not_called()

    def test_run_error_handling(self):
        sfo_data = {"title": "Error", "title_id": "ID", "app_type": "type"}
        mock_pkg = MagicMock(spec=Path)
        mock_pkg.name = "old.pkg"
        
        mock_target = MagicMock(spec=Path)
        mock_pkg.with_name.return_value = mock_target
        
        mock_pkg.rename.side_effect = Exception("Permission Denied")

        # Mock dry_run to return a name
        planned_name = "Error ID type.pkg"
        with patch.object(AutoFormatter, 'dry_run', return_value=planned_name):
            # Mock error_path
            mock_error_path = MagicMock(spec=Path)
            with patch("src.modules.auto_formatter.auto_formatter.Path", return_value=mock_error_path):
                formatter = AutoFormatter(error_path="/data/_errors")
                result = formatter.run(mock_pkg, sfo_data)
                
                self.assertIsNone(result)
                mock_error_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                # Should have been moved to errors folder due to exception
                mock_pkg.rename.assert_called_with(mock_error_path / "old.pkg")

    def test_run_conflict_handling(self):
        sfo_data = {"title": "Conflict", "title_id": "ID", "app_type": "type"}
        planned_name = "Conflict ID type.pkg"
        
        mock_pkg = MagicMock(spec=Path)
        mock_pkg.name = "old.pkg"
        
        # Conflict is now detected in dry_run
        with patch.object(AutoFormatter, 'dry_run', return_value=None):
            result = self.default_formatter.run(mock_pkg, sfo_data)
            
            self.assertIsNone(result)
            mock_pkg.rename.assert_not_called()

if __name__ == "__main__":
    unittest.main()
