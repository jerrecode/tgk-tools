"""Bounded file picker enumeration: output correctness and memory contract."""
import heapq
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tgk_tools.cli import _limited_file_entries


class FilePickerListingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.folder = self.base / 'root'
        self.folder.mkdir()

    def names(self, **options):
        paths, truncated = _limited_file_entries(self.folder, **options)
        return [path.name for path, _is_dir in paths], truncated

    def test_directories_first_and_sorted_before_limit(self):
        for name in ('Zoo', 'alpha'):
            (self.folder / name).mkdir()
        for i in range(350):
            (self.folder / f'f{i:04}.py').touch()
        (self.folder / 'a.py').touch()
        names, overflow = self.names(max_items=4)
        self.assertEqual(names, ['alpha', 'Zoo', 'a.py', 'f0000.py'])
        self.assertTrue(overflow)

    def test_hidden_extension_and_directory_filters(self):
        (self.folder / '.secret.py').touch()
        (self.folder / 'aa.py').touch()
        (self.folder / 'bb.txt').touch()
        (self.folder / 'folder').mkdir()
        self.assertEqual(self.names(extension={'py'}, max_items=10),
                         (['folder', 'aa.py'], False))
        self.assertEqual(self.names(extension={'py'}, hidden=True, max_items=10),
                         (['folder', '.secret.py', 'aa.py'], False))
        self.assertEqual(self.names(dirs_only=True, max_items=10),
                         (['folder'], False))

    def test_limit_applies_after_filtering(self):
        for i in range(40):
            (self.folder / f'ignored{i}.txt').touch()
        (self.folder / 'only.py').touch()
        self.assertEqual(self.names(extension={'py'}, max_items=1),
                         (['only.py'], False))

    def test_boundary_excludes_symlinks_outside_root(self):
        (self.base / 'outside.py').write_text('private')
        (self.folder / 'inside.py').write_text('normal')
        try:
            (self.folder / 'outside.py').symlink_to(self.base / 'outside.py')
        except (OSError, NotImplementedError):
            self.skipTest('symlinks not supported here')
        self.assertEqual(self.names(boundary=self.folder.resolve(), max_items=10),
                         (['inside.py'], False))

    def test_selector_receives_generator_not_materialized_directory_list(self):
        for i in range(100):
            (self.folder / f'{i:03}.py').touch()
        original = heapq.nsmallest
        observed = []
        def inspect(n, iterable, **kwargs):
            observed.append((n, not isinstance(iterable, (list, tuple))))
            return original(n, iterable, **kwargs)
        with patch('heapq.nsmallest', side_effect=inspect):
            names, truncated = self.names(max_items=5)
        self.assertEqual(observed, [(6, True)])
        self.assertEqual(names, [f'{i:03}.py' for i in range(5)])
        self.assertTrue(truncated)

    def test_invalid_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, 'positive'):
            self.names(max_items=0)


if __name__ == '__main__':
    unittest.main()
