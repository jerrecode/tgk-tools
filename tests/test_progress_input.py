"""Bounded progress snapshot parsing and error behavior."""
import json
import tempfile
import unittest
from pathlib import Path

from tgk_tools.cli import _read_progress_state, _MAX_PROGRESS_JSON_BYTES


class ProgressFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'state.json'

    def write(self, value):
        self.path.write_bytes(value)
        return self.path

    def test_valid_progress_and_multibyte_message(self):
        self.write(json.dumps({'progress': 42.5, 'message': 'Schritt ✓', 'done': True}).encode())
        self.assertEqual(_read_progress_state(self.path), (42.5, 'Schritt ✓', True))

    def test_clamps_outside_range(self):
        for raw, expected in ((-20, 0.0), (170, 100.0)):
            with self.subTest(raw=raw):
                self.write(json.dumps({'progress': raw}).encode())
                self.assertEqual(_read_progress_state(self.path)[0], expected)

    def test_rejects_oversized_input_without_unbounded_read(self):
        self.write(b'{"progress":0,"filler":"' + b'x' * (_MAX_PROGRESS_JSON_BYTES + 3))
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            _read_progress_state(self.path)

    def test_rejects_nan_and_infinity(self):
        for progress in ('NaN', 'Infinity', '-Infinity', float('nan'), float('inf')):
            with self.subTest(progress=str(progress)):
                self.write(json.dumps({'progress': progress}).encode())
                with self.assertRaisesRegex(ValueError, 'finite'):
                    _read_progress_state(self.path)

    def test_rejects_invalid_utf8_or_json(self):
        for data in (b'\xff', b'{', b'[]'):
            with self.subTest(data=data):
                self.write(data)
                with self.assertRaises(ValueError):
                    _read_progress_state(self.path)

    def test_missing_snapshot_keeps_file_not_found_behavior(self):
        with self.assertRaises(FileNotFoundError):
            _read_progress_state(self.path)


if __name__ == '__main__':
    unittest.main()
