"""CLI planning and Android Activity metrics for TGK adaptive layouts."""
from __future__ import annotations

from dataclasses import asdict
import json
from types import SimpleNamespace

from tgk.adaptive import ScreenMetrics,LayoutScale,arrange_spans
from tgk.style_tokens import DEFAULT_STYLES
from tgk.typography import PRESETS as TYPOGRAPHY
from tgk.theme import get_theme


def _metrics_for(args):
    if args.connect:
        import termuxgui as tg
        with tg.Connection() as c:
            activity=tg.Activity(c,intercept=True)
            try:
                return ScreenMetrics.from_configuration(activity.getconfiguration())
            finally:
                activity.finish()
    if args.width_dp is None or args.height_dp is None:
        raise ValueError("pass both --width-dp and --height-dp, or use --connect on Android")
    return ScreenMetrics(args.width_dp,args.height_dp,
                         density=args.density,font_scale=args.font_scale,
                         orientation=("landscape" if args.width_dp>args.height_dp else "portrait"))


def run_layout_plan(args):
    metrics=_metrics_for(args)
    cols=12
    children=[]
    if args.spans:
        for raw in args.spans:
            parts=raw.split(",")
            if len(parts)!=3:raise ValueError("--spans must be COMPACT,MEDIUM,EXPANDED")
            span=list(map(int,parts))
            if any(not 1<=number<=12 for number in span):
                raise ValueError("--spans must contain values from 1 to 12 in every size class")
            children.append(SimpleNamespace(span_compact=span[0],
                          span_medium=span[1],span_expanded=span[2]))
    else:
        for _ in range(args.items):
            children.append(SimpleNamespace(span_compact=12,span_medium=6,span_expanded=4))
    planner=LayoutScale(grid_unit_dp=args.grid_unit_dp,
                        touch_target_dp=args.touch_target_dp)
    positions=arrange_spans(children,columns=cols,metrics=metrics)
    result={"source":"termuxgui" if args.connect else "simulated",
            "screen":metrics.to_dict(),
            "grid":{"columns":cols,"unit_dp":planner.grid_unit_dp,
                    "touch_target_dp":planner.touch_target_dp,
                    "margin_dp":planner.margin(metrics),
                    "column_width_dp":round(planner.column_width(metrics),3),
                    "items":[{"row":r,"column":c,"row_span":rs,"col_span":cs}
                             for r,c,rs,cs in positions]}}
    if args.json:
        print(json.dumps(result,separators=(",",":")))
    else:
        print(f"{result['source']} window: {metrics.width_dp:g}x{metrics.height_dp:g}dp "
              f"({metrics.orientation}, {metrics.size_class})")
        print(f"Grid: {cols} columns, touch minimum {planner.touch_target_dp}dp")
        print("Hardware max FPS / physical resolution / depth / system insets: "
              "unknown unless separately provided")
        for i,(r,c,_,sp) in enumerate(positions):
            print(f"  {i+1:03d}: row={r}, col={c}, span={sp}")
    return 0


def run_style_catalog(args):
    import dataclasses
    styles={name:dataclasses.asdict(style) for name,style in DEFAULT_STYLES.items()}
    theme=get_theme()
    result={"theme":theme.name,"colors":dict(theme.colors),
            "typography":{name:dict(value) for name,value in TYPOGRAPHY.items()},
            "components":styles}
    if args.json:print(json.dumps(result,indent=2))
    else:
        print(f"Theme: {theme.name} ({len(theme.colors)} roles)")
        print("Typography: "+", ".join(result["typography"]))
        print("Component styles: "+", ".join(styles))
        print("Use --json for complete configurable values")
    return 0


def run_adaptive_demo(args):
    from tgk.adaptive_demo import AdaptiveLab
    from tgk.theme import get_theme
    from tgk.typography import get_text_style
    scale=LayoutScale(grid_unit_dp=args.grid_unit_dp,
                      touch_target_dp=args.touch_target_dp)
    app=AdaptiveLab(theme=get_theme(),text_style=get_text_style(),
                    layout_scale=scale,orientation_mode=args.orientation)
    app.run()
    return 0
