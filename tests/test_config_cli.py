"""TGK Tools persistent option selection, CLI precedence and no-overwrite."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tgk import config
from tgk.theme import get_theme,_active_theme
from tgk.typography import get_text_style,_active
from tgk_tools.cli import main


class ConfigCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"tgk_settings"
        env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        env.start();self.addCleanup(env.stop)
        theme_token=_active_theme.set(None);text_token=_active.set(None)
        self.addCleanup(lambda:_active_theme.reset(theme_token))
        self.addCleanup(lambda:_active.reset(text_token))
        config.clear_cache()
        self.addCleanup(config.clear_cache)

    def cli(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            status=main(list(args))
        return status,out.getvalue(),err.getvalue()

    def test_init_and_listing_are_json_serializable(self):
        status,out,err=self.cli("config","init","--json")
        self.assertEqual(status,0,err)
        result=json.loads(out)
        self.assertTrue(all(result["created"].values()))
        self.assertEqual(len(config.color_registry()),12)
        status,out,err=self.cli("config","list","--json")
        self.assertEqual(status,0,err)
        names=json.loads(out)
        self.assertIn("paper",names["palettes"])
        self.assertIn("terminal",names["typography"])
        self.assertIn("performance",names["options"])

    def test_defaults_persist_and_explicit_flags_win(self):
        self.cli("config","init","--json")
        status,out,err=self.cli("config","set","--palette","forest",
            "--typography","terminal","--options","accessible",
            "--orientation","landscape","--json")
        self.assertEqual(status,0,err)
        self.assertEqual(config.settings()["defaults"]["palette"],"forest")
        self.assertEqual(config.settings()["defaults"]["typography"],"terminal")
        self.assertEqual(config.layout_scale().touch_target_dp,56)
        _active_theme.set(None);_active.set(None)
        status,out,err=self.cli("themes","--json")
        self.assertEqual(status,0,err)
        self.assertEqual(get_theme().name,"forest")
        self.assertEqual(get_text_style().family,"mono")
        status,out,err=self.cli("themes","--theme","paper","--text-style","title_h2","--json")
        self.assertEqual(status,0,err)
        self.assertEqual(get_theme().name,"paper")
        self.assertEqual(get_text_style().size,27)
        self.assertEqual(config.settings()["defaults"]["palette"],"forest")

    def test_non_set_flags_are_usage_errors(self):
        for args in [
            ("config","show","--palette","paper"),
            ("config","set"),
        ]:
            with self.subTest(args=args),self.assertRaises(SystemExit) as exc:
                with contextlib.redirect_stderr(io.StringIO()):
                    main(list(args))
            self.assertEqual(exc.exception.code,2)

    def test_invalid_palette_reports_usage_error_without_overwrite(self):
        self.cli("config","init","--json")
        before=config.paths()["config"].read_bytes()
        status,out,err=self.cli("config","set","--palette","nonexistent")
        self.assertEqual(status,2)
        self.assertEqual(out,"")
        self.assertTrue(err)
        self.assertEqual(config.paths()["config"].read_bytes(),before)

    def test_reinstall_preserves_existing_preset_edits(self):
        self.cli("config","init","--json")
        paths=config.paths()
        values=json.loads(paths["colors"].read_text())
        values["palettes"]["paper"]["accent"]="#AB12EF"
        paths["colors"].write_text(json.dumps(values))
        config.clear_cache()
        status,out,err=self.cli("config","init","--json")
        self.assertEqual(status,0,err)
        self.assertFalse(any(json.loads(out)["created"].values()))
        self.assertEqual(config.color_registry()["paper"]["accent"],"#AB12EFFF")


if __name__=="__main__":
    unittest.main()
