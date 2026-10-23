#!/usr/bin/env sh
# Rotate the phone to reflow native grid cells in place.
set -eu
tgk adaptive-demo --orientation system --theme ocean \
  --touch-target-dp 56 --grid-unit-dp 4
