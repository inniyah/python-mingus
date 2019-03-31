#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import math
import rtmidi

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '../..'))

from pyglet.gl import *

#from mingus.core import progressions, intervals
#from mingus.core import chords as ch
#from mingus.containers import NoteContainer, Note
#from mingus.midi import fluidsynth

from mingus.core.notes import int_to_note

import freetype2

SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'

class PygletSector():
    STATE_NONE = 0
    STATE_IDLE = 1
    STATE_PRESSED = 2

    def __init__(self, outer_radius, inner_radius, width_angle, pos_angle, num_points, ref_colors):
        self.outer_radius = outer_radius
        self.inner_radius = inner_radius
        self.width_angle = width_angle
        self.pos_angle = pos_angle
        self.num_points = num_points
        self.vertex = []
        self.indices = []
        self.state = self.STATE_IDLE
        self.inner_point = width_angle/2 + width_angle
        self.colors = {}

        for i in range(self.num_points):
            angle = self.width_angle * (i / (self.num_points - 1)) + pos_angle
            x = math.cos(angle) * outer_radius
            y = math.sin(angle) * outer_radius
            z = 0
            self.vertex.extend([x,y,z])

        for i in range(self.num_points):
            angle = self.width_angle - self.width_angle * (i/(self.num_points-1)) + pos_angle
            x = math.cos(angle) * inner_radius
            y = math.sin(angle) * inner_radius
            z = 0
            self.vertex.extend([x,y,z])

        for i in range(self.num_points - 1):
            n = 2 * self.num_points - 1
            self.indices.extend([i, i + 1 , n - i])
            self.indices.extend([n - i, n - 1 - i, i + 1])

        for state in [self.STATE_IDLE, self.STATE_PRESSED]:
            if not ref_colors.get(state, None) is None:
                self.colors[state] = ref_colors[state][1] * self.num_points + ref_colors[state][0] * self.num_points
            else:
                self.colors[state] = None

    def render(self):
        if self.state != self.STATE_NONE:
            color = self.colors[self.state]
            if not color is None:
                vertices = pyglet.graphics.draw_indexed(
                    2 * self.num_points,
                    GL_TRIANGLES,
                    self.indices,
                    ('v3f', self.vertex),
                    ('c3B', color)
                )

    def played(self):
        self.state = self.STATE_PRESSED

    def idle(self):
        self.state = self.STATE_IDLE

class PygletSectorRing():
    def __init__(self, outer_radius, inner_radius, ref_colors=None):
        self.notes = { int_to_note((i*7)%12, 'b'): None for i in range(0, 12) } # Circle of fifths

        if ref_colors is None:
            ref_colors = {
                PygletSector.STATE_IDLE: [[255, 120, 12], [255, 8, 45]],
                PygletSector.STATE_PRESSED: [[0, 255, 255], [0, 128, 255]],
            }

        i = 0
        for note in self.notes:
            self.notes[note] = PygletSector(
                outer_radius,
                inner_radius,
                math.pi / 6.4,
                -2 * (i-2) * math.pi / 12,
                10,
                ref_colors
            )
            i += 1

    def render(self):
        for note in self.notes:
            self.notes[note].render()

class PygletLineSegments():
    def __init__(self, sectors):
        self.indices = []
        self.vertex = []
        self.sectors = sectors
        self.active = {}

    def render(self):
        self.indices = []
        self.vertex = []
        color = []

        for note,PygletSector in self.sectors.items():
            if PygletSector.state == PygletSector.STATE_PRESSED:
                self.active[note] = note
                tri = sorted(self.active.items(), key=lambda t: t[0])
                self.active = dict(tri)
            elif note in self.active.keys():
                self.active.pop(note)
        #print(self.active.keys())

        for note in self.active:
            x = (math.cos((self.sectors[note].width_angle / 2) + self.sectors[note].pos_angle)  * self.sectors[note].inner_radius)
            y = (math.sin((self.sectors[note].width_angle / 2) + self.sectors[note].pos_angle)  * self.sectors[note].inner_radius)
            self.vertex.extend([x,y,0])
            color.extend([140,140,240])

        for i in range(len(self.active) - 1):
            self.indices.extend([i, i + 1])
        self.indices.extend([len(self.active) - 1, 0])

        if len(self.active) > 2:
            vertices = pyglet.graphics.draw_indexed(
                len(self.active),
                GL_LINES,
                self.indices,
                ('v3f', self.vertex),
                ('c3B', color)
            )

