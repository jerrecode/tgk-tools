# TGK Examples — canonical entry points and aliases

TGK and TGK Tools share one set of framework/demo implementations. The shell
examples in this folder are **invocation recipes**, not separate copies of the
framework demos. Run `tgk demo --list` for all sixteen canonical TGK scenarios.

## Canonical interactive demos

| Goal | Canonical command | Convenience recipes |
|---|---|---|
| Switch between all TGK labs without reopening Termux:GUI | `tgk demo --gallery` | `05_gallery_scenarios.sh` |
| Live colors, RGB and swatches | `tgk demo --scenario 12_studio` | `07_theme_studio.sh`; TGK `examples/theme_studio.py` |
| Complex interactive controls | `tgk demo --scenario 13_workbench` | `08_complex_workbench.sh`; TGK `examples/complex_workbench.py` |
| Project → mode → demo, all within one Android Activity | `tgk workflow` | `09_composed_workflow.sh` |
| Tabs, screens and popup | `tgk ui-lab --mode normal` | `14_multiview_lab.sh` |
| Dialog with in-content titlebar/close | `tgk ui-lab --mode dialog` | `15_dialog_window.sh` |
| System overlay; explicit normal fallback | `tgk ui-lab --mode overlay --fallback-normal` | `16_system_overlay.sh` |
| Responsive grids | `tgk adaptive-demo` | `24_responsive_mobile_demo.sh`; TGK `examples/adaptive_layout.py` |

Do not run a separate `tgk choose` followed by `tgk demo` when a single
Activity should remain open; nested command substitution waits on the first
GUI's lifecycle on some Android/Termux:GUI versions. The unified gallery
keeps the window and process open while switching native ScreenManager pages.

## Data/output examples

- `01` themes, `11` typography, `12` icon catalog and `25` style-catalog print data.
- `02` native text prompt and confirmation; `03` multi-select; `04` file navigation;
  `13` icon-aware picker.
- `06` canvas renderer; `10` custom theme file; `17` raw SVG command output;
  `18` per-object styles.
- `19` bounded file/hash pipelines; `20` local FFprobe; `21` HTTPS download
  (requires URL, trusted hostname and output path).
- `22` offline layout plan; `23` Android window metrics; `26` CPU-path benchmark.
- `27` composable SVG catalog and `28` optional CairoSVG/Pillow PNG/JPEG/ICO pack.

## Icon output paths on Termux

The icon recipes no longer default to `/tmp`. By default they write to
`~/.cache/tgk/icon-examples/svg-catalog/icons/` and
`~/.cache/tgk/icon-examples/raster-pack/icons/`, respectively. They can
also use an explicit first argument or the `TGK_ICON_OUTPUT_DIR`
environment variable. Existing output inside those dedicated folders is
replaced only after the generator has staged and validated all assets.

Examples:

```sh
sh examples/27_layered_svg_catalog.sh
sh examples/28_multi_resolution_icon_pack.sh
sh examples/28_multi_resolution_icon_pack.sh "$HOME/storage/shared/Documents/my-icons"
```

Raster export requires CairoSVG and Pillow plus their native Cairo runtime.
On Termux, you can install dependencies using your preferred package manager
and `python -m pip install cairosvg pillow`. If the native library is
missing despite the Python package being installed, check the Termux
Cairo installation.

Normal Android `Activity` UI is not a desktop window manager: the dialog
titlebar is a native in-content row, not an operating-system-managed
resizable frame. System overlays may be unavailable due to permissions or
plugin protocol mismatch; using `--fallback-normal` reports the downgrade.
