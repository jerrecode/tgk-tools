"""Read-only, bounded views of installed TGK palette and typography presets."""
from __future__ import annotations

import os
from pathlib import Path
import stat

from tgk.config import config_home, _read_json, _safe_name
from tgk.theme import PRESETS as PALETTES, load_theme, resolve_theme
from tgk.typography import PRESETS as TEXT_STYLES, resolve_text_style


def _directory(folder):
    root = config_home()
    directory = root / folder
    if root.is_symlink() or directory.is_symlink():
        raise ValueError("symlink preset directory is not allowed: " + str(directory))
    if directory.exists() and not directory.is_dir():
        raise ValueError("preset path is not a directory: " + str(directory))
    return directory


def preset_names(catalogs, *, max_files=2000):
    """Union installed names with built-ins, bounding *all* directory entries.

    Listing names does not parse their contents; catalog commands validate each
    definition before emitting output. No configuration tree is initialized.
    """
    if type(max_files) is not int or not 1 <= max_files <= 5000:
        raise ValueError("max_files must be an integer in 1..5000")
    inspected = 0
    result = {}
    for folder, builtin in catalogs.items():
        names = set(builtin)
        directory = _directory(folder)
        if directory.exists():
            with os.scandir(directory) as entries:
                for entry in entries:
                    inspected += 1
                    if inspected > max_files:
                        raise ValueError("too many preset directory entries")
                    if Path(entry.name).suffix != ".json":
                        continue
                    details = entry.stat(follow_symlinks=False)
                    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                        raise ValueError("preset must be a regular nonlinked file: " + entry.path)
                    names.add(_safe_name(Path(entry.name).stem))
        result[folder] = sorted(names)
    return result


def load_palette_named(name):
    name = _safe_name(name)
    path = _directory("palettes") / (name + ".json")
    if path.exists() or path.is_symlink():
        return load_theme(path)
    return resolve_theme(name)


def load_text_named(name):
    name = _safe_name(name)
    path = _directory("text_styles") / (name + ".json")
    if not path.exists() and not path.is_symlink():
        return resolve_text_style(name)
    entry = _read_json(path)
    if set(entry) - {"style", "properties"} or not isinstance(entry.get("properties"), dict):
        raise ValueError("invalid typography preset: " + str(path))
    try:
        return resolve_text_style(entry.get("style", name), **entry["properties"])
    except TypeError as exc:
        raise ValueError("invalid typography preset: " + str(path) + ": " + str(exc)) from exc


def palette_entries():
    names = preset_names({"palettes": PALETTES})["palettes"]
    return {name: load_palette_named(name) for name in names}


def text_entries():
    names = preset_names({"text_styles": TEXT_STYLES})["text_styles"]
    return {name: load_text_named(name) for name in names}
