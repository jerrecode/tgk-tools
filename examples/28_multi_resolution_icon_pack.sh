#!/usr/bin/env sh
# Requires optional CairoSVG and Pillow. Generates all PNG/JPEG/ICO variants.
set -eu
output=${1:-/tmp}
tgk icons-build --output "$output" --raster --overwrite
printf 'Low/mid/high PNG/JPG and ICO icons are under %s/icons\n' "$output" >&2
