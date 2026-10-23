"""Shell-first management of TGK's editable, persistent configuration."""
from __future__ import annotations
import json
from pathlib import Path

from tgk.config import (config_home,config_path,initialize_config,load_config,
                        option_config,_read_json)


def _apply_defaults(args):
    """Persist all selected defaults as ONE fully validated transaction."""
    from tgk.config import update_settings,option_config,_safe_name
    from tgk.theme import PRESETS as PALETTES,load_theme
    from tgk.typography import PRESETS as FONTS
    ui={}
    if args.palette is not None:
        name=_safe_name(args.palette)
        preset=config_home()/"palettes"/(name+".json")
        if name not in PALETTES and not preset.is_file():
            raise ValueError("unknown palette preset "+name)
        if preset.is_file():load_theme(preset)
        ui["theme"]=name
    if args.typography is not None:
        name=_safe_name(args.typography)
        preset=config_home()/"text_styles"/(name+".json")
        if name not in FONTS and not preset.is_file():
            raise ValueError("unknown typography preset "+name)
        ui["text_style"]=name
    if args.options is not None:
        name=_safe_name(args.options)
        option_config(name)  # validate the profile before changing anything
        ui["option_profile"]=name
    if args.orientation is not None:ui["orientation"]=args.orientation
    if args.window_mode is not None:ui["window_mode"]=args.window_mode
    settings=update_settings({"ui":ui})
    return {"settings":settings,"profile_applied":args.options,
            "config_path":str(config_path())}


def _edit_one_setting(args):
    from tgk.config import update_config
    if not args.name or not args.key:
        raise ValueError("edit/reset requires SECTION KEY")
    if args.action=="reset":
        if args.value is not None:raise ValueError("reset does not accept VALUE")
        settings=update_config(args.name,args.key,None,reset=True)
    else:
        if args.value is None:raise ValueError("edit requires SECTION KEY VALUE")
        try:value=json.loads(args.value)
        except json.JSONDecodeError:value=args.value
        settings=update_config(args.name,args.key,value)
    return {"settings":settings,"config_path":str(config_path())}


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
    elif action in ("edit","reset"):
        result=_edit_one_setting(args)
    else:raise ValueError("unknown config operation")
    print(json.dumps(result,ensure_ascii=False,indent=None if args.compact else 2,
                     sort_keys=True,separators=(",",":") if args.compact else None))
    return 0
