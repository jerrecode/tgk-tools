#!/usr/bin/env sh
# Requires Termux:GUI "Display over other apps" permission.
# When the Android plugin rejects overlay creation, show a warning and use
# a normal Activity instead of an opaque TypeError traceback.
set -eu
exec tgk ui-lab --mode overlay --fallback-normal \
  --start-page canvas --theme cyberpunk
