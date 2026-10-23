"""Shell-first management of TGK's editable, persistent configuration."""
from __future__ import annotations
import json
from pathlib import Path

from tgk.config import (config_home,config_path,initialize_config,load_config,
                        option_config,_read_json)


def _apply_defaults(args):
    """Save selected defaults with a single validated framework transaction.

    The --options flag persists the profile selector itself. Effective values
    are derived on load; previously customized settings remain unchanged.
    """
    from tgk.config import patch_config,option_config,_safe_name
    changes={"ui":{}}
    for argument,key in (("palette","theme"),("typography","text_style"),
                         ("options","option_profile"),
                         ("orientation","orientation"),("window_mode","window_mode")):
        requested=getattr(args,argument,None)
        if requested is not None:
            if key in ("theme","text_style","option_profile"):
                _safe_name(requested)
            changes["ui"][key]=requested
    if not changes["ui"]:raise ValueError("no settings to update")
    if args.options is not None:
        option_config(args.options)
    saved=patch_config(changes)
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
