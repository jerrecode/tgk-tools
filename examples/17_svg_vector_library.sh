#!/usr/bin/env sh
# Export one self-contained text SVG (do not present as a directly native ImageView).
set -eu
output="${1:-search.svg}"
tgk icons --svg search --svg-size 96 --svg-color '#18D0F9' > "$output"
printf 'Wrote SVG: %s\n' "$output" >&2
