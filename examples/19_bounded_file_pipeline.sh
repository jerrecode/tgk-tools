#!/usr/bin/env sh
# Composable low-memory hashing + atomic copy. Path with spaces is supported.
set -eu
if [ "$#" -ne 2 ]; then
  printf 'Usage: %s SOURCE TARGET\n' "$0" >&2
  exit 2
fi
source=$1
target=$2
tgk pipeline hash "$source" --chunk-bytes 65536 --max-bytes 536870912
tgk pipeline copy "$source" "$target" --chunk-bytes 65536 \
  --max-bytes 536870912 --timeout 120
tgk pipeline hash "$target" --chunk-bytes 65536 --max-bytes 536870912
