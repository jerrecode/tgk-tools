"""Regression test for unhashable native Termux:GUI Button instances."""
import argparse
import contextlib
import io
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from tgk_tools.cli import run_files


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
    def __init__(self, *args, **kwargs):
        self.text = args[1] if len(args) > 1 else ''
        self.finished = False

    def setheight(self, *args): pass
    def setwidth(self, *args): pass
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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def events(self):
        for label in type(self).labels:
            buttons = [b for b in NativeButton.buttons if b.text == label]
            if not buttons:
                raise AssertionError(f'No button: {label!r}')
            yield types.SimpleNamespace(type='click', value={'id': buttons[-1].id})
        yield types.SimpleNamespace(type='destroy', value={'finishing': True})


tg = types.SimpleNamespace(Connection=Connection, Activity=NativeView,
    LinearLayout=NativeView, FrameLayout=NativeView, NestedScrollView=NativeView,
    TextView=NativeView, Button=NativeButton)


class NativeFileDialogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        NativeButton.buttons = []
        NativeButton.next_id = 0

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

    def test_unhashable_button_cancel(self):
        self.assertIsNone(NativeButton.__hash__)
        self.assertEqual(self.dialog(['Cancel']), (1, ''))

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
