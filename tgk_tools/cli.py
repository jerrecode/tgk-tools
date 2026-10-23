"""Termux:GUI shell tools. stdout is reserved for machine-readable results."""
import argparse
import math
import sys
from pathlib import Path
from tgk.widgets import App, BoxLayout, ScrollView, Label, Button, TextInput, CheckBox, Widget
from tgk_tools.mobile_actions import python_action_footer,native_action_footer

def _paint_object(view,part,args):
    """Apply named per-object shell flags after creating a native/TGK widget.

    Target names: root, heading, input, button, cancel, image, canvas,
    progress. These flags override semantic theme colors on that object
    without modifying sibling Views or global preset definitions.
    """
    from tgk.theme import tgui_color
    styles=getattr(args,'object_colors',{}) if args is not None else {}
    for property_name in ('background','text'):
        color=styles.get((part,property_name),styles.get(('*',property_name)))
        if color is None:continue
        if hasattr(view,'_native'):
            setattr(view, 'background_color' if property_name=='background'
                    else 'text_color',color)
        else:
            setter=getattr(view,'setbackgroundcolor' if property_name=='background'
                           else 'settextcolor',None)
            if callable(setter):setter(tgui_color(color))
    fonts=getattr(args,'object_fonts',{}) if args is not None else {}
    for property_name in ('style','size','family','weight','italic','underline',
                          'strike','align','line_height','role'):
        value=fonts.get((part,property_name),fonts.get(('*',property_name)))
        if value is None:continue
        if hasattr(view,'_native'):
            fields={'style':'text_style','size':'text_size','family':'font_family',
                    'weight':'font_weight','role':'font_color_role',
                    'align':'text_align'}
            setattr(view,fields.get(property_name,property_name),value)
        elif property_name=='size':
            setter=getattr(view,'settextsize',None)
            if callable(setter):setter(int(value))
        # Termux:GUI's native TextView protocol has no font face/bold/italic
        # setter; these are fully effective only with RichTextLabel WebView.
    return view


def layout(title,args=None):
    root=_paint_object(BoxLayout(orientation='vertical',padding=12),'root',args)
    root.add_widget(_paint_object(Label(text=title,font_size=22,height=65),'heading',args))
    return root

def run_prompt(args):
    class Prompt(App):
        result=None
        def build(self):
            root=layout(args.title or 'Enter text',args)
            self.entry=_paint_object(TextInput(text=args.default or '',multiline=args.multiline,password=args.password,height=85),'input',args)
            root.add_widget(self.entry)
            footer,buttons=python_action_footer([
                ('Cancel',lambda:self.done(False),'cancel'),
                ('OK',lambda:self.done(True),'button')])
            _paint_object(buttons[0],'cancel',args)
            _paint_object(buttons[1],'button',args)
            root.add_widget(Widget(weight=1))
            root.add_widget(footer)
            return root
        def done(self,accepted):
            self.result=self.entry.text if accepted else None
            self.stop()
    app=Prompt();app.run()
    if app.result is None:return 1
    print(app.result);return 0

def run_confirm(args):
    class Confirm(App):
        accepted=False
        def build(self):
            root=layout(args.title or 'Confirm',args)
            root.add_widget(Label(text=args.message,height=90))
            footer,buttons=python_action_footer([
                ('No',lambda:self.finish(False),'cancel'),
                ('Yes',lambda:self.finish(True),'button')])
            _paint_object(buttons[0],'cancel',args)
            _paint_object(buttons[1],'button',args)
            root.add_widget(Widget(weight=1))
            root.add_widget(footer);return root
        def finish(self,choice):self.accepted=choice;self.stop()
    app=Confirm();app.run()
    if app.accepted:print('yes');return 0
    print('no');return 1

def run_choose(args):
    if args.stdin:
        args.options.extend(line.rstrip('\r\n') for line in sys.stdin if line.rstrip('\r\n'))
    if args.json_input:
        import json
        values=json.load(sys.stdin)
        if not isinstance(values,list) or not all(isinstance(v,str) for v in values):
            raise ValueError('JSON input must be an array of strings')
        args.options.extend(values)
    if not args.options:raise ValueError('provide at least one option')
    class Choose(App):
        result=None
        def build(self):
            root=layout(args.title or 'Choose an option',args)
            scroll=ScrollView(weight=1)
            listbox=BoxLayout(orientation='vertical')
            if args.multi:
                self.checkboxes=[]
                for option in args.options:
                    ch=_paint_object(CheckBox(text=option,active=option in (args.selected or [])),'button',args)
                    self.checkboxes.append(ch);listbox.add_widget(ch)
                footer,buttons=python_action_footer([
                    ('Confirm selection',lambda:self.finish(
                        [c.text for c in self.checkboxes if c.active]),'button')])
                _paint_object(buttons[0],'button',args)
            else:
                for option in args.options:
                    button=_paint_object(Button(text=option,height=58),'button',args)
                    button.bind(on_release=lambda _,option=option:self.finish(option))
                    listbox.add_widget(button)
            scroll.add_widget(listbox);root.add_widget(scroll)
            if args.multi:root.add_widget(footer)
            return root
        def finish(self,selection):self.result=selection;self.stop()
    app=Choose();app.run()
    if app.result is None:return 1
    if isinstance(app.result,list):
        import json
        print(json.dumps(app.result,ensure_ascii=False))
    else:print(app.result)
    return 0

