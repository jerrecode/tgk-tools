#!/usr/bin/env sh
# Explore semantic system symbols, actions, media and file extensions.
set -eu
tgk icons --category actions
tgk icons --category media
tgk icons --path records.jsonl
tgk icons --path /usr/lib --directory
