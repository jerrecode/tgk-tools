"""Shell-first management of TGK's editable, persistent configuration."""
from __future__ import annotations
import json
from pathlib import Path

from tgk.config import (config_home,config_path,initialize_config,load_config,
                        option_config,_read_json)


def _apply_defaults(args):
    """Save all selected defaults in one atomic TGK core config transaction."""
    from tgk.config import patch_config,initialize_config,_safe_name
    changes={"ui":{}}
    for flag,key in (("palette","theme"),("typography","text_style"),
                     ("options","option_profile"),
                     ("orientation","orientation"),("window_mode","window_mode")):
        value=getattr(args,flag,None)
        if value is not None:
            if key in ("theme","text_style","option_profile"):_safe_name(value)
            changes["ui"][key]=value
    if not changes["ui"]:raise ValueError("at least one new default is required")
    # Keep the historical config set convenience on a new installation.
    # The framework installer also creates this tree with create-only writes.
    if not config_path().is_file():initialize_config()
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


def _edit_fields(args):
    """Validate every field and commit one atomic patch to config.json."""
    from tgk.config import patch_config,initialize_config,DEFAULT_CONFIG
    changes={}
    resets=[]
    seen=set()
    for item in args.field or ():
        if "=" not in item or "." not in item.split("=",1)[0]:
            raise ValueError("--field requires SECTION.KEY=JSON_VALUE")
        path,serialized=item.split("=",1)
        section,key=path.split(".",1)
        if (section,key) in seen:
            raise ValueError("duplicate edited setting: "+path)
        seen.add((section,key))
        try:value=json.loads(serialized)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid JSON value for "+path+": "+str(exc)) from exc
        changes.setdefault(section,{})[key]=value
    for item in args.reset_field or ():
        if "." not in item:raise ValueError("--reset-field requires SECTION.KEY")
        section,key=item.split(".",1)
        if (section,key) in seen:raise ValueError("setting both edited and reset: "+item)
        seen.add((section,key))
        resets.append((section,key))
    if not changes and not resets:
        raise ValueError("config edit requires --field and/or --reset-field")
    if not config_path().is_file():initialize_config()
    saved=patch_config(changes,reset=resets)
    return {"settings":saved,"changed":[s+"."+k for s,fields in changes.items()
                                       for k in fields],
            "reset":[s+"."+k for s,k in resets],
            "config_path":str(config_path())}


def _doctor():
    """Read-only assessment of selected profiles, durability and write contention.

    The only possible filesystem change is creation of the private lock inode,
    required for safe coordination. No preset or configuration values change.
    """
    import os
    from tgk import __version__
    from tgk.config import (_config_write_lock,configured_theme,
                            configured_text_style)
    from tgk.theme import PRESETS as PALETTES
    from tgk.typography import PRESETS as FONTS
    from tgk.config import OPTIONS
    home=config_home()
    path=config_path()
    checks={}
    problems=[]
    checks["config_exists"]=path.is_file() and not path.is_symlink()
    checks["preset_directories"]={
        name:(home/name).is_dir() and not (home/name).is_symlink()
        for name in ("palettes","text_styles","options")
    }
    expected={"palettes":PALETTES,"text_styles":FONTS,"options":OPTIONS}
    missing={}
    for folder,known in expected.items():
        missing[folder]=sorted(name for name in known
                               if not (home/folder/(name+".json")).is_file())
    checks["missing_default_presets"]=missing
    checks["config_file_mode"]=oct(path.stat().st_mode & 0o777) if path.is_file() else None
    if not checks["config_exists"]:problems.append("configuration not initialized")
    if any(not present for present in checks["preset_directories"].values()):
        problems.append("preset directories missing")
    if any(missing.values()):problems.append("default presets missing")
    if checks["config_exists"]:
        try:
            settings=load_config()
            theme=configured_theme()
            style=configured_text_style()
            option_config(settings["ui"]["option_profile"])
            checks["selected"]={
                "theme":theme.name,"text_style":settings["ui"]["text_style"],
                "option_profile":settings["ui"]["option_profile"],
                "orientation":settings["ui"]["orientation"]}
            checks["resolved_font_size"]=style.size
        except (ValueError,OSError,KeyError,TypeError) as exc:
            problems.append("invalid selected configuration or preset: "+str(exc))
        try:
            with _config_write_lock(home,timeout=0.1):
                checks["write_lock"]="acquired"
        except TimeoutError:
            checks["write_lock"]="busy"
            problems.append("another process currently holds the config lock")
        except (ValueError,OSError) as exc:
            checks["write_lock"]="error"
            problems.append("config lock unavailable: "+str(exc))
    else:
        checks["write_lock"]="not_checked"
    return {
        "healthy":not problems,"tgk_version":__version__,
        "config_path":str(path),"checks":checks,"problems":problems,
        "repair_command":"python -m tgk.config init",
    }


def run_config(args):
    action=args.action
    if action=="init":
        result=initialize_config()
    elif action=="show":
        result=load_config()
    elif action=="validate":
        result={"valid":True,"config_path":str(config_path()),
                "settings":load_config()}
    elif action=="audit":
        from tgk.config import audit_presets
        result=audit_presets(require_builtins=True,max_files=args.max_files)
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
    elif action=="edit":
        result=_edit_fields(args)
    elif action=="doctor":
        result=_doctor()
    else:raise ValueError("unknown config operation")
    print(json.dumps(result,ensure_ascii=False,indent=None if args.compact else 2,
                     sort_keys=True,separators=(",",":") if args.compact else None))
    return 2 if action=="doctor" and not result["healthy"] else 0