def run_show(args):
    if args.file=='-':text=sys.stdin.read(args.max_chars+1)
    else:
        with Path(args.file).open(encoding='utf-8') as source:
            text=source.read(args.max_chars+1)
    if len(text)>args.max_chars:raise ValueError('Input too large; use --max-chars explicitly')
    class Viewer(App):
        def build(self):
            root=layout(args.title or (args.file if args.file!='-' else 'Text viewer'),args)
            scroll=ScrollView(weight=1)
            scroll.add_widget(Label(text=text))
            root.add_widget(scroll)
            footer,buttons=python_action_footer([
                ('Close',self.stop,'cancel')])
            _paint_object(buttons[0],'cancel',args)
            root.add_widget(footer);return root
    Viewer().run();return 0

def run_image(args):
    path=Path(args.file)
    if path.suffix.lower() not in ('.png','.jpg','.jpeg'):raise ValueError('Native viewer accepts PNG/JPEG only')
    if path.stat().st_size>args.max_bytes:raise ValueError('Image exceeds --max-bytes')
    import termuxgui as tg
    with tg.Connection() as c:
        a=tg.Activity(c,intercept=True)
        from tgk.theme import get_theme,apply_activity_theme
        apply_activity_theme(a,get_theme())
        root=_paint_object(tg.LinearLayout(a,vertical=True),'root',args)
        _paint_object(tg.TextView(a,path.name,root),'heading',args)
        image=_paint_object(tg.ImageView(a,root),'image',args)
        image.setimage(path.read_bytes())
        image.setwidth(tg.View.MATCH_PARENT)
        image.setheight(0)
        image.setlinearlayoutparams(1)
        close=native_action_footer(tg,a,root,'Close',
              paint=lambda v:_paint_object(v,'cancel',args))
        for e in c.events():
            if e.type=='back' or (e.type=='click' and e.value.get('id')==close):a.finish()
            if e.type=='destroy' and e.value.get('finishing'):break
    return 0

def run_canvas(args):
    import math
    import time
    import termuxgui as tg
    from tgk.canvas import Canvas,rgba
    w,h=args.width,args.height
    if w<=0 or h<=0 or w*h>4_194_304:raise ValueError('canvas dimensions invalid/too large')
    with tg.Connection() as connection:
        activity=tg.Activity(connection,intercept=True)
        from tgk.theme import get_theme, apply_activity_theme,rgba_channels
        palette=apply_activity_theme(activity,get_theme())
        def rgb(role,opacity=None):
            channels=rgba_channels(palette[role])
            return rgba(*(channels if opacity is None else channels[:3]+(opacity,)))
        view=_paint_object(tg.ImageView(activity),'canvas',args)
        view.setdimensions(tg.View.MATCH_PARENT,tg.View.MATCH_PARENT)
        view.sendtouchevent(True)
        buffer=tg.Buffer(connection,w,h)
        view.setbuffer(buffer)
        with buffer as memory:
            canvas=Canvas(memory,w,h)
            touches=[]
            frame=0
            t0=time.monotonic()
            last=0.0
            running=True
            try:
                while running:
                    for _ in range(128):
                        event=connection.checkevent()
                        if event is None:break
                        if event.type=='back':activity.finish()
                        elif event.type=='destroy' and event.value.get('finishing'):
                            running=False
                            break
                        elif event.type=='touch':
                            action=event.value.get('action')
                            if action in ('up','cancel'):
                                touches=[]
                                continue
                            raw=event.value.get('pointers',[])
                            if isinstance(raw,dict):raw=[raw]
                            if isinstance(raw,(list,tuple)) and raw and isinstance(raw[-1],(list,tuple)):
                                raw=raw[-1]
                            if not isinstance(raw,(list,tuple)):continue
                            lifted=event.value.get('index') if action=='pointer_up' else None
                            points=[]
                            for index,p in enumerate(raw):
                                if type(lifted) is int and index==lifted:continue
                                if not isinstance(p,dict):continue
                                try:x,y=float(p['x']),float(p['y'])
                                except (KeyError,TypeError,ValueError,OverflowError):continue
                                # ImageView already transforms Android view coordinates
                                # into the displayed image/buffer pixel space.
                                if math.isfinite(x) and math.isfinite(y) and 0<=x<w and 0<=y<h:
                                    points.append((int(x),int(y)))
                            touches=points
                    if not running:break
                    now=time.monotonic()
                    if now-last<1/args.fps:
                        time.sleep(min(.005,max(0,1/args.fps-(now-last))))
                        continue
                    last=now;frame+=1
                    canvas.gradient(rgb('background'),rgb('surface_alt'))
                    for x in range(0,w,32):canvas.line(x,0,x,h-1,rgb('outline',75))
                    for y in range(0,h,32):canvas.line(0,y,w-1,y,rgb('outline',75))
                    t=now-t0
                    x=w//2+round(w*.28*math.cos(t*1.3))
                    y=h//2+round(h*.28*math.sin(t*1.3))
                    canvas.circle(x,y,24,rgb('accent'))
                    for tx,ty in touches:canvas.circle(tx,ty,18,rgb('accent_secondary'))
                    buffer.blit();view.refresh()
                    if args.seconds and t>args.seconds:activity.finish()
            finally:canvas.close();del canvas
    print(f'frames={frame}',file=sys.stderr)
    return 0

