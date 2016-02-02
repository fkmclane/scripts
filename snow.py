#!/usr/bin/env python3
import curses
import random
import time

class Flake:
    def __init__(self, y, x, speed, char):
        self.y = y
        self.x = x
        self.speed = speed
        self.char = char

    def tick(self):
        self.y += self.speed[0]
        self.x += self.speed[1]

    def draw(self, draw):
        draw(self.y, self.x, self.char)

def gen_flakes(num, top, height, width, fall, blow, chars='#*&%'):
    start = -height/fall[1]*blow[1]

    for _ in range(num):
        y = random.uniform(0, top)
        x = random.uniform(start, width)
        speed = (random.uniform(*fall), random.uniform(*blow))
        char = random.choice(chars)

        if x < 0:
            y += -x/speed[1]*speed[0]
            x = 0

        yield Flake(y, x, speed, char)

window = curses.initscr()
height, width = window.getmaxyx()

num = 100
top = 10
fall = (1, 4)
blow = (1, 0)
tick = 0.1

flakes = list(gen_flakes(num, height, height, width, fall, blow))

try:
    while True:
        window.clear()

        for flake in flakes:
            flake.tick()

        flakes = list(filter(lambda flake: flake.y < height and flake.x < width, flakes))

        for flake in flakes:
            try:
                flake.draw(lambda y, x, char: window.addstr(int(y), int(x), char))
            except curses.error:
                pass

        flakes += gen_flakes(num - len(flakes), 0, height, width, fall, blow)

        window.refresh()

        time.sleep(tick)
except KeyboardInterrupt:
    pass

curses.endwin()
