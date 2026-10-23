"""Size planning must use persisted touch preferences without inventing insets."""
import json
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
from unittest.mock import patch
import unittest

from tgk.config import initialize_config,clear_config_cache
from tgk_tools.cli import main


class SizePlanSavedConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.environment=patch.dict('os.environ',{'TGK_CONFIG_HOME':self.temp.name})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        clear_config_cache()
        initialize_config()

    def cli(self,*argv):
        out=StringIO();err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            rc=main(['size-plan','--width-dp','393','--height-dp','852',
                     '--item-height-dp','36','--item-width-dp','80',
                     '--interactive','--json',*argv])
        return rc,out.getvalue(),err.getvalue()

    def test_saved_accessibility_target_is_default(self):
        from tgk.config import update_config
        update_config('layout','touch_target_dp',64)
        rc,out,err=self.cli()
        self.assertEqual(rc,0,err)
        result=json.loads(out)
        self.assertEqual(result['resolved']['height_dp'],64)
        self.assertEqual(result['resolved']['width_dp'],80)

    def test_explicit_target_changes_one_invocation_not_disk(self):
        from tgk.config import update_config,load_config
        update_config('layout','touch_target_dp',64)
        rc,out,err=self.cli('--touch-target-dp','80')
        self.assertEqual(rc,0,err)
        self.assertEqual(json.loads(out)['resolved']['height_dp'],80)
        self.assertEqual(load_config()['layout']['touch_target_dp'],64)

    def test_measured_additional_insets_only(self):
        rc,out,err=self.cli('--item-height-fraction','0.5') if False else (0,'','')
        # Compare non-interactive fraction-driven plans without conflicting dims.
        def query(*args):
            output=StringIO()
            with redirect_stdout(output):
                status=main(['size-plan','--width-dp','393',
                    '--height-dp','852','--item-height-fraction','0.5','--json',*args])
            self.assertEqual(status,0)
            return json.loads(output.getvalue())
        ordinary=query()
        inset=query('--inset-top-dp','22','--inset-bottom-dp','18')
        self.assertIsNone(ordinary['screen']['inset_top_dp'])
        self.assertEqual(inset['screen']['inset_top_dp'],22)
        self.assertEqual(inset['screen']['inset_bottom_dp'],18)
        self.assertEqual(ordinary['resolved']['height_dp'],426)
        self.assertEqual(inset['resolved']['height_dp'],406)

    def test_invalid_insets_are_errors_not_partial_json(self):
        rc,out,err=self.cli('--inset-top-dp','-5')
        self.assertEqual(rc,2)
        self.assertFalse(out)
        self.assertIn('inset',err.lower())


if __name__=='__main__':
    unittest.main()