def _limited_file_entries(directory, *, boundary=None, hidden=False,
                          dirs_only=False, extension=(), max_items=150):
    """Return sorted visible entries with O(max_items) auxiliary memory.

    A directory with millions of children must not become a Python list
    merely to display up to max_items Android buttons. This still scans all
    directory entries; true paged browsing requires a separate UI contract.
    """
    import heapq

    if max_items < 1:
        raise ValueError('max_items must be positive')

    def eligible():
        for path in directory.iterdir():
            try:
                if not hidden and path.name.startswith('.'):
                    continue
                # Resolve symlinks before enforcing an optional browsing boundary.
                if boundary is not None and not path.resolve().is_relative_to(boundary):
                    continue
                is_dir = path.is_dir()
                if not is_dir and (dirs_only or
                                   (extension and path.suffix.lower().lstrip('.') not in extension)):
                    continue
                # Directory-first, case-folded ordering; name breaks ties.
                yield (not is_dir, path.name.casefold(), path.name, path, is_dir)
            except (OSError, RuntimeError):
                # A file can vanish or become inaccessible during enumeration.
                continue

    selected = heapq.nsmallest(max_items + 1, eligible())
    return [(item[3], item[4]) for item in selected[:max_items]], len(selected) > max_items


def run_files(args):
    import termuxgui as tg
    start=Path(args.start).expanduser().resolve()
    if not start.is_dir():raise ValueError('starting path is not a directory')
    boundary=Path(args.root).expanduser().resolve() if args.root else None
    if boundary and not start.is_relative_to(boundary):raise ValueError('start outside --root')
    extension={x.lower().lstrip('.').strip() for x in args.ext}
    selection=None
    with tg.Connection() as c:
        activity=tg.Activity(c,intercept=True)
        from tgk.theme import apply_activity_theme,get_theme
        apply_activity_theme(activity,get_theme())
        root=_paint_object(tg.LinearLayout(activity,vertical=True),'root',args)
        heading=_paint_object(tg.TextView(activity,'Files',root),'heading',args)
        heading.settextsize(19)
        scroll=tg.NestedScrollView(activity,root)
        scroll.setheight(0);scroll.setlinearlayoutparams(1)
        control=native_action_footer(tg,activity,root,'Cancel',
              paint=lambda v:_paint_object(v,'cancel',args))
        controls=[(control,'cancel',None)]
        def render(directory):
            nonlocal controls
            controls=[(control,'cancel',None)]
            heading.settext((args.title or 'Select a path')+'\n'+str(directory))
            scroll.clearchildren()
            listbox=tg.LinearLayout(activity,scroll,vertical=True)
            if directory.parent!=directory and (boundary is None or directory!=boundary):
                b=_paint_object(tg.Button(activity,'[..] Parent directory',listbox),'button',args);b.sendclickevent(True)
                controls.append((b,'dir',directory.parent))
            if args.dirs_only:
                b=_paint_object(tg.Button(activity,'[Select this directory]',listbox),'button',args);b.sendclickevent(True)
                controls.append((b,'select',directory))
            try:
                entries,truncated=_limited_file_entries(
                    directory,boundary=boundary,hidden=args.hidden,
                    dirs_only=args.dirs_only,extension=extension,
                    max_items=args.max_items)
            except OSError as exc:
                tg.TextView(activity,f'Cannot read directory: {exc}',listbox)
                return
            for path,is_dir in entries:
                if getattr(args,'icons',False):
                    from tgk.icons import glyph,icon_for_path
                    prefix=glyph(icon_for_path(path,is_dir=is_dir))+' '
                else:
                    prefix='[DIR] ' if is_dir else '       '
                b=_paint_object(tg.Button(activity,prefix+path.name,listbox),'button',args)
                b.sendclickevent(True)
                controls.append((b,'dir' if is_dir else 'select',path))
            if truncated:
                tg.TextView(activity,f'Only first {args.max_items} entries shown',listbox)
        render(start)
        for event in c.events():
            if event.type=='back':
                activity.finish()
            if event.type=='click':
                for button,action,target in tuple(controls):
                    if event.value.get('id')!=button:continue
                    if action=='dir':render(target)
                    elif action=='select':selection=target;activity.finish()
                    else:activity.finish()
                    break
            if event.type=='destroy' and event.value.get('finishing'):break
    if selection is None:return 1
    print(selection);return 0

