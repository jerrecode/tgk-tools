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

## Configure defaults and responsive sizing

The TGK installer creates `config.json`, named palette presets,
typography presets and option profiles without overwriting user edits.
Both the framework and CLI use the saved defaults unless an explicit
per-instance argument or CLI option overrides them.

```sh
tgk config init
tgk config list
tgk config show --compact

# Atomic update of several system/core configuration fields:
tgk config edit \
  --field layout.touch_target_dp=56 \
  --field layout.compact_breakpoint_dp=720 \
  --field runtime.clock_callbacks_per_tick=64 \
  --field io.workers=2 \
  --field icons.max_icons=500

# Reset just one value (does not erase unrelated settings):
tgk config edit --reset-field layout.touch_target_dp

# Set named default palette, font and resource profile:
tgk config set --palette ocean --typography terminal --options battery_saver

# Default layout settings now come from config.json:
tgk layout-plan --width-dp 700 --height-dp 850 --json
tgk size-plan --width-dp 393 --height-dp 852 --interactive --json

# Confirm the actual active preset, not a hard-coded factory default:
tgk themes --json
tgk typography --json
```

`tgk config edit` accepts repeated `--field SECTION.KEY=JSON_VALUE` and
`--reset-field SECTION.KEY` options. Changes are validated together and
committed as one atomic file replacement; validation failure leaves the
previous configuration unchanged. String values must use JSON quoting
(e.g. `--field 'ui.theme="forest"'`). Changing a preset or saved breakpoint
does **not** force other per-instance overrides back to defaults. The layout
planner uses the configured column count, grid units, touch minimum and both
compact/expanded breakpoints unless individually overridden. It still
operates on Android **window dp**, not unverified physical display properties.

## Update an existing installation

For existing checkouts, update **the framework first**, followed by the
shell tools. This ensures the required TGK API is present before the tools
installer checks its dependencies:

```sh
cd ~/tgk
git switch main
git pull --ff-only
sh ./install.sh --copy

cd ~/tgk/tgk-tools
git switch main
git pull --ff-only
sh ./install.sh --copy

tgk doctor --connect
tgk config show
tgk size-plan --width-dp 393 --height-dp 852 --interactive --json
```

If the tools live in `~/tgk-tools`, replace the second `cd` with that
location. If you do not have a retained source checkout, clone the latest
repositories first, or use a recent successfully verified offline installer.
`--copy` installs durable non-editable packages, so deleting the checkouts
afterwards does not break Python import paths. The TGK installer fills in
missing config/preset files but **does not overwrite user-customized**
palettes, styles, option profiles or `config.json`. Inspect `git status`
before updating dirty or diverged branches; do not force-reset local work.

For an isolated installation use `PYTHON=/path/to/python sh ./install.sh --copy`
consistently for both repositories. `tgk doctor --connect` checks real
Termux:GUI IPC, while other commands can be tested on Linux without a GUI.

## Downloadable offline installer archive

