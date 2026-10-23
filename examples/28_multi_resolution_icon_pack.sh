#!/usr/bin/env sh
# Requires optional CairoSVG and Pillow. Generates all PNG/JPEG/ICO variants.
set -eu
# Android/Termux does not guarantee /tmp is writable. Keep generated
# assets outside repository examples and away from the user's existing files.
output=${1:-${TGK_ICON_OUTPUT_DIR:-${HOME:?HOME required}/.cache/tgk/icon-examples/raster-pack}}
mkdir -p "$output"
if [ ! -w "$output" ]; then
  printf 'Error: icon output is not writable: %s\n' "$output" >&2
  exit 2
fi
tgk icons-build --output "$output" --raster --overwrite
printf 'Low/mid/high PNG/JPG and ICO icons are under %s/icons\n' "$output" >&2
