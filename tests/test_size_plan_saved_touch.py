"""Tests for saved touch presets, explicit overrides, measured system insets."""
import json
import os
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from tgk_tools.cli import main
from tgk.config import initialize_config,patch_config,clear_config_cache

class SizePlanSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config_patch=patch.dict(os.environ,{'TGK_CONFIG_HOME':self.temp.name})
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        initialize_config()
        patch_config({'layout':{'touch_target_dp':64}})
        self.addCleanup(clear_config_cache)

    def run_plan(self,*options):
        stdout=StringIO();stderr=StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            status=main(['size-plan','--width-dp','393','--height-dp','852',
                         '--item-width-dp','44','--item-height-dp','30',
                         '--interactive','--json',*options])
        return status,stdout.getvalue(),stderr.getvalue()

    def test_saved_touch_minimum_used_without_flag(self):
        code,out,err=self.run_plan()
        self.assertEqual(code,0,err)
        payload=json.loads(out)
        self.assertEqual(payload['touch_target_dp_effective'],64)
        self.assertEqual(payload['resolved']['height_dp'],64)
        self.assertEqual(payload['resolved']['width_dp'],64)
        self.assertFalse(payload['physical_display_metrics_verified'])

    def test_explicit_flag_overrides_persisted_config_only_for_this_call(self):
        code,out,err=self.run_plan('--touch-target-dp','80')
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)['resolved']['height_dp'],80)
        code,out,err=self.run_plan()
        self.assertEqual(json.loads(out)['touch_target_dp_effective'],64)

    def test_only_explicit_insets_reduce_available_content_height(self):
        code,out,err=self.run_plan('--inset-top-dp','24','--inset-bottom-dp','32')
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data['screen']['inset_top_dp'],24)
        self.assertEqual(data['screen']['inset_bottom_dp'],32)
        self.assertEqual(data['resolved']['available_height_dp'],796)
        code,out,err=self.run_plan()
        self.assertIsNone(json.loads(out)['screen']['inset_top_dp'])
        self.assertEqual(json.loads(out)['resolved']['available_height_dp'],852)

    def test_invalid_insets_and_minimums_have_no_json_output(self):
        for args in [('--inset-top-dp','-3'),('--inset-bottom-dp','nan'),
                     ('--touch-target-dp','20'),('--touch-target-dp','999')]:
            with self.subTest(args=args):
                out=StringIO()
                with redirect_stdout(out),redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit) as error:
                        main(['size-plan','--width-dp','393','--height-dp','852',*args])
                self.assertEqual(error.exception.code,2)
                self.assertEqual(out.getvalue(),'')

if __name__=='__main__':unittest.main()
