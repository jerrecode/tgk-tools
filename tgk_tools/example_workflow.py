"""One-Activity example workflow: text prompt, mode choice and native demos.

Unlike invoking 'tgk prompt', 'tgk choose', 'tgk demo' in shell command
substitutions, this keeps a single Android Activity and ScreenManager alive.
No nested Activity lifecycle waits or shell process handoff.
"""
from __future__ import annotations
import json

from tgk.demos import Gallery
from tgk.widgets import TextInput,Label,Button
from tgk.layout_helpers import action_width


class WorkflowGallery(Gallery):
    MODES=(("simple","01_basics"),("advanced","08_states"),
           ("expert","13_workbench"))

    def __init__(self,project="Termux lab",**kwargs):
        if not isinstance(project,str) or len(project)>256:
            raise ValueError("project name must be a string up to 256 characters")
        object.__setattr__(self,"default_project",project)
        object.__setattr__(self,"selected_mode",None)
        object.__setattr__(self,"selected_project",None)
        super().__init__(scenarios=tuple(s for _,s in self.MODES),**kwargs)

    def build(self):
        root=super().build()
        # Replace the generic gallery menu contents before native rendering.
        # The underlying scenario screens and their Close-to-menu behavior
        # remain shared; there is only one App and one Termux:GUI Activity.
        catalog=self.manager.children[0]
        scroll=catalog.children[2]
        contents=scroll.children[0]
        for child in tuple(contents.children):
            contents.remove_widget(child)
        contents.add_widget(Label(text="Project",height=42,
                                  text_style="title_h4"))
        self.project_field=TextInput(text=self.default_project,height=56)
        contents.add_widget(self.project_field)
        contents.add_widget(Label(text="Choose complexity",height=48))
        for mode,scenario in self.MODES:
            button=Button(text=mode.title(),width=action_width(mode.title()),
                          height=48)
            button.bind(on_release=lambda _b,mode=mode,scenario=scenario:
                        self.choose(mode,scenario))
            contents.add_widget(button)
        return root

    def choose(self,mode,scenario):
        object.__setattr__(self,"selected_mode",mode)
        object.__setattr__(self,"selected_project",self.project_field.text)
        return self.show(scenario)

    def result(self):
        if self.selected_mode is None:return None
        return {"project":self.selected_project,"mode":self.selected_mode,
                "scenario":dict(self.MODES)[self.selected_mode]}


def run_workflow(args):
    from tgk.theme import get_theme
    app=WorkflowGallery(project=args.project,theme=get_theme())
    app.run()
    selected=app.result()
    if selected is None:return 1
    print(json.dumps(selected,ensure_ascii=False,separators=(",",":")))
    return 0
