#!/usr/bin/env sh
# Tier 10: ephemeral JSON theme; overwriting a single semantic role.
set -eu
config=$(mktemp)
trap 'rm -f "$config"' EXIT HUP INT TERM
printf '{"theme":"ocean","colors":{"accent":"#FF42AA","surface":"#0E2D4B"}}\n' > "$config"
tgk demo --scenario 12_studio --theme-file "$config" --color text=#FFFFFF
