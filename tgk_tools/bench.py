"""Reproducible, bounded TGK *Python-side* microbenchmarks.

No Android GUI Activity or native socket connection is created. In particular
these timings MUST NOT be described as Android FPS or live touch latency.
"""
from __future__ import annotations

import json
import math
import platform
import statistics
import sys
from time import perf_counter_ns
from types import SimpleNamespace

from tgk.widgets import BoxLayout,Button,TermuxBackend,_Clock


def _stats(measure,operations,samples):
    observations=[]
    for _ in range(samples):
        began=perf_counter_ns()
        count=measure()
        elapsed=perf_counter_ns()-began
        if count!=operations:raise RuntimeError("benchmark operation count mismatch")
        observations.append(max(0,elapsed)/operations)
    ordered=sorted(observations)
    index=min(len(ordered)-1,math.ceil(.95*len(ordered))-1)
    return {
        "operations_per_sample":operations,
        "samples":samples,
        "median_ns_per_operation":round(statistics.median(observations),2),
        "p95_ns_per_operation":round(ordered[index],2),
        "min_ns_per_operation":round(ordered[0],2),
        "max_ns_per_operation":round(ordered[-1],2),
    }


class _CountingView:
    def __init__(self,id):
        self.id=id
        self.background_messages=0
        self.text_messages=0
        self.size_messages=0
    def setbackgroundcolor(self,color):self.background_messages+=1
    def settextcolor(self,color):self.text_messages+=1
    def settextsize(self,size):self.size_messages+=1


def benchmark(nodes=256,iterations=500,samples=3):
    """Benchmark deterministic API paths with hard work limits."""
    if type(nodes) is not int or not 1<=nodes<=5000:
        raise ValueError("nodes must be in 1..5000")
    if type(iterations) is not int or not 1<=iterations<=10000:
        raise ValueError("iterations must be in 1..10000")
    if type(samples) is not int or not 1<=samples<=10:
        raise ValueError("samples must be in 1..10")
    if nodes*iterations*samples>2_000_000:
        raise ValueError("work exceeds 2,000,000 node-iterations")

    root=BoxLayout(orientation="vertical")
    buttons=[]
    backend=TermuxBackend(tg=object())
    received=[0]
    for i in range(nodes):
        btn=Button(text=str(i))
        btn._native=_CountingView(i+1)
        btn.bind(on_release=lambda *_:received.__setitem__(0,received[0]+1))
        root.add_widget(btn)
        buttons.append(btn)
        backend.nodes.append(btn)
        backend._native_index[i+1]=btn

    def walk():
        total=0
        for _ in range(iterations):
            for widget in root.walk():
                total+=1
        return total

    cursor=[0]
    def dispatch():
        for _ in range(iterations):
            cursor[0]=(cursor[0]%nodes)+1
            backend.event(SimpleNamespace(type="click",value={"id":cursor[0]}))
        return iterations

    # Style invalidation is a single View-local setter, not a full UI repaint.
    target=buttons[0]
    target._theme_hook=lambda name:backend.invalidate_style(target,name)
    target._native.background_messages=0
    def style():
        before=target._native.background_messages
        for i in range(iterations):
            target.background_color="#113355" if i%2 else "#335577"
        difference=target._native.background_messages-before
        if difference!=iterations:
            raise RuntimeError("style invalidation did not emit exactly one setter per change")
        return iterations

    def clock():
        local=_Clock()
        seen=[0]
        for _ in range(iterations):
            local.schedule_once(lambda delta:seen.__setitem__(0,seen[0]+1),0)
        while local._jobs:
            local.tick(max_callbacks=128)
        if local._active:
            raise RuntimeError("Clock retained callbacks after completing work")
        return seen[0]

    measurements={
        "widget_walk":_stats(walk,(nodes+1)*iterations,samples),
        "indexed_event_dispatch":_stats(dispatch,iterations,samples),
        "local_style_invalidation":_stats(style,iterations,samples),
        "bounded_clock_callbacks":_stats(clock,iterations,samples),
    }
    return {
        "schema_version":1,
        "measurement_scope":"python-only",
        "native_android_ipc":False,
        "display_fps_measured":False,
        "hardware_touch_latency_measured":False,
        "python":platform.python_version(),
        "platform":platform.platform(),
        "configuration":{"nodes":nodes,"iterations":iterations,"samples":samples,
                         "max_node_iterations":2_000_000},
        "measurements":measurements,
    }


def run_benchmark(args):
    result=benchmark(nodes=args.nodes,iterations=args.iterations,samples=args.samples)
    if args.json:
        print(json.dumps(result,separators=(",",":"),allow_nan=False))
    else:
        print("TGK Python-only benchmark (NOT Android graphics or touch latency)")
        print("nodes={nodes}, iterations={iterations}, samples={samples}".format(
            **result["configuration"]))
        for name,stats in result["measurements"].items():
            print(f"{name:26s} median={stats['median_ns_per_operation']:10.2f} "
                  f"p95={stats['p95_ns_per_operation']:10.2f} ns/op")
    return 0
