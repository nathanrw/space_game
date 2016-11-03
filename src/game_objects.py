""" Definitions of all game objects. Note that pretty much all they now
do is fill themselves with components. It should soon be possible to
initialise them from data and remove this file."""

from utils import GameObject
from physics import CollisionHandler
from behaviours import ManuallyShootsBullets, DamageOnContact

import pygame

class Target(GameObject):
    """ An enemy than can fly around shooting bullets. """

class Player(GameObject):
    """ The player! """

class BulletShooterCollisionHandler(CollisionHandler):
    """ Collision handler to apply bullet damage. """
    def __init__(self):
        CollisionHandler.__init__(self, GameObject, GameObject)
    def handle_matching_collision(self, a, b):
        dmg = a.get_component(DamageOnContact)
        if dmg is not None:
            dmg.apply_damage(b)
