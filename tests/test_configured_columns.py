"""TGK Tools matches persisted layout profiles and native logical grid units."""
import contextlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tgk import config
from tgk_tools.cli import main


class ConfiguredColumnTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/"tgk-config"
        override=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        override.start();self.addCleanup(override.stop)
        config.clear_config_cache()
        self.addCleanup(config.clear_config_cache)
        config.initialize_config()

    def invoke(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=main(list(args))
        return code,out.getvalue(),err.getvalue()

    def test_saved_native_columns_are_used_in_layout_plan(self):
        config.update_settings({"layout":{"columns":6,"touch_target_dp":56,
                                         "grid_unit_dp":8}})
        code,out,err=self.invoke("layout-plan","--width-dp","950",
                                 "--height-dp","420","--items","3","--json")
        self.assertEqual(code,0,err)
        result=json.loads(out)
        self.assertEqual(result["grid"]["columns"],6)
        self.assertEqual(result["grid"]["span_units"],12)
        self.assertEqual(result["grid"]["touch_target_dp"],56)
        self.assertEqual(result["grid"]["unit_dp"],8)
        self.assertEqual([x["column"] for x in result["grid"]["items"]],[0,2,4])
        self.assertGreater(result["grid"]["column_width_dp"],0)
        self.assertGreaterEqual(result["grid"]["gutter_dp"],0)

    def test_flags_override_persistent_profile_without_overwriting_file(self):
        config.update_settings({"layout":{"columns":6,"touch_target_dp":56}})
        original=(self.root/"config.json").read_bytes()
        code,out,err=self.invoke(
            "layout-plan","--width-dp","700","--height-dp","800",
            "--columns","8","--span-units","8","--touch-target-dp","64",
            "--spans","8,4,3","--spans","8,4,3","--json")
        self.assertEqual(code,0,err)
        result=json.loads(out)
        self.assertEqual(result["grid"]["columns"],8)
        self.assertEqual(result["grid"]["span_units"],8)
        self.assertEqual(result["grid"]["touch_target_dp"],64)
        self.assertEqual([x["col_span"] for x in result["grid"]["items"]],[4,4])
        self.assertEqual(original,(self.root/"config.json").read_bytes())

    def test_adaptive_demo_inherits_option_profile_layout(self):
        config.update_config("ui","option_profile","accessibility_touch")
        captured={}
        def factory(**kwargs):
            captured.update(kwargs)
            return type("Demo",(),{"run":lambda self:None})()
        with patch("tgk.adaptive_demo.AdaptiveLab",side_effect=factory):
            code,_,err=self.invoke("adaptive-demo","--columns","4")
        self.assertEqual(code,0,err)
        scale=captured["layout_scale"]
        self.assertEqual(scale.columns,4)
        self.assertEqual(scale.touch_target_dp,64)
        self.assertEqual(scale.grid_unit_dp,8)

    def test_bad_columns_and_logical_spans_fail_as_usage_errors(self):
        cases=[
            ("--columns","0"),("--columns","33"),
            ("--span-units","0"),("--span-units","33"),
            ("--span-units","8","--spans","8,9,4"),
        ]
        for args in cases:
            with self.subTest(args=args):
                try:
                    code,out,err=self.invoke(
                        "layout-plan","--width-dp","393","--height-dp","852",*args)
                except SystemExit as exc:
                    self.assertEqual(exc.code,2)
                else:
                    self.assertEqual(code,2)
                    self.assertEqual(out,"")
                    self.assertTrue(err)


if __name__=="__main__":
    unittest.main()
