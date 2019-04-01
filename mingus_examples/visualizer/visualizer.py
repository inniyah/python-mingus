#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import math
import numpy
import rtmidi
import freetype2

this_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(this_dir, '../..'))

import pyglet
from pyglet import gl

#from mingus.core import progressions, intervals
#from mingus.core import chords as ch
#from mingus.containers import NoteContainer, Note
#from mingus.midi import fluidsynth

from mingus.core.notes import int_to_note

SF2 = '/usr/share/sounds/sf2/FluidR3_GM.sf2'


class TrueTypeMonoFont():
  def __init__(self, font_name, size):
    FT = freetype2.FT # easier access to constants
    self.lib = freetype2.get_default_lib()

    # Load font  and check it is monotype
    face = self.lib.find_face(font_name)
    face.set_char_size(size=size, resolution=90)
    if face.face_flags & FT.FACE_FLAG_FIXED_WIDTH  == 0:
        raise 'Font is not monotype'

    # Determine largest glyph size
    width, height, ascender, descender = 0, 0, 0, 0
    for c in range(32,128):
        face.load_char(c, FT.LOAD_RENDER | FT.LOAD_FORCE_AUTOHINT)
        bitmap    = face.glyph.bitmap
        width     = max( width, bitmap.width )
        ascender  = max( ascender, face.glyph.bitmap_top )
        descender = max( descender, bitmap.rows-face.glyph.bitmap_top )
    height = ascender+descender

    # Generate texture data
    Z = numpy.zeros((height*6, width*16), dtype=numpy.ubyte)
    for j in range(6):
        for i in range(16):
            face.load_char(32+j*16+i, FT.LOAD_RENDER | FT.LOAD_FORCE_AUTOHINT )
            bitmap = face.glyph.bitmap.copy_with_array()
            x = i*width  + face.glyph.bitmap_left
            y = j*height + ascender - face.glyph.bitmap_top
            Z[y:y+bitmap.rows,x:x+bitmap.width].flat = bitmap.buffer

    # Bound texture
    self.texture_ids = (pyglet.gl.GLuint * 1) ()
    gl.glGenTextures(1, self.texture_ids)
    self.texture_id = self.texture_ids[0]
    gl.glBindTexture( gl.GL_TEXTURE_2D, self.texture_id )
    gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR )
    gl.glTexParameterf( gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR )
    gl.glTexImage2D( gl.GL_TEXTURE_2D, 0, gl.GL_ALPHA, Z.shape[1], Z.shape[0],
                     0, gl.GL_ALPHA, gl.GL_UNSIGNED_BYTE, Z.tostring() )

    # Generate display lists
    dx, dy = width/float(Z.shape[1]), height/float(Z.shape[0])
    self.base = gl.glGenLists(8*16)
    for i in range(8*16):
        c = chr(i)
        x = i % 16
        y = i // 16 - 2
        gl.glNewList(self.base+i, gl.GL_COMPILE)
        if (c == '\n'):
            gl.glPopMatrix( )
            gl.glTranslatef( 0, -height, 0 )
            gl.glPushMatrix( )
        elif (c == '\t'):
            gl.glTranslatef( 4*width, 0, 0 )
        elif (i >= 32):
            gl.glBegin( gl.GL_QUADS )
            gl.glTexCoord2d( (x  )*dx, (y+1)*dy ), gl.glVertex2d( 0,     -height )
            gl.glTexCoord2d( (x  )*dx, (y  )*dy ), gl.glVertex2d( 0,     0 )
            gl.glTexCoord2d( (x+1)*dx, (y  )*dy ), gl.glVertex2d( width, 0 )
            gl.glTexCoord2d( (x+1)*dx, (y+1)*dy ), gl.glVertex2d( width, -height )
            gl.glEnd( )
            gl.glTranslatef( width, 0, 0 )
        gl.glEndList( )

  def write_text(self, text):
    #gl.glTexEnvf( gl.GL_TEXTURE_ENV, gl.GL_TEXTURE_ENV_MODE, gl.GL_MODULATE )
    #gl.glEnable( gl.GL_DEPTH_TEST )
    gl.glEnable( gl.GL_BLEND )
    #gl.glEnable( gl.GL_COLOR_MATERIAL )
    #gl.glColorMaterial( gl.GL_FRONT_AND_BACK, gl.GL_AMBIENT_AND_DIFFUSE )
    gl.glBlendFunc( gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA )
    gl.glEnable( gl.GL_TEXTURE_2D )

    gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
    gl.glColor4f(1, 1, 0, 1)
    gl.glPushMatrix()
    gl.glLoadIdentity( )
    gl.glScalef(0.003, 0.003, 0)
    #gl.glTranslatef(10, 100, 0)
    gl.glPushMatrix()
    gl.glListBase(self.base)
    gl.glCallLists(len(text), gl.GL_UNSIGNED_BYTE, bytes(text, 'utf-8'))
    #for c in text:
    #    gl.glCallList(self.base + 1 + ord(c))
    gl.glPopMatrix()
    gl.glPopMatrix()

    gl.glDisable( gl.GL_BLEND )
    gl.glDisable( gl.GL_TEXTURE_2D )



