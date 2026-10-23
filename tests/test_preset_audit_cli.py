"""CLI-level validation of all active and inactive TGK preset files."""
import contextlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tgk.config import initialize_config,clear_config_cache
from tgk_tools.cli import main


class PresetAuditCLITests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/"tgk"
        env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        env.start();self.addCleanup(env.stop)
        clear_config_cache();self.addCleanup(clear_config_cache)
        initialize_config()

    def invoke(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            status=main(["config",*args])
        return status,out.getvalue(),err.getvalue()

    def test_full_audit_reports_all_installed_presets(self):
        code,out,err=self.invoke("audit","--compact")
        self.assertEqual(code,0,err)
        result=json.loads(out)
        self.assertTrue(result["valid"])
        self.assertGreater(result["counts"]["palettes"],8)
        self.assertGreater(result["counts"]["text_styles"],35)
        self.assertFalse(any(result["missing_builtins"].values()))

    def test_corrupt_inactive_style_is_found_without_changing_files(self):
        path=self.root/"text_styles"/"code.json"
        path.write_text('{"style":"code","properties":{"size":5000}}',encoding="utf-8")
        before=path.read_bytes()
        status,out,err=self.invoke("audit")
        self.assertEqual(status,2)
        self.assertFalse(out)
        self.assertTrue(err)
        self.assertEqual(path.read_bytes(),before)
        # Ordinary active-config validation remains separately available.
        self.assertEqual(self.invoke("validate")[0],0)

    def test_max_files_protects_slow_or_unbounded_scans(self):
        result,out,err=self.invoke("audit","--max-files","1")
        self.assertEqual(result,2)
        self.assertFalse(out)
        self.assertIn("too many",err)
        with self.assertRaises(SystemExit) as fail:
            with contextlib.redirect_stderr(io.StringIO()):
                main(["config","audit","--max-files","5001"])
        self.assertEqual(fail.exception.code,2)

    def test_missing_installed_preset_fails_strict_audit(self):
        (self.root/"options"/"balanced.json").unlink()
        result,out,err=self.invoke("audit")
        self.assertEqual(result,2)
        self.assertFalse(out)
        self.assertIn("missing built-in",err)


if __name__=="__main__":
    unittest.main()
