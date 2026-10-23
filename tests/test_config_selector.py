"""Regression for persistent preset selectors and non-snapshot option profiles."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import os
import unittest

from tgk_tools.cli import main
from tgk import config


class PersistentSelectorTests(unittest.TestCase):
    def setUp(self):
        tmp=TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)/"user_config"
        env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.root)})
        env.start()
        self.addCleanup(env.stop)
        config.clear_config_cache()
        self.addCleanup(config.clear_config_cache)
        config.initialize_config()

    def command(self,*args):
        buffer=StringIO()
        with redirect_stdout(buffer):
            status=main(["config",*args,"--compact"])
        self.assertEqual(status,0)
        return json.loads(buffer.getvalue())

    def test_switch_profiles_does_not_pin_snapshot_defaults(self):
        battery=self.command("set","--options","battery_saver")
        self.assertEqual(battery["settings"]["ui"]["option_profile"],"battery_saver")
        self.assertEqual(battery["settings"]["io"]["workers"],1)
        self.assertEqual(battery["settings"]["runtime"]["clock_callbacks_per_tick"],48)
        raw=json.loads((self.root/"config.json").read_text())
        self.assertEqual(raw["io"]["workers"],config.DEFAULT_CONFIG["io"]["workers"])
        self.assertEqual(raw["ui"]["option_profile"],"battery_saver")

        performance=self.command("set","--options","performance")
        self.assertEqual(performance["settings"]["io"]["workers"],4)
        self.assertEqual(performance["settings"]["runtime"]["clock_callbacks_per_tick"],256)
        self.assertEqual(performance["settings"]["ui"]["option_profile"],"performance")
        self.assertEqual(json.loads((self.root/"config.json").read_text())["io"]["workers"],2)

    def test_individual_edits_remain_pinned_across_profile_switch(self):
        file=self.root/"config.json"
        raw=json.loads(file.read_text())
        raw["io"]["pending"]=3
        file.write_text(json.dumps(raw),encoding="utf-8")
        config.clear_config_cache()
        out=self.command("set","--options","battery_saver")
        self.assertEqual(out["settings"]["io"]["pending"],3)
        out=self.command("set","--options","performance")
        self.assertEqual(out["settings"]["io"]["pending"],3)
        self.assertEqual(out["settings"]["io"]["workers"],4)

    def test_saved_palette_typography_orientation_and_window(self):
        out=self.command("set","--palette","ocean","--typography","title_h2",
                         "--orientation","landscape","--window-mode","dialog")
        ui=out["settings"]["ui"]
        self.assertEqual(ui["theme"],"ocean")
        self.assertEqual(ui["text_style"],"title_h2")
        self.assertEqual(ui["orientation"],"landscape")
        self.assertEqual(ui["window_mode"],"dialog")

    def test_unknown_profile_preserves_original_file(self):
        file=self.root/"config.json"
        before=file.read_bytes()
        from contextlib import redirect_stderr
        with redirect_stderr(StringIO()):
            status=main(["config","set","--options","missing_profile"])
        self.assertEqual(status,2)
        self.assertEqual(file.read_bytes(),before)


if __name__=="__main__":
    unittest.main()
