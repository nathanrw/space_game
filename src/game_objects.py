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

    def start_shooting(self, pos):
        """ Start shooting at a particular screen space point. """
        guns = self.get_components(ManuallyShootsBullets)
        for g in guns:
            g.start_shooting_screen(pos)

    def stop_shooting(self):
        """ Stop the guns. """
        guns = self.get_components(ManuallyShootsBullets)
        for g in guns:
            g.stop_shooting()

    def is_shooting(self):
        """ Are the guns firing? If one is they both are. """
        guns = self.get_components(ManuallyShootsBullets)
        return guns[0].shooting

class BulletShooterCollisionHandler(CollisionHandler):
    """ Collision handler to apply bullet damage. """
    def __init__(self):
        CollisionHandler.__init__(self, GameObject, GameObject)
    def handle_matching_collision(self, a, b):
        dmg = a.get_component(DamageOnContact)
        if dmg is not None:
            dmg.apply_damage(b)
