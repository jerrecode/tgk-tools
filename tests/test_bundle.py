import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_bundle import BUNDLE_NAME, build


class OfflineBundleTests(unittest.TestCase):
    def test_bundle_contains_sources_but_not_host_binaries_or_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core = base / 'tgk-checkout'
            tools = base / 'tools-checkout'
            (core / 'tgk/native').mkdir(parents=True)
            (tools / 'tgk_tools').mkdir(parents=True)
            (core / '.git').mkdir()
            (core / '.git/config').write_text('private fixture')
            (core / 'tgk/native/tgk_canvas.c').write_text('/* test */')
            (core / 'tgk/libtgk.so').write_bytes(b'not portable')
            (tools / 'tgk_tools/cli.py').write_text('main = None')
            bundle = build(core, tools, base / 'artifact.tgz')
            with tarfile.open(bundle) as archive:
                names = archive.getnames()
                self.assertIn(f'{BUNDLE_NAME}/tgk/tgk/native/tgk_canvas.c', names)
                self.assertIn(f'{BUNDLE_NAME}/tgk-tools/tgk_tools/cli.py', names)
                self.assertIn(f'{BUNDLE_NAME}/install.sh', names)
                self.assertFalse(any(name.endswith('.so') or '/.git/' in name for name in names))
                installer = archive.extractfile(f'{BUNDLE_NAME}/install.sh').read().decode()
                self.assertIn('./install.sh --copy', installer)
                check = subprocess.run(['sh', '-n'], input=installer, text=True,
                                       capture_output=True, check=False)
                self.assertEqual(check.returncode, 0, check.stderr)

    def test_invalid_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build(Path(tmp), ROOT, Path(tmp) / 'bad.tgz')


if __name__ == '__main__':
    unittest.main()
