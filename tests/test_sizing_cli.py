"""Consistent grid layouts and viewport sizing from the shell frontend."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from unittest.mock import patch
from types import SimpleNamespace
import json
import unittest

from tgk_tools.cli import main


class SizingCLITests(unittest.TestCase):
    def cli(self,*args):
        out,err=StringIO(),StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(list(args))
        return status,out.getvalue(),err.getvalue()

    def test_explicit_physical_columns_with_logical_span_units(self):
        code,out,err=self.cli("layout-plan","--width-dp","393","--height-dp","852",
                              "--columns","8","--span-units","12",
                              "--spans","6,6,6","--spans","6,6,6","--json")
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data["grid"]["columns"],8)
        self.assertEqual(data["grid"]["span_units"],12)
        self.assertEqual([x["col_span"] for x in data["grid"]["items"]],[4,4])
        self.assertEqual([x["column"] for x in data["grid"]["items"]],[0,4])

    def test_custom_logical_units_and_invalid_spans(self):
        code,out,err=self.cli("layout-plan","--width-dp","720","--height-dp","980",
                              "--columns","8","--span-units","8",
                              "--spans","4,4,4","--spans","4,4,4","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["grid"]["items"][1]["column"],4)
        bad_code,bad_out,bad_err=self.cli("layout-plan","--width-dp","393",
                              "--height-dp","852","--span-units","8","--spans","9,4,3")
        self.assertEqual(bad_code,2)
        self.assertEqual(bad_out,"")
        self.assertIn("span",bad_err.lower())

    def test_size_plan_fraction_and_height_limit(self):
        code,out,err=self.cli("size-plan","--width-dp","393","--height-dp","852",
                              "--item-width-fraction",".5","--item-height-fraction",".5",
                              "--max-height-fraction",".2","--json")
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data["resolved"]["width_dp"],197)
        self.assertEqual(data["resolved"]["height_dp"],171)
        self.assertFalse(data["physical_display_metrics_verified"])
        self.assertIsNone(data["screen"]["max_refresh_hz"])

    def test_size_plan_maintains_touch_minima_and_aspect_ratio(self):
        code,out,err=self.cli("size-plan","--width-dp","393","--height-dp","852",
                              "--item-width-dp","120","--item-height-dp","240",
                              "--aspect-ratio","2","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["resolved"]["height_dp"],60)
        code,out,err=self.cli("size-plan","--width-dp","393","--height-dp","852",
                              "--item-width-dp","12","--interactive","--json")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["resolved"]["width_dp"],48)

    def test_invalid_conflicting_sizing_is_usage_error(self):
        code,out,err=self.cli("size-plan","--width-dp","393","--height-dp","852",
                              "--item-width-dp","120","--item-width-fraction",".5")
        self.assertEqual(code,2)
        self.assertEqual(out,"")
        self.assertIn("width_dp",err)

    def test_invalid_grid_columns_rejected_before_any_native_calls(self):
        with self.assertRaises(SystemExit) as exc:
            with redirect_stderr(StringIO()):
                main(["layout-plan","--width-dp","393","--height-dp","852",
                      "--columns","33"])
        self.assertEqual(exc.exception.code,2)

    def test_adaptive_demo_per_app_columns(self):
        from tgk.adaptive_demo import AdaptiveLab
        observed=[]
        def fake_run(self):
            observed.append(self.layout_scale.columns)
        with patch.object(AdaptiveLab,"run",fake_run):
            status,out,err=self.cli("adaptive-demo","--columns","8")
        self.assertEqual(status,0,err)
        self.assertEqual(observed,[8])


if __name__=="__main__":
    unittest.main()
