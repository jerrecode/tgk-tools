"""Installed preset files remain visible and selectable without rewriting them."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tgk import config
from tgk.theme import _active_theme, get_theme
from tgk.typography import _active, get_text_style
from tgk_tools.cli import main


class InstalledPresetCatalogTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "preferences"
        environment = patch.dict(os.environ, {"TGK_CONFIG_HOME": str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)
        token = _active_theme.set(None)
        font_token = _active.set(None)
        self.addCleanup(lambda: _active_theme.reset(token))
        self.addCleanup(lambda: _active.reset(font_token))
        config.clear_config_cache()
        self.addCleanup(config.clear_config_cache)

    def invoke(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                code = main(list(arguments))
            except SystemExit as exc:
                code = exc.code
        return code, output.getvalue(), errors.getvalue()

    def write_preset(self, folder, name, value):
        directory = self.root / folder
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (name + ".json")
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_theme_catalog_and_explicit_flag_use_edited_builtin(self):
        self.write_preset("palettes", "ocean", {
            "theme": "ocean", "colors": {"accent": "#123456"}})
        code, output, errors = self.invoke("themes", "--theme", "ocean", "--json")
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output)["presets"]["ocean"]["accent"], "#123456FF")
        self.assertEqual(get_theme()["accent"], "#123456FF")

    def test_custom_palette_is_listed_and_selectable_without_saving(self):
        path = self.write_preset("palettes", "custom_ocean", {
            "theme": "ocean", "colors": {"accent": "#123456"}})
        before = path.read_bytes()
        code, output, errors = self.invoke("themes", "--theme", "custom_ocean",
            "--color", "accent=#ABCDEF", "--json")
        self.assertEqual(code, 0, errors)
        data = json.loads(output)
        self.assertEqual(data["default"], "custom_ocean")
        self.assertEqual(data["presets"]["custom_ocean"]["accent"], "#123456FF")
        self.assertEqual(get_theme()["accent"], "#ABCDEFFF")
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / "config.json").exists())

    def test_typography_and_style_catalog_include_installed_definitions(self):
        self.write_preset("text_styles", "body", {
            "style": "body", "properties": {"size": 21}})
        self.write_preset("text_styles", "custom_mono", {
            "style": "terminal", "properties": {"size": 23}})
        for command, key in (("typography", "presets"), ("style-catalog", "typography")):
            with self.subTest(command=command):
                code, output, errors = self.invoke(command, "--json")
                self.assertEqual(code, 0, errors)
                styles = json.loads(output)[key]
                self.assertEqual(styles["body"]["size"], 21)
                self.assertEqual(styles["custom_mono"]["size"], 23)
                self.assertEqual(styles["custom_mono"]["family"], "mono")

    def test_explicit_custom_typography_allows_per_run_font_override(self):
        path = self.write_preset("text_styles", "custom_mono", {
            "style": "terminal", "properties": {"size": 23}})
        before = path.read_bytes()
        code, output, errors = self.invoke("typography", "--text-style", "custom_mono",
            "--font-size", "27", "--json")
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output)["default"], "custom_mono")
        self.assertEqual(get_text_style().size, 27)
        self.assertEqual(get_text_style().family, "mono")
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.root / "config.json").exists())

    def test_typography_previews_render_installed_edits_and_custom_presets(self):
        from tgk import RichTextLabel
        self.write_preset("text_styles", "body", {
            "style": "body", "properties": {"size": 21}})
        self.write_preset("text_styles", "custom_mono", {
            "style": "terminal", "properties": {"size": 23}})
        def samples(app):
            pending = [app.build()]
            while pending:
                widget = pending.pop()
                pending.extend(widget.children)
                if isinstance(widget, RichTextLabel):
                    shown[widget.text.split(":", 1)[0]] = widget
        for arguments in (("typography", "--preview"), ("ui-lab",)):
            with self.subTest(arguments=arguments):
                shown = {}
                with patch("tgk.App.run", autospec=True, side_effect=samples):
                    code, output, errors = self.invoke(*arguments)
                self.assertEqual(code, 0, errors)
                self.assertIn("custom_mono", shown)
                self.assertEqual(shown["custom_mono"].style.size, 23)
                self.assertEqual(shown["custom_mono"].style.family, "mono")
                self.assertEqual(shown["body"].style.size, 21)
                self.assertIn("custom_mono", shown["custom_mono"].html())

    def test_inactive_invalid_catalog_entry_reports_error_without_partial_json(self):
        self.write_preset("text_styles", "invalid_style", {
            "style": "body", "properties": {"size": 9999}})
        code, output, errors = self.invoke("typography", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertTrue(errors)

    def test_unknown_typography_property_is_a_clean_cli_error(self):
        self.write_preset("text_styles", "invalid_style", {
            "style": "body", "properties": {"unknown_property": 17}})
        for arguments in (("typography", "--text-style", "invalid_style", "--json"),
                          ("typography", "--json"), ("style-catalog", "--json")):
            with self.subTest(arguments=arguments):
                try:
                    code, output, errors = self.invoke(*arguments)
                except TypeError as exc:
                    self.fail("malformed preset leaked TypeError: " + str(exc))
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertTrue(errors)

    def test_malformed_palette_is_a_clean_catalog_and_selection_error(self):
        for document in ({"theme":[]},{"colors":[]},{"colors":None}):
            self.write_preset("palettes","invalid_palette",document)
            for arguments in (("themes","--json"),
                              ("themes","--theme","invalid_palette","--json")):
                with self.subTest(document=document,arguments=arguments):
                    code, output, errors=self.invoke(*arguments)
                    self.assertEqual(code,2)
                    self.assertEqual(output,"")
                    self.assertTrue(errors)

    def test_manually_corrupted_selected_typography_is_a_clean_error(self):
        config.initialize_config()
        path=self.write_preset("text_styles","custom",{
            "style":"body","properties":{"size":21}})
        config.patch_config({"ui":{"text_style":"custom"}})
        path.write_text('{"style":"body","properties":{"unknown_property":17}}')
        code,output,errors=self.invoke("typography","--json")
        self.assertEqual(code,2)
        self.assertEqual(output,"")
        self.assertTrue(errors)

    def test_catalog_rejects_symlinked_directory_and_nonregular_file(self):
        external = self.root.parent / "external"
        external.mkdir()
        self.root.mkdir()
        (self.root / "palettes").symlink_to(external, target_is_directory=True)
        code, output, errors = self.invoke("themes", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertTrue(errors)
        (self.root / "palettes").unlink()
        (self.root / "palettes").mkdir()
        os.mkfifo(self.root / "palettes" / "fifo.json")
        code, output, errors = self.invoke("themes", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertTrue(errors)

    def test_config_list_rejects_unsafe_names_and_obeys_scan_limit(self):
        self.write_preset("palettes", "Unsafe", {"theme": "ocean"})
        code, output, errors = self.invoke("config", "list")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertTrue(errors)
        (self.root / "palettes" / "Unsafe.json").unlink()
        self.write_preset("palettes", "one", {"theme": "ocean"})
        self.write_preset("palettes", "two", {"theme": "ocean"})
        code, output, errors = self.invoke("config", "list", "--max-files", "1")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("too many", errors)

    def test_catalog_rejects_linked_and_oversized_inactive_json(self):
        source = self.root.parent / "source.json"
        source.write_text('{"theme":"ocean"}', encoding="utf-8")
        directory = self.root / "palettes"
        directory.mkdir(parents=True)
        target = directory / "custom.json"
        for kind in ("symlink", "hardlink", "oversized"):
            with self.subTest(kind=kind):
                if kind == "symlink":
                    target.symlink_to(source)
                elif kind == "hardlink":
                    os.link(source, target)
                else:
                    target.write_bytes(b" " * (config.MAX_JSON_BYTES + 1))
                try:
                    code, output, errors = self.invoke("themes", "--json")
                    self.assertEqual(code, 2)
                    self.assertEqual(output, "")
                    self.assertTrue(errors)
                finally:
                    target.unlink()

    def test_catalog_scan_cap_also_bounds_unrelated_directory_entries(self):
        directory = self.root / "palettes"
        directory.mkdir(parents=True)
        for index in range(2001):
            (directory / ("ignored_" + str(index) + ".txt")).touch()
        code, output, errors = self.invoke("themes", "--json")
        self.assertEqual(code, 2)
        self.assertEqual(output, "")
        self.assertIn("too many", errors)

    def test_catalog_commands_do_not_initialize_missing_settings(self):
        for arguments in (("themes", "--json"), ("typography", "--json"),
                          ("style-catalog", "--json"), ("config", "list")):
            with self.subTest(arguments=arguments):
                code, output, errors = self.invoke(*arguments)
                self.assertEqual(code, 0, errors)
                self.assertIsInstance(json.loads(output), dict)
                self.assertFalse(self.root.exists())


if __name__ == "__main__":
    unittest.main()
