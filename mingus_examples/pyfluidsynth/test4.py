#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import random

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '../..'))

from mingus.midi import pyfluidsynth

fs = pyfluidsynth.Synth()
fs.start(driver="alsa")

sfid = fs.sfload(os.path.join(this_dir, "example.sf2"))
fs.program_select(0, sfid, 0, 0)

def press(key, velocity=64, duration=0.5):
    fs.noteon(0, key + 19, velocity)
    time.sleep(duration)
    fs.noteoff(0, key + 19)

def random_key(mean_key=44):
    x = random.gauss(mean_key, 10.0)
    if x < 1:
        x = 1
    elif x > 88:
        x = 88
    return int(round(x))

def random_velocity():
    x = random.gauss(100.0, 10.0)
    if x < 1:
        x = 1
    elif x > 127:
        x = 127
    return int(round(x))

def random_duration(mean_duration=2.0):
    x = random.gauss(mean_duration, 2.0)
    if x < 0.2:
        x = 0.2
    return x

def random_play(num, mean_key, mean_duration):
    while num != 0:
        num -= 1
        key = random_key(mean_key)
        velocity = random_velocity()
        duration = random_duration(mean_duration)
        press(key, velocity, duration)

random_play(8, 10, 0.3)

fs.delete()
