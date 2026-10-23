#!/usr/bin/env python3
"""Build an offline-installable source archive containing TGK and TGK Tools.

Only source files are included: C shared objects are compiled on the target
Termux device rather than shipping incompatible Linux x86_64 binaries.
"""
import argparse
import gzip
import shutil
import tarfile
import tempfile
from pathlib import Path

BUNDLE_NAME = 'tgk_bundle_v0.6.0'
IGNORED = {'.git', '__pycache__', '.pytest_cache', '.mypy_cache', 'build', 'dist'}

INSTALLER = '''#!/usr/bin/env sh
# TGK + TGK Tools offline installation. No GitHub access required.
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python}"
AUTO_ARG="${1:---enable-auto}"
case "$AUTO_ARG" in
  --enable-auto|--no-auto) ;;
  --help|-h)
    echo 'Usage: sh ./install.sh [--enable-auto|--no-auto]'
    exit 0 ;;
  *) printf 'Invalid option: %s\\n' "$AUTO_ARG" >&2; exit 2 ;;
esac
(cd tgk && PYTHON="$PYTHON" sh ./install.sh --copy "$AUTO_ARG")
"$PYTHON" -m pip install --no-build-isolation --no-deps --force-reinstall ./tgk-tools
"$PYTHON" -c 'from tgk.canvas import _lib; import tgk_tools.cli; _lib(); print("TGK bundle installation verified")'
echo 'Next: tgk doctor --connect (requires the Termux:GUI Android app)'
'''

README = '''# TGK + TGK Tools offline source installer (v0.6.0)

This bundle includes both repositories, without precompiled libraries or Git history. It compiles TGK for the local device and installs both packages as **non-editable copies**, so the extracted directory can be deleted after installation.

Install the matching Termux:GUI Android app first. In Termux:

```sh
pkg update
pkg install -y python clang
python -m pip install setuptools termuxgui
tar -xzf tgk_bundle_v0.6.0.tar.gz
cd tgk_bundle_v0.6.0
sh ./install.sh
tgk doctor --connect
```

Use `sh ./install.sh --no-auto` if the Kivy import bridge should not be enabled. The bridge supports only a subset of upstream Kivy. For an interactive test run `tgk prompt --title 'Your name'` or `tgk canvas-demo --seconds 10`.

Sources: https://github.com/jerrecode/tgk and https://github.com/jerrecode/tgk-tools. MIT license.
'''


def _ignore(directory, names):
    return [name for name in names if name in IGNORED or name.endswith(('.pyc', '.so', '.egg-info'))]


def _archive_metadata(member):
    """Keep archive bytes independent of the build host and wall clock."""
    member.uid = member.gid = 0
    member.uname = member.gname = ''
    member.mtime = 0
    member.mode = 0o755 if member.isdir() or member.mode & 0o111 else 0o644
    member.pax_headers = {}
    return member


def build(tgk: Path, tools: Path, out: Path) -> Path:
    tgk = tgk.resolve(strict=True)
    tools = tools.resolve(strict=True)
    if not (tgk / 'tgk/native/tgk_canvas.c').is_file():
        raise ValueError(f'Not a TGK framework checkout: {tgk}')
    if not (tools / 'tgk_tools/cli.py').is_file():
        raise ValueError(f'Not a TGK tools checkout: {tools}')
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='tgk-bundle-') as temp:
        root = Path(temp) / BUNDLE_NAME
        root.mkdir()
        def ignore(directory, names):
            return _ignore(directory, names) + [
                name for name in names if (Path(directory)/name).resolve() == out]
        shutil.copytree(tgk, root / 'tgk', ignore=ignore)
        shutil.copytree(tools, root / 'tgk-tools', ignore=ignore)
        script = root / 'install.sh'
        script.write_text(INSTALLER, encoding='utf-8')
        script.chmod(0o755)
        (root / 'README.md').write_text(README, encoding='utf-8')
        with out.open('wb') as target, gzip.GzipFile(filename='', mode='wb', fileobj=target, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode='w') as archive:
                archive.add(root, arcname=BUNDLE_NAME, filter=_archive_metadata)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tgk-source', type=Path, default=Path(__file__).resolve().parents[2] / 'tgk')
    p.add_argument('--out', type=Path, default=Path(BUNDLE_NAME + '.tar.gz'))
    args = p.parse_args()
    print(build(args.tgk_source, Path(__file__).resolve().parents[1], args.out))


if __name__ == '__main__':
    main()
