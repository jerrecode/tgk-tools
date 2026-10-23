#!/usr/bin/env sh
# Requires ffprobe (Termux: pkg install ffmpeg). Emits one JSON object.
set -eu
if [ "$#" -ne 1 ]; then
  printf 'Usage: %s MEDIA_FILE\n' "$0" >&2
  exit 2
fi
tgk pipeline probe "$1" --timeout 20 --max-metadata-bytes 8388608
