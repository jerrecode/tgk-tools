"""Exercise the demo event loop and inspect real C-rendered RGBA pixels."""
import argparse
import itertools
import sys
import types
import unittest
from unittest.mock import patch

from tgk_tools.cli import run_canvas


class CanvasInputTests(unittest.TestCase):
    def run_frames(self, *events):
        snapshots = []
        queue = []
        for event in events:
            queue.extend([types.SimpleNamespace(type='touch', value=event), None])
        queue.extend([types.SimpleNamespace(type='destroy', value={'finishing': True}), None])

        class Connection:
            def __enter__(self): return self
            def __exit__(self, *exc): pass
            def checkevent(self): return queue.pop(0)

        class Activity:
            def __init__(self, *args, **kwargs): pass
            def finish(self): pass

        class View:
            def __init__(self, *args): pass
            def setdimensions(self, *args): pass
            def sendtouchevent(self, *args): pass
            def setbuffer(self, *args): pass
            def refresh(self): pass
            def getdimensions(self): return (1080, 1440)

        class Buffer:
            def __init__(self, connection, w, h): self.data = bytearray(w*h*4)
            def __enter__(self): return self.data
            def __exit__(self, *exc): pass
            def blit(self): snapshots.append(bytes(self.data))

        tg = types.SimpleNamespace(Connection=Connection, Activity=Activity,
                                   ImageView=View, Buffer=Buffer,
                                   View=types.SimpleNamespace(MATCH_PARENT=-1))
        args = argparse.Namespace(width=512, height=256, fps=60, seconds=0)
        clock = itertools.count(step=0.1)
        with patch.dict(sys.modules, {'termuxgui': tg}), \
                patch('time.monotonic', side_effect=lambda: next(clock)), \
                patch('sys.stderr'):
            self.assertEqual(run_canvas(args), 0)
        return snapshots

    @staticmethod
    def pixel(frame, x, y):
        offset = (y*512+x)*4
        return frame[offset:offset+4]

    def test_image_pixels_are_not_rescaled_using_view_dimensions(self):
        frames = self.run_frames({'action': 'down', 'pointers': [[{'id': 7, 'x': 300, 'y': 180}]]})
        self.assertEqual(self.pixel(frames[0], 300, 180), bytes((255, 126, 180, 255)))

    def test_terminal_events_remove_touch_markers(self):
        point = {'id': 7, 'x': 300, 'y': 180}
        for action in ('up', 'cancel'):
            with self.subTest(action=action):
                frames = self.run_frames({'action': 'down', 'pointers': [[point]]},
                                         {'action': action, 'pointers': [[point]]})
                self.assertNotEqual(self.pixel(frames[1], 300, 180), bytes((255, 126, 180, 255)))

    def test_pointer_up_removes_only_lifted_pointer(self):
        frames = self.run_frames({'action': 'pointer_up', 'index': 1, 'pointers': [[
            {'id': 7, 'x': 300, 'y': 180}, {'id': 42, 'x': 450, 'y': 180}]]})
        self.assertEqual(self.pixel(frames[0], 300, 180), bytes((255, 126, 180, 255)))
        self.assertNotEqual(self.pixel(frames[0], 450, 180), bytes((255, 126, 180, 255)))

    def test_invalid_coordinates_are_ignored_without_aborting_demo(self):
        for x in ('bad', None, float('nan'), float('inf'), -20, 520):
            with self.subTest(x=x):
                frames = self.run_frames({'action': 'move', 'pointers': [[
                    {'id': 7, 'x': x, 'y': 180}, {'id': 42, 'x': 300, 'y': 180}]]})
                self.assertEqual(self.pixel(frames[0], 300, 180), bytes((255, 126, 180, 255)))

    def test_destroy_stops_rendering_immediately(self):
        self.assertEqual(len(self.run_frames()), 0)


if __name__ == '__main__':
    unittest.main()
