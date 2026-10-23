#!/usr/bin/env sh
# Tier 2: prompt, validate cancellation and confirm.
set -eu
name=$(tgk prompt --theme paper --title 'Your alias' --default 'Explorer') || exit $?
if tgk confirm "Proceed as $name?" --theme ocean --title 'Confirm'; then
  printf 'Confirmed: %s\n' "$name"
else
  printf 'Cancelled\n' >&2
  exit 1
fi
