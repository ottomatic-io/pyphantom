#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

from threading import Thread

import time
from kivy.config import Config

Config.set("graphics", "width", "878")
Config.set("graphics", "height", "598")
Config.set("graphics", "resizable", 0)
Config.set("kivy", "window_icon", "fakecam.png")

from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import ObjectProperty

import fakecam


def threaded(fn):
    def wrapper(*args, **kwargs):
        t = Thread(target=fn, args=args, kwargs=kwargs)
        t.daemon = True
        t.start()

    return wrapper


class RootWidget(FloatLayout):
    manager = ObjectProperty()


class FakeCamApp(App):
    use_kivy_settings = False
    state = fakecam.state
    mags = {1: "", 2: "", 3: ""}

    @threaded
    def toggle(self, widget, value):
        if value == "down":
            # reload takes in case mag got erased
            fakecam.load_takes()

            self.state["mag"]["state"] = 0
            self.state["fc0"]["meta"]["uuid"] = self.mags[widget.mag_number]
            time.sleep(1)
            self.state["mag"]["state"] = 4
        else:
            self.state["mag"]["state"] = 0

    def build(self):
        fakecam.run()
        self.mags = {
            1: fakecam.state["fc0"]["meta"]["uuid"],
            2: "d6552632-fd95-4cf6-afb9-d2e1a8ad72c8",
            3: "6fe23556-010c-4980-9e95-c19af0ca6039",
        }

        root = RootWidget()
        self.title = "FakeCam"

        return root


if __name__ == "__main__":
    FakeCamApp().run()
