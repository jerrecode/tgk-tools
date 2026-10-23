#!/usr/bin/env sh
# Tier 6: a canvas with active palette-based C graphics and touch traces.
set -eu
tgk canvas-demo --width 512 --height 384 --fps 30 --seconds 20 \
    --theme cyberpunk --color accent=#FF36D4 \
    --color accent_secondary=#18D0F9 --color outline=#8E5DA6
