#!/usr/bin/env sh
# Generate deterministic filename/extension vector icons without raster libraries.
set -eu
# Android/Termux does not guarantee /tmp is writable. Keep generated
# assets outside repository examples and away from the user's existing files.
output=${1:-${TGK_ICON_OUTPUT_DIR:-${HOME:?HOME required}/.cache/tgk/icon-examples/svg-catalog}}
mkdir -p "$output"
if [ ! -w "$output" ]; then
  printf 'Error: icon output is not writable: %s\n' "$output" >&2
  exit 2
fi
tgk icons-build --output "$output" --svg-only --overwrite \
  --icon filename_readme_md \
  --icon filename_requirements_txt \
  --icon file_ext_py \
  --icon file_ext_jsonl \
  --icon file_document
printf 'SVG icons are under %s/icons/svg\n' "$output" >&2
