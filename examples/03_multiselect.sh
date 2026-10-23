#!/usr/bin/env sh
# Tier 3: JSON input/selection piped between a shell script and native Android.
set -eu
printf '["CPU", "GPU", "Memory", "Latency"]\n' |
  tgk choose --json-input --multi --theme terminal \
      --title 'Select metrics'
