#!/usr/bin/env sh
# Safe example: explicit HTTPS hostname allowlist and byte limit.
set -eu
if [ "$#" -ne 3 ]; then
  printf 'Usage: %s URL ALLOWED_HOST OUTPUT_FILE\n' "$0" >&2
  exit 2
fi
tgk pipeline download "$1" "$3" \
  --allow-host "$2" --max-bytes 52428800 --timeout 30