class SectorRing():
    STATE_NONE = 0
    STATE_IDLE = 1
    STATE_PRESSED = 2

    class Sector():
        def __init__(self, outer_radius, inner_radius, width_angle, pos_angle, num_points, ref_colors):
            self.outer_radius = outer_radius
            self.inner_radius = inner_radius
            self.width_angle = width_angle
            self.pos_angle = pos_angle
            self.num_points = num_points
            self.vertex = []
            self.indices = []
            self.state = SectorRing.STATE_IDLE
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

            for state in [SectorRing.STATE_IDLE, SectorRing.STATE_PRESSED]:
                if not ref_colors.get(state, None) is None:
                    self.colors[state] = ref_colors[state][1] * self.num_points + ref_colors[state][0] * self.num_points
                else:
                    self.colors[state] = None

        def render(self):
            if self.state != SectorRing.STATE_NONE:
                color = self.colors[self.state]
                if not color is None:
                    vertices = pyglet.graphics.draw_indexed(
                        2 * self.num_points,
                        gl.GL_TRIANGLES,
                        self.indices,
                        ('v3f', self.vertex),
                        ('c3B', color)
                    )

        def set_state(self, state):
            self.state = state

    def __init__(self, outer_radius, inner_radius, ref_colors=None):
        self.notes = { int_to_note((i*7)%12, 'b'): None for i in range(0, 12) } # Circle of fifths

        if ref_colors is None:
            ref_colors = {
                SectorRing.STATE_IDLE: [[255, 120, 12], [255, 8, 45]],
                SectorRing.STATE_PRESSED: [[0, 255, 255], [0, 128, 255]],
            }

        i = 0
        for note in self.notes:
            self.notes[note] = SectorRing.Sector(
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
        gl.glClearColor(0.2, 0.2, 0.21, 1)

        self.font = TrueTypeMonoFont("Liberation Mono", 64)

        self.inner_ring = SectorRing(
            0.8,
            0.7,
            {
                SectorRing.STATE_IDLE: [[255, 120, 12], [255, 8, 45]],
                SectorRing.STATE_PRESSED: [[0, 255, 255], [0, 128, 255]],
            }
        )

        self.outer_ring = SectorRing(
            0.85,
            0.82,
            {
                SectorRing.STATE_IDLE: None,
                SectorRing.STATE_PRESSED: [[0, 255, 0], [0, 128, 0]],
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
        self.font.write_text("Test")

    def on_resize(self, width, height):
        gl.glViewport(0, 0, width, height)

    def on_key_press(self, key, modifier):
        if key == pyglet.window.key.ESCAPE:
            pyglet.app.exit()
            self.midi_in.close_port()
            print("Exit ;(")
            sys.exit()

    def on_key_release(self, key, modifier):
        if key == pyglet.window.key.Q:
            self.inner_ring.notes[self.key_map[1]].set_state(SectorRing.STATE_PRESSED)

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
                    window.outer_ring.notes[window.key_map[pitch_class]].set_state(SectorRing.STATE_PRESSED)
                else:
                    window.outer_ring.notes[window.key_map[pitch_class]].set_state(SectorRing.STATE_IDLE)

    def midi_received(self, midi_event, data=None):
        current_timestamp = time.time_ns() / (10 ** 9) # Converted to floating-point seconds
        midi_msg, delta_time = midi_event
        if len(midi_msg) > 2:
            pitch_class = midi_msg[1] % 12
            octave = midi_msg[1] // 12

            # A note was hit
            if midi_msg[2] != 0:
                self.inner_ring.notes[self.key_map[pitch_class]].set_state(SectorRing.STATE_PRESSED)
                self.press_counter[pitch_class] += 1

            # The last note with that pitch was released
            elif self.press_counter[pitch_class] <= 1:
                self.inner_ring.notes[self.key_map[pitch_class]].set_state(SectorRing.STATE_IDLE)
                self.press_counter[pitch_class] -= 1

            # More than one octaves were being played simultaneously
            else:
                self.press_counter[pitch_class] -= 1

            self.last_notes.append((current_timestamp,  midi_msg[2] != 0, midi_msg[1], octave, pitch_class))
            if midi_msg[2] != 0: # A note was hit
                self.memory_counter[pitch_class] += 1
                self.outer_ring.notes[self.key_map[pitch_class]].set_state(SectorRing.STATE_PRESSED)

if __name__ == "__main__":
    window = MainWindow(800, 800, "Harmonic Visualizer", resizable=True)
    pyglet.clock.schedule_interval(MainWindow.update, 1/60, window)
    pyglet.app.run()
