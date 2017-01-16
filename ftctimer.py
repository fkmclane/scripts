#!/usr/bin/env python3
import subprocess
import time

import urwid


class Mode:
    def __init__(self, name='idle', period=0, sounds=[]):
        self.name = name
        self.period = period
        self.sounds = sounds


class ClockDisplay:
    def __init__(self, modes):
        self.modes = modes

        self.background = urwid.Frame(body=urwid.SolidFill())
        self.clocktext = urwid.BigText('clock', urwid.HalfBlock7x7Font())
        self.modetext = urwid.BigText('mode', urwid.HalfBlock7x7Font())
        self.overlay = urwid.Overlay(self.clocktext, self.background, 'center', None, 'middle', None)
        self.overlay = urwid.Overlay(self.modetext, self.overlay, 'center', None, 'middle', None, top=20)
        self.loop = urwid.MainLoop(self.overlay, unhandled_input=self.unhandled_input)

        self.mode_index = -1
        self.update_mode()

    def run(self):
        self.loop.run()

    def unhandled_input(self, key):
        if key == ' ':
            self.update_mode()
        elif key == 'q':
            raise urwid.ExitMainLoop()

    def get_time(self):
        return time.time() * 1000

    def update_mode(self):
        if len(self.modes) == 0:
            return

        self.mode_index = (self.mode_index + 1) % len(self.modes)

        self.mode = self.modes[self.mode_index]
        self.start = self.get_time()
        self.done = False

        self.sound_index = -1
        self.update_sound()

        self.update_clock()

    def update_sound(self):
        self.sound_index += 1

        if self.sound_index >= len(self.mode.sounds):
            self.sound_time, self.sound_file = None, None
        else:
            self.sound_time, self.sound_file = self.mode.sounds[self.sound_index]

    def update_clock(self, loop=None, user_data=None):
        if self.done:
            return

        self.left = max(self.mode.period * 1000 - (self.get_time() - self.start), 0)

        self.loop.set_alarm_in(0.1, self.update_clock)

        minute = int(self.left // 60000)
        second = int(self.left // 1000 % 60)
        decisecond = int(self.left // 100 % 10)

        if self.sound_index < len(self.mode.sounds):
            time = self.left / 1000

            if time <= self.sound_time:
                subprocess.Popen(['aplay', self.sound_file], stderr=subprocess.DEVNULL)
                self.update_sound()

        self.clock = '{:02}:{:02}.{:1}'.format(minute, second, decisecond)

        self.clocktext.set_text(self.clock)
        self.modetext.set_text(self.mode.name)

        if self.left == 0:
            self.done = True


if __name__ == '__main__':
    modes = [
            Mode('idle'),
            Mode('autonomous', period=30, sounds=[(30, 'auto_start.wav'), (0, 'auto_stop.wav')]),
            Mode('teleop', period=90, sounds=[(90, 'tele_start.wav'), (30, 'tele_end.wav'), (0, 'tele_stop.wav')]),
    ]

    display = ClockDisplay(modes)

    display.run()