_MAX_PROGRESS_JSON_BYTES = 1_048_576


def _read_progress_state(path, max_bytes=_MAX_PROGRESS_JSON_BYTES):
    """Read a bounded JSON progress snapshot, including during writer races.

    The file may grow between stat and read: read limit+1 bytes directly
    rather than trusting st_size or loading an arbitrarily large file.
    """
    import json
    with Path(path).open('rb') as source:
        payload = source.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f'Progress JSON exceeds {max_bytes} byte limit')
    state = json.loads(payload.decode('utf-8'))
    if not isinstance(state, dict):
        raise ValueError('expected JSON object')
    raw_value = state.get('progress', 0)
    if isinstance(raw_value, bool):
        raise ValueError('progress must be a finite number')
    try:
        value = float(raw_value)
    except (ValueError, TypeError, OverflowError) as exc:
        # Even well-formed JSON numbers (e.g. 400 digits) may overflow float.
        raise ValueError('progress must be a finite number') from exc
    if not math.isfinite(value):
        raise ValueError('progress must be a finite number')
    message = state.get('message', '')
    if not isinstance(message, str):
        raise ValueError('message must be a string')
    completed = state.get('done', False)
    if type(completed) is not bool:
        raise ValueError('done must be a JSON boolean')
    return max(0.0, min(100.0, value)), message, completed


def _progress_completion_since(previous, completed, now):
    """Start the auto-close delay on completion; reset it after a retry."""
    return (now if previous is None else previous) if completed else None


def run_progress(args):
    import json
    import termuxgui as tg
    import time
    path=Path(args.file).expanduser()
    last=None;done_since=None;started=time.monotonic()
    with tg.Connection() as c:
        activity=tg.Activity(c,intercept=True)
        from tgk.theme import apply_activity_theme,get_theme
        apply_activity_theme(activity,get_theme())
        root=_paint_object(tg.LinearLayout(activity,vertical=True),'root',args)
        title=_paint_object(tg.TextView(activity,args.title or 'Progress',root),'heading',args)
        title.settextsize(20)
        info=_paint_object(tg.TextView(activity,'Awaiting progress data ...',root),'heading',args)
        bar=_paint_object(tg.ProgressBar(activity,root),'progress',args)
        spacer=tg.FrameLayout(activity,root)
        spacer.setheight(0);spacer.setlinearlayoutparams(1)
        close=native_action_footer(tg,activity,root,'Cancel',
              paint=lambda v:_paint_object(v,'cancel',args))
        outcome=1;next_read=0
        while True:
            now=time.monotonic()
            if args.timeout and now-started>args.timeout:
                outcome=124;activity.finish()
            if now>=next_read:
                next_read=now+0.20
                try:
                    value,message,completed=_read_progress_state(path)
                    snapshot=(value,message,completed)
                    if snapshot!=last:
                        last=snapshot
                        bar.setprogress(round(value))
                        info.settext(f"{value:.1f}%  {message}")
                    done_since=_progress_completion_since(done_since, completed, now)
                except FileNotFoundError:
                    done_since=None
                except (ValueError,TypeError) as exc:
                    done_since=None
                    info.settext(f'Invalid progress file: {exc}')
            if (outcome!=124 and args.auto_close and done_since is not None
                    and now-done_since>0.8):
                outcome=0;activity.finish()
            event=c.checkevent()
            if event:
                if event.type=='back' or (event.type=='click' and event.value.get('id')==close):
                    activity.finish()
                elif event.type=='destroy' and event.value.get('finishing'):break
            else:time.sleep(.02)
    return outcome

