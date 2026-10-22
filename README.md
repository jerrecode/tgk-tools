# TGK Tools — graphical dialogs and utilities for Termux shell

[![CI](https://github.com/jerrecode/tgk-tools/actions/workflows/ci.yml/badge.svg)](https://github.com/jerrecode/tgk-tools/actions/workflows/ci.yml)

Shell-friendly Android utilities powered by [TGK](https://github.com/jerrecode/tgk), rendered with **Termux:GUI**, with optional C-accelerated animations. No root required. Intended for Termux on Android, not standard Linux GUI desktops.

## Installation

Install Termux, the matching Termux:GUI Android plugin, and in Termux run:

```sh
pkg update
pkg install -y git python clang
python -m pip install termuxgui setuptools
git clone https://github.com/jerrecode/tgk-tools.git
cd tgk-tools
./install.sh
# Fetches the TGK framework if it is not installed.
tgk doctor --connect
```

If GitHub repositories are cloned side-by-side in `~/tgk` and `~/tgk-tools`, `./install.sh` uses the sibling `tgk` checkout. **The framework is installed as a self-contained, non-editable copy**: the tools installer also works when it downloads TGK into a temporary directory and removes that directory afterwards. The tools themselves install editably, so keep the `tgk-tools` directory. The installer uses the selected `PYTHON` interpreter consistently and does not require root.

To install the framework directly without retaining the source checkout, run `./install.sh --copy` inside `tgk`. Keep the Termux:GUI Android plugin installed and compatible with your Termux app. For an initial connection diagnostic, run `tgk doctor --connect`; for an offline check of just the C renderer run `tgk doctor --json`.

## Shell commands

```sh
# Read user input from a native Android dialog
value=$(tgk prompt --title 'Search' --default 'file') || exit 1
printf '%s\n' "$value"

# Confirmation: 0=yes, 1=no; use it before destructive operations
if tgk confirm 'Proceed?' --title 'Confirm'; then echo yes; fi

# Single choice => line on stdout
mode=$(tgk choose fast balanced accurate --title 'Preset') || exit 1

# Multiselect => JSON string array on stdout
tgk choose A B C --title 'Enabled channels' --multi

# Read choices from stdin as one choice per line
printf 'One\nTwo\n' | tgk choose --stdin

# Read JSON array of choices from stdin
printf '["Choice 1", "Choice 2"]\n' | tgk choose --json-input

# Scrollable UTF-8 file/stdin viewer
ps -ef | tgk show - --title 'Processes'
tgk show README.md

# Native PNG/JPEG viewer
tgk image ./preview.png

# Path picker (returns path on stdout)
tgk files --start "$HOME" --ext py --ext kv --title 'Select source'
tgk files --start "$HOME" --dirs-only

# Watch a job's JSON file (0..100), optionally auto-close
tgk progress "$TMPDIR/task.json" --auto-close

# Test the native rendering path and actual Termux:GUI IPC
tgk doctor --json --connect
tgk canvas-demo --width 512 --height 512 --fps 30 --seconds 15
```

### Progress file format

A producer should publish complete updates atomically by writing to a separate temporary file and renaming it into place:

```sh
printf '{"progress":0,"message":"Starting"}\n' > "$TMPDIR/task.json"
tgk progress "$TMPDIR/task.json" --title 'Task' --auto-close &
printf '{"progress":100,"message":"Done","done":true}\n' > "$TMPDIR/task.json.tmp"
mv "$TMPDIR/task.json.tmp" "$TMPDIR/task.json"
```

Exit codes: success 0, user cancellation/negative confirmation 1, argument/runtime error 2; progress timeout returns 124. The program prints structured return values to stdout; logs and diagnostics go to stderr where possible. GUI commands are blocking by design; run `progress` in background if the terminal must keep working.

`tgk doctor --connect` and any GUI command require the Termux:GUI Android app/service; ordinary help and option parsing can run anywhere. The file picker enforces optional `--root` via resolved paths to reduce accidental traversal, but it is not a security sandbox. Large images/text have configurable limits.

## Developer notes

Tools are in `tgk_tools/cli.py`; native widget, KV and canvas implementations remain upstream in TGK. Do not duplicate TGK internals here. Contributions should preserve the stdout result contract and support piped input. Run `python -m unittest discover -s tests -v` and `python -m compileall -q tgk_tools` before PR submission. Android UI tests and hardware benchmarks must be performed on a device.

MIT license. See [AGENTS.md](AGENTS.md) for priorities.
