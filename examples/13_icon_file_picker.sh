#!/usr/bin/env sh
# Native Android file picker with semantic symbols, custom typography size.
set -eu
tgk files --start "$HOME" --icons --max-items 150 \
  --theme forest --font-size 16 --object-font heading.size=22 \
  --object-color heading.text=#FFEAAF
