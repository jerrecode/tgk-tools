"""TGK Tools honors persisted JSON defaults and explicit flag precedence."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tgk.config import DEFAULT_CONFIG,initialize_config
from tgk.theme import _active_theme
from tgk.typography import _active
from tgk_tools.cli import main


class ConfigCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)/"tgk-user"
        self.env=patch.dict(os.environ,{"TGK_CONFIG_HOME":str(self.home)})
        self.env.start()
        self.addCleanup(self.env.stop)
        token_theme=_active_theme.set(None)
        token_font=_active.set(None)
        self.addCleanup(lambda:_active_theme.reset(token_theme))
        self.addCleanup(lambda:_active.reset(token_font))

    def run_cmd(self,*args):
        out=io.StringIO();err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            code=main(list(args))
        return code,out.getvalue(),err.getvalue()

    def test_config_commands_work_before_initialization(self):
        code,out,err=self.run_cmd("config","path","--compact")
        self.assertEqual(code,0,err)
        self.assertFalse(self.home.exists())
        self.assertEqual(json.loads(out)["config_path"],str(self.home/"config.json"))
        code,out,err=self.run_cmd("config","init","--compact")
        self.assertEqual(code,0,err)
        result=json.loads(out)
        self.assertGreater(result["total"],35)
        code,out,err=self.run_cmd("config","validate","--compact")
        self.assertEqual(code,0,err)
        self.assertTrue(json.loads(out)["valid"])
        code,out,err=self.run_cmd("config","palette","ocean","--compact")
        self.assertEqual(code,0,err)
        self.assertIn("accent",json.loads(out)["colors"])
        code,out,err=self.run_cmd("config","typography","body","--compact")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["style"]["size"],16)
        code,out,err=self.run_cmd("config","options","battery_saver","--compact")
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["settings"]["io"]["workers"],1)

    def test_saved_defaults_apply_without_flags_but_explicit_flags_win(self):
        initialize_config()
        settings=json.loads((self.home/"config.json").read_text())
        settings["ui"].update({"theme":"ocean","text_style":"title_h1"})
        settings["tools"]["max_file_items"]=30
        settings["tools"]["canvas_fps"]=12
        settings["tools"]["max_progress_json_bytes"]=123456
        settings["icons"].update({"low":24,"mid":72,"high":192})
        (self.home/"config.json").write_text(json.dumps(settings))
        captured={}
        def capture_files(args):
            captured["file_limit"]=args.max_items
            from tgk.theme import get_theme
            from tgk.typography import get_text_style
            captured["theme"]=get_theme().name
            captured["font_size"]=get_text_style().size
            return 0
        with patch("tgk_tools.cli.run_files",side_effect=capture_files):
            self.assertEqual(self.run_cmd("files")[0],0)
            self.assertEqual(self.run_cmd("files","--max-items","67",
                                          "--theme","paper",
                                          "--text-style","caption")[0],0)
        self.assertEqual(captured["file_limit"],67)
        self.assertEqual(captured["theme"],"paper")
        self.assertEqual(captured["font_size"],12)
        with patch("tgk_tools.cli.run_files",side_effect=capture_files):
            self.assertEqual(self.run_cmd("files")[0],0)
        self.assertEqual(captured["file_limit"],30)
        self.assertEqual(captured["theme"],"ocean")
        self.assertEqual(captured["font_size"],32)
        with patch("tgk_tools.cli.run_canvas",side_effect=lambda args:captured.update(fps=args.fps) or 0):
            self.assertEqual(self.run_cmd("canvas-demo","--seconds","1")[0],0)
        self.assertEqual(captured["fps"],12)
        with patch("tgk_tools.cli.run_progress",side_effect=lambda args:captured.update(progress_limit=args.max_progress_json_bytes) or 0):
            self.assertEqual(self.run_cmd("progress","missing.json")[0],0)
        self.assertEqual(captured["progress_limit"],123456)

    def test_reinstall_preserves_settings_and_invalid_profile_is_safe(self):
        self.assertEqual(self.run_cmd("config","init")[0],0)
        custom=self.home/"palettes"/"midnight.json"
        custom.write_text('{"theme":"midnight","colors":{"accent":"#33EE44"}}')
        self.assertEqual(self.run_cmd("config","init")[0],0)
        self.assertIn("#33EE44",custom.read_text())
        status,out,error=self.run_cmd("config","palette","../not-allowed")
        self.assertEqual(status,2)
        self.assertEqual(out,"")
        self.assertIn("lowercase",error)

    def test_option_selection_persists_profile_name_and_keeps_custom_fields(self):
        initialize_config()
        from tgk.config import update_config,load_config
        update_config("io","workers",6)
        status,out,error=self.run_cmd("config","set","--options","battery_saver",
                                      "--palette","ocean","--compact")
        self.assertEqual(status,0,error)
        selected=json.loads(out)
        self.assertEqual(selected["settings"]["ui"]["option_profile"],"battery_saver")
        self.assertEqual(selected["settings"]["ui"]["theme"],"ocean")
        self.assertEqual(selected["settings"]["io"]["workers"],6)
        self.assertEqual(selected["settings"]["runtime"]["clock_callbacks_per_tick"],48)
        raw=json.loads((self.home/"config.json").read_text())
        self.assertEqual(raw["ui"]["option_profile"],"battery_saver")
        self.assertEqual(raw["io"]["workers"],6)
        self.assertEqual(load_config()["runtime"]["clock_callbacks_per_tick"],48)

    def test_config_set_is_one_transaction_and_rollback_on_invalid_choice(self):
        initialize_config()
        old=(self.home/"config.json").read_bytes()
        code,out,err=self.run_cmd("config","set","--palette","not_a_palette")
        self.assertEqual(code,2)
        self.assertEqual(out,"")
        self.assertTrue(err)
        self.assertEqual((self.home/"config.json").read_bytes(),old)
        code,out,err=self.run_cmd("config","set","--orientation","landscape",
                                  "--window-mode","dialog","--compact")
        self.assertEqual(code,0,err)
        selected=json.loads(out)["settings"]
        self.assertEqual(selected["ui"]["orientation"],"landscape")
        self.assertEqual(selected["ui"]["window_mode"],"dialog")

    def test_corrupt_config_allows_init_recovery_and_fails_other_commands(self):
        initialize_config()
        (self.home/"config.json").write_text("{ not-json",encoding="utf-8")
        code,out,err=self.run_cmd("config","init")
        self.assertEqual(code,0,err)
        self.assertIn("preserved",out)
        code,out,err=self.run_cmd("files")
        self.assertEqual(code,2)
        self.assertEqual(out,"")
        self.assertTrue(err)


if __name__=="__main__":unittest.main()
