"""Choice input limits protect native views and the shell output contract."""
import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tgk.widgets import App, Button, CheckBox
from tgk_tools.cli import main


class ByteInput(io.BytesIO):
    def __init__(self, data, short_reads=False):
        super().__init__(data)
        self.requests = []
        self.short_reads = short_reads

    def read(self, size=-1):
        if size < 0:
            raise AssertionError('stdin reads must be bounded')
        self.requests.append(size)
        return super().read(min(size, 2) if self.short_reads else size)


class TextInput(io.StringIO):
    def __init__(self, text):
        super().__init__(text)
        self.requests = []

    def read(self, size=-1):
        if size < 0:
            raise AssertionError('stdin reads must be bounded')
        self.requests.append(size)
        return super().read(size)


class ChooseInputTests(unittest.TestCase):
    def invoke(self, args, source=None, accept=True):
        output, errors, choices = io.StringIO(), io.StringIO(), []

        def offline_run(app):
            root = app.build()
            choices.extend(view.text for view in root.walk()
                           if isinstance(view, (Button, CheckBox))
                           and view.text != 'Confirm selection')
            if accept:
                app.result = choices[:] if '--multi' in args else choices[0]

        with patch('sys.stdin', source or io.StringIO()), \
                patch.object(App, 'run', offline_run), \
                contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                code = main(['choose', *args])
            except SystemExit as exc:
                self.fail(f'valid choose arguments rejected ({exc.code}): {errors.getvalue()}')
        return code, output.getvalue(), errors.getvalue(), choices

    def rejected(self, args, source=None, error=''):
        # Construction itself must never happen on rejected input.
        with patch.object(App, '__init__', side_effect=AssertionError('opened GUI')):
            code, output, errors, _ = self.invoke(args, source)
        self.assertEqual(code, 2)
        self.assertEqual(output, '')
        self.assertTrue(errors)
        self.assertIn(error, errors)
        self.assertNotIn('Traceback', errors)

    def test_exact_combined_item_and_byte_limits_preserve_plain_order(self):
        self.assertEqual(self.invoke(['first', '--stdin', '--multi',
                                    '--max-options', '3', '--max-input-bytes', '13'],
                                   io.StringIO('\nA\r\n\nBC\n')),
                         (0, '["first", "A", "BC"]\n', '', ['first', 'A', 'BC']))

    def test_combined_item_limit_rejects_before_gui(self):
        self.rejected(['first', '--stdin', '--max-options', '2'],
                      io.StringIO('A\nB\n'), '--max-options')

    def test_positional_item_limit_rejects_before_reading_stdin(self):
        source = ByteInput(b'unread')
        self.rejected(['A', 'B', '--stdin', '--max-options', '1'],
                      SimpleNamespace(buffer=source), '--max-options')
        self.assertEqual(source.tell(), 0)

    def test_positional_unicode_counts_encoded_bytes(self):
        self.assertEqual(self.invoke(['é🙂', '--max-input-bytes', '6'])[:3],
                         (0, 'é🙂\n', ''))
        self.rejected(['é🙂', '--max-input-bytes', '5'], error='--max-input-bytes')

    def test_combined_byte_limit_rejects_before_gui(self):
        self.rejected(['é', '--stdin', '--max-input-bytes', '4'],
                      io.StringIO('AB\n'), '--max-input-bytes')

    def test_byte_stdin_reads_only_remaining_budget_plus_one(self):
        source = ByteInput(b'x' * 100)
        self.rejected(['AB', '--stdin', '--max-input-bytes', '10'],
                      SimpleNamespace(buffer=source), '--max-input-bytes')
        self.assertEqual(source.tell(), 9)
        self.assertTrue(all(0 < n <= 9 for n in source.requests))

    def test_short_byte_reads_still_stop_at_budget_plus_one(self):
        source = ByteInput(b'x' * 100, short_reads=True)
        self.rejected(['--stdin', '--max-input-bytes', '10'],
                      SimpleNamespace(buffer=source), '--max-input-bytes')
        self.assertEqual(source.tell(), 11)
        remaining = 11
        for request in source.requests:
            self.assertLessEqual(request, remaining)
            remaining -= min(request, 2)

    def test_oversized_text_line_does_not_use_line_iteration(self):
        source = TextInput('x' * 100_000)
        self.rejected(['--stdin', '--max-input-bytes', '10'], source,
                      '--max-input-bytes')
        self.assertTrue(source.requests)
        self.assertEqual(source.tell(), 11)

    def test_text_only_unicode_reads_at_most_one_extra_character(self):
        source = TextInput('🙂' * 10_000)
        self.rejected(['--stdin', '--max-input-bytes', '100'], source,
                      '--max-input-bytes')
        self.assertEqual(source.tell(), 26)
        self.assertTrue(source.requests)

    def test_byte_stdin_decodes_utf8_and_counts_crlf_bytes(self):
        source = ByteInput('é\r\n🙂\n'.encode('utf-8'), short_reads=True)
        self.assertEqual(self.invoke(['--stdin', '--multi', '--max-input-bytes', '9'],
                                     SimpleNamespace(buffer=source)),
                         (0, '["é", "🙂"]\n', '', ['é', '🙂']))

    def test_invalid_utf8_is_actionable_before_gui(self):
        source = io.TextIOWrapper(ByteInput(b'A\n\xff'), encoding='latin1')
        self.rejected(['--stdin'], source,
                      'UTF-8')

    def test_raw_stdin_accepts_cr_lf_crlf_without_unicode_line_splitting(self):
        source = ByteInput('A\rB\r\nC\nD\u2028E\u0085F\r'.encode('utf-8'), short_reads=True)
        self.assertEqual(self.invoke(['--stdin', '--multi'], SimpleNamespace(buffer=source)),
                         (0, '["A", "B", "C", "D\u2028E\u0085F"]\n', '',
                          ['A', 'B', 'C', 'D\u2028E\u0085F']))

    def test_raw_crlf_bytes_count_before_newline_normalization(self):
        source = SimpleNamespace(buffer=ByteInput(b'A\r\nB\r'))
        self.rejected(['--stdin', '--max-input-bytes', '4'], source, '--max-input-bytes')
        source = SimpleNamespace(buffer=ByteInput(b'A\r\nB\r'))
        self.assertEqual(self.invoke(['--stdin', '--multi', '--max-input-bytes', '5'], source),
                         (0, '["A", "B"]\n', '', ['A', 'B']))

    def test_unpaired_json_surrogates_are_rejected_before_gui(self):
        for text in ('["\\ud800"]', '["\\udfff"]', '["A\\ud800B"]'):
            with self.subTest(text=text):
                self.rejected(['--json-input'], io.StringIO(text), 'UTF-8')

    def test_paired_json_surrogates_remain_valid(self):
        self.assertEqual(self.invoke(['--json-input'], io.StringIO('["\\ud83d\\ude42"]')),
                         (0, '🙂\n', '', ['🙂']))

    def test_json_syntax_and_whitespace_consume_byte_budget(self):
        self.assertEqual(self.invoke(['--json-input', '--max-input-bytes', '7'],
                                    io.StringIO('["é"]\n'))[:3], (0, 'é\n', ''))
        self.rejected(['--json-input', '--max-input-bytes', '6'],
                      io.StringIO('["é"]\n'), '--max-input-bytes')

    def test_json_combines_positionals_and_counts_empty_string_options(self):
        self.assertEqual(self.invoke(['first', '--json-input', '--multi',
                                     '--max-options', '3'], io.StringIO('["", "é"]')),
                         (0, '["first", "", "é"]\n', '', ['first', '', 'é']))
        self.rejected(['first', '--json-input', '--max-options', '2'],
                      io.StringIO('["", "é"]'), '--max-options')

    def test_malformed_or_nonstring_json_fails_before_gui(self):
        for text in ('[', '{}', 'null', '[1]', '[true]', '["A", null]'):
            with self.subTest(text=text):
                self.rejected(['--json-input'], io.StringIO(text))

    def test_deeply_nested_json_fails_cleanly_before_gui(self):
        self.rejected(['--json-input'], io.StringIO('[' * 10000 + ']' * 10000),
                      'JSON')

    def test_empty_input_error_remains_unchanged(self):
        for args, text in (([], ''), (['--stdin'], '\n\r\n'),
                           (['--json-input'], '[]')):
            with self.subTest(args=args):
                self.rejected(args, io.StringIO(text), 'provide at least one option')

    def test_default_limits_are_enforced(self):
        self.rejected(['A'] * 1001, error='--max-options')
        source = ByteInput(b'x' * 1_048_578)
        self.rejected(['--stdin'], SimpleNamespace(buffer=source), '--max-input-bytes')
        self.assertEqual(source.tell(), 1_048_577)

    def test_parser_rejects_invalid_limits_before_gui(self):
        for flag, values in (('--max-options', ('0', '-1', '10001', 'nan', 'inf', '1.5')),
                             ('--max-input-bytes', ('0', '-1', '16777217', 'nan', 'inf', '1.5'))):
            for value in values:
                with self.subTest(flag=flag, value=value), \
                        patch.object(App, '__init__', side_effect=AssertionError('opened GUI')), \
                        contextlib.redirect_stdout(io.StringIO()) as output, \
                        contextlib.redirect_stderr(io.StringIO()) as errors:
                    with self.assertRaises(SystemExit) as exc:
                        main(['choose', 'A', flag, value])
                    self.assertEqual(exc.exception.code, 2)
                    self.assertEqual(output.getvalue(), '')
                    self.assertIn(flag, errors.getvalue())
                    self.assertNotIn('unrecognized arguments', errors.getvalue())

    def test_upper_bounds_are_accepted_and_selected_does_not_add_options(self):
        self.assertEqual(self.invoke(['A', '--multi', '--selected', 'absent',
                                     '--max-options', '10000',
                                     '--max-input-bytes', '16777216']),
                         (0, '["A"]\n', '', ['A']))

    def test_cancellation_remains_code_one_without_output(self):
        self.assertEqual(self.invoke(['A'], accept=False), (1, '', '', ['A']))


if __name__ == '__main__':
    unittest.main()
