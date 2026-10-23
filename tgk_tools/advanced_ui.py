"""Advanced TGK Tools commands: catalog exploration and native multiview studio."""
from __future__ import annotations
import json

from tgk.icons import ICONS,CATEGORIES,icon_names,icon_for_path,glyph,svg
from tgk.typography import PRESETS,resolve_text_style,get_text_style
from tgk.theme import get_theme


def run_icons(args):
    if args.path:
        name=icon_for_path(args.path,is_dir=True if args.directory else None,
                           detailed=getattr(args,"detailed",False))
        if args.json:print(json.dumps({"path":args.path,"icon":name,"glyph":glyph(name)},
                                     ensure_ascii=False))
        else:print(name+" "+glyph(name))
        return 0
    if args.svg:
        print(svg(args.svg,size=args.svg_size,color=args.svg_color))
        return 0
    names=icon_names(args.category)
    if args.json:
        print(json.dumps({"category":args.category,"icons":{name:glyph(name) for name in names}},
                         ensure_ascii=False,indent=2))
    else:
        for name in names:print(name+"\t"+glyph(name))
    return 0


def run_typography(args):
    from tgk.config import load_config
    from tgk.typography import get_text_style
    current_name=args.text_style or load_config()["ui"]["text_style"]
    if args.preview:
        TypographyPreview(args).run()
    elif args.json:
        print(json.dumps({"default":current_name,"active_size":get_text_style().size,
                          "presets":{
            name:dict(family=resolve_text_style(name).family,
                      size=resolve_text_style(name).size,
                      weight=resolve_text_style(name).weight,
                      italic=resolve_text_style(name).italic,
                      underline=resolve_text_style(name).underline,
                      strike=resolve_text_style(name).strike,
                      role=resolve_text_style(name).role,
                      line_height=resolve_text_style(name).line_height)
            for name in PRESETS}},indent=2))
    else:
        print("Typography presets (default: "+current_name+"):")
        for name in PRESETS:
            s=resolve_text_style(name)
            print(f"  {name:12s}  {s.family:5s} {s.size:3d}sp "
                  f"weight={s.weight} role={s.role}")
    return 0


def _make_button(parent,text,callback):
    from tgk import Button
    from tgk.layout_helpers import action_width
    button=Button(text=text,height=48,width=action_width(text))
    button.bind(on_release=lambda *_:callback())
    parent.add_widget(button)
    return button


def _page(name,title,content=None):
    from tgk import Tab
    tab=Tab(name=name,title=title,padding=8,spacing=6)
    if content is not None:tab.add_widget(content)
    return tab


def _intro():
    from tgk import BoxLayout,Label
    body=BoxLayout(orientation="vertical",padding=8)
    body.add_widget(Label(text="TGK NAVIGATION LAB",height=70,font_size=24))
    body.add_widget(Label(text="Tabs • Screens • Popup • Typography • Canvas",height=60))
    return body


