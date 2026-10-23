#!/usr/bin/env sh
# Uses Termux:GUI Activity.getconfiguration() for *window* dp geometry.
# Max refresh, physical panel resolution, color depth and inset heights may be unknown.
set -eu
tgk layout-plan --connect --json
