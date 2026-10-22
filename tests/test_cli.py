import contextlib
import io
import sys
import unittest
from unittest.mock import patch
from tgk_tools.cli import main

class CLITests(unittest.TestCase):
    def test_help(self):
        with self.assertRaises(SystemExit) as e:
            with contextlib.redirect_stdout(io.StringIO()): main(["--help"])
        self.assertEqual(e.exception.code, 0)
    def test_argument_constraints(self):
        for args in (("choose", "--stdin", "--json-input"),
                     ("canvas-demo", "--fps", "0"),
                     ("files", "--max-items", "0")):
            with self.subTest(args=args), self.assertRaises(SystemExit) as e:
                with contextlib.redirect_stderr(io.StringIO()):main(list(args))
            self.assertEqual(e.exception.code, 2)
    def test_choose_requires_options(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["choose"]),2)
if __name__=="__main__": unittest.main()
