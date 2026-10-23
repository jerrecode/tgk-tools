"""Structured, bounded media/file pipeline commands for Termux.

No implicit network activity, shell execution or uncapped full-file reads.
All successful commands emit exactly one JSON object on stdout.
"""
from __future__ import annotations
import json
from pathlib import Path

from tgk.io_pipeline import Limits,copy_file,hash_file,download,ffprobe


def run_pipeline(args):
    if args.operation=="probe":
        data=ffprobe(args.source,timeout=args.timeout,max_json_bytes=args.max_metadata_bytes)
        print(json.dumps({"operation":"probe","source":str(args.source),
                          "data":data},ensure_ascii=False,separators=(",",":")))
        return 0

    limits=Limits(chunk_bytes=args.chunk_bytes,max_bytes=args.max_bytes,
                  timeout=args.timeout)
    if args.operation=="hash":
        result=hash_file(args.source,limits=limits)
    elif args.operation=="copy":
        if not args.target:raise ValueError("copy requires TARGET")
        result=copy_file(args.source,args.target,limits=limits,
                         overwrite=args.overwrite)
    elif args.operation=="download":
        if not args.target:raise ValueError("download requires TARGET")
        result=download(args.source,args.target,limits=limits,
                        overwrite=args.overwrite,allow_http=args.allow_http,
                        allow_hosts=args.allow_host or None)
    else:raise ValueError("unsupported pipeline operation")

    print(json.dumps({"operation":args.operation,"source":str(args.source),
                      "target":str(args.target) if args.target else None,
                      "bytes":result.bytes_copied,"sha256":result.sha256,
                      "elapsed_seconds":round(result.elapsed,6)},
                     ensure_ascii=False,separators=(",",":")))
    return 0
