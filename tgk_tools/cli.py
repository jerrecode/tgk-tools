"""Termux:GUI shell tools. stdout is reserved for machine-readable results."""
import argparse
import sys
from pathlib import Path
from tgk.widgets import App, BoxLayout, ScrollView, Label, Button, TextInput, CheckBox

def layout(title):
    root=BoxLayout(orientation='vertical',padding=12)
    root.add_widget(Label(text=title,font_size=22,height=65))
    return root

def run_prompt(args):
    class Prompt(App):
        result=None
        def build(self):
            root=layout(args.title or 'Enter text')
            self.entry=TextInput(text=args.default or '',multiline=args.multiline,password=args.password,height=85)
            root.add_widget(self.entry)
            bar=BoxLayout(orientation='horizontal',height=55)
            yes=Button(text='OK');no=Button(text='Cancel')
            yes.bind(on_release=lambda *_: self.done(True))
            no.bind(on_release=lambda *_: self.done(False))
            bar.add_widget(no);bar.add_widget(yes);root.add_widget(bar)
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
            root=layout(args.title or 'Confirm')
            root.add_widget(Label(text=args.message,height=90))
            buttons=BoxLayout(height=60)
            for name,choice in [('No',False),('Yes',True)]:
                b=Button(text=name);b.bind(on_release=lambda _,choice=choice:self.finish(choice))
                buttons.add_widget(b)
            root.add_widget(buttons);return root
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
            root=layout(args.title or 'Choose an option')
            scroll=ScrollView()
            listbox=BoxLayout(orientation='vertical')
            if args.multi:
                self.checkboxes=[]
                for option in args.options:
                    ch=CheckBox(text=option,active=option in (args.selected or []))
                    self.checkboxes.append(ch);listbox.add_widget(ch)
                ok=Button(text='Confirm selection',height=58)
                ok.bind(on_release=lambda *_:self.finish([c.text for c in self.checkboxes if c.active]))
                root.add_widget(ok)
            else:
                for option in args.options:
                    button=Button(text=option,height=58)
                    button.bind(on_release=lambda _,option=option:self.finish(option))
                    listbox.add_widget(button)
            scroll.add_widget(listbox);root.add_widget(scroll)
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
    if args.file=='-':text=sys.stdin.read()
    else:text=Path(args.file).read_text(encoding='utf-8')
    if len(text)>args.max_chars:raise ValueError('Input too large; use --max-chars explicitly')
    class Viewer(App):
        def build(self):
            root=layout(args.title or (args.file if args.file!='-' else 'Text viewer'))
            scroll=ScrollView()
            scroll.add_widget(Label(text=text))
            root.add_widget(scroll)
            close=Button(text='Close',height=55)
            close.bind(on_release=lambda *_:self.stop())
            root.add_widget(close);return root
    Viewer().run();return 0

