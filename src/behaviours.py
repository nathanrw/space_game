""" Object behaviours for the game and game objects composed out of them.

See utils.py for the overall scheme this fits into.

Currently for the most part all derived game objects do is initialise()
themselves with different components. I think all this will get pushed
into components and some data driven composition scheme, and the actual
game objects will become very simple. Even the player could be turned
into a behaviour as opposed to a derived object. This is probably what
I want to do.

"""

from vector2d import Vec2d

from utils import *
from physics import *
from drawing import *
from input_handling import *
from physics import *

import pygame
        
class Behaviour(Component):
    """ A component with access to the game state so that it can do
    various things. Perhaps eventually all components will look like
    this, and this class can be deleted. """
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)

class EnemyBehaviour(Behaviour):
    def towards_player(self):
        """ Get the direction towards the player. """
        player = self.game_services.get_player()
        if player.is_garbage:
            return Vec2d(0, 1)
        player_pos = player.get_component(Body).position
        displacement = player_pos - self.get_component(Body).position
        direction = displacement.normalized()
        return direction

class FollowsPlayer(EnemyBehaviour):
    def __init__(self, game_object, game_services, config):
        EnemyBehaviour.__init__(self, game_object, game_services, config)

    def update(self, dt):

        # accelerate towards the player and tries to match velocities when close
        player = self.game_services.get_player()
        if player.is_garbage:
            return
        
        body = self.get_component(Body)
        player_body = player.get_component(Body)
        displacement = player_body.position - body.position
        rvel = player_body.velocity - body.velocity
        target_dist = self.config["desired_distance_to_player"]

        # distality is a mapping of distance onto the interval [0,1) to
        # interpolate between two behaviours
        distality = 1 - 2 ** ( - displacement.length / target_dist )
        direction = ( 1 - distality ) * rvel.normalized() + distality * displacement.normalized()

        # Determine the fraction of our thrust to apply. This is governed by
        # how far away the target is, and how far away we want to be.
        frac = min(max(displacement.length / target_dist, rvel.length/200), 1)

        # Apply force in the interpolated direction.
        thrust = body.mass * self.config["acceleration"]
        force = frac * thrust * direction
        body.force = force

class ManuallyShootsBullets(Behaviour):
    """ Something that knows how to spray bullets. Note that this is not a
    game object, it's something game objects can use to share code. """

    def __init__(self, game_object, game_services, config):
        """ Inject dependencies and set up default parameters. """
        Behaviour.__init__(self, game_object, game_services, config)
        self.shooting = False
        self.shooting_at = Vec2d(0, 0)
        self.shooting_at_screen = False
        self.shot_timer = 0

    def start_shooting_world(self, at):
        """ Start shooting at a point in world space. """
        self.shooting = True
        self.shooting_at = at
        self.shooting_at_screen = False

    def start_shooting_screen(self, at):
        """ Start shooting at a point in screen space. """
        self.start_shooting_world(at)
        self.shooting_at_screen = True

    def shooting_at_world(self):
        """ Get the point, in world space, that we are shooting at. """
        if self.shooting_at_screen:
            return self.game_services.get_camera().screen_to_world(self.shooting_at)
        else:
            return self.shooting_at

    def stop_shooting(self):
        """ Stop spraying bullets. """
        self.shooting = False

    def update(self, dt):
        """ Create bullets if shooting. Our rate of fire is governed by a timer. """
        if self.shot_timer > 0:
            self.shot_timer -= dt
        if self.shooting:
            body = self.get_component(Body)
            shooting_at_world = self.shooting_at_world()
            shooting_at_dir = (shooting_at_world - body.position).normalized()
            while self.shot_timer <= 0:
                self.shot_timer += 1.0/self.config["shots_per_second"]
                bullet = self.create_game_object(self.config["bullet_config"])
                muzzle_velocity = shooting_at_dir * self.config["bullet_speed"]
                spread = self.config["spread"]
                muzzle_velocity.rotate(random.random() * spread - spread)
                bullet_body = bullet.get_component(Body)
                bullet_body.velocity = body.velocity + muzzle_velocity
                separation = body.size+bullet_body.size+1
                bullet_body.position = Vec2d(body.position) + shooting_at_dir * separation

