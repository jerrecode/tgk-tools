#!/usr/bin/env sh
# Canonical gallery: all scenarios share ONE Activity / ScreenManager.
# No chained "tgk choose" process and no Activity-switch wait/deadlock.
set -eu
exec tgk demo --gallery --theme ocean
