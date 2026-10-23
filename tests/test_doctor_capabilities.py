"""New diagnostics are machine-readable and never open Termux:GUI by default."""
import contextlib
from io import StringIO
import json
import unittest

from tgk_tools.cli import main
import tgk
import tgk_tools


class DoctorCapabilityTests(unittest.TestCase):
    def test_doctor_advertises_native_index_and_bounded_io(self):
        output=StringIO()
        with contextlib.redirect_stdout(output):
            code=main(['doctor','--json'])
        self.assertEqual(code,0)
        info=json.loads(output.getvalue())
        self.assertEqual(info['tgk_version'],tgk.__version__)
        self.assertEqual(info['tgk_tools_version'],tgk_tools.__version__)
        self.assertTrue(info['native_view_id_dispatch'])
        self.assertTrue(info['bounded_io_available'])
        self.assertIn('ffmpeg_executable',info)
        self.assertIn('ffprobe_executable',info)
        self.assertIn('c_renderer',info)
        self.assertNotIn('termuxgui_connection_version',info)

    def test_text_mode_uses_same_keys(self):
        output=StringIO()
        with contextlib.redirect_stdout(output):
            code=main(['doctor'])
        self.assertEqual(code,0)
        self.assertIn('native_view_id_dispatch: True',output.getvalue())
        self.assertIn('bounded_io_available: True',output.getvalue())


if __name__=='__main__':
    unittest.main()