class AutomaticallyShootsBullets(ManuallyShootsBullets):
    """ Something that shoots bullets at something else. """

    def __init__(self, game_object, game_services, config):
        """ Initialise. """
        gun_config = game_services.get_resource_loader().load_config_file(config["gun_config"])
        ManuallyShootsBullets.__init__(self, game_object, game_services, gun_config)
        self.tracking_config = config
        self.track_type = game_services.lookup_type(config["track_type"])
        self.fire_timer = Timer(config["fire_period"])
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_timer = Timer(config["burst_period"])
        self.tracking = None

    def update(self, dt):
        """ Update the shooting bullet. """

        body = self.get_component(Body)

        # Update tracking.
        if not self.tracking:
            closest = self.get_system_by_type(Physics).closest_body_of_type(
                body.position,
                self.track_type
            )
            if closest:
                self.tracking = closest

        # Update aim.
        if self.tracking:
            if self.tracking.is_garbage():
                self.tracking = None
        if self.tracking:
            if not self.shooting:
                if self.fire_timer.tick(dt):
                    self.fire_timer.reset()
                    self.start_shooting_world(self.tracking.position)
            else:
                if self.burst_timer.tick(dt):
                    self.burst_timer.reset()
                    self.stop_shooting()
                else:
                    # Maintain aim.
                    self.start_shooting_world(self.tracking.position)

        # Shoot bullets.
        ManuallyShootsBullets.update(self, dt)

class MovesCamera(Behaviour):
    def update(self, dt):
        self.game_services.get_camera().position = Vec2d(self.get_component(Body).position)

class LaunchesFighters(EnemyBehaviour):
    def __init__(self, game_object, game_services, config):
        Behaviour.__init__(self, game_object, game_services, config)
        self.spawn_timer = Timer(config["spawn_period"])
        self.spawn_timer.advance_to_fraction(0.8)
    def update(self, dt):
        if self.spawn_timer.tick(dt):
            self.spawn_timer.reset()
            self.spawn()
    def spawn(self):
        for i in xrange(20):
            direction = self.towards_player()
            spread = self.config["takeoff_spread"]
            direction.rotate(spread*random.random()-spread/2.0)
            child = self.create_game_object(self.config["fighter_config"])
            body = self.get_component(Body)
            child_body = child.get_component(Body)
            child_body.velocity = body.velocity + direction * self.config["takeoff_speed"]
            child_body.position = Vec2d(body.position)

class KillOnTimer(Behaviour):
    """ For objects that should be destroyed after a limited time. """
    def __init__(self, game_object, game_services, config):
        Behaviour.__init__(self, game_object, game_services, config)
        self.lifetime = Timer(config["lifetime"])
    def update(self, dt):
        if self.lifetime.tick(dt):
            self.game_object.kill()

class ExplodesOnDeath(Behaviour):
    """ For objects that spawn an explosion when they die. """
    def on_object_killed(self):
        explosion = self.create_game_object(self.config["explosion_config"])
        explosion.get_component(Body).position = Vec2d(self.get_component(Body).position)

class Hitpoints(Behaviour):
    def __init__(self, game_object, game_services, config):
        Behaviour.__init__(self, game_object, game_services, config)
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.

    def receive_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.game_object.kill()

class DamageOnContact(Behaviour):
    def apply_damage(self, game_object):
        """ Apply damage to an object we've hit. """
        if self.config.get_or_default("destroy_on_hit", True):
            self.game_object.kill()
        hitpoints = game_object.get_component(Hitpoints)
        if hitpoints is not None:
            hitpoints.receive_damage(self.config["damage"])
