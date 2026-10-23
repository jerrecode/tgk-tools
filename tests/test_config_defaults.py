"""Persistent default selection and profiles against current TGK config API."""
import contextlib
import io
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tgk.config import config_home,load_config,initialize_config,DEFAULT_CONFIG
from tgk_tools.cli import main


class PersistentCLIConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"config"
        env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        env.start()
        self.addCleanup(env.stop)

    def run_cli(self,*arguments):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=main(["config",*arguments])
        return code,out.getvalue(),err.getvalue()

    def test_listing_and_default_selection_survives_reinstall(self):
        code,out,err=self.run_cli("init")
        self.assertEqual(code,0,err)
        listed=json.loads(self.run_cli("list")[1])
        self.assertIn("forest",listed["palettes"])
        self.assertIn("terminal",listed["typography"])
        self.assertIn("performance",listed["options"])
        self.assertEqual(self.run_cli("set","--palette","forest",
                         "--typography","terminal",
                         "--orientation","landscape")[0],0)
        config=load_config()
        self.assertEqual(config["ui"]["theme"],"forest")
        self.assertEqual(config["ui"]["text_style"],"terminal")
        self.assertEqual(config["ui"]["orientation"],"landscape")
        before=(self.root/"config.json").read_bytes()
        self.assertEqual(self.run_cli("init")[0],0)
        self.assertEqual((self.root/"config.json").read_bytes(),before)

    def test_profile_snapshot_configures_runtime_io_and_tool_fps(self):
        self.assertEqual(self.run_cli("set","--options","performance")[0],0)
        saved=load_config()
        self.assertEqual(saved["runtime"]["clock_callbacks_per_tick"],256)
        self.assertEqual(saved["io"]["workers"],4)
        self.assertEqual(saved["tools"]["canvas_fps"],60)
        self.assertEqual(self.run_cli("set","--options","battery_saver")[0],0)
        saved=load_config()
        self.assertEqual(saved["runtime"]["clock_callbacks_per_tick"],48)
        self.assertEqual(saved["io"]["workers"],1)
        self.assertEqual(saved["tools"]["canvas_fps"],20)

    def test_bad_names_are_rejected_without_overwriting(self):
        initialize_config()
        path=self.root/"config.json"
        original=path.read_bytes()
        for args in [("set","--palette","invalid"),
                     ("set","--typography","unknown"),
                     ("set","--options","../evil")]:
            status,out,err=self.run_cli(*args)
            self.assertEqual(status,2)
            self.assertEqual(out,"")
            self.assertTrue(err)
            self.assertEqual(path.read_bytes(),original)

    def test_commands_reject_unsupported_flag_combinations(self):
        for args in [("set",),("show","--palette","ocean"),
                     ("path","irrelevant")]:
            with self.subTest(args=args),self.assertRaises(SystemExit) as exc:
                with contextlib.redirect_stderr(io.StringIO()):
                    main(["config",*args])
            self.assertEqual(exc.exception.code,2)

    def test_symlink_not_overwritten(self):
        with TemporaryDirectory() as external:
            target=Path(external)/"user.json"
            target.write_text(json.dumps(DEFAULT_CONFIG))
            self.root.mkdir()
            (self.root/"config.json").symlink_to(target)
            status,out,err=self.run_cli("set","--palette","forest")
            self.assertEqual(status,2)
            self.assertIn("symlink",err.lower())
            self.assertEqual(json.loads(target.read_text())["ui"]["theme"],"midnight")


if __name__=="__main__":
    unittest.main()