def run_doctor(args):
    import json
    import platform
    import importlib.util
    import shutil
    import tgk
    import tgk_tools
    from tgk.canvas import _lib
    from tgk.widgets import TermuxBackend
    result={'platform':platform.platform(),'python':sys.version.split()[0],
            'tgk_version':tgk.__version__,
            'tgk_tools_version':tgk_tools.__version__,
            'termux_detected':'com.termux' in str(Path(sys.executable)) or
             'com.termux' in str(__import__('os').environ.get('PREFIX','')),
            'termuxgui_binding_present':importlib.util.find_spec('termuxgui') is not None,
            'native_view_id_dispatch':hasattr(TermuxBackend(tg=object()),'_native_index'),
            'bounded_io_available':importlib.util.find_spec('tgk.io_pipeline') is not None,
            'ffmpeg_executable':shutil.which('ffmpeg'),
            'ffprobe_executable':shutil.which('ffprobe')}
    try:
        _lib()
        result['c_renderer']='available'
    except (RuntimeError,OSError) as exc:
        result['c_renderer']=f'error: {exc}'
    if args.connect:
        try:
            import termuxgui as tg
            with tg.Connection() as c:result['termuxgui_connection_version']=str(c.getversion())
        except Exception as exc:
            result['connection_error']=f'{type(exc).__name__}: {exc}'
    if args.json:print(json.dumps(result,indent=2,ensure_ascii=False))
    else:
        for key,val in result.items():print(f'{key}: {val}')
    return 0 if result['c_renderer']=='available' and (
        not args.connect or 'termuxgui_connection_version' in result) else 2


def run_themes(args):
    """List available named presets or expose semantic roles as JSON."""
    import json
    from tgk.theme import PRESETS,ROLES,DEFAULT_NAME,resolve_theme
    if args.json:
        print(json.dumps({"default":DEFAULT_NAME,"roles":list(ROLES),
                          "presets":{name:resolve_theme(name).to_dict()["colors"]
                                     for name in PRESETS}},
                         ensure_ascii=False,indent=2))
    else:
        print("TGK presets (default: "+DEFAULT_NAME+"):")
        for name in PRESETS:print("  "+name)
        print("Roles: "+", ".join(ROLES))
    return 0


def run_demo(args):
    from tgk.demos import Laboratory,SCENARIOS
    from tgk.theme import get_theme
    if args.list:
        for name,description in SCENARIOS.items():print(name+"  "+description)
        return 0
    Laboratory(scenario=args.scenario,theme=get_theme()).run()
    return 0


def _configure_theme(args,parser):
    """Select preset/file first; command-line role overrides have final precedence."""
    from tgk.theme import load_theme,resolve_theme,set_theme
    try:
        chosen=load_theme(args.theme_file) if args.theme_file else resolve_theme()
        if args.theme:chosen=resolve_theme(args.theme)
        overrides={}
        for item in args.color:
            if '=' not in item:raise ValueError("--color requires ROLE=#HEX")
            role,value=item.split('=',1)
            if not role.strip():raise ValueError("--color requires a role")
            overrides[role.strip()]=value.strip()
        set_theme(chosen,**overrides)
        from tgk.typography import resolve_text_style,set_text_style,PRESETS as FONT_PRESETS
        from tgk.theme import normalize_color
        style_options={}
        for field,arg_name in (("family","font_family"),("size","font_size"),
                               ("weight","font_weight"),("role","font_color_role"),
                               ("align","text_align"),("line_height","line_height")):
            value=getattr(args,arg_name)
            if value is not None:style_options[field]=value
        for flag in ("italic","underline","strike"):
            if getattr(args,flag):style_options[flag]=True
        set_text_style(args.text_style,**style_options)
        args.object_fonts={}
        allowed={"root","heading","input","button","cancel","image",
                 "canvas","progress","*"}
        fields={"style","size","family","weight","italic","underline",
                "strike","align","line_height","role"}
        for item in args.object_font:
            if "=" not in item or "." not in item.split("=",1)[0]:
                raise ValueError("--object-font requires TARGET.FIELD=VALUE")
            targetfield,raw=item.split("=",1)
            target,field=targetfield.rsplit(".",1)
            if target not in allowed or field not in fields:
                raise ValueError("unknown --object-font target/field")
            if field=="style":
                resolve_text_style(raw)
                val=raw
            elif field in ("size","weight"):
                val=int(raw)
            elif field=="line_height":
                val=float(raw)
            elif field in ("italic","underline","strike"):
                if raw.lower() not in ("true","false","1","0"):
                    raise ValueError("boolean object font values must be true/false")
                val=raw.lower() in ("true","1")
            else:val=raw
            # Use TextStyle's validator for each override.
            if field!="style":resolve_text_style("body",**{field:val})
            args.object_fonts[(target,field)]=val
        target_types={'root','heading','input','button','cancel','image','canvas','progress','*'}
        args.object_colors={}
        for item in args.object_color:
            if '=' not in item or '.' not in item.split('=',1)[0]:
                raise ValueError('--object-color requires TARGET.PROPERTY=#HEX')
            locator,hexvalue=item.split('=',1)
            target,property_name=locator.rsplit('.',1)
            if target not in target_types or property_name not in ('background','text'):
                raise ValueError('unsupported --object-color target or property')
            args.object_colors[(target,property_name)]=normalize_color(hexvalue.strip())
    except (ValueError,OSError) as exc:
        parser.error(str(exc))

