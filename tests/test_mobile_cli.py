"""Responsive layout tools: no hardware required for deterministic geometry."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import json
import sys
import types
import unittest
from unittest.mock import patch

from tgk_tools.cli import main


class MobileCLITests(unittest.TestCase):
    def run_cli(self,*args):
        out=StringIO();err=StringIO()
        with redirect_stdout(out),redirect_stderr(err):
            status=main(list(args))
        return status,out.getvalue(),err.getvalue()

    def test_phone_and_landscape_grid_snapshots(self):
        rc,out,err=self.run_cli('layout-plan','--width-dp','393','--height-dp','852',
                                '--items','4','--json')
        self.assertEqual(rc,0,err)
        data=json.loads(out)
        self.assertEqual(data['source'],'simulated')
        self.assertEqual(data['screen']['size_class'],'compact')
        self.assertEqual([item['column'] for item in data['grid']['items']],[0]*4)
        self.assertIsNone(data['screen']['max_refresh_hz'])
        rc,out,err=self.run_cli('layout-plan','--width-dp','930','--height-dp','430',
                                '--items','4','--json')
        self.assertEqual(rc,0,err)
        data=json.loads(out)
        self.assertEqual(data['screen']['orientation'],'landscape')
        self.assertEqual([item['column'] for item in data['grid']['items']],[0,4,8,0])

    def test_custom_spans_and_touch_scale(self):
        rc,out,err=self.run_cli('layout-plan','--width-dp','700','--height-dp','900',
            '--spans','6,4,3','--spans','6,8,6','--touch-target-dp','56',
            '--grid-unit-dp','8','--theme','paper','--json')
        self.assertEqual(rc,0,err)
        doc=json.loads(out)
        self.assertEqual([x['col_span'] for x in doc['grid']['items']],[4,8])
        self.assertEqual(doc['grid']['touch_target_dp'],56)
        self.assertEqual(doc['grid']['unit_dp'],8)

    def test_style_catalog_has_color_and_geometry(self):
        rc,out,err=self.run_cli('style-catalog','--theme','forest','--json')
        self.assertEqual(rc,0,err)
        doc=json.loads(out)
        self.assertEqual(doc['theme'],'forest')
        self.assertIn('button_pressed',doc['colors'])
        self.assertIn('table_first_row',doc['colors'])
        self.assertIn('title_h1',doc['typography'])
        self.assertEqual(doc['components']['table']['header_bottom_width_dp'],2)
        self.assertIn('dropdown',doc['components'])

    def test_connected_metrics_use_actual_termuxgui_configuration(self):
        class Activity:
            def __init__(self,*args,**kwargs):self.finished=False
            def getconfiguration(self):
                return {'screenwidth':480,'screenheight':1000,
                        'density':3.0,'fontscale':1.3,'orientation':'portrait'}
            def finish(self):self.finished=True
        class Connection:
            def __enter__(self):return self
            def __exit__(self,*args):return None
        fake=types.SimpleNamespace(Connection=Connection,Activity=Activity)
        with patch.dict(sys.modules,{'termuxgui':fake}):
            rc,out,err=self.run_cli('layout-plan','--connect','--json')
        self.assertEqual(rc,0,err)
        data=json.loads(out)
        self.assertEqual(data['source'],'termuxgui')
        self.assertEqual(data['screen']['approx_window_px'],[1440,3000])
        self.assertIsNone(data['screen']['color_depth_bits'])

    def test_invalid_layout_args_are_rejected(self):
        bad=[
          ('--width-dp','393'),
          ('--width-dp','0','--height-dp','852'),
          ('--width-dp','393','--height-dp','852','--spans','6,6'),
          ('--width-dp','393','--height-dp','852','--spans','20,6,4'),
        ]
        for args in bad:
            with self.subTest(args=args):
                status,out,err=self.run_cli('layout-plan',*args)
                self.assertEqual(status,2)
                self.assertEqual(out,'')
                self.assertTrue(err)

    def test_invalid_min_touch_is_usage_error(self):
        with self.assertRaises(SystemExit) as cm:
            with redirect_stderr(StringIO()):
                main(['adaptive-demo','--touch-target-dp','20'])
        self.assertEqual(cm.exception.code,2)


if __name__=='__main__':unittest.main()