The [GitHub Actions CI workflow](https://github.com/jerrecode/tgk-tools/actions/workflows/ci.yml) builds an artifact named **tgk-offline-installer** containing both TGK and TGK Tools sources, a combined `install.sh`, and installation instructions. Download the `tgk_bundle_v0.6.7.tar.gz` archive from a successful workflow run, then on Termux:

```sh
pkg install -y python clang
python -m pip install setuptools termuxgui
tar -xzf tgk_bundle_v0.6.7.tar.gz
cd tgk_bundle_v0.6.7
sh ./install.sh
tgk doctor --connect
```

That bundle installs both packages as **non-editable copies**; the extracted source directory may be removed once installed. You need a compatible Termux:GUI Android app for real GUI operations. To build this same bundle locally with sibling repository checkouts, run `python scripts/build_bundle.py --tgk-source ../tgk --out tgk_bundle_v0.6.7.tar.gz`. No x86 Linux binary is shipped; the C library is compiled on the installation device.

Bundle builds normalize timestamps, owner IDs and permissions so identical source contents produce identical archive bytes. Rebuilding at the same output path excludes the previous archive. CI verifies each downloadable bundle with `python scripts/check_bundle_install.py tgk_bundle_v0.6.7.tar.gz`: a disposable environment installs and reinstalls without network access, deletes the extracted sources, checks the installed C renderer and CLI, then uninstalls both packages. The checker requires Python 3.12+ and existing pip/setuptools/wheel build tools. This Linux installation check does not establish Android ABI or GUI correctness.

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
tgk demo --list                    # print the 16 supported interactive scenarios
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
are rejected before opening the Android GUI. For named native tool controls, use `--object-color TARGET.PROPERTY=#HEX`
(repeatable). Supported targets: `root`, `heading`, `input`, `button`,
`cancel`, `image`, `canvas`, `progress` and `*` (all tagged objects).
The property is `text` or `background`. Example:
`tgk files --theme ocean --object-color cancel.background=#7C2251
--object-color heading.text=#FFFFFF`. Unsupported targets/colors fail early.
These switches affect tagged native tool controls, not arbitrary internal
widgets inside `tgk demo`. 

For **per-widget overrides**,
programmers can use TGK's `colors={"role":"#HEX"}` on a nested component or
`background_color` / `text_color` on an individual object.

The `tgk demo` launcher exposes the same **16 increasingly complex layout
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

## Advanced typography, windows, semantic icons and UI laboratories

The new `tgk icons`, `tgk typography` and `tgk ui-lab` commands build
on TGK's advanced navigation and typography APIs.

```sh
tgk icons --json                       # full icon registry as JSON
tgk icons --category actions           # searchable/action symbol palette
tgk icons --path dataset.jsonl         # classify JSONL file
tgk icons --path /usr/lib --directory  # Linux directory icon
tgk icons --svg search --svg-size 64 --svg-color '#18D0F9' > search.svg
tgk files --start "$HOME" --icons --theme forest

tgk typography --json                  # all default font preset definitions
tgk typography --preview --theme paper # rich-text styled font gallery

tgk ui-lab --mode normal --start-page home --theme ocean
tgk ui-lab --mode dialog --start-page text --theme paper
# overlay requires "Display over other apps" in Termux:GUI advanced settings:
tgk ui-lab --mode overlay --start-page canvas --theme cyberpunk
```

The UI lab provides native TabLayout pages (home, icons, text, canvas,
nested screens), in-activity popup visibility, a bounded RGBA world viewport
with pan/pinch zoom, and HTML-formatted rich labels with JavaScript disabled.
This is not full Kivy, unrestricted floating windows, or arbitrary HTML/CSS
injection. App-level Android dialog/overlay windows operate as Activities;
Termux:GUI overlay activity lifecycle differs from ordinary Activities.

### Global typography and per-control overrides

```sh
tgk prompt --text-style terminal --font-family mono --font-size 19 \
  --font-weight 700 --font-color-role accent --theme ocean \
  --object-font heading.style=display \
  --object-font heading.size=30 \
  --object-color cancel.background=#6A274A \
  --title 'Your project'
```

The `--text-style` selector defaults to `body`, and offers fifteen other
presets including `display`, `title`, `small`, `terminal`, `code`,
`serif`, `quote`, `warning`, `danger`, `muted`, and `link`.
Other global overrides: `--font-family sans|serif|mono`, `--font-size`,
`--font-weight` (100..900 by 100), `--italic`, `--underline`,
`--strike`, `--text-align`, `--line-height`, and
`--font-color-role`.

For individual tagged native widgets, repeat
`--object-font TARGET.FIELD=VALUE`: valid TARGET names are `root`,
`heading`, `input`, `button`, `cancel`, `image`, `canvas`,
`progress`, or `*` for generic fallback. Valid FIELD names are
`style`, `size`, `family`, `weight`, `italic`, `underline`,
`strike`, `align`, `line_height` and `role`.

**Native rendering limitation:** Termux:GUI's ordinary TextViews support
text size, gravity and color, **not** general font families, bold, italic,
underline or mixed-span styling. TGK stores these properties as validated
style metadata and renders their full semantics using its
`RichTextLabel` WebView. A `--font-family` flag on an ordinary native
button does not magically add a typeface setter that the Android bridge
doesn't expose. The UI lab and typography gallery demonstrate the rich
WebView path.

Semantic icons use Unicode fallback glyphs for all named categories and
a small self-contained SVG stroke subset; glyph appearance depends on
Android fallback fonts. Exported SVG must be rasterized separately before
display in a native ImageView.

The `examples/` gallery now includes additional workflows:
`11_typography_gallery.sh`, `12_icon_catalog.sh`,
`13_icon_file_picker.sh`, `14_multiview_lab.sh`,
`15_dialog_window.sh`, `16_system_overlay.sh`,
`17_svg_vector_library.sh`, `18_custom_ui_style.sh`.
```sh
sh examples/11_typography_gallery.sh
sh examples/14_multiview_lab.sh
sh examples/18_custom_ui_style.sh
```

The advanced TGK core APIs have been merged into `jerrecode/tgk/main`.
This tools feature branch now tests against the installed default TGK core
branch; no temporary checkout of an unmerged core branch is required.

## Environment and resource capability diagnostics

`tgk doctor --json` now includes both installed package versions,
`native_view_id_dispatch` (O(1) scalar-ID event routing),
`bounded_io_available`, optional `ffmpeg_executable` and
`ffprobe_executable` paths, and the existing native renderer and Android
connection diagnostics. Running without `--connect` does not open an Android
Activity or require Termux:GUI. On Android:

```sh
tgk doctor --json
tgk doctor --connect
pkg install ffmpeg  # only needed for optional tgk pipeline probe and FFmpeg tools
```

These capability flags show **software availability**, not actual frame rates
or the results of a hardware validation. Run GUI tests on your device.

## Bounded media and data processing — non-GUI pipeline commands

The `tgk pipeline` subcommand is a composable, JSON-output interface to
TGK's resource-bounded binary streaming library. It works in Termux or
ordinary Python without opening an Android Activity.

```sh
tgk pipeline hash video.mp4 --chunk-bytes 65536 --max-bytes 536870912
tgk pipeline copy video.mp4 /tmp/video-copy.mp4 --timeout 30
tgk pipeline probe video.mp4 --timeout 10
tgk pipeline download https://example.org/data.bin /tmp/data.bin \
    --allow-host example.org --max-bytes 10485760 --timeout 20
```

- `hash`: stream SHA-256 and byte count without accumulating the input.
- `copy`: atomic sibling temporary file + rename; `--overwrite` is
  mandatory to replace an existing file.
- `probe`: local FFprobe metadata (`pkg install ffmpeg`), with bounded
  JSON response and deadline.
- `download`: opt-in HTTPS-only by default, with redirect refusal,
  optional repeatable `--allow-host`, and explicit `--allow-http`
  for insecure endpoints.

Every successful command prints exactly one JSON object on stdout; errors
go to stderr and exit with code 2. `--max-bytes`, `--chunk-bytes`,
`--max-metadata-bytes` and `--timeout` are validated. No shell-string
interpolation is used. HTTP(S) host allowlists are not DNS/IP SSRF defenses:
treat remote resources as untrusted and apply network policy externally.

Direct Python users can access `tgk.io_pipeline.Limits`,
`transfer()`, `copy_file()`, `hash_file()`, `download()`,
`ffprobe()` and `BoundedPool` for configurable small-thread-pool
pipelines with bounded in-flight submissions.

These are foundations for future FFmpeg frame extraction, buffering,
streaming and format-specific processors; no broad protocol support or
full media playback is claimed. Benchmarks and power use on Android remain
to be measured.

## Responsive Android UI and design-system CLI (TGK 0.6.1)

The new commands expose a **12-column Android window-dp grid**, extended
component palettes, typography hierarchy, styled tables and configurable
per-Activity touch minima. `layout-plan` can run without Android.

```sh
tgk layout-plan --width-dp 393 --height-dp 852 --items 8 --json
tgk layout-plan --width-dp 920 --height-dp 430 --spans 12,6,4 --json
tgk layout-plan --connect --json     # Termux:GUI's actual window configuration
tgk style-catalog --theme ocean --json
tgk adaptive-demo --theme forest --orientation system --touch-target-dp 56
tgk adaptive-demo --orientation landscape --grid-unit-dp 8
```

Window metrics have width/height dp, logical aspect, orientation, density
and font scale. Android Activity `getconfiguration()` supplies **window**
dimensions. Hardware maximum refresh rate, physical maximum pixel
resolution, screen color depth and explicit status-bar inset measurements
are **not available through this binding**; the JSON reports `null`,
never guessed numbers. Normal Android Activities already get a content
viewport below system chrome, so no extra hard-coded status bar offset is
applied. Adaptive spans change on Android `config` events via native
`setgridlayoutparams`, without rebuilding the view tree.

The `--spans COMPACT,MEDIUM,EXPANDED` option may be repeated to define
each item's spans (integers 1–12); otherwise defaults are 12, 6 and 4.
Breakpoints are compact (<600dp), medium (600–839dp), expanded (>=840dp).
`--grid-unit-dp` sets spacing increments and
`--touch-target-dp` changes the interactive minimum for that Activity.
The default is 48dp; smaller than 32dp is rejected by the CLI.

`style-catalog` prints all current semantic theme colors (including
button pressed/active/inactive, tab active/inactive, table striping,
selection, input, dropdown, panel and navigation backgrounds), typography
presets and component geometry. Each predefined theme includes the same
roles, with color variants derived from the theme's base colors.
Styles can still be overridden for individual objects in Python.
Native Android Views do not support all declarative styling fields:
fully styled row/column borders, backgrounds and text weight are
available in TGK's local `RichTable` WebView.

The advanced sample scripts include:
`examples/22_adaptive_layout_plan.sh`,
`examples/23_android_screen_metrics.sh`,
`examples/24_responsive_mobile_demo.sh`, and
`examples/25_component_style_catalog.sh`.

Hardware touch and orientation behavior must be checked on a real Android
device. Linux CI verifies API semantics, geometry calculations, model
reflow and installability, not native graphical fidelity.

## Python-path performance baseline (bounded and reproducible)

`tgk benchmark` measures four TGK *Python* execution paths: widget-tree
traversal, indexed event dispatch, local style invalidation, and bounded
Clock callbacks. Results include median/p95 nanoseconds per operation across
independent samples. The benchmark deliberately never creates an Android
Activity, does not use real Termux:GUI IPC, and **cannot** measure actual UI
frame rate, GPU performance, touchscreen-to-display latency or battery use.
Use the JSON output to compare changes on the same Termux device and Python
version, not to compare dissimilar hardware without context.

```sh
tgk benchmark --nodes 256 --iterations 500 --samples 3
tgk benchmark --nodes 1000 --iterations 500 --samples 4 --json
sh examples/26_cpu_performance_baseline.sh
```

Controls: `--nodes` 1–5000, `--iterations` 1–10000,
`--samples` 1–10; the total product may not exceed 2 million
node-iterations. The Clock benchmark processes pending callbacks in chunks of
128 to exercise GUI-tick fairness. No external network or shell subprocess
is started. `tgk doctor --connect` remains the separate native Termux:GUI
connection validation entrypoint.

## Mobile-sized Close / Cancel controls

All shell dialogs and viewers use compact action footers instead of stretching
Close or Cancel buttons across the screen. A 48dp-high button receives a
text-bounded width, a weighted spacer on its left, and 12dp bottom/right
margins. Files and progress tools use Termux:GUI native LinearLayouts;
TGK-based prompt/confirm/choose/show and rich typography UI use the matching
framework widget footer.

Scrollable content takes the remaining vertical space so Close remains
reachable near the screen's bottom-right, even on short portrait phones.
Use Android's Back action as an alternative. Per-object `--object-color`
overrides continue to apply to Close/Cancel roles.

## Layered icon builder (TGK 0.6.1)

The icon catalog now supports hierarchical SVG recipes with reusable base
shapes and foreground modifiers such as text lines, code markers, pens,
terminal prompt, archive zippers, locks, badges and automatically scaled
filetype labels. This includes README, LICENSE, AGENTS, INSTALL, INFO, MAKE,
REQ and uppercase labels for Python, JSONL, HTML, CSS, XML, YAML, TOML,
TeX, C, H, JavaScript, Java and many more extensions.

```sh
# Backward-compatible general classification
tgk icons --path README.md --json
# Specific filename-layered SVG design
tgk icons --path README.md --detailed --json
tgk icons --svg filename_readme_md > readme.svg

# Build and validate all known SVG combinations before publication
tgk icons-build --output /tmp --overwrite
# Limit the build to specific icon recipes
tgk icons-build --output /tmp --overwrite \
  --icon file_ext_jsonl --icon filename_agents_md --icon file_document

# Build low/mid/high PNG and JPEG, plus ICO (CairoSVG + Pillow required)
python -m pip install cairosvg pillow
tgk icons-build --output /tmp --raster --overwrite
```

The output is `/tmp/icons/svg`, `/tmp/icons/ico`,
`/tmp/icons/low_res`, `/tmp/icons/mid_res`,
`/tmp/icons/high_res` and `/tmp/icons/manifest.json`. The default
raster dimensions are 32, 96 and 256 pixels, and ICO contains several
small resolutions. A pure SVG build leaves raster directories empty.

The generator validates **every** recipe before writing a staging
directory, then publishes the whole icon pack atomically after success.
Existing output cannot be overwritten without an explicit flag. No
user-provided strings are evaluated as code, and generated names are
validated. A GitHub Actions workflow provides a complete downloadable
`tgk-layered-icon-pack` asset artifact; device raster quality remains
subject to font/rendering differences.

## Persistent, editable configuration and preset catalogs (0.6.1)

Installing TGK now creates a private XDG config directory (or
`TGK_CONFIG_HOME`) containing `config.json`, `palettes/*.json`,
`text_styles/*.json`, and `options/*.json`. Every available color
scheme and typography preset is initialized with its defaults. Reinstalling
creates missing files **without replacing edits**.

```sh
tgk config init                             # create missing presets only
tgk config path                             # active config/preset directory
tgk config show --compact                   # full validated runtime config as JSON
tgk config validate                         # reject malformed settings
tgk config palette ocean --compact          # inspect edited palette
tgk config typography title_h2 --compact    # inspect edited font style
tgk config options battery_saver --compact  # inspect named option profile
```

Set `ui.theme` and `ui.text_style` in `config.json` to select a
default palette/style for every subsequent invocation. Change the associated
preset JSON file to modify semantic colors and font properties without editing
Python source. Explicit `--theme`, `--theme-file`, `--color`,
`--text-style` and font CLI parameters take precedence and never modify
the saved settings.

The same config controls responsive 12-column layout and minimum touch
target sizes, orientation/window mode, maximum Clock jobs per tick, idle
sleep time, bounded I/O defaults, icon output dimensions and default
`tgk files --max-items`, `tgk canvas-demo --fps`,
`tgk progress --max-progress-json-bytes`, and
`tgk icons-build --low/--mid/--high` values. Every setting has a
schema/range check; invalid or corrupt configuration produces an explicit
error rather than silently resetting to factory settings.

For a different root, set `export TGK_CONFIG_HOME=/path/to/config`.
A configuration edit takes effect when a new CLI process or GUI App starts.
See the [TGK core README](https://github.com/jerrecode/tgk) for the
complete JSON schema and precedence contract.

## Persistently select defaults (TGK Tools 0.6.2)

TGK Tools now delegates multi-setting updates to TGK 0.6.3's atomic
`patch_config()` API. A single `tgk config set` changes the selected
palette, typography, option profile, orientation and window mode as **one
validated transaction**. Errors leave the prior config untouched. The
option profile is saved as a name rather than an irreversible numeric
snapshot. Global defaults remain overrideable by CLI flags or per-widget
options.


TGK installs editable JSON configuration beneath `~/.config/tgk/` or the
directory chosen through `TGK_CONFIG_HOME` / `XDG_CONFIG_HOME`.
The TGK Tools installer now also initializes any missing files, including
when TGK was installed separately. Reinstalling never overwrites modified
palette/text/option presets.

```sh
tgk config init                 # initialize missing preset files
tgk config show                 # inspect current effective defaults
tgk config list                 # list installed named profiles
tgk config set --palette forest --typography terminal
tgk config set --orientation system --window-mode normal
tgk config set --options performance
tgk config set --options battery_saver
```

The `set` command validates and atomically writes `config.json`. A selected
options profile is now saved as `ui.option_profile`, **not** as a copied
snapshot of its numeric settings. Switching from `battery_saver` to
`performance` therefore changes inherited worker counts and scheduling
budgets instead of leaving the old snapshot pinned. Individually edited
settings retain precedence over a profile; editable preset files are not
overwritten. New apps inherit saved defaults, while explicit `--theme`,
`--text-style`, and App constructor options still win.

For individual numeric values, TGK 0.6.2 supports typed, validated writes:

```sh
python -m tgk.config set layout touch_target_dp 64
python -m tgk.config get layout touch_target_dp
python -m tgk.config set runtime clock_callbacks_per_tick 80
```

`tgk config set --options battery_saver` and other named presets require no
hand-editing or manual JSON reformatting.

The existing `tgk config palette NAME`, `typography NAME`, and `options NAME`
continue to inspect individual preset files. The configuration is per-user
and does not adjust Android system-wide settings.

## Viewport-aware widget sizing preview (TGK 0.6.6)

`tgk size-plan` resolves TGK's opt-in `SizeSpec` controls in Android
content-window dp. It accepts fixed or viewport-relative dimensions,
optional min/max dp and fraction caps, margins, aspect ratio containment,
and a configurable interactive touch minimum. It is deterministic and
does not require Termux:GUI unless `--connect` is supplied.

```sh
tgk size-plan --width-dp 393 --height-dp 852 \
  --item-width-fraction .5 --item-height-fraction .5 \
  --max-height-fraction .2 --interactive --json
tgk size-plan --width-dp 915 --height-dp 412 \
  --item-width-dp 240 --item-height-dp 120 \
  --aspect-ratio 1 --fit contain --json
tgk size-plan --connect --item-width-fraction .9 --json
```

Existing `tgk layout-plan` and `tgk adaptive-demo` continue to honor
configured physical grid columns and their 12-unit logical span mapping.
This release makes installed TGK Tools package metadata, its Python version,
and the downloadable `tgk_bundle_v0.6.7.tar.gz` agree.

Physical display FPS, panel resolution, and unknown status-bar insets are
not guessed; Android hardware validation is still required.

## Concurrent-safe configuration diagnostics (TGK 0.6.7)

The TGK 0.6.7 core now serializes simultaneous `config.json` updates from
independent processes using a private POSIX `flock` file. TGK Tools 0.6.7
requires this core version. `sh ./install.sh` installs missing default
palettes, text styles, option profiles, and the main configuration without
overwriting user modifications.

Run the diagnostic after installation, configuration edits, or changing
option presets:

```sh
tgk config init                 # create only missing preset files
tgk config doctor               # detailed install and lock diagnostics
tgk config doctor --compact     # machine-readable, single-line JSON
tgk config list                 # available themes/fonts/option profiles
tgk config set --palette ocean --typography title_h2 --options battery_saver
```

The doctor validates the selected theme/font/profile and reports missing
default preset files, config permissions and whether the write lock is
available **at inspection time**. Exit status is 0 when healthy or 2 when
repair is needed; even failures return a JSON report on stdout. A busy lock
does not prove the configuration is damaged—it may mean another Termux
session is writing it. The diagnostic does not overwrite settings.

All persistent updates remain atomic and bounded: cross-process locking is
handled by the core, while each application and CLI can still override saved
defaults explicitly. Direct manual edits made by other programs do not
participate in the lock unless those programs also acquire it.

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

## Native-grid scaling and saved layout settings (0.6.3)

`tgk layout-plan` and `tgk adaptive-demo` now use the saved
`layout.columns`, `layout.grid_unit_dp` and `layout.touch_target_dp`
from `~/.config/tgk/config.json` (including active option-profile defaults).
Explicit CLI options override those values **without writing** to the saved
configuration.

```sh
# Exact native columns, with design spans still specified in 12 logical units:
tgk layout-plan --width-dp 393 --height-dp 852 \\
  --columns 6 --span-units 12 --items 12 --json

# Load persistent settings (including the selected accessibility profile):
tgk config set --options accessibility_touch
tgk layout-plan --width-dp 393 --height-dp 852 --json

# Native Android GUI (needs Termux:GUI):
tgk adaptive-demo --columns 6 --orientation system
```

The planner exposes both `grid.columns` (real Android GridLayout columns)
and `grid.span_units` (virtual layout units), plus the resolved gutter in
dp. A 12-unit span becomes six physical columns when `--columns 6` is
selected; a span of four becomes two. Touch-target width and height minima
are enforced on TGK native widgets, while `allow_small_touch_target=True`
explicitly opts out for specialized controls. Hardware FPS, physical display
size and system-bar insets remain unknown unless a supported Android API
provides them.

## Durable TGK Tools installation (0.6.4)

`sh ./install.sh` now installs TGK Tools as a **self-contained copy** by
default. The source checkout can be moved or removed afterwards, and the
`tgk`/`tgk-tools` executables will still load from site-packages. For
active development, use `sh ./install.sh --editable` to link imports to
the repository instead. `--copy` selects the durable mode explicitly and
`--help` displays usage; unknown options fail before modifying anything.

The offline source bundle continues compiling the TGK C renderer for the
installation device and checking the resulting non-editable installation in
a disposable environment. A green Linux bundle check confirms Python and C
packaging, **not** Termux:GUI Android service compatibility or touch/render
accuracy. Existing user-modified `~/.config/tgk` presets are initialized in
create-only mode and are not overwritten.
