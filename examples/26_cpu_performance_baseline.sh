#!/usr/bin/env sh
# Repeat on different Termux hardware / Python versions and compare measured
# CPU-path timings; this DOES NOT test GUI rendering FPS or actual touch IPC.
set -eu
tgk benchmark --nodes 300 --iterations 500 --samples 5 --json
