"""Persisted settings govern layout, reporting, and atomic CLI edits."""
import contextlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tgk import config
from tgk.theme import _active_theme
from tgk.typography import _active
from tgk_tools.cli import main


class ConfigEditingTests(unittest.TestCase):
    def setUp(self):
        home=TemporaryDirectory();self.addCleanup(home.cleanup)
        self.root=Path(home.name)/"user"
        p=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        p.start();self.addCleanup(p.stop)
        old_t=_active_theme.set(None)
        old_f=_active.set(None)
        self.addCleanup(lambda:_active_theme.reset(old_t))
        self.addCleanup(lambda:_active.reset(old_f))
        config.clear_config_cache();self.addCleanup(config.clear_config_cache)
        config.initialize_config()

    def run_command(self,*argv):
        output=io.StringIO();errors=io.StringIO()
        with contextlib.redirect_stdout(output),contextlib.redirect_stderr(errors):
            code=main(list(argv))
        return code,output.getvalue(),errors.getvalue()

    def test_default_layout_plan_inherits_all_saved_parameters(self):
        config.patch_config({"layout":{"columns":6,"grid_unit_dp":8,
                                       "touch_target_dp":60,
                                       "compact_breakpoint_dp":750,
                                       "expanded_breakpoint_dp":1050}})
        code,out,err=self.run_command("layout-plan","--width-dp","700",
                                      "--height-dp","800","--items","4","--json")
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data["grid"]["columns"],6)
        self.assertEqual(data["grid"]["grid_unit_dp"] if "grid_unit_dp" in data["grid"] else data["grid"]["unit_dp"],8)
        self.assertEqual(data["grid"]["touch_target_dp"],60)
        # 700 dp is *compact* under the saved threshold 750, not medium
        # under the historical default 600.
        self.assertEqual(data["screen"]["size_class"],"compact")
        self.assertEqual([p["row"] for p in data["grid"]["items"]],[0,1,2,3])
        self.assertEqual([p["col_span"] for p in data["grid"]["items"]],[6]*4)

    def test_explicit_layout_flags_take_precedence_without_writing(self):
        config.patch_config({"layout":{"columns":6,"touch_target_dp":60}})
        before=(self.root/"config.json").read_bytes()
        code,out,err=self.run_command("layout-plan","--width-dp","850",
            "--height-dp","440","--columns","8","--touch-target-dp","72",
            "--items","3","--json")
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data["grid"]["columns"],8)
        self.assertEqual(data["grid"]["touch_target_dp"],72)
        self.assertEqual(before,(self.root/"config.json").read_bytes())

    def test_atomic_edit_and_reset_multiple_runtime_and_layout_fields(self):
        code,out,err=self.run_command("config","edit",
            "--field","runtime.clock_callbacks_per_tick=64",
            "--field","layout.touch_target_dp=56",
            "--field","io.workers=3","--compact")
        self.assertEqual(code,0,err)
        result=json.loads(out)
        self.assertEqual(result["settings"]["runtime"]["clock_callbacks_per_tick"],64)
        self.assertEqual(result["settings"]["layout"]["touch_target_dp"],56)
        self.assertEqual(result["settings"]["io"]["workers"],3)
        self.assertIn("layout.touch_target_dp",result["settings"]["pinned"])
        code,out,err=self.run_command("config","edit",
                                      "--reset-field","layout.touch_target_dp",
                                      "--compact")
        self.assertEqual(code,0,err)
        data=json.loads(out)["settings"]
        self.assertEqual(data["layout"]["touch_target_dp"],48)
        self.assertNotIn("layout.touch_target_dp",data["pinned"])
        self.assertEqual(data["runtime"]["clock_callbacks_per_tick"],64)

    def test_invalid_multi_field_transaction_rolls_back_everything(self):
        path=self.root/"config.json"
        before=path.read_bytes()
        code,out,err=self.run_command("config","edit",
            "--field","layout.touch_target_dp=52",
            "--field","io.workers=200",
            "--compact")
        self.assertEqual(code,2)
        self.assertFalse(out)
        self.assertTrue(err)
        self.assertEqual(path.read_bytes(),before)
        self.assertFalse(list(self.root.glob(".tgk-config-*")))

    def test_edit_reports_malformed_json_and_conflicting_resets(self):
        for argv in (
            ("--field","io.workers=nope"),
            ("--field","io.workers=2","--reset-field","io.workers"),
            ("--reset-field","not_valid"),
            ("--field","io.workers=2","--field","io.workers=3"),
        ):
            with self.subTest(argv=argv):
                result,out,err=self.run_command("config","edit",*argv)
                self.assertEqual(result,2)
                self.assertFalse(out)
                self.assertTrue(err)

    def test_listed_theme_and_text_defaults_reflect_saved_selection(self):
        config.patch_config({"ui":{"theme":"forest","text_style":"terminal"}})
        code,out,err=self.run_command("themes","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["default"],"forest")
        code,out,err=self.run_command("typography","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["default"],"terminal")
        code,out,err=self.run_command("typography","--text-style","title","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["default"],"title")


if __name__=="__main__":
    unittest.main()