def _run_pipeline_lazily(args):
    # Do not break existing shell commands while a user's older TGK core is
    # awaiting upgrade; only the new pipeline operation needs the new API.
    from tgk_tools.pipeline_cli import run_pipeline
    return run_pipeline(args)


def _run_icons_lazily(args):
    from tgk_tools.advanced_ui import run_icons
    return run_icons(args)


def _run_typography_lazily(args):
    from tgk_tools.advanced_ui import run_typography
    return run_typography(args)


def _run_lab_lazily(args):
    from tgk_tools.advanced_ui import run_lab
    return run_lab(args)


def _run_mobile(name,args):
    from tgk_tools import mobile_ui
    return getattr(mobile_ui,name)(args)


def _run_benchmark_lazily(args):
    from tgk_tools.bench import run_benchmark
    return run_benchmark(args)


def _run_icons_build(args):
    from tgk.icon_builder import build_assets
    import json
    output=Path(args.output).expanduser()/'icons'
    if output.exists() and not args.overwrite:
        raise FileExistsError(f'icon output already exists: {output}; use --overwrite to replace')
    result=build_assets(args.output,names=args.icon,raster=args.raster,
                        overwrite=args.overwrite,low=args.low,mid=args.mid,
                        high=args.high,max_icons=args.max_icons)
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0


