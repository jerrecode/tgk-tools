#!/usr/bin/env sh
# Global defaults and isolated heading/cancel-control overrides.
set -eu
tgk prompt --theme ocean --text-style terminal \
  --font-size 18 --font-color-role accent \
  --object-font heading.style=display \
  --object-font heading.size=28 \
  --object-color cancel.background=#882944 \
  --title 'Styled input'
