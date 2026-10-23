"""Reproducible TGK CPU microbenchmarks; no Android/native IPC or network."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import json
import math
import unittest

from tgk_tools.bench import benchmark
from tgk_tools.cli import main


class BenchmarkTests(unittest.TestCase):
    def test_small_json_run_reports_real_operations_without_hardware_claims(self):
        out=StringIO();err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=main(["benchmark","--nodes","4","--iterations","9",
                     "--samples","2","--json"])
        self.assertEqual(rc,0,err.getvalue())
        self.assertEqual(err.getvalue(),"")
        result=json.loads(out.getvalue())
        self.assertEqual(result["schema_version"],1)
        self.assertEqual(result["measurement_scope"],"python-only")
        self.assertFalse(result["native_android_ipc"])
        self.assertFalse(result["display_fps_measured"])
        self.assertFalse(result["hardware_touch_latency_measured"])
        self.assertEqual(result["configuration"]["nodes"],4)
        self.assertEqual(result["measurements"]["widget_walk"]["operations_per_sample"],45)
        for measurements in result["measurements"].values():
            self.assertEqual(measurements["samples"],2)
            self.assertGreaterEqual(measurements["median_ns_per_operation"],0)
            self.assertTrue(math.isfinite(measurements["p95_ns_per_operation"]))

    def test_odd_even_iteration_counts_preserve_style_invalidation(self):
        for iterations in (1,2,3,8):
            with self.subTest(iterations=iterations):
                data=benchmark(nodes=3,iterations=iterations,samples=3)
                self.assertEqual(
                    data["measurements"]["local_style_invalidation"]["operations_per_sample"],
                    iterations)

    def test_bounds_reject_unlimited_work(self):
        cases=[(0,1,1),(5001,1,1),(5,0,1),(1,10001,1),
               (10,10,0),(10,10,11),(5000,1000,2)]
        for nodes,iters,samples in cases:
            with self.subTest(nodes=nodes,iters=iters,samples=samples):
                with self.assertRaises(ValueError):
                    benchmark(nodes=nodes,iterations=iters,samples=samples)

    def test_cli_usage_rejects_oversized_request_without_benchmarking(self):
        with self.assertRaises(SystemExit) as exc:
            with redirect_stderr(StringIO()):
                main(["benchmark","--nodes","5000","--iterations","10000","--samples","10"])
        self.assertEqual(exc.exception.code,2)

    def test_human_output_disclaims_android_graphics_metrics(self):
        out=StringIO()
        with redirect_stdout(out):
            rc=main(["benchmark","--nodes","2","--iterations","3","--samples","1"])
        self.assertEqual(rc,0)
        self.assertIn("NOT Android graphics",out.getvalue())
        self.assertIn("bounded_clock_callbacks",out.getvalue())


if __name__=="__main__":
    unittest.main()
