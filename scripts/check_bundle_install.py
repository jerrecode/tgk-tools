#!/usr/bin/env python3
"""Verify a source bundle offline in a disposable venv (Python 3.12+).

Build tools (pip, setuptools and wheel) come from the invoking environment.
No Android service is needed; this checks installation and the C renderer.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

from build_bundle import BUNDLE_NAME


def check(archive):
    with tempfile.TemporaryDirectory(prefix='tgk bundle check ') as temp:
        base = Path(temp)
        environment = base/'env'
        subprocess.run([sys.executable, '-m', 'venv', '--system-site-packages',
                        str(environment)], check=True)
        python = environment/'bin/python'
        env = os.environ.copy()
        env.pop('PYTHONPATH', None)
        env.update(PYTHON=str(python), PIP_NO_INDEX='1', PIP_NO_CACHE_DIR='1',
                   PIP_DISABLE_PIP_VERSION_CHECK='1', TGK_DISABLE='1')
        source = base/'sources'
        with tarfile.open(archive) as bundle:
            bundle.extractall(source, filter='data')
        root = source/BUNDLE_NAME
        for _ in range(2):  # first installation and upgrade/reinstallation
            subprocess.run(['sh', './install.sh', '--no-auto'], cwd=root,
                           env=env, check=True)
        shutil.rmtree(source)
        # Isolated Python and an empty cwd prevent source-path imports from
        # hiding an incomplete or accidentally editable installation.
        verification = '''
import sys
from pathlib import Path
import tgk, tgk_tools
from tgk.canvas import Canvas, rgba
prefix = Path(sys.prefix)
for module in (tgk, tgk_tools):
    assert Path(module.__file__).is_relative_to(prefix), module.__file__
pixels = bytearray(4*4*4)
canvas = Canvas(pixels, 4, 4)
canvas.clear(rgba(11, 22, 33))
canvas.close()
assert pixels == bytes((11, 22, 33, 255))*16
'''
        subprocess.run([str(python), '-I', '-c', verification], cwd=base,
                       env=env, check=True)
        cli = environment/'bin/tgk'
        subprocess.run([str(cli), '--help'], cwd=base, env=env, check=True,
                       stdout=subprocess.DEVNULL)
        result = subprocess.run([str(cli), 'doctor', '--json'], cwd=base,
                                env=env, check=True, capture_output=True, text=True)
        assert json.loads(result.stdout)['c_renderer'] == 'available'
        subprocess.run([str(python), '-m', 'pip', 'uninstall', '-y', 'tgk-tools', 'tgk'],
                       cwd=base, env=env, check=True)
        purelib = environment/'lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages'
        for path in (purelib/'tgk', purelib/'tgk_tools', purelib/'tgk_auto.pth', cli):
            assert not path.exists(), f'Uninstall left installed file: {path}'
    print('Bundle verified: offline install, reinstall, source deletion, C rendering, CLI and uninstall')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    check(parser.parse_args().archive)
