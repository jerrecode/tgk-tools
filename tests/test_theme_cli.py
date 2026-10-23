"""Tests for palette CLI without requiring an Android service."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tgk.theme import get_theme, set_theme, PRESETS, tgui_color
from tgk_tools.cli import main


class ThemeCLITests(unittest.TestCase):
    def setUp(self):
        self.before=get_theme()
        self.addCleanup(lambda:set_theme(self.before))

    def run_with_output(self,argv):
        stdout=io.StringIO()
        with contextlib.redirect_stdout(stdout):
            result=main(argv)
        return result,stdout.getvalue()

    def test_themes_json_lists_all_presets(self):
        status,output=self.run_with_output(['themes','--json'])
        self.assertEqual(status,0)
        data=json.loads(output)
        self.assertEqual(set(data['presets']),set(PRESETS))
        self.assertIn('accent',data['roles'])

    def test_theme_and_repeatable_color_override(self):
        result,_=self.run_with_output(['themes','--theme','forest',
            '--color','accent=#AB12EF','--color','text=#123456'])
        self.assertEqual(result,0)
        self.assertEqual(get_theme().name,'forest')
        self.assertEqual(get_theme()['accent'],'#AB12EFFF')
        self.assertEqual(get_theme()['text'],'#123456FF')

    def test_theme_json_file_and_override_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'colors.json'
            path.write_text(json.dumps({'theme':'ocean','colors':{'accent':'#BC4210'}}))
            result,_=self.run_with_output(['themes','--theme-file',str(path),
                                           '--color','text=#112233'])
        self.assertEqual(result,0)
        self.assertEqual(get_theme().name,'ocean')
        self.assertEqual(get_theme()['accent'],'#BC4210FF')
        self.assertEqual(get_theme()['text'],'#112233FF')

    def test_unsupported_color_and_theme_rejected_before_gui(self):
        for flags in (['--color','x=#FFFFFF'],['--color','accent=blue'],
                      ['--color','accent'],['--theme','doesnotexist']):
            with self.subTest(flags=flags),self.assertRaises(SystemExit) as cm:
                with contextlib.redirect_stderr(io.StringIO()):
                    main(['prompt',*flags])
            self.assertEqual(cm.exception.code,2)

    def test_demo_list_has_thirteen_scenarios(self):
        result,output=self.run_with_output(['demo','--list'])
        self.assertEqual(result,0)
        self.assertIn('13_workbench',output)
        self.assertIn('01_basics',output)

    def test_per_object_flags_override_only_named_native_views(self):
        from types import SimpleNamespace
        from tgk_tools.cli import _paint_object
        result,_=self.run_with_output(['themes','--object-color',
             'cancel.background=#FF0088','--object-color','heading.text=#102030'])
        self.assertEqual(result,0)
        args=SimpleNamespace(object_colors={
            ('cancel','background'):'#FF0088FF',
            ('heading','text'):'#102030FF',
        })
        class Native:
            def __init__(self):self.bg=None;self.fg=None
            def setbackgroundcolor(self,color):self.bg=color
            def settextcolor(self,color):self.fg=color
        cancel=Native();header=Native();unrelated=Native()
        _paint_object(cancel,'cancel',args)
        _paint_object(header,'heading',args)
        _paint_object(unrelated,'button',args)
        self.assertEqual(cancel.bg,tgui_color('#FF0088'))
        self.assertEqual(header.fg,tgui_color('#102030'))
        self.assertIsNone(unrelated.bg)
        self.assertIsNone(unrelated.fg)

    def test_invalid_object_role_fails_before_launch(self):
        for flag in ('cancel.outline=#FFFFFF','unknown.text=#000000',
                     'cancel.background=not-a-color','cancel'):
            with self.subTest(flag=flag),self.assertRaises(SystemExit) as cm:
                with contextlib.redirect_stderr(io.StringIO()):
                    main(['prompt','--object-color',flag])
            self.assertEqual(cm.exception.code,2)

    def test_theme_list_runs_without_termux_connection(self):
        code,stdout=self.run_with_output(['themes'])
        self.assertEqual(code,0)
        self.assertIn('high_contrast',stdout)


if __name__=='__main__':
    unittest.main()
