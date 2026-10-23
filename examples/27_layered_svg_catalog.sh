#!/usr/bin/env sh
# Generate deterministic filename/extension vector icons without raster libraries.
set -eu
output=${1:-/tmp}
tgk icons-build --output "$output" --overwrite \
  --icon filename_readme_md \
  --icon filename_requirements_txt \
  --icon file_ext_py \
  --icon file_ext_jsonl \
  --icon file_document
printf 'SVG icons are under %s/icons/svg\n' "$output" >&2
