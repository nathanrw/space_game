from vector2d import Vec2d

from utils import *

import pygame

class Behaviours(object):
    def __init__(self):
        self.behaviours = []
    def add_behaviour(self, behaviour):
        self.behaviours.append(behaviour)
        return behaviour
    def update(self, dt):
        garbage = [x for x in self.behaviours if x.is_garbage()]
        for behaviour in garbage:
            self.behaviours.remove(behaviour)
            behaviour.on_object_killed()
        for behaviour in self.behaviours:
            behaviour.update(dt)

class Behaviour(object):
    def __init__(self, game_object, game_services, config):
        self.game_object = game_object
        self.game_services = game_services
        self.config = config
    def is_garbage(self):
        return self.game_object.is_garbage
    def update(self, dt):
        pass
    def on_object_killed(self):
        pass

class EnemyBehaviour(Behaviour):
    def towards_player(self):
        """ Get the direction towards the player. """
        player = self.game_services.get_player()
        player_pos = player.body.position
        displacement = player_pos - self.game_object.body.position
        direction = displacement.normalized()
        return direction

class FollowsPlayer(EnemyBehaviour):
    def update(self, dt):
        # Accelerate towards the player.
        # Todo: make it accelerate faster if moving away from the player.
        player = self.game_services.get_player()
        player_pos = player.body.position
        displacement = player_pos - self.game_object.body.position
        direction = displacement.normalized()
        if displacement.length > self.config["desired_distance_to_player"]:
            acceleration = direction * self.config["acceleration"]
            self.game_object.body.velocity += acceleration * dt
        else:
            self.game_object.body.velocity += (player.body.velocity - self.game_object.body.velocity)*dt

class ManuallyShootsBullets(Behaviour):
    """ Something that knows how to spray bullets. Note that this is not a
    game object, it's something game objects can use to share code. """

    def __init__(self, game_object, game_services, config):
        """ Inject dependencies and set up default parameters. """
        Behaviour.__init__(self, game_object, game_services, config)
        self.body = game_object.body
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
            shooting_at_world = self.shooting_at_world()
            shooting_at_dir = (shooting_at_world - self.body.position).normalized()
            while self.shot_timer <= 0:
                self.shot_timer += 1.0/self.config["shots_per_second"]
                bullet = self.game_services.create_game_object(self.config["bullet_config"])
                muzzle_velocity = shooting_at_dir * self.config["bullet_speed"]
                spread = self.config["spread"]
                muzzle_velocity.rotate(random.random() * spread - spread)
                bullet.body.velocity = self.body.velocity + muzzle_velocity
                separation = self.body.size+bullet.body.size+1
                bullet.body.position = Vec2d(self.body.position) + shooting_at_dir * separation

class AutomaticallyShootsBullets(ManuallyShootsBullets):
    """ Something that shoots bullets at something else. """

    def __init__(self, game_object, game_services, config):
        """ Initialise. """
        gun_config = game_services.load_config_file(config["gun_config"])
        ManuallyShootsBullets.__init__(self, game_object, game_services, gun_config)
        self.tracking_config = config
        self.track_type = game_services.lookup_type(config["track_type"])
        self.fire_timer = Timer(config["fire_period"])
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_timer = Timer(config["burst_period"])
        self.tracking = None

    def update(self, dt):
        """ Update the shooting bullet. """

        # Update tracking.
        if not self.tracking:
            closest = self.game_services.get_physics().closest_body_of_type(
                self.body.position,
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
        self.game_services.get_camera().target_position = Vec2d(self.game_object.body.position)

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
            child = self.game_services.create_game_object(self.config["fighter_config"])
            child.body.velocity = self.game_object.body.velocity + direction * self.config["takeoff_speed"]
            child.body.position = Vec2d(self.game_object.body.position)

class KillOnTimer(Behaviour):
    def __init__(self, game_object, game_services, config):
        Behaviour.__init__(self, game_object, game_services, config)
        self.lifetime = Timer(config["lifetime"])
    def update(self, dt):
        if self.lifetime.tick(dt):
            self.game_object.kill()

class ExplodesOnDeath(Behaviour):
    def on_object_killed(self):
        explosion = self.game_services.create_game_object(self.config["explosion_config"])
        explosion.body.position = Vec2d(self.game_object.body.position)
        
