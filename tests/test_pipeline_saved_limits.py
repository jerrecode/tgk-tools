"""Saved I/O budgets apply to shell pipelines unless explicitly overridden."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from tgk import config
from tgk_tools.cli import main


class SavedPipelineLimitTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, {"TGK_CONFIG_HOME": str(self.root / "config")})
        environment.start()
        self.addCleanup(environment.stop)
        config.clear_config_cache()
        self.addCleanup(config.clear_config_cache)
        config.initialize_config()
        self.source = self.root / "source.bin"
        self.source.write_bytes(b"x" * 10240)

    def invoke(self, *arguments):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = main(["pipeline", *map(str, arguments)])
        return code, output.getvalue(), errors.getvalue()

    def test_saved_byte_cap_bounds_hash_and_preserves_copy_destination(self):
        config.patch_config({"io": {"max_bytes": 512}})
        destination = self.root / "destination.bin"
        destination.write_bytes(b"original")
        for arguments in (("hash", self.source),
                          ("copy", self.source, destination, "--overwrite")):
            with self.subTest(arguments=arguments):
                code, output, errors = self.invoke(*arguments)
                self.assertEqual(code, 2)
                self.assertEqual(output, "")
                self.assertIn("maximum transfer size", errors)
                self.assertEqual(destination.read_bytes(), b"original")
                self.assertFalse(list(self.root.glob(".tgk-copy-*")))

    def test_explicit_byte_limit_overrides_saved_cap_without_saving(self):
        config.patch_config({"io": {"max_bytes": 512}})
        before = config.config_path().read_bytes()
        code, output, errors = self.invoke("hash", self.source, "--max-bytes", "10240")
        self.assertEqual(code, 0, errors)
        self.assertEqual(json.loads(output)["bytes"], 10240)
        self.assertEqual(config.config_path().read_bytes(), before)

    def test_saved_chunk_size_bounds_reads_and_explicit_override_wins(self):
        config.patch_config({"io": {"chunk_bytes": 4096}})
        original_open = Path.open
        for flags, bound in (((), 4096), (("--chunk-bytes", "2048"), 2048)):
            with self.subTest(flags=flags):
                reads = []

                @contextlib.contextmanager
                def recording_open(path, *arguments, **keywords):
                    with original_open(path, *arguments, **keywords) as stream:
                        class Reader:
                            def read(self, size):
                                reads.append(size)
                                return stream.read(size)
                        yield Reader()

                with patch.object(Path, "open", recording_open):
                    code, output, errors = self.invoke("hash", self.source, *flags)
                self.assertEqual(code, 0, errors)
                self.assertEqual(json.loads(output)["sha256"],
                                 hashlib.sha256(b"x" * 10240).hexdigest())
                self.assertEqual(max(reads), bound)

    def test_probe_uses_saved_timeout_and_allows_explicit_override(self):
        binary = self.root / "ffprobe"
        binary.write_text("#!" + sys.executable + "\nimport time\n"
                          "time.sleep(0.15)\nprint('{\"format\":{\"fixture\":true}}')\n",
                          encoding="utf-8")
        binary.chmod(0o700)
        config.patch_config({"io": {"timeout": 0.02}})
        before = config.config_path().read_bytes()
        with patch.dict(os.environ, {"PATH": str(self.root) + os.pathsep + os.environ["PATH"]}):
            code, output, errors = self.invoke("probe", self.source)
            self.assertEqual(code, 2)
            self.assertEqual(output, "")
            self.assertIn("timeout", errors)
            code, output, errors = self.invoke("probe", self.source, "--timeout", "2")
            self.assertEqual(code, 0, errors)
            self.assertTrue(json.loads(output)["data"]["format"]["fixture"])
        self.assertEqual(config.config_path().read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