def run_image(args):
    path=Path(args.file)
    if path.suffix.lower() not in ('.png','.jpg','.jpeg'):raise ValueError('Native viewer accepts PNG/JPEG only')
    if path.stat().st_size>args.max_bytes:raise ValueError('Image exceeds --max-bytes')
    import termuxgui as tg
    with tg.Connection() as c:
        a=tg.Activity(c,intercept=True)
        root=tg.LinearLayout(a,vertical=True)
        tg.TextView(a,path.name,root)
        image=tg.ImageView(a,root)
        image.setimage(path.read_bytes())
        image.setwidth(tg.View.MATCH_PARENT)
        image.setheight(0)
        image.setlinearlayoutparams(1)
        close=tg.Button(a,'Close',root);close.sendclickevent(True)
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
        view=tg.ImageView(activity)
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
                        elif event.type=='destroy' and event.value.get('finishing'):running=False
                        elif event.type=='touch':
                            raw=event.value.get('pointers',[])
                            if isinstance(raw,dict):raw=[raw]
                            if raw and isinstance(raw[0],list):raw=raw[-1]
                            dims=view.getdimensions()
                            points=[]
                            for p in raw:
                                if not isinstance(p,dict):continue
                                q=canvas.map_touch(p.get('x',-1),p.get('y',-1),dims[0],dims[1])
                                if q is not None:points.append(q)
                            touches=points
                    now=time.monotonic()
                    if now-last<1/args.fps:
                        time.sleep(min(.005,max(0,1/args.fps-(now-last))))
                        continue
                    last=now;frame+=1
                    canvas.gradient(rgba(16,22,55),rgba(54,18,73))
                    for x in range(0,w,32):canvas.line(x,0,x,h-1,rgba(72,77,122,75))
                    for y in range(0,h,32):canvas.line(0,y,w-1,y,rgba(72,77,122,75))
                    t=now-t0
                    x=w//2+round(w*.28*math.cos(t*1.3))
                    y=h//2+round(h*.28*math.sin(t*1.3))
                    canvas.circle(x,y,24,rgba(35,214,239))
                    for tx,ty in touches:canvas.circle(tx,ty,18,rgba(255,126,180))
                    buffer.blit();view.refresh()
                    if args.seconds and t>args.seconds:activity.finish()
            finally:canvas.close();del canvas
    print(f'frames={frame}',file=sys.stderr)
    return 0

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
        root=tg.LinearLayout(activity,vertical=True)
        heading=tg.TextView(activity,'Files',root)
        heading.settextsize(19)
        scroll=tg.NestedScrollView(activity,root)
        scroll.setheight(0);scroll.setlinearlayoutparams(1)
        control=tg.Button(activity,'Cancel',root);control.sendclickevent(True)
        controls={control:('cancel',None)}
        def render(directory):
            nonlocal controls
            controls={control:('cancel',None)}
            heading.settext((args.title or 'Select a path')+'\n'+str(directory))
            scroll.clearchildren()
            listbox=tg.LinearLayout(activity,scroll,vertical=True)
            if directory.parent!=directory and (boundary is None or directory!=boundary):
                b=tg.Button(activity,'[..] Parent directory',listbox);b.sendclickevent(True)
                controls[b]=('dir',directory.parent)
            if args.dirs_only:
                b=tg.Button(activity,'[Select this directory]',listbox);b.sendclickevent(True)
                controls[b]=('select',directory)
            try:
                entries=sorted(directory.iterdir(),key=lambda p:(not p.is_dir(),p.name.casefold()))
            except OSError as exc:
                tg.TextView(activity,f'Cannot read directory: {exc}',listbox)
                return
            shown=0
            for path in entries:
                if not args.hidden and path.name.startswith('.'):continue
                if boundary and not path.resolve().is_relative_to(boundary):continue
                if not (path.is_dir() or (not args.dirs_only and
                        (not extension or path.suffix.lower().lstrip('.') in extension))):continue
                if shown>=args.max_items:
                    tg.TextView(activity,f'Only first {args.max_items} entries shown',listbox)
                    break
                b=tg.Button(activity,('[DIR] ' if path.is_dir() else '       ')+path.name,listbox)
                b.sendclickevent(True)
                controls[b]=('dir' if path.is_dir() else 'select',path)
                shown+=1
        render(start)
        for event in c.events():
            if event.type=='back':
                activity.finish()
            if event.type=='click':
                for button,(action,target) in tuple(controls.items()):
                    if event.value.get('id')!=button:continue
                    if action=='dir':render(target)
                    elif action=='select':selection=target;activity.finish()
                    else:activity.finish()
                    break
            if event.type=='destroy' and event.value.get('finishing'):break
    if selection is None:return 1
    print(selection);return 0

