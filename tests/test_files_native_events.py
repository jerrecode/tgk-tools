"""Native file-picker event dispatch and stale-path regressions."""
import argparse
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tgk_tools.cli import main, run_files


class NativeButton:
    # Termux:GUI native buttons implement equality but are not hashable.
    __hash__ = None
    buttons = []
    next_id = 0

    def __init__(self, activity, text, parent):
        type(self).next_id += 1
        self.id = self.next_id
        self.text = text
        type(self).buttons.append(self)

    def __eq__(self, value):
        return self.id == getattr(value, 'id', value)

    def sendclickevent(self, enabled):
        self.click_enabled=enabled

    def setwidth(self, width):
        self.width=width

    def setheight(self, height):
        self.height=height


class NativeView:
    views=[]
    def __init__(self, *args, **kwargs):
        self.text = args[1] if len(args) > 1 else ''
        self.finished = False
        self.width=None
        self.height=None
        type(self).views.append(self)

    def setheight(self, height): self.height=height
    def setwidth(self, width): self.width=width
    def setmargin(self, *args): pass
    def setlinearlayoutparams(self, *args): pass
    def settextsize(self, *args): pass
    def clearchildren(self): pass

    def settext(self, value):
        self.text = value

    def finish(self):
        self.finished = True


class Connection:
    labels = []
    entered = exited = False

    def __enter__(self):
        type(self).entered = True
        return self

    def __exit__(self, *args):
        type(self).exited = True

    def events(self):
        for label in type(self).labels:
            if isinstance(label, tuple):
                label, change = label
                change()
            buttons = [b for b in NativeButton.buttons if b.text == label]
            if not buttons:
                raise AssertionError(f'No button: {label!r}')
            yield types.SimpleNamespace(type='click', value={'id': buttons[-1].id})
        yield types.SimpleNamespace(type='destroy', value={'finishing': True})


tg = types.SimpleNamespace(Connection=Connection, Activity=NativeView,
    LinearLayout=NativeView, FrameLayout=NativeView, NestedScrollView=NativeView,
    TextView=NativeView, Button=NativeButton,
    View=types.SimpleNamespace(MATCH_PARENT='MATCH_PARENT'))


class NativeFileDialogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        NativeButton.buttons = []
        NativeButton.next_id = 0
        NativeView.views = []
        Connection.entered = Connection.exited = False

    def dialog(self, clicks, *, dirs_only=False, boundary=None):
        Connection.labels = clicks
        options = argparse.Namespace(start=str(self.root),
            root=str(boundary) if boundary else None,
            title=None, hidden=False, ext=[], max_items=25,
            dirs_only=dirs_only)
        stdout = io.StringIO()
        with patch.dict(sys.modules, {'termuxgui': tg}), contextlib.redirect_stdout(stdout):
            code = run_files(options)
        return code, stdout.getvalue()

    def cli_dialog(self, clicks, *, start=None, boundary=None, dirs_only=False):
        Connection.labels = clicks
        args = ['files', '--start', str(start or self.root), '--max-items', '25']
        if boundary is not None:
            args += ['--root', str(boundary)]
        if dirs_only:
            args += ['--dirs-only']
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.dict(sys.modules, {'termuxgui': tg}), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def assert_stale_rejected(self, clicks, **kwargs):
        code, output, error = self.cli_dialog(clicks, **kwargs)
        self.assertEqual((code, output), (2, ''))
        self.assertTrue(error)
        self.assertNotIn('Traceback', error)
        self.assertTrue(Connection.entered)
        self.assertTrue(Connection.exited)

    def test_retargeted_file_link_is_rejected_before_selection(self):
        (self.root / 'target.txt').write_text('inside')
        for initial_link in (False, True):
            with self.subTest(initial_link=initial_link), tempfile.TemporaryDirectory() as outside:
                file = self.root / 'inside.txt'
                file.unlink(missing_ok=True)
                if initial_link:
                    file.symlink_to(self.root / 'target.txt')
                else:
                    file.write_text('inside')
                target = Path(outside) / 'private.txt'
                target.write_text('outside')
                def replace():
                    file.unlink()
                    file.symlink_to(target)
                self.assert_stale_rejected([('       inside.txt', replace)], boundary=self.root)
                file.unlink()

    def test_retargeted_directory_link_is_rejected_before_population(self):
        (self.root / 'inside').mkdir()
        link = self.root / 'link'
        link.symlink_to(self.root / 'inside', target_is_directory=True)
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / 'private.txt').write_text('outside')
            def retarget():
                link.unlink()
                link.symlink_to(outside, target_is_directory=True)
            self.assert_stale_rejected([('[DIR] link', retarget), 'Cancel'], boundary=self.root)
            self.assertFalse(any(b.text.endswith('private.txt') for b in NativeButton.buttons))

    def test_vanished_file_is_rejected_before_selection(self):
        file = self.root / 'gone.txt'
        file.touch()
        self.assert_stale_rejected([('       gone.txt', file.unlink)])

    def test_file_replaced_with_directory_is_rejected_before_selection(self):
        file = self.root / 'changed.txt'
        file.touch()
        def replace():
            file.unlink()
            file.mkdir()
        self.assert_stale_rejected([('       changed.txt', replace)])

    def test_directory_replaced_with_file_is_rejected_before_navigation(self):
        directory = self.root / 'changed'
        directory.mkdir()
        def replace():
            directory.rmdir()
            directory.touch()
        self.assert_stale_rejected([('[DIR] changed', replace), 'Cancel'])

    def test_current_directory_retarget_is_rejected_before_selection(self):
        (self.root / 'inside').mkdir()
        link = self.root / 'link'
        link.symlink_to(self.root / 'inside', target_is_directory=True)
        with tempfile.TemporaryDirectory() as outside:
            def retarget():
                link.unlink()
                link.symlink_to(outside, target_is_directory=True)
            self.assert_stale_rejected(
                ['[DIR] link', ('[Select this directory]', retarget)],
                dirs_only=True, boundary=self.root)

    def test_parent_retarget_is_rejected_before_population(self):
        (self.root / 'inside' / 'sub').mkdir(parents=True)
        link = self.root / 'link'
        link.symlink_to(self.root / 'inside', target_is_directory=True)
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / 'private.txt').touch()
            def retarget():
                link.unlink()
                link.symlink_to(outside, target_is_directory=True)
            self.assert_stale_rejected(
                ['[DIR] link', '[DIR] sub', ('[..] Parent directory', retarget), 'Cancel'],
                boundary=self.root)
            self.assertFalse(any(b.text.endswith('private.txt') for b in NativeButton.buttons))

    def test_invalid_initial_paths_fail_before_activity(self):
        file = self.root / 'file'
        file.touch()
        missing = self.root / 'missing'
        child = self.root / 'child'
        child.mkdir()
        for start, boundary in ((missing, None), (file, None),
                                (self.root, missing), (self.root, file),
                                (self.root, child)):
            with self.subTest(start=start, boundary=boundary), \
                    patch.object(tg, 'Activity', side_effect=AssertionError('opened Activity')):
                code, output, error = self.cli_dialog([], start=start, boundary=boundary)
                self.assertEqual((code, output), (2, ''))
                self.assertTrue(error)
                self.assertFalse(Connection.entered)

    def test_valid_in_root_file_link_preserves_lexical_selection(self):
        (self.root / 'inside.txt').touch()
        link = self.root / 'link.txt'
        link.symlink_to(self.root / 'inside.txt')
        self.assertEqual(self.cli_dialog(['       link.txt'], boundary=self.root),
                         (0, str(link) + '\n', ''))

    def test_valid_in_root_directory_link_and_parent_navigation(self):
        (self.root / 'inside' / 'sub').mkdir(parents=True)
        link = self.root / 'link'
        link.symlink_to(self.root / 'inside', target_is_directory=True)
        self.assertEqual(self.cli_dialog(
            ['[DIR] link', '[DIR] sub', '[..] Parent directory', '[Select this directory]'],
            dirs_only=True, boundary=self.root), (0, str(link) + '\n', ''))

    def test_unhashable_button_cancel(self):
        self.assertIsNone(NativeButton.__hash__)
        self.assertEqual(self.dialog(['Cancel']), (1, ''))

    def test_full_width_list_and_buttons(self):
        (self.root/'a.txt').write_text('a',encoding='utf-8')
        self.dialog(['Cancel'])
        widths=[view.width for view in NativeView.views]
        self.assertGreaterEqual(widths.count('MATCH_PARENT'),3)
        entry=next(button for button in NativeButton.buttons
                   if button.text.endswith('a.txt'))
        self.assertEqual(entry.width,'MATCH_PARENT')
        cancel=next(button for button in NativeButton.buttons
                    if button.text=='Cancel')
        self.assertLess(cancel.width,192)

    def test_navigate_and_select_file(self):
        (self.root / 'sub').mkdir()
        file = self.root / 'sub' / 'hello.txt'
        file.write_text('hello', encoding='utf-8')
        self.assertEqual(self.dialog(['[DIR] sub', '       hello.txt']),
                         (0, str(file) + '\n'))

    def test_select_directory_with_root_constraint(self):
        (self.root / 'sub').mkdir()
        self.assertEqual(self.dialog(
            ['[DIR] sub', '[Select this directory]'],
            dirs_only=True, boundary=self.root),
            (0, str(self.root / 'sub') + '\n'))


if __name__ == '__main__':
    unittest.main()
