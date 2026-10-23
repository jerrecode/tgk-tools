"""Shell-first management of TGK's editable, persistent configuration."""
from __future__ import annotations
import json
from pathlib import Path

from tgk.config import (config_home,config_path,initialize_config,load_config,
                        option_config,_read_json)


def _atomic_persist(selected):
    """Validate and atomically replace the user's own config, never presets."""
    import os
    import tempfile
    from tgk.config import validate_config,MAX_JSON_BYTES
    value=validate_config(selected)
    path=config_path()
    if path.is_symlink():raise ValueError("refusing to overwrite a config symlink")
    data=(json.dumps(selected,ensure_ascii=False,indent=2,sort_keys=True)+"\\n").encode("utf-8")
    if len(data)>MAX_JSON_BYTES:raise ValueError("configuration size limit exceeded")
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd,tmp=tempfile.mkstemp(prefix=".tgk-config-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            os.fchmod(out.fileno(),0o600)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp,path)
    finally:
        try:os.unlink(tmp)
        except FileNotFoundError:pass
    return value


def _apply_defaults(args):
    from tgk.config import DEFAULT_CONFIG,validate_config,OPTIONS,_safe_name
    from tgk.theme import PRESETS,load_theme
    from tgk.typography import PRESETS as TEXT_PRESETS
    from copy import deepcopy

    raw=_read_json(config_path()) if config_path().exists() else deepcopy(DEFAULT_CONFIG)
    # Reject unknown/unsafe settings before applying any patches.
    validate_config(raw)
    ui=raw.setdefault("ui",{})
    if args.palette is not None:
        name=_safe_name(args.palette)
        if name not in PRESETS:raise ValueError("unknown palette preset "+name)
        candidate=config_home()/"palettes"/(name+".json")
        if candidate.exists():load_theme(candidate)
        ui["theme"]=name
    if args.typography is not None:
        name=_safe_name(args.typography)
        if name not in TEXT_PRESETS:raise ValueError("unknown typography preset "+name)
        ui["text_style"]=name
    if args.orientation is not None:ui["orientation"]=args.orientation
    if args.window_mode is not None:ui["window_mode"]=args.window_mode

    if args.options is not None:
        name=_safe_name(args.options)
        snapshot=option_config(name)  # validates even custom option files
        # Profile selection is an explicit snapshot: persist those defaults.
        # Users may subsequently edit any individual setting in config.json.
        if name in OPTIONS:
            source=OPTIONS[name]
        else:
            source=_read_json(config_home()/"options"/(name+".json"))["settings"]
        for section,values in source.items():
            target=raw.setdefault(section,{})
            target.update(values)
        validate_config(snapshot)
    saved=_atomic_persist(raw)
    return {"settings":saved,"profile_applied":args.options,
            "config_path":str(config_path())}


def _list_presets():
    from tgk.config import OPTIONS
    from tgk.theme import PRESETS
    from tgk.typography import PRESETS as TEXT_PRESETS
    result={"palettes":sorted(PRESETS),"typography":sorted(TEXT_PRESETS),
            "options":sorted(OPTIONS)}
    for folder,key in (("palettes","palettes"),("text_styles","typography"),
                       ("options","options")):
        base=config_home()/folder
        if base.is_dir():
            result[key]=sorted(set(result[key])|{
                file.stem for file in base.glob("*.json") if file.stem.isidentifier()})
    return result


def run_config(args):
    action=args.action
    if action=="init":
        result=initialize_config()
    elif action=="show":
        result=load_config()
    elif action=="validate":
        result={"valid":True,"config_path":str(config_path()),
                "settings":load_config()}
    elif action=="path":
        result={"config_path":str(config_path()),
                "preset_root":str(config_home())}
    elif action=="palette":
        if not args.name:raise ValueError("palette requires NAME")
        from tgk.config import _safe_name
        from tgk.theme import load_theme
        name=_safe_name(args.name)
        path=config_home()/"palettes"/(name+".json")
        result=load_theme(path).to_dict()
    elif action=="typography":
        if not args.name:raise ValueError("typography requires NAME")
        from tgk.config import _safe_name
        name=_safe_name(args.name)
        path=config_home()/"text_styles"/(name+".json")
        data=_read_json(path)
        from tgk.typography import resolve_text_style
        style=resolve_text_style(data.get("style",name),**data.get("properties",{}))
        from dataclasses import asdict
        result={"name":name,"style":asdict(style),"source":str(path)}
    elif action=="options":
        if not args.name:raise ValueError("options requires NAME")
        result={"profile":args.name,"settings":option_config(args.name)}
    elif action=="list":
        result=_list_presets()
    elif action=="set":
        result=_apply_defaults(args)
    else:raise ValueError("unknown config operation")
    print(json.dumps(result,ensure_ascii=False,indent=None if args.compact else 2,
                     sort_keys=True,separators=(",",":") if args.compact else None))
    return 0
