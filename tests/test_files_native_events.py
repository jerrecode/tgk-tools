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
