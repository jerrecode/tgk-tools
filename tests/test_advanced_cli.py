"""CLI schema and output checks for semantic icons, text styles and windows."""
from contextlib import redirect_stderr,redirect_stdout
from io import StringIO
import json
import unittest
from types import SimpleNamespace

from tgk_tools.cli import main,_paint_object
from tgk.typography import get_text_style,set_text_style
from tgk.icons import ICONS
from tgk.theme import tgui_color


class AdvancedCLITests(unittest.TestCase):
    def setUp(self):
        self.previous=get_text_style()
        self.addCleanup(lambda:set_text_style(self.previous))

    def cli(self,arguments):
        output=StringIO()
        with redirect_stdout(output):
            result=main(arguments)
        return result,output.getvalue()

    def test_semantic_icon_catalog(self):
        code,data=self.cli(["icons","--json"])
        self.assertEqual(code,0)
        self.assertEqual(set(json.loads(data)["icons"]),set(ICONS))
        self.assertGreater(len(ICONS),200)

    def test_file_path_classification(self):
        status,out=self.cli(["icons","--path","items.jsonl"])
        self.assertEqual(status,0)
        self.assertTrue(out.startswith("jsonl "))
        status,out=self.cli(["icons","--path","/usr/lib","--directory","--json"])
        self.assertEqual(status,0)
        self.assertEqual(json.loads(out)["icon"],"folder_lib")

    def test_vector_svg(self):
        status,out=self.cli(["icons","--svg","search","--svg-size","64",
                             "--svg-color","#18D0F9"])
        self.assertEqual(status,0)
        self.assertIn('<svg ',out)
        self.assertIn('width="64"',out)
        self.assertIn("#18D0F9FF",out)

    def test_typography_preset_listing(self):
        status,data=self.cli(["typography","--json"])
        self.assertEqual(status,0)
        presets=json.loads(data)["presets"]
        self.assertIn("body",presets)
        self.assertIn("display",presets)
        self.assertIn("monospace",presets)

    def test_global_text_flags_and_per_object_attributes(self):
        status,_=self.cli(["typography","--text-style","title",
                           "--font-size","29","--font-weight","800",
                           "--font-family","mono",
                           "--font-color-role","warning",
                           "--object-font","heading.style=display",
                           "--object-font","heading.size=44"])
        self.assertEqual(status,0)
        self.assertEqual(get_text_style().size,29)
        self.assertEqual(get_text_style().family,"mono")
        self.assertEqual(get_text_style().role,"warning")
        styles={("heading","style"):"display",("heading","size"):44}
        mock=SimpleNamespace(_native=None)
        _paint_object(mock,"heading",SimpleNamespace(object_fonts=styles,object_colors={}))
        self.assertEqual(mock.text_style,"display")
        self.assertEqual(mock.text_size,44)
        unrelated=SimpleNamespace(_native=None)
        _paint_object(unrelated,"button",SimpleNamespace(object_fonts=styles,object_colors={}))
        self.assertFalse(hasattr(unrelated,"text_style"))

    def test_native_text_size_only(self):
        class Native:
            value=None
            def settextsize(self,n):self.value=n
        obj=Native()
        args=SimpleNamespace(object_fonts={("heading","size"):26,
            ("heading","italic"):True},object_colors={})
        _paint_object(obj,"heading",args)
        self.assertEqual(obj.value,26)

    def test_invalid_font_values_fail_before_gui(self):
        bad=[
            ("--font-size","500"),
            ("--font-weight","650"),
            ("--font-family","unsupported"),
            ("--text-style","invalid"),
            ("--font-color-role","unknown"),
            ("--line-height","nan"),
            ("--object-font","heading.size=999"),
            ("--object-font","settings.style=body"),
            ("--object-font","heading.italic=maybe"),
            ("--object-font","heading.style=unknown"),
        ]
        for flag,value in bad:
            with self.subTest(flag=flag,value=value),self.assertRaises(SystemExit) as exc:
                with redirect_stderr(StringIO()):
                    main(["icons",flag,value])
            self.assertEqual(exc.exception.code,2)

    def test_ui_lab_arguments_parse_in_help(self):
        with self.assertRaises(SystemExit) as exc:
            with redirect_stdout(StringIO()):
                main(["ui-lab","--help"])
        self.assertEqual(exc.exception.code,0)


if __name__=="__main__":
    unittest.main()
