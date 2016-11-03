""" Definitions of all game objects. Note that pretty much all they now
do is fill themselves with components. It should soon be possible to
initialise them from data and remove this file."""

from utils import GameObject

class Target(GameObject):
    """ An enemy than can fly around shooting bullets. """

class Player(GameObject):
    """ The player! """
