"""TGK Tools persistent config behavior, stdout contracts and CLI precedence."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from tgk import config
from tgk.theme import get_theme,_active_theme
from tgk.typography import get_text_style,_active
from tgk_tools.cli import main


class PersistentCLIConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir=Path(self.tmp.name)/"my-config"
        env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.dir)})
        env.start()
        self.addCleanup(env.stop)
        token_theme=_active_theme.set(None)
        token_text=_active.set(None)
        self.addCleanup(lambda:_active_theme.reset(token_theme))
        self.addCleanup(lambda:_active.reset(token_text))
        config.clear_cache()
        self.addCleanup(config.clear_cache)

    def command(self,*tokens):
        out=StringIO()
        err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            result=main(list(tokens))
        return result,out.getvalue(),err.getvalue()

    def edit(self,name,modify):
        file=config.paths()[name]
        data=json.loads(file.read_text("utf-8"))
        modify(data)
        file.write_text(json.dumps(data),encoding="utf-8")
        config.clear_cache()

    def test_config_init_preserves_customized_defaults(self):
        code,output,error=self.command("config","init","--json")
        self.assertEqual((code,error),(0,""))
        self.assertTrue(all(json.loads(output)["created"].values()))
        self.edit("config",lambda d:d["defaults"].update(palette="ocean",typography="title_h2"))
        code,output,error=self.command("config","init","--json")
        self.assertEqual(code,0,error)
        self.assertFalse(any(json.loads(output)["created"].values()))
        self.assertEqual(config.settings()["defaults"]["palette"],"ocean")
        code,output,error=self.command("config","validate","--json")
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(output)["default_palette"],"ocean")

    def test_active_themes_and_typography_inherit_file_defaults(self):
        config.init_config()
        self.edit("config",lambda d:d["defaults"].update(palette="forest",typography="title_h1"))
        code,output,error=self.command("themes","--json")
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(output)["default"],"forest")
        code,output,error=self.command("typography","--json")
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(output)["default"],"title_h1")
        self.assertEqual(get_text_style().size,32)
        self.assertEqual(get_theme().name,"forest")

    def test_explicit_theme_and_font_flags_win(self):
        config.init_config()
        self.edit("config",lambda d:d["defaults"].update(palette="paper",typography="caption"))
        code,output,error=self.command("style-catalog","--theme","ocean",
                                       "--text-style","title_h5","--json")
        self.assertEqual(code,0,error)
        self.assertEqual(json.loads(output)["theme"],"ocean")
        self.assertEqual(get_text_style().size,18)

    def test_layout_plan_uses_configured_touch_and_grid_when_flags_omitted(self):
        config.init_config()
        self.edit("config",lambda d:d["ui"]["layout_overrides"].update(
            touch_target_dp=60,grid_unit_dp=8))
        code,out,err=self.command("layout-plan","--width-dp","393","--height-dp","852",
                                  "--json")
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data["grid"]["touch_target_dp"],60)
        self.assertEqual(data["grid"]["unit_dp"],8)
        code,out,err=self.command("layout-plan","--width-dp","393","--height-dp","852",
                                  "--touch-target-dp","52","--grid-unit-dp","4","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["grid"]["touch_target_dp"],52)
        self.assertEqual(json.loads(out)["grid"]["unit_dp"],4)

    def test_invalid_configuration_reports_usage_without_partial_output(self):
        config.init_config()
        config.paths()["config"].write_text('{"schema_version":27}',encoding="utf-8")
        config.clear_cache()
        code,out,err=self.command("config","validate","--json")
        self.assertEqual(code,2)
        self.assertEqual(out,"")
        self.assertIn("schema",err)

    def test_config_paths_available_before_install(self):
        code,out,err=self.command("config","paths","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["root"],str(self.dir))
        self.assertFalse(self.dir.exists())


if __name__=="__main__":
    unittest.main()
