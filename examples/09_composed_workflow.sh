#!/usr/bin/env sh
# Project input -> complexity selection -> live demo inside ONE Android Activity.
# This replaces three sequential Termux:GUI processes that could block waiting
# for the previous Activity's destroy notification after a user selection.
set -eu
exec tgk workflow --project 'Termux lab' --theme terminal
