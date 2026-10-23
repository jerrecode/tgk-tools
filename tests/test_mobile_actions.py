"""Compact shell action controls: test precise sizes and native layout calls."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from tgk.widgets import App,BoxLayout,Button,Widget
from tgk.layout_helpers import action_width
from tgk_tools.mobile_actions import python_action_footer,native_action_footer
from tgk_tools.cli import main


class NativeView:
    created=[]
    def __init__(self,*args,**kwargs):
        self.args=args
        self.values={}
        type(self).created.append(self)
    def setheight(self,n):self.values['height']=n
    def setwidth(self,n):self.values['width']=n
    def setmargin(self,n,d=None):self.values['margin_'+str(d)]=n
    def setlinearlayoutparams(self,n):self.values['weight']=n
    def sendclickevent(self,n):self.values['click']=n


class Native:
    LinearLayout=NativeView
    FrameLayout=NativeView
    Button=NativeView


class FooterTests(unittest.TestCase):
    def test_python_footer_keeps_bottom_right_actions_small(self):
        calls=[]
        footer,buttons=python_action_footer([
            ('Cancel',lambda:calls.append('cancel'),'cancel'),
            ('OK',lambda:calls.append('ok'),'button')])
        self.assertEqual(footer.orientation,'horizontal')
        self.assertEqual(footer.height,72)
        self.assertEqual(footer.padding,12)
        self.assertIs(type(footer.children[0]),Widget)
        self.assertEqual(footer.children[0].weight,1)
        for button in buttons:
            self.assertIsInstance(button,Button)
            self.assertEqual(button.height,48)
            self.assertLessEqual(button.width,192)
        buttons[0].dispatch('on_release')
        buttons[1].dispatch('on_release')
        self.assertEqual(calls,['cancel','ok'])

    def test_native_footer_has_weighted_spacer_small_action_and_margin(self):
        NativeView.created=[]
        selected=[]
        label=native_action_footer(Native,object(),object(),'Cancel',paint=selected.append)
        self.assertEqual(label.values['width'],action_width('Cancel',maximum=192))
        self.assertEqual(label.values['height'],48)
        self.assertTrue(label.values['click'])
        bar,spacer,_=NativeView.created
        self.assertEqual(bar.values['height'],72)
        self.assertEqual(bar.values['margin_bottom'],12)
        self.assertEqual(bar.values['margin_right'],12)
        self.assertEqual(spacer.values['width'],0)
        self.assertEqual(spacer.values['weight'],1)
        self.assertEqual(selected,[label])

    def test_invalid_action_settings(self):
        with self.assertRaises(ValueError):python_action_footer([])
        with self.assertRaises(ValueError):native_action_footer(Native,object(),object(),margin=-1)

    def test_prompt_confirm_choose_and_show_have_bounded_buttons(self):
        captured=[]
        def offline_run(self):
            self.root=self.build()
            captured.append(self.root)
        with patch.object(App,'run',offline_run):
            with redirect_stdout(StringIO()):
                self.assertEqual(main(['prompt','--default','something']),1)
                self.assertEqual(main(['confirm','Accept?']),1)
                self.assertEqual(main(['choose','red','blue','--multi']),1)
                with TemporaryDirectory() as temp:
                    file=Path(temp)/'short.txt';file.write_text('hi',encoding='utf-8')
                    self.assertEqual(main(['show',str(file)]),0)
        self.assertEqual(len(captured),4)
        for root in captured:
            buttons=[n for n in root.walk() if isinstance(n,Button)]
            self.assertTrue(buttons)
            for button in buttons:
                self.assertTrue(hasattr(button,'width'))
                self.assertLessEqual(button.width,192)
            self.assertIsInstance(root.children[-1],BoxLayout)
            self.assertEqual(root.children[-1].orientation,'horizontal')
            self.assertEqual(root.children[-1].children[0].weight,1)


if __name__=='__main__':unittest.main()
