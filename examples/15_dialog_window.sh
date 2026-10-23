#!/usr/bin/env sh
# Android dialog Activity; screen decorations come from Termux:GUI.
set -eu
tgk ui-lab --mode dialog --start-page text --theme paper \
  --text-style serif
