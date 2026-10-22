#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python}"
# Install framework from sibling checkout if present, otherwise clone it.
if ! "$PYTHON" -c 'import tgk; assert tgk.__version__ >= "0.2.0"' 2>/dev/null; then
  if [ -f ../tgk/install.sh ]; then
    (cd ../tgk && ./install.sh)
  elif command -v git >/dev/null 2>&1; then
    FRAMEWORK_DIR="${TMPDIR:-/tmp}/tgk-source-$$"
    trap 'rm -rf "$FRAMEWORK_DIR"' EXIT HUP INT TERM
    git clone --depth 1 https://github.com/jerrecode/tgk.git "$FRAMEWORK_DIR"
    (cd "$FRAMEWORK_DIR" && ./install.sh)
  else
    echo 'Install tgk framework first: https://github.com/jerrecode/tgk' >&2
    exit 1
  fi
fi
"$PYTHON" -m pip install --no-build-isolation --no-deps --editable .
printf '%s\n' 'Installed. Start with: tgk doctor --connect; tgk --help'
