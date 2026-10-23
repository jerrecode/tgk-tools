"""Validated, lazy views of installed user-editable TGK palette/font catalogs."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import re

from tgk.config import config_home,load_config,_read_json
from tgk.theme import PRESETS as BUILTIN_COLORS,load_theme,resolve_theme
from tgk.typography import PRESETS as BUILTIN_TEXT,resolve_text_style

_SAFE=re.compile(r"^[a-z][a-z0-9_]{0,70}$")


def _names(folder,builtin):
    result=set(builtin)
    if folder.exists():
        if not folder.is_dir():raise ValueError("TGK preset path is not a directory")
        files=tuple(folder.glob("*.json"))
        if len(files)>256:raise ValueError("too many user preset files")
        for path in files:
            if not _SAFE.fullmatch(path.stem):raise ValueError("invalid user preset filename")
            result.add(path.stem)
    return tuple(sorted(result))


def load_palette_named(name):
    if not _SAFE.fullmatch(name):raise ValueError("invalid theme name")
    candidate=config_home()/"palettes"/(name+".json")
    return load_theme(candidate) if candidate.is_file() else resolve_theme(name)


def palette_entries():
    folder=config_home()/"palettes"
    return {name:load_palette_named(name) for name in _names(folder,BUILTIN_COLORS)}


def load_text_named(name):
    if not _SAFE.fullmatch(name):raise ValueError("invalid typography name")
    file=config_home()/"text_styles"/(name+".json")
    if not file.is_file():return resolve_text_style(name)
    data=_read_json(file)
    if set(data)-{"style","properties"} or not isinstance(data.get("properties"),dict):
        raise ValueError("invalid typography preset file: "+str(file))
    return resolve_text_style(data.get("style",name),**data["properties"])


def text_entries():
    folder=config_home()/"text_styles"
    return {name:load_text_named(name) for name in _names(folder,BUILTIN_TEXT)}


def current_defaults():
    ui=load_config()["ui"]
    return {"palette":ui["theme"],"typography":ui["text_style"],
            "option_profile":ui["option_profile"]}
