""" Basic building blocks of the game infrastructure. This includes a scheme
for assembly entitys from components, a system for loading entity
configuration from json data files, and other utilities. """

import random
import pygame
import sys
import os
import math
import collections
import yaml
from pymunk.vec2d import Vec2d

def fromwin(path):
    """Paths serialized on windows have \\ in them, so we need to convert
       them in order to read them on unix. Windows will happily read unix
       paths so we dont need to worry about going the other way."""
    return path.replace("\\", "/")

def bail():
    """ Bail out, ensuring the pygame windows goes away. """
    pygame.quit()
    sys.exit(1)

def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=collections.OrderedDict):
    """ Taken from http://stackoverflow.com/a/21912744

    We need to be able to iterate component keys in 'document order' because
    component types have implicit dependencies on other types, if we try to
    construct components in an arbitrary order then it might not work.

    A better solution to this problem would be to have component types declare
    their dependencies, and not allow them to access undeclared dependencies.

    For now, to get it working again, we will use this solution. """

    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)

def lookup_type(class_path):
    """ Lookup a class by string name so that it can be dynamically
    instantiated. This is used for component and entity creation. This
    implementation has been pinched from an answer on stack overflow:
    http://stackoverflow.com/questions/16696225/dynamically-\
    instantiate-object-of-the-python-class-similar-to-php-new-classname"""

    try:
        module_path, class_name = class_path.rsplit(".", 1)
    except ValueError as e:
        print( "**************************************************************" )
        print( "ERROR CREATING OBJECT: '%s'" % class_path )
        print( "Must specify e.g. module.class in path. Got: '%s'." % class_path )
        print( "**************************************************************" )
        print(e)
        bail()

    try:
        module = __import__(module_path, fromlist=[class_name])
    except ImportError as e:
        print( "**************************************************************" )
        print( "ERROR CREATING OBJECT: '%s'" % class_path )
        print( "The module '%s' could not be imported." % module_path )
        print( "**************************************************************" )
        print(e)
        bail()

    try:
        cls = getattr(module, class_name)
    except AttributeError as e:
        print( "**************************************************************" )
        print( "ERROR CREATING OBJECT: '%s'" % class_path )
        print( "The attribute '%s' could not be found." % class_name )
        print( "**************************************************************" )
        print(e)
        bail()

    # Might not actually be a class. But if it's a function that returns
    # an instance, who cares...
    return cls

class Timer(object):
    """ A simple stopwatch - you tell it how much time has gone by and it
    tells you when it's done. """
    def __init__(self, period):
        self.timer = 0
        self.period = period
    def advance_to_fraction(self, frac):
        self.timer = self.period * frac
    def tick(self, dt):
        self.timer += dt
        return self.expired()
    def expired(self):
        return self.timer >= self.period
    def pick_index(self, num_indices):
        n = num_indices-1
        return min(int((self.timer/float(self.period))*n), n)
    def reset(self):
        self.timer -= self.period
    def randomise(self):
        self.timer = self.period * random.random()

class Polygon(object):
    """ A polygon. Used to be used for bullets. """
    @classmethod
    def make_bullet_polygon(klass, a, b):
        perp = (a-b).perpendicular_normal() * (a-b).length * 0.1
        lerp = a + (b - a) * 0.1
        c = lerp + perp
        d = lerp - perp
        return Polygon((a,c,b,d,a))
    def __init__(self, points):
        self.points = [p for p in points]