class AdvancedLab:
    """Factory wrapping an App to keep shell command creation fully lazy."""
    @staticmethod
    def launch(args):
        from tgk import (App,BoxLayout,FloatLayout,GridLayout,ScrollView,Label,
                         Popup,TabbedPanel,Tab,ScreenManager,Screen,IconLabel,
                         InfiniteCanvas,RichTextLabel,TextSpan,Button)
        from tgk.icons import CATEGORIES
        from tgk.theme import PRESETS as COLORS
        from tgk.typography import PRESETS as TEXTS
        class Lab(App):
            def __init__(self):
                self.n=0
                self.dialog=None
                super().__init__(theme=get_theme(),text_style=get_text_style(),
                                 window_mode=args.mode)
            def build(self):
                from tgk.layout_helpers import compact_action_bar
                root=BoxLayout(orientation="vertical")
                layer=FloatLayout(weight=1)
                self.tabs=TabbedPanel(height=740)
                home=_page("home","Home",_intro())
                _make_button(home,"Open Popup",lambda:self.popup.open())
                _make_button(home,"Cycle Theme",self.cycle_theme)
                _make_button(home,"Go to Canvas",lambda:self.tabs.switch("canvas"))
                self.tabs.add_widget(home)

                icon_page=_page("icons","Icons")
                scroll=ScrollView(weight=1)
                grid=GridLayout(cols=2,rows=0)
                for category,names in CATEGORIES.items():
                    for name in names[:30]:
                        grid.add_widget(IconLabel(icon=name,text=name,
                                                  font_size=13,height=42))
                scroll.add_widget(grid)
                icon_page.add_widget(scroll)
                self.tabs.add_widget(icon_page)

                text_page=_page("text","Typography")
                text_scroll=ScrollView(weight=1)
                stack=BoxLayout(orientation="vertical",spacing=5,padding=8)
                stack.add_widget(RichTextLabel(
                    spans=[TextSpan("Bold heading ",style="title"),
                           TextSpan("italic text ",style="quote",color="#9AC8FF"),
                           TextSpan("and code <tags>",style="code")],height=115))
                for name in TEXTS:
                    stack.add_widget(RichTextLabel(text=f"{name}: Font scale Aa 123",
                                                   style=name,height=62))
                text_scroll.add_widget(stack)
                text_page.add_widget(text_scroll)
                self.tabs.add_widget(text_page)

                canvas_page=_page("canvas","Canvas")
                canvas_page.add_widget(Label(text="Drag + pinch (buffer coordinates)",
                                             height=45))
                self.viewport=InfiniteCanvas(width=512,height=384)
                for i in range(16):
                    self.viewport.add_marker((i-8)*90,(i%5-2)*75,
                                             role="accent" if i%2 else "success")
                canvas_page.add_widget(self.viewport)
                actions=BoxLayout(orientation="horizontal",height=57)
                _make_button(actions,"Zoom +",lambda:self.viewport.zoom_at(1.25))
                _make_button(actions,"Zoom -",lambda:self.viewport.zoom_at(.8))
                _make_button(actions,"Reset",self.reset_canvas)
                canvas_page.add_widget(actions)
                self.tabs.add_widget(canvas_page)

                pages=_page("screens","Screens")
                self.screens=ScreenManager()
                for page in ("first","second","third"):
                    screen=Screen(name=page,title=page)
                    screen.add_widget(Label(text="Nested screen "+page,height=75))
                    _make_button(screen,"Next screen",self.screens.next)
                    self.screens.add_widget(screen)
                pages.add_widget(self.screens)
                self.tabs.add_widget(pages)
                layer.add_widget(self.tabs)

                self.popup=Popup(visible=False,width=330,height=260,
                                 padding=10,spacing=8,background_color="#243452")
                self.popup.add_widget(Label(text="Popup / Overlay View",height=46))
                self.popup.add_widget(RichTextLabel(
                    text="Live popup content using an existing view. Not yet a full focus-trapping modal.",
                    style="small",height=100))
                _make_button(self.popup,"Close Popup",self.popup.dismiss)
                layer.add_widget(self.popup)
                root.add_widget(layer)
                root.add_widget(compact_action_bar("Close",self.stop,margin=12))
                if args.start_page not in ("home","icons","text","canvas","screens"):
                    raise ValueError("unknown starting page")
                self.tabs.switch(args.start_page)
                return root
            def cycle_theme(self):
                names=list(COLORS);idx=names.index(self.theme.name)
                self.set_theme(names[(idx+1)%len(names)])
            def reset_canvas(self):
                self.viewport.center_x=0;self.viewport.center_y=0;self.viewport.zoom=1
        Lab().run()
    def run(self):
        self.launch(self.args)


class TypographyPreview:
    def __init__(self,args):self.args=args
    def run(self):
        from tgk import App,ScrollView,BoxLayout,RichTextLabel,Button
        args=self.args
        class Showcase(App):
            def build(self):
                root=BoxLayout(orientation="vertical")
                scroll=ScrollView(weight=1)
                stack=BoxLayout(orientation="vertical")
                for name in PRESETS:
                    stack.add_widget(RichTextLabel(
                        text=f"{name}: The quick brown fox jumps over 0123456789.",
                        style=name,height=82))
                scroll.add_widget(stack);root.add_widget(scroll)
                from tgk.layout_helpers import compact_action_bar
                root.add_widget(compact_action_bar("Close",self.stop,margin=12))
                return root
        Showcase(text_style=get_text_style(),theme=get_theme()).run()


def run_lab(args):
    AdvancedLab.launch(args)
    return 0
