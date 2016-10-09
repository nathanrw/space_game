from vector2d import Vec2d

import pygame

class Behaviours(object):
    def __init__(self):
        self.behaviours = []
    def add_behaviour(self, behaviour):
        self.behaviours.append(behaviour)
    def update(self, dt):
        garbage = [x for x in self.drawables if not x.is_garbage()]
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
        displacement = player_pos - self.body.position
        direction = displacement.normalized()
        if displacement.length > self.config["desired_distance_to_player"]:
            acceleration = direction * self.config["acceleration"]
            self.body.velocity += acceleration * dt
        else:
            self.body.velocity += (player.body.velocity - self.body.velocity)*dt

class ShootsBullets(Behaviour):
    def __init__(self, game_object, game_services, config, gun, gunnery):
        Behaviour.__init__(self, game_object, game_services, config)
        self.gun = gun
        self.gunnery = gunnery
        self.track_type = game_services.lookup_type(config["track_type"])
    def update(self, dt):
        """ Update the shooting bullet. """
        Bullet.update(self, dt)
        if not self.gunner.tracking:
            closest = self.game_services.get_physics().closest_body_of_type(
                self.body.position,
                self.track_type
            )
            if closest:
                self.gunner.track(closest)
        self.gun.update(dt)
        self.gunner.update(dt)

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
        GameObject.update(self, dt)
        if self.lifetime.tick(dt):
            self.game_object.kill()

class ExplodesOnDeath(Behaviour):
    def on_object_killed(self):
        explosion = self.game_services.create_game_object(self.config["explosion_config"])
        explosion.body.position = Vec2d(self.game_object.body.position)
        
