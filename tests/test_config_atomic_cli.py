"""Persistent TGK shell settings across profiles and explicit overrides."""
from contextlib import redirect_stderr,redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tgk.config import initialize_config,load_config,clear_config_cache
from tgk_tools.cli import main


class AtomicConfigCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/"config"
        self.env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.home)})
        self.env.start();self.addCleanup(self.env.stop)
        clear_config_cache();self.addCleanup(clear_config_cache)

    def cli(self,*args):
        out=StringIO();err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(["config",*args])
        return status,out.getvalue(),err.getvalue()

    def test_set_atomic_batch_and_explicit_profile_pin(self):
        status,out,err=self.cli("set","--palette","forest",
                                "--typography","terminal",
                                "--options","battery_saver")
        self.assertEqual(status,0,err)
        data=json.loads(out)["settings"]
        self.assertEqual(data["ui"]["theme"],"forest")
        self.assertEqual(data["ui"]["text_style"],"terminal")
        self.assertEqual(data["io"]["workers"],1)
        self.assertEqual(data["runtime"]["clock_callbacks_per_tick"],48)
        self.assertEqual(self.cli("edit","io","workers","2")[0],0)
        self.assertEqual(load_config()["io"]["workers"],2)
        self.assertIn("io.workers",load_config()["pinned"])
        self.assertEqual(self.cli("reset","io","workers")[0],0)
        self.assertEqual(load_config()["io"]["workers"],1)

    def test_quoted_string_and_boolean_edits(self):
        initialize_config()
        self.assertEqual(self.cli("edit","ui","theme","ocean")[0],0)
        self.assertEqual(self.cli("edit","icons","raster","false")[0],0)
        self.assertEqual(self.cli("edit","layout","touch_target_dp","64")[0],0)
        cfg=load_config()
        self.assertEqual(cfg["ui"]["theme"],"ocean")
        self.assertIs(cfg["icons"]["raster"],False)
        self.assertEqual(cfg["layout"]["touch_target_dp"],64)

    def test_rejected_transaction_does_not_change_files(self):
        initialize_config()
        before=(self.home/"config.json").read_bytes()
        status,out,err=self.cli("set","--palette","forest",
                                "--typography","nonexistent")
        self.assertEqual(status,2)
        self.assertEqual(out,"")
        self.assertTrue(err)
        self.assertEqual((self.home/"config.json").read_bytes(),before)
        status,out,err=self.cli("edit","io","workers","999")
        self.assertEqual(status,2)
        self.assertEqual(out,"")
        self.assertEqual((self.home/"config.json").read_bytes(),before)

    def test_create_only_reinstall_does_not_touch_preset_or_settings(self):
        initialize_config()
        file=self.home/"text_styles"/"body.json"
        file.write_text('{"style":"body","properties":{"size":19}}')
        self.cli("edit","ui","theme","paper")
        saved=(self.home/"config.json").read_bytes()
        self.cli("init")
        self.assertEqual(saved,(self.home/"config.json").read_bytes())
        self.assertEqual(json.loads(file.read_text())["properties"]["size"],19)

    def test_missing_positional_arguments_are_usage_errors(self):
        for args in (("edit","layout"),("edit","layout","touch_target_dp"),
                     ("reset","layout"),("reset","layout","touch_target_dp","99")):
            with self.subTest(args=args),self.assertRaises(SystemExit) as exc:
                with redirect_stderr(StringIO()):
                    main(["config",*args])
            self.assertEqual(exc.exception.code,2)


if __name__=="__main__":unittest.main()
