#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import numpy
import pyaudio

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '../..'))

from mingus.midi import pyfluidsynth

pa = pyaudio.PyAudio()
strm = pa.open(
    format = pyaudio.paInt16,
    channels = 2, 
    rate = 44100, 
    output = True)

s = []

fl = pyfluidsynth.Synth()

# Initial silence is 1 second
s = numpy.append(s, fl.get_samples(44100 * 1))

sfid = fl.sfload(os.path.join(this_dir, "example.sf2"))
fl.program_select(0, sfid, 0, 0)

fl.noteon(0, 60, 30)
fl.noteon(0, 67, 30)
fl.noteon(0, 76, 30)

# Chord is held for 2 seconds
s = numpy.append(s, fl.get_samples(44100 * 2))

fl.noteoff(0, 60)
fl.noteoff(0, 67)
fl.noteoff(0, 76)

# Decay of chord is held for 1 second
s = numpy.append(s, fl.get_samples(44100 * 1))

fl.delete()

samps = pyfluidsynth.raw_audio_string(s)

print(len(samps))
print('Starting playback')
strm.write(samps)
