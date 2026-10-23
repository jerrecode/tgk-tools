"""Regression coverage from Android-16 TGK Tools example reports."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest.mock import patch
import unittest

from tgk.widgets import App,Button
from tgk_tools.cli import main
from tgk_tools.example_workflow import WorkflowGallery


ROOT=Path(__file__).resolve().parents[1]


class ReportedTermuxRegressions(unittest.TestCase):
    def _shell_example(self,name):
        with tempfile.TemporaryDirectory() as temp:
            target=Path(temp)
            bin_dir=target/'bin'
            bin_dir.mkdir()
            capture=target/'args.txt'
            fake=bin_dir/'tgk'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$TGK_CAPTURE"\n',
                            encoding='utf-8')
            fake.chmod(0o755)
            env=dict(os.environ,PATH=str(bin_dir)+os.pathsep+os.environ.get('PATH',''),
                     TGK_ICON_OUTPUT_DIR=str(target/'output'),TGK_CAPTURE=str(capture))
            program=ROOT/'examples'/name
            result=subprocess.run(['sh',str(program)],cwd=target,env=env,
                                  capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            options=capture.read_text(encoding='utf-8').splitlines()
            self.assertIn('--output',options)
            self.assertEqual(Path(options[options.index('--output')+1]),
                             target/'output')
            self.assertTrue((target/'output').is_dir())
            self.assertNotIn('/tmp',options)

    def test_svg_catalog_uses_writable_output_directory(self):
        self._shell_example('27_layered_svg_catalog.sh')

    def test_raster_pack_uses_writable_output_directory(self):
        self._shell_example('28_multi_resolution_icon_pack.sh')

    def test_gallery_script_starts_exactly_one_activity_process(self):
        text=(ROOT/'examples'/'05_gallery_scenarios.sh').read_text()
        self.assertIn('exec tgk demo --gallery',text)
        self.assertNotIn('tgk choose',text.split('set -eu')[-1])

    def test_workflow_script_no_longer_chains_activities(self):
        text=(ROOT/'examples'/'09_composed_workflow.sh').read_text()
        self.assertIn('exec tgk workflow',text)
        self.assertNotIn('tgk prompt',text.split('set -eu')[-1])

    def test_workflow_nav_retains_project_and_outputs_only_one_json(self):
        output=StringIO()
        def simulate(app):
            app.root=app.build()
            self.assertEqual(app.manager.current,'catalog')
            self.assertEqual(len(app.labs),3)
            app.project_field.text='Termux workspace'
            app.choose('advanced','08_states')
            self.assertEqual(app.manager.current,'08_states')
            app.show_menu()
            self.assertEqual(app.manager.current,'catalog')
        with patch.object(App,'run',simulate),redirect_stdout(output):
            result=main(['workflow','--project','Original','--theme','forest'])
        self.assertEqual(result,0)
        self.assertEqual(json.loads(output.getvalue()),
                         {'project':'Termux workspace','mode':'advanced',
                          'scenario':'08_states'})

    def test_workflow_cancellation_has_no_success_output(self):
        output=StringIO()
        with patch.object(App,'run',lambda app:setattr(app,'root',app.build())),redirect_stdout(output):
            result=main(['workflow','--project','Cancelled'])
        self.assertEqual(result,1)
        self.assertFalse(output.getvalue())

    def test_dialog_title_close_is_48dp_and_tabs_are_responsive(self):
        captured=[]
        def simulate(app):
            root=app.build()
            captured.append((app,root))
        with patch.object(App,'run',simulate):
            status=main(['ui-lab','--mode','dialog','--start-page','text'])
        self.assertEqual(status,0)
        _,root=captured[-1]
        titlebar=root.children[0]
        self.assertEqual(titlebar.height,48)
        close=next(item for item in titlebar.children if isinstance(item,Button))
        self.assertEqual((close.width,close.height),(48,48))
        panel=captured[-1][0].tabs
        self.assertFalse(hasattr(panel,'height'))

    def test_overlay_fallback_is_opt_in_and_passed_to_app(self):
        created=[]
        with patch.object(App,'run',lambda app:created.append(app)):
            self.assertEqual(main(['ui-lab','--mode','overlay',
                                   '--fallback-normal','--start-page','canvas']),0)
        self.assertEqual(created[-1].window_mode,'overlay')
        self.assertTrue(created[-1].overlay_fallback)


if __name__=='__main__':
    unittest.main()
