""" Low-level gubbins that are needed in many places. """

import random
import pygame
import sys

# Use the vec2d class from pymunk to avoid writing our own.
from pymunk import Vec2d


def fromwin(path):
    """Paths serialized on windows have \\ in them, so we need to convert
       them in order to read them on unix. Windows will happily read unix
       paths so we dont need to worry about going the other way."""
    return path.replace("\\", "/")


def bail():
    """ Bail out, ensuring the pygame windows goes away. """
    pygame.quit()
    sys.exit(1)


class Timer(object):
    """ A simple stopwatch - you tell it how much time has gone by and it
    tells you when it's done. """

    def __init__(self, period):
        """ Constructor. """
        self.timer = 0
        self.period = period

    def advance_to_fraction(self, frac):
        """ Advance the timer to a fraction of the period. 'frac' is a number in the range [0, 1]. """
        self.timer = self.period * frac

    def tick(self, dt):
        """ Advance the timer by the given time interval, and return whether it has dinged.  The timer
        value can exceed the period (and subsequent calls to tick() will still advance the timer, but
        will all return True i.e. 'expired'. """
        self.timer += dt
        return self.expired()

    def expired(self):
        """ Has the timer been counting for the period or more? """
        return self.timer >= self.period

    def pick_index(self, num_indices):
        """ Given a count, map the timer value (as a fraction of the period) to a value in the range [0, count). If
        the timer has exceeded the period, the value is clamped to 'num_indices-1'. """
        n = num_indices-1
        return min(int((self.timer/float(self.period))*n), n)

    def reset(self):
        """ Reset the timer by subtracting the period from the counter.  This avoids time being 'lost' from
        repeating timers if the counter exceeds the period. """
        self.timer -= self.period

    def randomise(self):
        """ Set the timer to a random number in the range [0, period]. """
        self.timer = self.period * random.random()


class Polygon(object):
    """ A polygon. Used to be used for bullets. """

    @classmethod
    def make_bullet_polygon(klass, a, b):
        """ Make a diamond-shaped polygon with a long tail. """
        perp = (a-b).perpendicular_normal() * (a-b).length * 0.1
        lerp = a + (b - a) * 0.1
        c = lerp + perp
        d = lerp - perp
        return Polygon((a,c,b,d,a))

    def __init__(self, points):
        """ Constructor. """
        self.points = [p for p in points]
