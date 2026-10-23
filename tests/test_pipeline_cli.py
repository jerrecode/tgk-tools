"""Bounded pipeline commands must remain composable without Android."""
from contextlib import redirect_stdout,redirect_stderr
from io import StringIO
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tgk_tools.cli import main


class PipelineCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.source=self.root/'input.data'
        self.source.write_bytes((b'tgk-pipeline-test\n')*500)

    def run_cli(self,*args):
        stdout=StringIO();stderr=StringIO()
        with redirect_stdout(stdout),redirect_stderr(stderr):
            code=main(['pipeline',*map(str,args)])
        return code,stdout.getvalue(),stderr.getvalue()

    def test_hash_json_and_digest(self):
        code,out,err=self.run_cli('hash',self.source,'--chunk-bytes','1024')
        self.assertEqual(code,0,err)
        data=json.loads(out)
        self.assertEqual(data['sha256'],hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(data['bytes'],self.source.stat().st_size)
        self.assertEqual(data['operation'],'hash')
        self.assertEqual(err,'')

    def test_copy_overwrite_and_atomic_failure(self):
        target=self.root/'target'
        code,out,err=self.run_cli('copy',self.source,target,'--chunk-bytes','1024')
        self.assertEqual(code,0,err)
        self.assertEqual(target.read_bytes(),self.source.read_bytes())
        code,out,err=self.run_cli('copy',self.source,target)
        self.assertEqual(code,2)
        self.assertFalse(out)
        self.assertIn('exists',err.lower())
        code,out,err=self.run_cli('copy',self.source,target,
                                  '--overwrite','--max-bytes','1024')
        self.assertEqual(code,2)
        self.assertEqual(target.read_bytes(),self.source.read_bytes())
        self.assertFalse(list(self.root.glob('.tgk-copy-*')))

    def test_probe_json_metadata_and_timeout(self):
        with patch('tgk_tools.pipeline_cli.ffprobe',return_value={
            'format':{'duration':'123.45'},'streams':[{'codec_name':'h264'}]
        }) as tool:
            code,out,err=self.run_cli('probe',self.source,'--timeout','2')
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)['data']['streams'][0]['codec_name'],'h264')
        self.assertEqual(tool.call_args.kwargs['timeout'],2)

    def test_download_requires_explicit_target(self):
        with self.assertRaises(SystemExit) as exception:
            main(['pipeline','download','https://example.invalid/a'])
        self.assertEqual(exception.exception.code,2)

    def test_unsafe_url_is_rejected_without_network(self):
        code,out,err=self.run_cli('download','http://example.invalid/a',
                                  self.root/'download')
        self.assertEqual(code,2)
        self.assertIn('unsupported download URL',err)
        self.assertFalse((self.root/'download').exists())

    def test_invalid_limits_rejected_before_effect(self):
        for options in (('--timeout','0'),('--chunk-bytes','0'),
                        ('--max-bytes','-1')):
            with self.subTest(options=options), self.assertRaises(SystemExit):
                with redirect_stderr(StringIO()):
                    main(['pipeline','hash',str(self.source),*options])


if __name__=='__main__':
    unittest.main()
