"""SizeSpec CLI integration and saved touch-target defaults."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from tgk import config
from tgk_tools.cli import main


class SizePlanCLITests(unittest.TestCase):
    def setUp(self):
        folder=TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        home=Path(folder.name)/"tgk"
        self.override=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(home)})
        self.override.start();self.addCleanup(self.override.stop)
        config.clear_config_cache();self.addCleanup(config.clear_config_cache)
        config.initialize_config()
        self.home=home

    def cli(self,*args):
        out=StringIO();err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            result=main(list(args))
        return result,out.getvalue(),err.getvalue()

    def test_window_fraction_and_independent_height_cap(self):
        status,out,err=self.cli(
            "size-plan","--width-dp","393","--height-dp","852",
            "--item-width-fraction",".5","--item-height-fraction",".5",
            "--max-height-fraction",".2","--json")
        self.assertEqual(status,0,err)
        doc=json.loads(out)
        self.assertEqual(doc["resolved"]["width_dp"],197)
        self.assertEqual(doc["resolved"]["height_dp"],171)
        self.assertFalse(doc["physical_display_metrics_verified"])
        self.assertIsNone(doc["screen"]["max_refresh_hz"])

    def test_ratio_and_known_insets(self):
        status,out,err=self.cli(
            "size-plan","--width-dp","393","--height-dp","852",
            "--item-width-dp","120","--item-height-dp","240",
            "--aspect-ratio","2","--json")
        self.assertEqual(status,0,err)
        self.assertEqual(json.loads(out)["resolved"]["height_dp"],60)
        status,out,err=self.cli(
            "size-plan","--width-dp","393","--height-dp","852",
            "--item-height-fraction","1","--inset-top-dp","24",
            "--inset-bottom-dp","30","--json")
        self.assertEqual(status,0,err)
        self.assertEqual(json.loads(out)["resolved"]["height_dp"],798)

    def test_saved_touch_target_and_explicit_override(self):
        config.update_config("ui","option_profile","accessibility_touch")
        saved=(self.home/"config.json").read_bytes()
        args=("size-plan","--width-dp","393","--height-dp","852",
              "--item-width-dp","24","--item-height-dp","12","--interactive",
              "--json")
        status,out,err=self.cli(*args)
        self.assertEqual(status,0,err)
        first=json.loads(out)
        self.assertEqual(first["touch_target_dp"],64)
        self.assertEqual(first["resolved"]["width_dp"],64)
        self.assertEqual(first["resolved"]["height_dp"],64)
        status,out,err=self.cli(*args,"--touch-target-dp","80")
        self.assertEqual(status,0,err)
        self.assertEqual(json.loads(out)["resolved"]["width_dp"],80)
        self.assertEqual(saved,(self.home/"config.json").read_bytes())

    def test_invalid_spec_does_not_emit_json(self):
        cases=(
            ("--item-width-fraction","1.5"),
            ("--item-width-fraction",".5","--item-width-dp","80"),
            ("--min-width-dp","100","--max-width-dp","80"),
            ("--aspect-ratio","nan"),
            ("--inset-top-dp","-2"),
        )
        for flags in cases:
            with self.subTest(flags=flags):
                status,out,err=self.cli("size-plan","--width-dp","393",
                                        "--height-dp","852",*flags,"--json")
                self.assertEqual(status,2)
                self.assertEqual(out,"")
                self.assertTrue(err)

    def test_default_output_preserves_native_intrinsic_dimensions(self):
        status,out,err=self.cli("size-plan","--width-dp","393",
                                "--height-dp","852","--json")
        self.assertEqual(status,0,err)
        self.assertIsNone(json.loads(out)["resolved"]["width_dp"])
        self.assertIsNone(json.loads(out)["resolved"]["height_dp"])


if __name__=="__main__":
    unittest.main()
