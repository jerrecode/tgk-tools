"""User-visible TGK persistent configuration: show/init/set/list presets."""
from __future__ import annotations
import json

def run_config(args):
    from tgk.config import (config_directory,get_config,initialize_config,
                            update_config)
    if args.operation=="init":
        result=initialize_config()
    elif args.operation=="show":
        result={"directory":str(config_directory()),"config":get_config()}
    elif args.operation=="set":
        if not args.key or "." not in args.key or args.value is None:
            raise ValueError("config set requires SECTION.KEY VALUE")
        section,key=args.key.split(".",1)
        try:value=json.loads(args.value)
        except json.JSONDecodeError:value=args.value
        result={"updated":args.key,"directory":str(config_directory()),
                "config":update_config(section,key,value)}
    elif args.operation=="presets":
        from tgk.theme import PRESETS
        from tgk.typography import PRESETS as FONTS
        from tgk.style_tokens import DEFAULT_STYLES
        result={"directory":str(config_directory()),
                "palettes":sorted(PRESETS),
                "typography":sorted(FONTS),
                "components":sorted(DEFAULT_STYLES)}
    else:raise ValueError("invalid config operation")
    if args.json:
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    elif args.operation=="presets":
        for category,names in result.items():
            print(category+": "+(", ".join(names) if isinstance(names,list) else names))
    else:
        print(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True))
    return 0
