
from vector2d import Vec2d

from utils import *
from physics import *
from drawing import *
from input_handling import *
from physics import *
from behaviours import *

import pygame

class Explosion(GameObject):
    """ An explosion. It will play an animation and then disappear. """

    def initialise(self, game_services, config):
        """ Create a body and a drawable for the explosion. """
        GameObject.initialise(self, game_services, config)
        self.add_component(Body(self, game_services, config))
        self.add_component(AnimBodyDrawable(self, game_services, config))

class Bullet(GameObject):
    """ A projectile. """

    def initialise(self, game_services, config):
        """ Build a body and drawable. The bullet will be destroyed after
        a few seconds. """
        GameObject.initialise(self, game_services, config)
        self.add_component(DamageOnContact(self, game_services, config))
        self.add_component(Body(self, game_services, config))
        self.add_component(BulletDrawable(self, game_services, config))
        self.add_component(ExplodesOnDeath(self, game_services, config))
        self.add_component(KillOnTimer(self, game_services, config))

class ShootingBullet(Bullet):
    """ A bullet that is a gun! """

    def initialise(self, game_services, config):
        """ Initialise the shooting bullet. """
        Bullet.initialise(self, game_services, config)
        self.add_component(AutomaticallyShootsBullets(self, game_services, config))

class Shooter(GameObject):
    """ An object with a health bar that can shoot bullets. """

    def initialise(self, game_services, config):
        """ Create a body and some drawables. We also set up the gun. """
        GameObject.initialise(self, game_services, config)
        self.add_component(Hitpoints(self, game_services, config))
        self.add_component(Body(self, game_services, config))
        self.add_component(AnimBodyDrawable(self, game_services, config))
        self.add_component(HealthBarDrawable(self, game_services, config))
        self.add_component(ExplodesOnDeath(self, game_services, config))

class Target(Shooter):
    """ An enemy than can fly around shooting bullets. """

    def initialise(self, game_services, config):
        """ Overidden to configure the body and the gun. """
        Shooter.initialise(self, game_services, config)
        self.add_component(AutomaticallyShootsBullets(self, game_services, config))
        self.add_component(FollowsPlayer(self, game_services, config))

class Carrier(Target):
    """ A large craft that launches fighters. """

    def initialise(self, game_services, config):
        """ Overidden to configure the body and the gun. """
        Target.initialise(self, game_services, config)
        self.add_component(LaunchesFighters(self, game_services, config))

class Player(Shooter):
    """ The player! """

    def initialise(self, game_services, config):
        """ Initialise with the game services: create an input handler so
        the player can drive us around. """
        Shooter.initialise(self, game_services, config)
        gun_config = game_services.get_resource_loader().load_config_file(config["gun_config"])
        torp_config = game_services.get_resource_loader().load_config_file(config["torpedo_gun_config"])
        self.add_component(PlayerInputHandler(self, game_services, config))
        self.add_component(ManuallyShootsBullets(self, game_services, gun_config))
        self.add_component(ManuallyShootsBullets(self, game_services, torp_config))
        self.add_component(MovesCamera(self, game_services, config))

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
        CollisionHandler.__init__(self, Bullet, Shooter)
    def handle_matching_collision(self, bullet, shooter):
        dmg = bullet.get_component(DamageOnContact)
        if dmg is not None:
            dmg.apply_damage(shooter)
        
