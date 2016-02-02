#!/usr/bin/env python
from __future__ import print_function

from blinkstick import blinkstick

import netifaces
import sys
import time

iface = 'wlp8s0'

bstick = blinkstick.find_first()

if bstick is None:
	print('no blinkstick found')
	sys.exit(1)

for char in netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']:
	time.sleep(2)
	if char is '.':
		bstick.blink(20, 20, 20, delay=1000)
	else:
		bstick.blink(20, 20, 20, repeats=int(char), delay=200)
