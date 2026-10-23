"""Mobile-sized bottom-right action layouts, shared by TGK shell dialogs.

Native Termux:GUI does not expose FrameLayout gravity. A fixed-height
horizontal LinearLayout with a weighted spacer right-aligns small controls.
"""
from tgk.layout_helpers import action_width
from tgk.widgets import BoxLayout,Button,Widget


def python_action_footer(actions,*,margin=12):
    """Create a TGK widget footer with compact buttons.

    actions is a sequence of (label, callable, role); each button is sized
    by label, never by available screen width.
    """
    if not actions:raise ValueError("at least one action required")
    if type(margin) is not int or not 0<=margin<=48:raise ValueError("invalid footer margin")
    row=BoxLayout(orientation="horizontal",height=48+2*margin,padding=margin)
    row.add_widget(Widget(weight=1))
    buttons=[]
    for label,callback,role in actions:
        width=action_width(label,maximum=192)
        btn=Button(text=label,width=width,height=48,action_role=role)
        btn.bind(on_release=lambda _w,callback=callback:callback())
        row.add_widget(btn)
        buttons.append(btn)
    return row,buttons


def native_action_footer(tg,activity,parent,label="Cancel",*,paint=None,
                         margin=12):
    """Create a native footer and return the action Button object."""
    if type(margin) is not int or not 0<=margin<=48:raise ValueError("invalid footer margin")
    bar=tg.LinearLayout(activity,parent,vertical=False)
    bar.setheight(48+2*margin)
    bar.setmargin(margin,"bottom")
    bar.setmargin(margin,"right")
    spacer=tg.FrameLayout(activity,bar)
    spacer.setwidth(0)
    spacer.setlinearlayoutparams(1)
    button=tg.Button(activity,label,bar)
    button.setwidth(action_width(label,maximum=192))
    button.setheight(48)
    button.sendclickevent(True)
    if paint is not None:paint(button)
    return button
