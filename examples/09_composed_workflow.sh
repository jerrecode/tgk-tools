#!/usr/bin/env sh
# Tier 9: shell orchestration: text -> choices -> file browsing -> animated UI.
set -eu
title=$(tgk prompt --theme paper --title 'Project' --default 'Termux lab') || exit $?
mode=$(tgk choose simple advanced expert --theme ocean --title "$title") || exit $?
case "$mode" in
  simple) scenario=01_basics ;;
  advanced) scenario=08_states ;;
  expert) scenario=13_workbench ;;
  *) printf 'Unknown mode\n' >&2; exit 2 ;;
esac
printf 'Project=%s mode=%s\n' "$title" "$mode"
tgk demo --scenario "$scenario" --theme terminal
