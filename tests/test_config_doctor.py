"""End-to-end diagnostics for install-created presets and config locking."""
from contextlib import redirect_stdout
from io import StringIO
import fcntl
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tgk import config
from tgk_tools.cli import main


class ConfigDoctorTests(unittest.TestCase):
    def setUp(self):
        temp=TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)/"tgk"
        env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        config.clear_config_cache()
        self.addCleanup(config.clear_config_cache)

    def run_doctor(self):
        out=StringIO()
        with redirect_stdout(out):status=main(["config","doctor","--compact"])
        return status,json.loads(out.getvalue())

    def test_new_install_reports_selection_and_all_presets(self):
        config.initialize_config()
        code,report=self.run_doctor()
        self.assertEqual(code,0,report)
        self.assertTrue(report["healthy"])
        self.assertEqual(report["checks"]["selected"]["theme"],"midnight")
        self.assertEqual(report["checks"]["selected"]["text_style"],"body")
        self.assertEqual(report["checks"]["write_lock"],"acquired")
        self.assertTrue(all(not x for x in report["checks"]["missing_default_presets"].values()))
        self.assertEqual(report["checks"]["config_file_mode"],"0o600")

    def test_uninitialized_install_returns_machine_readable_repair_hint(self):
        code,report=self.run_doctor()
        self.assertEqual(code,2)
        self.assertFalse(report["healthy"])
        self.assertIn("not initialized"," ".join(report["problems"]))
        self.assertEqual(report["checks"]["write_lock"],"not_checked")
        self.assertFalse(self.root.exists())
        self.assertEqual(report["repair_command"],"python -m tgk.config init")

    def test_broken_selected_palette_is_detected_without_overwriting_it(self):
        config.initialize_config()
        palette=self.root/"palettes"/"midnight.json"
        palette.write_text("not json",encoding="utf-8")
        snapshot=palette.read_bytes()
        code,report=self.run_doctor()
        self.assertEqual(code,2)
        self.assertFalse(report["healthy"])
        self.assertIn("invalid selected configuration",str(report["problems"]))
        self.assertEqual(palette.read_bytes(),snapshot)

    def test_in_use_lock_reports_contention_then_recovers(self):
        config.initialize_config()
        lock=self.root/".config.lock"
        with lock.open("w") as stream:
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
            code,report=self.run_doctor()
            self.assertEqual(code,2)
            self.assertEqual(report["checks"]["write_lock"],"busy")
            self.assertFalse(report["healthy"])
            fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        code,report=self.run_doctor()
        self.assertEqual(code,0,report)
        self.assertTrue(report["healthy"])


if __name__=="__main__":unittest.main()
