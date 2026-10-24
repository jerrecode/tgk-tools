"""Shell CLI: layered SVG build, manifest, type detection and input bounds."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
from pathlib import Path
import json
import tempfile
import unittest
import os
from unittest.mock import patch

from tgk_tools.cli import main


class IconBuildCLITests(unittest.TestCase):
    def run_cli(self,*argv):
        output=StringIO();errors=StringIO()
        with redirect_stdout(output),redirect_stderr(errors):
            code=main(list(argv))
        return code,output.getvalue(),errors.getvalue()

    def test_selected_icons_generate_only_svg_and_empty_raster_dirs(self):
        with tempfile.TemporaryDirectory() as root:
            code,output,error=self.run_cli('icons-build','--output',root,
                  '--icon','file_ext_jsonl','--icon','filename_agents_md')
            self.assertEqual(code,0,error)
            data=json.loads(output)
            self.assertEqual(data['svg_files'],2)
            icons=Path(root)/'icons'
            self.assertTrue((icons/'svg'/'file_ext_jsonl.svg').exists())
            self.assertTrue((icons/'svg'/'filename_agents_md.svg').exists())
            for folder in ('ico','low_res','mid_res','high_res'):
                self.assertEqual(list((icons/folder).iterdir()),[])
            self.assertEqual(len(json.loads((icons/'manifest.json').read_text())['icons']),2)

    def test_purpose_built_semantic_icons_export_through_tools_cli(self):
        from xml.etree import ElementTree as ET
        symbols = ("refresh", "sync", "copy", "cut", "run",
                   "play", "pause", "stop", "repeat_off", "star_filled")
        for name in symbols:
            with self.subTest(name=name):
                code, source, errors = self.run_cli("icons", "--svg", name)
                self.assertEqual(code, 0, errors)
                root = ET.fromstring(source)
                self.assertEqual(root.get("viewBox"), "0 0 64 64")
                self.assertNotIn("<text", source)
                self.assertIn("path", source)

        with tempfile.TemporaryDirectory() as directory:
            args = ["icons-build", "--output", directory, "--svg-only"]
            for name in symbols:
                args.extend(("--icon", name))
            code, out, err = self.run_cli(*args)
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["count"], len(symbols))
            manifest = json.loads((Path(directory) / "icons" /
                                   "manifest.json").read_text())
            self.assertGreaterEqual(manifest["geometry_revision"], 2)
            for name in symbols:
                data = (Path(directory) / "icons/svg" /
                        (name + ".svg")).read_text()
                self.assertNotIn("<text", data)
                ET.fromstring(data)

    def test_explicit_svg_only_overrides_saved_raster_default(self):
        from tgk.config import initialize_config, patch_config, clear_config_cache
        with tempfile.TemporaryDirectory() as root:
            with patch.dict(os.environ, {'TGK_CONFIG_HOME': str(Path(root)/'config')}):
                initialize_config()
                patch_config({'icons': {'raster': True}})
                code, output, error = self.run_cli('icons-build', '--output', root,
                                                  '--icon', 'file', '--svg-only')
                self.assertEqual(code, 0, error)
                self.assertFalse(json.loads(output)['raster'])
                self.assertEqual(list((Path(root)/'icons/ico').iterdir()), [])
                clear_config_cache()

    def test_svg_color_overrides_all_semantic_parts(self):
        from xml.etree import ElementTree as ET
        for name in ('refresh','sync','run'):
            with self.subTest(name=name):
                code,source,error=self.run_cli('icons','--svg',name,
                                              '--svg-color','#E12345')
                self.assertEqual(code,0,error)
                root=ET.fromstring(source)
                colors={node.get(key) for node in root.iter()
                        for key in ('stroke','fill')
                        if node.get(key) not in (None,'none')}
                self.assertEqual(colors,{'#E12345FF'})

    def test_rebuilding_existing_output_requires_explicit_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(self.run_cli('icons-build','--output',root,
                            '--icon','file')[0],0)
            code,out,err=self.run_cli('icons-build','--output',root,
                                      '--icon','folder')
            self.assertEqual(code,2)
            self.assertFalse(out)
            self.assertIn('exists',err.lower())
            self.assertEqual(self.run_cli('icons-build','--output',root,
                            '--icon','folder','--overwrite')[0],0)
            self.assertFalse((Path(root)/'icons'/'svg'/'file.svg').exists())

    def test_detailed_path_command_keeps_backward_compatibility(self):
        code,out,err=self.run_cli('icons','--path','README.md','--json')
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)['icon'],'markdown')
        code,out,err=self.run_cli('icons','--path','README.md','--detailed','--json')
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)['icon'],'filename_readme_md')
        code,out,err=self.run_cli('icons','--svg','file_ext_py')
        self.assertEqual(code,0,err)
        self.assertIn('<svg',out)
        self.assertIn('>PY</text>',out)

    def test_missing_or_unsafe_icon_selection_fails_without_partial_output(self):
        with tempfile.TemporaryDirectory() as root:
            code,out,err=self.run_cli('icons-build','--output',root,
                                      '--icon','file','--icon','../escape')
            self.assertEqual(code,2)
            self.assertFalse(out)
            self.assertFalse((Path(root)/'icons').exists())
            code,out,err=self.run_cli('icons-build','--output',root,
                                      '--icon','file','--max-icons','0')
            self.assertEqual(code,2)
            self.assertFalse((Path(root)/'icons').exists())


if __name__=="__main__":
    unittest.main()
