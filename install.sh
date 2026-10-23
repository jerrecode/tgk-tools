#!/usr/bin/env sh
# Install the CLI and, when needed, a durable copy of the TGK framework.
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python}"

command -v "$PYTHON" >/dev/null 2>&1 || {
  echo 'Missing Python: pkg install python' >&2
  exit 1
}
"$PYTHON" -m pip --version >/dev/null 2>&1 || {
  echo 'Missing pip: install the Python pip module for this interpreter' >&2
  exit 1
}
"$PYTHON" -c 'import setuptools.build_meta' || {
  echo 'Missing Python build backend: python -m pip install setuptools' >&2
  exit 1
}
if ! "$PYTHON" -c 'import tgk; from tgk.canvas import _lib; _lib(); from tgk import io_pipeline,adaptive,style_tokens,layout_helpers,icon_builder,config; assert tuple(map(int, tgk.__version__.split(".")[:3])) >= (0, 6, 2)' >/dev/null 2>&1; then
  if [ -f ../install.sh ] && [ -f ../tgk/native/tgk_canvas.c ]; then
    printf '%s\n' 'Installing TGK from parent checkout as a self-contained copy...'
    (cd .. && PYTHON="$PYTHON" sh ./install.sh --copy)
  elif [ -f ../tgk/install.sh ]; then
    printf '%s\n' 'Installing TGK from sibling checkout as a self-contained copy...'
    (cd ../tgk && PYTHON="$PYTHON" sh ./install.sh --copy)
  elif command -v git >/dev/null 2>&1; then
    # Source checkout is ephemeral: an editable installation would break after cleanup.
    FRAMEWORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/tgk-source.XXXXXXXX")"
    trap 'rm -rf -- "$FRAMEWORK_DIR"' 0
    trap 'exit 130' INT
    trap 'exit 143' TERM
    printf '%s\n' 'Fetching TGK framework...'
    git clone --depth 1 https://github.com/jerrecode/tgk.git "$FRAMEWORK_DIR"
    (cd "$FRAMEWORK_DIR" && PYTHON="$PYTHON" sh ./install.sh --copy)
  else
    echo 'Install TGK framework first: https://github.com/jerrecode/tgk' >&2
    exit 1
  fi
fi
"$PYTHON" -m pip install --no-build-isolation --no-deps --editable .
# Even when TGK 0.6 was already installed independently, populate any
# missing user-owned preset files without replacing customized ones.
"$PYTHON" -m tgk.config init
"$PYTHON" -m tgk.config validate
"$PYTHON" -c 'import tgk_tools.cli; from tgk.canvas import _lib; from tgk import io_pipeline,adaptive,style_tokens,layout_helpers,icon_builder,config; _lib()'
printf '%s\n' 'Installed. Start with: tgk doctor --connect; tgk --help'