def run_progress(args):
    import json
    import termuxgui as tg
    import time
    path=Path(args.file).expanduser()
    last=None;done_since=None;started=time.monotonic()
    with tg.Connection() as c:
        activity=tg.Activity(c,intercept=True)
        root=tg.LinearLayout(activity,vertical=True)
        title=tg.TextView(activity,args.title or 'Progress',root)
        title.settextsize(20)
        info=tg.TextView(activity,'Awaiting progress data ...',root)
        bar=tg.ProgressBar(activity,root)
        close=tg.Button(activity,'Cancel',root);close.sendclickevent(True)
        outcome=1;next_read=0
        while True:
            now=time.monotonic()
            if args.timeout and now-started>args.timeout:
                outcome=124;activity.finish()
            if now>=next_read:
                next_read=now+0.20
                try:
                    text=path.read_text(encoding='utf-8')
                    if text!=last:
                        last=text
                        state=json.loads(text)
                        if not isinstance(state,dict):raise ValueError('expected JSON object')
                        value=max(0,min(100,float(state.get('progress',0))))
                        bar.setprogress(round(value))
                        info.settext(f"{value:.1f}%  {state.get('message','')}")
                        if state.get('done') and done_since is None:done_since=now
                except FileNotFoundError:pass
                except (ValueError,TypeError) as exc:
                    info.settext(f'Invalid progress file: {exc}')
            if args.auto_close and done_since is not None and now-done_since>0.8:
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
    from tgk.canvas import _lib
    result={'platform':platform.platform(),'python':sys.version.split()[0],
            'termux_detected':'com.termux' in str(Path(sys.executable)) or
             'com.termux' in str(__import__('os').environ.get('PREFIX','')),
            'termuxgui_binding_present':importlib.util.find_spec('termuxgui') is not None}
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

def main(argv=None):
    p=argparse.ArgumentParser(prog='tgk',description='Android GUI tools for Termux; stdout emits only selections/results')
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prompt',help='prompt for text; prints answer');a.add_argument('--title');a.add_argument('--default',default='');a.add_argument('--password',action='store_true');a.add_argument('--multiline',action='store_true');a.set_defaults(run=run_prompt)
    a=sub.add_parser('confirm',help='yes/no choice; exit status 0=yes, 1=no');a.add_argument('message');a.add_argument('--title');a.set_defaults(run=run_confirm)
    a=sub.add_parser('choose',help='single/multiple choice; --multi outputs JSON array');a.add_argument('options',nargs='*');a.add_argument('--title');a.add_argument('--stdin',action='store_true');a.add_argument('--json-input',action='store_true');a.add_argument('--multi',action='store_true');a.add_argument('--selected',action='append');a.set_defaults(run=run_choose)
    a=sub.add_parser('show',help='read text file or piped input in native scroll view');a.add_argument('file');a.add_argument('--title');a.add_argument('--max-chars',type=int,default=100_000);a.set_defaults(run=run_show)
    a=sub.add_parser('image',help='PNG/JPG native image viewer');a.add_argument('file');a.add_argument('--max-bytes',type=int,default=24_000_000);a.set_defaults(run=run_image)
    a=sub.add_parser('files',help='browse and choose a file or folder');a.add_argument('--start',default='.');a.add_argument('--root');a.add_argument('--title');a.add_argument('--dirs-only',action='store_true');a.add_argument('--hidden',action='store_true');a.add_argument('--ext',action='append',default=[]);a.add_argument('--max-items',type=int,default=150);a.set_defaults(run=run_files)
    a=sub.add_parser('progress',help='watch a JSON progress file and display a native progress bar');a.add_argument('file');a.add_argument('--title');a.add_argument('--auto-close',action='store_true');a.add_argument('--timeout',type=float,default=0);a.set_defaults(run=run_progress)
    a=sub.add_parser('doctor',help='inspect Termux:GUI/C runtime; --connect checks actual IPC');a.add_argument('--connect',action='store_true');a.add_argument('--json',action='store_true');a.set_defaults(run=run_doctor)
    a=sub.add_parser('canvas-demo',help='C-rendered animated RGBA canvas');a.add_argument('--width',type=int,default=512);a.add_argument('--height',type=int,default=512);a.add_argument('--fps',type=int,default=25);a.add_argument('--seconds',type=float,default=0);a.set_defaults(run=run_canvas)
    args=p.parse_args(argv)
    if args.command=='canvas-demo' and not 1<=args.fps<=60:p.error('--fps must be in 1..60')
    if args.command=='files' and not 1<=args.max_items<=500:p.error('--max-items must be in 1..500')
    if args.command=='choose' and args.stdin and args.json_input:p.error('Use either --stdin or --json-input')
    try:return args.run(args)
    except (RuntimeError,ValueError,OSError) as exc:
        print('tgk:',str(exc),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
