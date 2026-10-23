#!/usr/bin/env sh
# Tier 5: choose a progressively more complex layout scenario.
set -eu
choice=$(tgk choose 01_basics 02_rows 03_grid 04_nesting 05_scroll \
    06_form 07_sliders 08_states 09_anchors 10_overrides 11_stress \
    12_studio 13_workbench --theme lavender \
    --title 'TGK laboratory') || exit $?
tgk demo --scenario "$choice" --theme ocean
