#!/usr/bin/env sh
# Tier 4: path selection with bounded root, extension filters and explicit cancellation.
set -eu
root="${HOME}"
path=$(tgk files --start "$root" --root "$root" --ext py \
    --ext kv --theme forest --max-items 80) || exit $?
printf 'Selected: %s\n' "$path"
