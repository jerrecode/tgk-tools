"""Persistent TGK preferences: inspect, validate, initialize, and set defaults."""
from __future__ import annotations
import json
from tgk import config as configuration


def run_config(args):
    action=args.action
    if action=="init":
        data=configuration.init_config()
        data["validated"]=configuration.validate_installation()
    elif action=="validate":
        data=configuration.validate_installation()
    elif action=="paths":
        data={key:str(value) for key,value in configuration.paths().items()}
    elif action=="list":
        data={"palettes":sorted(configuration.color_registry()),
              "typography":sorted(configuration.text_registry()),
              "options":sorted(configuration.option_registry())}
    elif action=="set":
        data=configuration.set_defaults(
            palette=args.palette,typography=args.typography,options=args.options,
            orientation=args.orientation,window_mode=args.window_mode)
    else:
        data={"settings":configuration.settings(),
              "effective_layout":vars(configuration.layout_scale()),
              "effective_runtime":configuration.runtime_settings(),
              "defaults":configuration.validate_installation()}
    if args.json:
        print(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2))
    else:
        for key,value in data.items():
            print(f"{key}: {value}")
    return 0
