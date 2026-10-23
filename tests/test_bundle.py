import subprocess
import hashlib
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from build_bundle import BUNDLE_NAME, build


class OfflineBundleTests(unittest.TestCase):
    def sources(self, base):
        core, tools = base/'core', base/'tools'
        (core/'tgk/native').mkdir(parents=True)
        (core/'tgk/native/tgk_canvas.c').write_text('/* source */')
        (tools/'tgk_tools').mkdir(parents=True)
        (tools/'tgk_tools/cli.py').write_text('main = None')
        return core, tools

    def test_rebuilding_inside_checkout_does_not_bundle_previous_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            output = tools/'bundle.tar.gz'
            build(core, tools, output)
            build(core, tools, output)
            with tarfile.open(output) as archive:
                self.assertNotIn(f'{BUNDLE_NAME}/tgk-tools/bundle.tar.gz', archive.getnames())

    def test_output_alias_inside_checkout_excludes_previous_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            (tools/'sub').mkdir()
            alias = base/'tools-alias'
            alias.symlink_to(tools, target_is_directory=True)
            for output in (tools/'sub'/'..'/'bundle.tgz', alias/'bundle.tgz'):
                with self.subTest(output=output):
                    build(core, tools, output)
                    build(core, tools, output)
                    with tarfile.open(output) as archive:
                        self.assertNotIn(f'{BUNDLE_NAME}/tgk-tools/bundle.tgz',
                                         archive.getnames())

    def test_identical_sources_produce_identical_archive_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            first = build(core, tools, base/'first.tar.gz')
            second = build(core, tools, base/'second.tar.gz')
            self.assertEqual(hashlib.sha256(first.read_bytes()).hexdigest(),
                             hashlib.sha256(second.read_bytes()).hexdigest())

    def test_external_source_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            secret = base/'private.txt'
            secret.write_text('outside checkout')
            (tools/'external.txt').symlink_to(secret)
            with self.assertRaisesRegex(ValueError, 'symlink|regular'):
                build(core, tools, base/'artifact.tgz')
            self.assertFalse((base/'artifact.tgz').exists())

    def test_output_symlink_does_not_modify_its_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            original = base/'original.tgz'
            original.write_bytes(b'keep')
            output = base/'artifact.tgz'
            output.symlink_to(original)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                build(core, tools, output)
            self.assertEqual(original.read_bytes(), b'keep')
            self.assertTrue(output.is_symlink())

    def test_normalized_output_symlink_is_also_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            original = base/'original.tgz'
            original.write_bytes(b'keep')
            link = base/'artifact.tgz'
            link.symlink_to(original)
            output = base/'missing'/'..'/'artifact.tgz'
            with self.assertRaisesRegex(ValueError, 'symlink'):
                build(core, tools, output)
            self.assertTrue(link.is_symlink())
            self.assertEqual(original.read_bytes(), b'keep')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX special file test')
    def test_special_source_files_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            os.mkfifo(tools/'pipe')
            with self.assertRaisesRegex(ValueError, 'regular'):
                build(core, tools, base/'artifact.tgz')

    def test_failed_archive_write_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            core, tools = self.sources(base)
            output = base/'artifact.tgz'
            output.write_bytes(b'previous verified archive')
            with patch('tarfile.TarFile.add', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(OSError, 'disk full'):
                    build(core, tools, output)
            self.assertEqual(output.read_bytes(), b'previous verified archive')
            self.assertEqual(sorted(path.name for path in base.iterdir()),
                             ['artifact.tgz', 'core', 'tools'])

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
                self.assertIn('sh ./install.sh --copy', installer)
                check = subprocess.run(['sh', '-n'], input=installer, text=True,
                                       capture_output=True, check=False)
                self.assertEqual(check.returncode, 0, check.stderr)

    def test_invalid_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                build(Path(tmp), ROOT, Path(tmp) / 'bad.tgz')


if __name__ == '__main__':
    unittest.main()
