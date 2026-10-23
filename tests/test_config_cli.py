"""TGK Tools persistent config usage, precedence and validation."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import unittest

from tgk_tools.cli import main
from tgk.theme import _active_theme
from tgk.typography import _active


class ConfigCLITests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/"prefs"
        patcher=patch.dict(os.environ,{"TGK_CONFIG_DIR":str(self.root)})
        patcher.start();self.addCleanup(patcher.stop)
        t=_active_theme.set(None);self.addCleanup(lambda:_active_theme.reset(t))
        ty=_active.set(None);self.addCleanup(lambda:_active.reset(ty))

    def command(self,*arguments):
        out=StringIO();err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            code=main(list(arguments))
        return code,out.getvalue(),err.getvalue()

    def test_init_does_not_replace_user_content(self):
        code,out,err=self.command("config","init","--json")
        self.assertEqual(code,0,err)
        result=json.loads(out)
        self.assertEqual(result["created"],result["total"])
        path=self.root/"palettes/midnight.json"
        saved=path.read_bytes()
        code,out,_=self.command("config","init","--json")
        self.assertEqual(code,0)
        self.assertEqual(json.loads(out)["created"],0)
        self.assertEqual(path.read_bytes(),saved)

    def test_set_saved_theme_then_explicit_cli_override(self):
        self.command("config","init")
        code,out,err=self.command("config","set","defaults.theme","ocean","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["config"]["defaults"]["theme"],"ocean")
        # Config command never overrides per-process theme. Ordinary tools use
        # the saved selection unless a --theme flag is supplied.
        from tgk.theme import get_theme
        self.assertEqual(get_theme().name,"ocean")
        status,data,err=self.command("themes","--json")
        self.assertEqual(status,0,err)
        from tgk.theme import get_theme
        self.assertEqual(get_theme().name,"ocean")
        status,data,err=self.command("themes","--theme","paper","--json")
        self.assertEqual(status,0,err)
        self.assertEqual(get_theme().name,"paper")

    def test_font_default_and_numeric_value(self):
        self.command("config","init")
        rc,out,err=self.command("config","set","defaults.text_style","title_h2","--json")
        self.assertEqual(rc,0,err)
        from tgk.typography import get_text_style
        self.assertEqual(get_text_style().size,27)
        rc,out,err=self.command("config","set","layout.touch_target_dp","56","--json")
        self.assertEqual(rc,0,err)
        self.assertEqual(json.loads(out)["config"]["layout"]["touch_target_dp"],56)
        rc,out,err=self.command("config","show","--json")
        self.assertEqual(rc,0,err)
        self.assertEqual(json.loads(out)["config"]["layout"]["touch_target_dp"],56)

    def test_invalid_config_change_reports_error_without_mutation(self):
        self.command("config","init")
        before=(self.root/"config.json").read_bytes()
        rc,out,err=self.command("config","set","layout.columns","999")
        self.assertEqual(rc,2)
        self.assertFalse(out)
        self.assertIn("12 columns",err)
        self.assertEqual((self.root/"config.json").read_bytes(),before)

    def test_presets_contain_expected_roles_and_component_names(self):
        rc,out,err=self.command("config","presets","--json")
        self.assertEqual(rc,0,err)
        data=json.loads(out)
        self.assertIn("forest",data["palettes"])
        self.assertIn("title_h1",data["typography"])
        self.assertIn("table",data["components"])


if __name__=="__main__":
    unittest.main()
