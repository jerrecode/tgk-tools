"""Resource limits and dependency failures must preserve the shell contract."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tgk_tools.cli import main


class InputContractTests(unittest.TestCase):
    def test_show_reads_only_limit_plus_one_characters_from_stdin(self):
        class LimitedStream(io.StringIO):
            def read(self, size=-1):
                self_size.append(size)
                return super().read(size)
        self_size = []
        output, errors = io.StringIO(), io.StringIO()
        with patch('sys.stdin', LimitedStream('a'*100)), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(main(['show', '-', '--max-chars', '8']), 2)
        self.assertEqual(self_size, [9])
        self.assertEqual(output.getvalue(), '')
        self.assertIn('Input too large', errors.getvalue())

    def test_show_file_limit_is_enforced_during_read(self):
        sizes = []
        class LimitedFile(io.StringIO):
            def read(self, size=-1):
                sizes.append(size)
                return super().read(size)
        with patch.object(Path, 'open', return_value=LimitedFile('a'*100)), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['show', 'large.txt', '--max-chars', '8']), 2)
        self.assertEqual(sizes, [9])

    def test_show_accepts_exact_limit_of_unicode_characters(self):
        for source in ('stdin', 'file'):
            with self.subTest(source=source), tempfile.TemporaryDirectory() as tmp:
                text = 'ä🙂é'
                path = Path(tmp)/'unicode.txt'
                path.write_text(text, encoding='utf-8')
                shown = []
                with patch('sys.stdin', io.StringIO(text)), patch('tgk_tools.cli.App.run',
                        autospec=True, side_effect=lambda app: shown.append(
                            app.build().children[1].children[0].text)):
                    self.assertEqual(main(['show', '-' if source=='stdin' else str(path),
                                           '--max-chars', '3']), 0)
                self.assertEqual(shown, [text])

    def test_invalid_limits_fail_before_opening_any_gui(self):
        cases = [('show', '-', '--max-chars', '0'),
                 ('image', 'test.png', '--max-bytes', '-1'),
                 ('progress', 'state.json', '--timeout', '-1'),
                 ('progress', 'state.json', '--timeout', 'nan'),
                 ('progress', 'state.json', '--timeout', 'inf'),
                 ('canvas-demo', '--seconds', '-1'),
                 ('canvas-demo', '--seconds', 'nan'),
                 ('canvas-demo', '--seconds', 'inf'),
                 ('canvas-demo', '--width', '0'),
                 ('canvas-demo', '--width', '4096', '--height', '4096')]
        for args in cases:
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), \
                    patch.dict('sys.modules', {'termuxgui': None}):
                with self.assertRaises(SystemExit) as exc:
                    main(args)
                self.assertEqual(exc.exception.code, 2)

    def test_missing_binding_has_actionable_stderr_and_no_traceback(self):
        output, errors = io.StringIO(), io.StringIO()
        with patch.dict('sys.modules', {'termuxgui': None}), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(main(['files']), 2)
        self.assertEqual(output.getvalue(), '')
        self.assertIn('pip install termuxgui', errors.getvalue())
        self.assertNotIn('Traceback', errors.getvalue())


if __name__ == '__main__':
    unittest.main()
