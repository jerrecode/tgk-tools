#!/usr/bin/env sh
# Offline: simulate adaptive grid positions on a 393 x 852 dp mobile window.
set -eu
tgk layout-plan --width-dp 393 --height-dp 852 --items 9 \
  --theme midnight --json
