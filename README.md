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
sh ./install.sh
# Fetches the TGK framework if it is not installed.
tgk doctor --connect
```

If GitHub repositories are cloned side-by-side in `~/tgk` and `~/tgk-tools`, `sh ./install.sh` uses the sibling `tgk` checkout. **The framework is installed as a self-contained, non-editable copy**: the tools installer also works when it downloads TGK into a temporary directory and removes that directory afterwards. The tools themselves install editably, so keep the `tgk-tools` directory. The installer uses the selected `PYTHON` interpreter consistently and does not require root.

To install the framework directly without retaining the source checkout, run `sh ./install.sh --copy` inside `tgk`. Keep the Termux:GUI Android plugin installed and compatible with your Termux app. For an initial connection diagnostic, run `tgk doctor --connect`; for an offline check of just the C renderer run `tgk doctor --json`.

## Downloadable offline installer archive

The [GitHub Actions CI workflow](https://github.com/jerrecode/tgk-tools/actions/workflows/ci.yml) builds an artifact named **tgk-offline-installer** containing both TGK and TGK Tools sources, a combined `install.sh`, and installation instructions. Download the `tgk_bundle_v0.2.0.tar.gz` archive from a successful workflow run, then on Termux:

```sh
pkg install -y python clang
python -m pip install setuptools termuxgui
tar -xzf tgk_bundle_v0.2.0.tar.gz
cd tgk_bundle_v0.2.0
sh ./install.sh
tgk doctor --connect
```

That bundle installs both packages as **non-editable copies**; the extracted source directory may be removed once installed. You need a compatible Termux:GUI Android app for real GUI operations. To build this same bundle locally with sibling repository checkouts, run `python scripts/build_bundle.py --tgk-source ../tgk --out tgk_bundle_v0.2.0.tar.gz`. No x86 Linux binary is shipped; the C library is compiled on the installation device.

Bundle builds normalize timestamps, owner IDs and permissions so identical source contents produce identical archive bytes. Rebuilding at the same output path excludes the previous archive. CI verifies each downloadable bundle with `python scripts/check_bundle_install.py tgk_bundle_v0.2.0.tar.gz`: a disposable environment installs and reinstalls without network access, deletes the extracted sources, checks the installed C renderer and CLI, then uninstalls both packages. The checker requires Python 3.12+ and existing pip/setuptools/wheel build tools. This Linux installation check does not establish Android ABI or GUI correctness.

## Unified colors and progressively complex GUI laboratories

TGK Tools now uses TGK's centralized 17-role semantic theme system. Every GUI
subcommand accepts theme flags **after the subcommand**; `midnight` is the default.

```sh
tgk themes                         # list all 12 palettes and semantic roles
tgk themes --json                  # machine-readable colors and roles
tgk prompt --theme paper --title 'Name'
tgk choose alpha beta --theme ocean --color accent=#33AAFF
tgk files --start "$HOME" --theme forest --color button=#1A6552
tgk canvas-demo --theme cyberpunk --color accent=#FF34E7
tgk demo --list                    # print the 13 supported interactive scenarios
tgk demo --scenario 12_studio --theme lavender
tgk demo --scenario 13_workbench --theme midnight --color accent=#18D0F9
```

JSON custom theme files use the following structure:

```json
{
  "theme": "ocean",
  "colors": {
    "accent": "#18D0F9",
    "background": "#082337",
    "text": "#F1F9FF"
  }
}
```

Load them with `tgk demo --theme-file ./my_theme.json`. Use repeated
`--color ROLE=#HEX` flags to override individual semantic roles; they take
precedence over the theme file. `--theme PRESET`, if present, replaces the
preset named inside `--theme-file`. Malformed color values or unknown roles
are rejected before opening the Android GUI. For **per-widget overrides**,
programmers can use TGK's `colors={"role":"#HEX"}` on a nested component or
`background_color` / `text_color` on an individual object.

