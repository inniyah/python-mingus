#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '../..'))

from mingus.midi import pyfluidsynth

fs = pyfluidsynth.Synth()
fs.start(driver="alsa")

sfid = fs.sfload(os.path.join(this_dir, "example.sf2"))
fs.program_select(0, sfid, 0, 0)

fs.noteon(0, 60, 30)
time.sleep(0.3)

for i in range(10):
    fs.cc(0, 93, 127)
    fs.pitch_bend(0, i * 512)
    time.sleep(0.1)
fs.noteoff(0, 60)

time.sleep(1.0)

fs.delete()