class FifoList():
    def __init__(self):
        self.data = {}
        self.nextin = 0
        self.nextout = 0
    def append(self, data):
        self.nextin += 1
        self.data[self.nextin] = data
    def pop(self):
        self.nextout += 1
        result = self.data[self.nextout]
        del self.data[self.nextout]
        return result
    def peek(self):
        return self.data[self.nextout + 1] if self.data else None

class MainWindow(pyglet.window.Window):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        icon = pyglet.image.load(os.path.join(this_dir, 'icon.png'))
        self.set_icon(icon)
        self.set_minimum_size(300, 300)
        glClearColor(0.2, 0.2, 0.21, 1)

        self.inner_ring = PygletSectorRing(
            0.8,
            0.7,
            {
                PygletSector.STATE_IDLE: [[255, 120, 12], [255, 8, 45]],
                PygletSector.STATE_PRESSED: [[0, 255, 255], [0, 128, 255]],
            }
        )
        self.pyglet_line = PygletLineSegments(self.inner_ring.notes)

        self.outer_ring = PygletSectorRing(
            0.85,
            0.82,
            {
                PygletSector.STATE_IDLE: None,
                PygletSector.STATE_PRESSED: [[0, 255, 0], [0, 128, 0]],
            }
        )

        self.midi_in = rtmidi.MidiIn()
        available_ports = self.midi_in.get_ports()
        if available_ports:
            midi_port_num = 1
            self.midi_in_port = self.midi_in.open_port(midi_port_num)
            print("Using MIDI Interface {}: '{}'".format(midi_port_num, available_ports[midi_port_num]))
        else:
            print("Creating virtual MIDI input.")
            self.midi_in_port = self.midi_in.open_virtual_port("midi_driving_in")

        self.midi_in.set_callback(self.midi_received)

        self.key_map = { i: int_to_note(i, 'b') for i in range(0, 12) }
        self.press_counter = [0] * 12
        self.memory_counter = [0] * 12

        self.last_notes = FifoList()

    def on_draw(self):
        self.clear()
        self.outer_ring.render()
        self.inner_ring.render()
        self.pyglet_line.render()

    def on_resize(self, width, height):
        glViewport(0, 0, width, height)

    def on_key_press(self, key, modifier):
        if key == pyglet.window.key.ESCAPE:
            pyglet.app.exit()
            self.midi_in.close_port()
            print("Exit ;(")
            sys.exit()

    def on_key_release(self, key, modifier):
        if key == pyglet.window.key.Q:
            self.inner_ring.notes[self.key_map[1]].played()

    def update(dt, window):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        threshold_timestamp = current_timestamp - 5.0 # In floating-point seconds
        data = window.last_notes.peek()
        while data is not None:
            timestamp, pressed, note, octave, pitch_class = data
            data = None
            if timestamp < threshold_timestamp:
                window.last_notes.pop()
                #print("%s" % ((pressed, note, octave, pitch_class),))
                if not pressed:
                    window.memory_counter[pitch_class] -= 1

                if window.press_counter[pitch_class] > 0 or window.memory_counter[pitch_class] > 0:
                    window.outer_ring.notes[window.key_map[pitch_class]].played()
                else:
                    window.outer_ring.notes[window.key_map[pitch_class]].idle()

    def midi_received(self, midi_event, data=None):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        midi_msg, delta_time = midi_event
        if len(midi_msg) > 2:
            pitch_class = midi_msg[1] % 12
            octave = midi_msg[1] // 12

            # A note was hit
            if midi_msg[2] != 0:
                self.inner_ring.notes[self.key_map[pitch_class]].played()
                self.press_counter[pitch_class] += 1

            # The last note with that pitch was released
            elif self.press_counter[pitch_class] <= 1:
                self.inner_ring.notes[self.key_map[pitch_class]].idle()
                self.press_counter[pitch_class] -= 1

            # More than one octaves were being played simultaneously
            else:
                self.press_counter[pitch_class] -= 1

            self.last_notes.append((current_timestamp,  midi_msg[2] != 0, midi_msg[1], octave, pitch_class))
            if midi_msg[2] != 0: # A note was hit
                self.memory_counter[pitch_class] += 1
                self.outer_ring.notes[self.key_map[pitch_class]].played()

if __name__ == "__main__":
    window = MainWindow(800, 800, "Harmonic Visualizer", resizable=True)
    pyglet.clock.schedule_interval(MainWindow.update, 1/60, window)
    pyglet.app.run()