The `tgk demo` launcher exposes the same **13 increasingly complex layout
and interaction probes** implemented in the core TGK package. Its
`12_studio` and `13_workbench` scenarios include preset selection, color
scales, editable semantic roles, RGB sliders, nested layouts and complex
controls. The shell `examples/` folder contains 10 progressively more
complex workflows, from palette listing and simple dialogs to shell-driven
native interfaces and the comprehensive workbench:

```sh
sh examples/01_theme_catalog.sh
sh examples/03_multiselect.sh
sh examples/05_gallery_scenarios.sh
sh examples/07_theme_studio.sh
sh examples/09_composed_workflow.sh
sh examples/10_custom_theme_file.sh
```

Termux:GUI provides activity-wide theme colors before View creation and
individual background/text color setters. TGK applies those to supported native
controls, while the C canvas uses semantic colors directly. Native Android
switch/checkbox/progress-track decorations can remain platform-styled.
Hardware visual alignment, layout performance and full Kivy parity are **not**
established by the offline test suite. This tools feature requires the
corresponding TGK core theme API; the feature PR's CI intentionally tests
against TGK's theme feature branch until it lands.

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

A producer should publish complete updates atomically by writing to a separate temporary file and renaming it into place. The viewer reads at most **1 MiB + 1 byte** per update; oversized or malformed JSON shows a validation error instead of allocating unbounded memory. Non-finite progress values (`NaN`/`Infinity`) are rejected; finite values are clamped to 0–100. Repeated equivalent snapshots do not trigger redundant native progress/text updates:

```sh
printf '{"progress":0,"message":"Starting"}\n' > "$TMPDIR/task.json"
tgk progress "$TMPDIR/task.json" --title 'Task' --auto-close &
printf '{"progress":100,"message":"Done","done":true}\n' > "$TMPDIR/task.json.tmp"
mv "$TMPDIR/task.json.tmp" "$TMPDIR/task.json"
```

Exit codes: success 0, user cancellation/negative confirmation 1, argument/runtime error 2; progress timeout returns 124. The program prints structured return values to stdout; logs and diagnostics go to stderr where possible. GUI commands are blocking by design; run `progress` in background if the terminal must keep working.

`tgk doctor --connect` and any GUI command require the Termux:GUI Android app/service; ordinary help and option parsing can run anywhere. The file picker enforces optional `--root` via resolved paths to reduce accidental traversal, but it is not a security sandbox. It now retains at most `--max-items` + 1 eligible entries for sorting instead of loading the entire directory into a Python list; directories are listed first with case-insensitive ordering. A full directory scan is still needed to determine the first entries, so this is a **memory improvement, not asynchronous browsing or pagination**. Large images/text have configurable limits.

`show --max-chars N` reads at most N+1 Unicode characters before rejecting oversized file/stdin input; it does not read the entire input into memory first. Text/image limits must be positive. Timeouts and demo durations must be finite and non-negative (0 disables the limit). Invalid options fail before opening a GUI. Missing Termux:GUI Python bindings produce installation guidance on stderr and exit 2.

The canvas demo uses ImageView image/buffer pixel coordinates directly, following the [Termux:GUI touch protocol](https://github.com/termux/termux-gui/blob/main/Protocol.md#touch-events). Pink touch markers track the latest batched pointer frame, disappear on release/cancellation, and ignore malformed or out-of-buffer coordinates. Rendering stops when the Activity is destroyed. These behaviors have offline event-loop and C framebuffer regression coverage; touchscreen alignment on Android hardware remains unverified.

## Developer notes

Tools are in `tgk_tools/cli.py`; native widget, KV and canvas implementations remain upstream in TGK. Do not duplicate TGK internals here. Contributions should preserve the stdout result contract and support piped input. Run `python -m unittest discover -s tests -v` and `python -m compileall -q tgk_tools` before PR submission. Android UI tests and hardware benchmarks must be performed on a device.

MIT license. See [AGENTS.md](AGENTS.md) for priorities.