def main(argv=None):
    p=argparse.ArgumentParser(prog='tgk',description='Android GUI tools for Termux; stdout emits only selections/results')
    sub=p.add_subparsers(dest='command',required=True)
    theme_flags=argparse.ArgumentParser(add_help=False)
    theme_flags.add_argument('--theme',help='Named preset (see: tgk themes)')
    theme_flags.add_argument('--theme-file',help='JSON: {"theme":"ocean","colors":{"accent":"#18D0F9"}}')
    theme_flags.add_argument('--color',action='append',default=[],metavar='ROLE=#HEX',
                             help='Override any semantic color role; repeatable')
    theme_flags.add_argument('--object-color',action='append',default=[],
                             metavar='TARGET.PROPERTY=#HEX',
                             help='Override native root/heading/input/button/cancel/... .text or .background')
    theme_flags.add_argument('--text-style',default='body',help='Typography preset')
    theme_flags.add_argument('--font-family',choices=('sans','serif','mono'))
    theme_flags.add_argument('--font-size',type=int)
    theme_flags.add_argument('--font-weight',type=int)
    theme_flags.add_argument('--italic',action='store_true')
    theme_flags.add_argument('--underline',action='store_true')
    theme_flags.add_argument('--strike',action='store_true')
    theme_flags.add_argument('--font-color-role')
    theme_flags.add_argument('--text-align',choices=('left','center','right','justify'))
    theme_flags.add_argument('--line-height',type=float)
    theme_flags.add_argument('--object-font',action='append',default=[],
                             metavar='TARGET.FIELD=VALUE',
                             help='Named per-view text styling (size/style/family/weight/role/...)')
    a=sub.add_parser('prompt',parents=[theme_flags],help='prompt for text; prints answer');a.add_argument('--title');a.add_argument('--default',default='');a.add_argument('--password',action='store_true');a.add_argument('--multiline',action='store_true');a.set_defaults(run=run_prompt)
    a=sub.add_parser('confirm',parents=[theme_flags],help='yes/no choice; exit status 0=yes, 1=no');a.add_argument('message');a.add_argument('--title');a.set_defaults(run=run_confirm)
    a=sub.add_parser('choose',parents=[theme_flags],help='single/multiple choice; --multi outputs JSON array');a.add_argument('options',nargs='*');a.add_argument('--title');a.add_argument('--stdin',action='store_true');a.add_argument('--json-input',action='store_true');a.add_argument('--multi',action='store_true');a.add_argument('--selected',action='append');a.set_defaults(run=run_choose)
    a=sub.add_parser('show',parents=[theme_flags],help='read text file or piped input in native scroll view');a.add_argument('file');a.add_argument('--title');a.add_argument('--max-chars',type=int,default=100_000);a.set_defaults(run=run_show)
    a=sub.add_parser('image',parents=[theme_flags],help='PNG/JPG native image viewer');a.add_argument('file');a.add_argument('--max-bytes',type=int,default=24_000_000);a.set_defaults(run=run_image)
    a=sub.add_parser('files',parents=[theme_flags],help='browse and choose a file or folder');a.add_argument('--start',default='.');a.add_argument('--root');a.add_argument('--title');a.add_argument('--dirs-only',action='store_true');a.add_argument('--hidden',action='store_true');a.add_argument('--ext',action='append',default=[]);a.add_argument('--max-items',type=int,default=150);a.add_argument('--icons',action='store_true',help='show semantic file/folder symbols');a.set_defaults(run=run_files)
    a=sub.add_parser('progress',parents=[theme_flags],help='watch a JSON progress file and display a native progress bar');a.add_argument('file');a.add_argument('--title');a.add_argument('--auto-close',action='store_true');a.add_argument('--timeout',type=float,default=0);a.set_defaults(run=run_progress)
    a=sub.add_parser('doctor',parents=[theme_flags],help='inspect Termux:GUI/C runtime; --connect checks actual IPC');a.add_argument('--connect',action='store_true');a.add_argument('--json',action='store_true');a.set_defaults(run=run_doctor)
    a=sub.add_parser('canvas-demo',parents=[theme_flags],help='C-rendered animated RGBA canvas');a.add_argument('--width',type=int,default=512);a.add_argument('--height',type=int,default=512);a.add_argument('--fps',type=int,default=25);a.add_argument('--seconds',type=float,default=0);a.set_defaults(run=run_canvas)
    a=sub.add_parser('themes',parents=[theme_flags],help='list theme presets and semantic roles')
    a.add_argument('--json',action='store_true');a.set_defaults(run=run_themes)
    a=sub.add_parser('demo',parents=[theme_flags],help='run 16 graduated UI and theme studio labs')
    a.add_argument('--scenario',default='12_studio',help='scenario code, see --list')
    a.add_argument('--list',action='store_true');a.set_defaults(run=run_demo)
    a=sub.add_parser('icons',parents=[theme_flags],help='semantic icons and file type resolver')
    a.add_argument('--json',action='store_true')
    a.add_argument('--category',choices=('files','directories','actions','media','view','navigation'))
    a.add_argument('--path')
    a.add_argument('--directory',action='store_true')
    a.add_argument('--detailed',action='store_true',
                   help='use extension/special-file layered SVG asset ID')
    a.add_argument('--svg')
    a.add_argument('--svg-size',type=int,default=24)
    a.add_argument('--svg-color',default='#FFFFFF')
    a.set_defaults(run=_run_icons_lazily)
    a=sub.add_parser('icons-build',parents=[theme_flags],
                     help='atomic layered SVG/PNG/JPG/ICO pack generator')
    a.add_argument('--output',default='.',help='parent directory for icons/')
    a.add_argument('--icon',action='append',help='specific named recipe; repeatable')
    a.add_argument('--raster',action='store_true',
                   help='generate raster variants; requires optional CairoSVG + Pillow')
    a.add_argument('--overwrite',action='store_true',
                   help='replace an existing icon pack only after successful staging')
    a.add_argument('--low',type=int,default=32)
    a.add_argument('--mid',type=int,default=96)
    a.add_argument('--high',type=int,default=256)
    a.add_argument('--max-icons',type=int,default=1500)
    a.set_defaults(run=_run_icons_build)
    a=sub.add_parser('typography',parents=[theme_flags],help='list or preview text presets')
    a.add_argument('--json',action='store_true')
    a.add_argument('--preview',action='store_true')
    a.set_defaults(run=_run_typography_lazily)
    a=sub.add_parser('ui-lab',parents=[theme_flags],help='tabs, popup, icons, rich text and canvas')
    a.add_argument('--mode',choices=('normal','dialog','overlay'),default='normal')
    a.add_argument('--start-page',choices=('home','icons','text','canvas','screens'),default='home')
    a.set_defaults(run=_run_lab_lazily)
    a=sub.add_parser('pipeline',parents=[theme_flags],
                     help='bounded local copy, SHA-256, HTTPS download and ffprobe JSON')
    a.add_argument('operation',choices=('hash','copy','download','probe'))
    a.add_argument('source',help='local path (or HTTPS URL for download)')
    a.add_argument('target',nargs='?',help='destination for copy or download')
    a.add_argument('--chunk-bytes',type=int,default=65536)
    a.add_argument('--max-bytes',type=int,default=268435456)
    a.add_argument('--timeout',type=float,default=30)
    a.add_argument('--max-metadata-bytes',type=int,default=8388608)
    a.add_argument('--overwrite',action='store_true')
    a.add_argument('--allow-http',action='store_true',help='allow insecure HTTP explicitly')
    a.add_argument('--allow-host',action='append',default=[],
                   help='optional HTTPS hostname allowlist (repeatable)')
    a.set_defaults(run=_run_pipeline_lazily)
    a=sub.add_parser('layout-plan',parents=[theme_flags],
                     help='12-column responsive layout plan; optional live Android window metrics')
    a.add_argument('--connect',action='store_true',
                   help='read real window configuration from Termux:GUI')
    a.add_argument('--width-dp',type=float,help='window width for offline simulation')
    a.add_argument('--height-dp',type=float,help='window height for offline simulation')
    a.add_argument('--density',type=float,default=1.0)
    a.add_argument('--font-scale',type=float,default=1.0)
    a.add_argument('--items',type=int,default=8)
    a.add_argument('--spans',action='append',default=[],
                   metavar='COMPACT,MEDIUM,EXPANDED')
    a.add_argument('--touch-target-dp',type=int,default=48)
    a.add_argument('--grid-unit-dp',type=int,default=4)
    a.add_argument('--json',action='store_true')
    a.set_defaults(run=lambda args:_run_mobile('run_layout_plan',args))
    a=sub.add_parser('style-catalog',parents=[theme_flags],
                     help='show preset typography, component geometry and full palette')
    a.add_argument('--json',action='store_true')
    a.set_defaults(run=lambda args:_run_mobile('run_style_catalog',args))
    a=sub.add_parser('adaptive-demo',parents=[theme_flags],
                     help='launch window-aware 12-column grid and rich table lab')
    a.add_argument('--orientation',choices=('system','portrait','landscape'),default='system')
    a.add_argument('--touch-target-dp',type=int,default=48)
    a.add_argument('--grid-unit-dp',type=int,default=4)
    a.set_defaults(run=lambda args:_run_mobile('run_adaptive_demo',args))
    a=sub.add_parser('benchmark',parents=[theme_flags],
                     help='bounded Python-only performance measurements (not Android FPS)')
    a.add_argument('--nodes',type=int,default=256)
    a.add_argument('--iterations',type=int,default=500)
    a.add_argument('--samples',type=int,default=3)
    a.add_argument('--json',action='store_true')
    a.set_defaults(run=_run_benchmark_lazily)
    args=p.parse_args(argv)
    _configure_theme(args,p)
    if args.command=='show' and args.max_chars<=0:p.error('--max-chars must be positive')
    if args.command=='image' and args.max_bytes<=0:p.error('--max-bytes must be positive')
    for name in ('timeout','seconds'):
        value=getattr(args,name,0)
        if not math.isfinite(value) or value<0:p.error(f'--{name} must be finite and non-negative')
    if args.command=='canvas-demo' and not 1<=args.fps<=60:p.error('--fps must be in 1..60')
    if args.command=='canvas-demo' and (args.width<=0 or args.height<=0 or args.width*args.height>4_194_304):
        p.error('canvas dimensions must be positive and at most 4194304 pixels')
    if args.command=='files' and not 1<=args.max_items<=500:p.error('--max-items must be in 1..500')
    if args.command=='choose' and args.stdin and args.json_input:p.error('Use either --stdin or --json-input')
    if args.command in ('adaptive-demo','layout-plan'):
        if args.touch_target_dp<32 or args.grid_unit_dp<1:
            p.error('touch target must be >=32dp and grid unit must be >=1dp')
        if args.command=='layout-plan' and not 0<=args.items<=2000:
            p.error('--items must be in 0..2000')
    if args.command=='benchmark':
        if not 1<=args.nodes<=5000 or not 1<=args.iterations<=10000 or not 1<=args.samples<=10:
            p.error('benchmark bounds: --nodes 1..5000, --iterations 1..10000, --samples 1..10')
        if args.nodes*args.iterations*args.samples>2_000_000:
            p.error('benchmark work must not exceed 2,000,000 node-iterations')
    if args.command=='pipeline':
        if args.operation in ('copy','download') and not args.target:
            p.error('pipeline '+args.operation+' requires TARGET')
        if args.operation in ('hash','probe') and args.target:
            p.error('pipeline '+args.operation+' does not accept TARGET')
        if args.timeout<=0:p.error('--timeout must be positive')
        if args.max_bytes<=0 or args.chunk_bytes<=0 or args.max_metadata_bytes<=0:
            p.error('pipeline size limits must be positive')
    if args.command=='icons' and args.svg and (args.path or args.category):
        p.error('Use --svg separately from --path or --category')
    if args.command=='icons' and args.path and args.category:
        p.error('Use --path separately from --category')
    try:return args.run(args)
    except ModuleNotFoundError as exc:
        if exc.name=='tgk.io_pipeline':
            print('tgk: pipeline requires TGK >=0.3.0; update the framework '
                  'using sh ./install.sh --copy in the TGK checkout',
                  file=sys.stderr)
            return 2
        if exc.name!='termuxgui':raise
        print('tgk: Missing Python bindings: python -m pip install termuxgui; '
              'also install the matching Termux:GUI Android app',file=sys.stderr)
        return 2
    except (RuntimeError,ValueError,OSError) as exc:
        print('tgk:',str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
