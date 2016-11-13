""" Object behaviours for the game and game objects composed out of them.

See utils.py for the overall scheme this fits into.

"""

from vector2d import Vec2d
from utils import Component, Timer
from physics import Body, Physics, CollisionHandler

import pygame
import random
        
class EnemyBehaviour(Component):
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

class ManuallyShootsBullets(Component):
    """ Something that knows how to spray bullets. Note that this is not a
    game object, it's something game objects can use to share code. """

    def __init__(self, game_object, game_services, config):
        """ Inject dependencies and set up default parameters. """
        Component.__init__(self, game_object, game_services, config)
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

class AutomaticallyShootsBullets(Component):
    """ Something that shoots bullets at something else. """

    def __init__(self, game_object, game_services, config):
        """ Initialise. """
        Component.__init__(self, game_object, game_services, config)
        self.fire_timer = Timer(config["fire_period"])
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_timer = Timer(config["burst_period"])
        self.tracking = None

    def update(self, dt):
        """ Update the shooting bullet. """

        body = self.get_component(Body)
        gun = self.get_component(ManuallyShootsBullets)

        # Update tracking.
        if not self.tracking:

            # Find the closest object we don't like.
            self_team = self.get_component(Team)
            def f(body):
                if self_team is None:
                    return True
                team = body.get_component(Team)
                if team is not None:
                    return team.team() != self_team.team()
                return True
            closest = self.get_system_by_type(Physics).closest_body_with(
                body.position,
                f
            )
            if closest:
                self.tracking = closest

        # Update aim.
        if self.tracking:
            if self.tracking.is_garbage():
                self.tracking = None
        if self.tracking:
            if not gun.shooting:
                if self.fire_timer.tick(dt):
                    self.fire_timer.reset()
                    gun.start_shooting_world(self.tracking.position)
            else:
                if self.burst_timer.tick(dt):
                    self.burst_timer.reset()
                    gun.stop_shooting()
                else:
                    # Maintain aim.
                    gun.start_shooting_world(self.tracking.position)

class MovesCamera(Component):
    def update(self, dt):
        self.game_services.get_camera().position = Vec2d(self.get_component(Body).position)

class LaunchesFighters(EnemyBehaviour):
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
        self.spawn_timer = Timer(config["spawn_period"])
    def update(self, dt):
        if self.spawn_timer.tick(dt):
            self.spawn_timer.reset()
            self.spawn()
    def spawn(self):
        for i in xrange(self.config["num_fighters"]):
            direction = self.towards_player()
            spread = self.config["takeoff_spread"]
            direction.rotate(spread*random.random()-spread/2.0)
            child = self.create_game_object(self.config["fighter_config"])
            body = self.get_component(Body)
            child_body = child.get_component(Body)
            child_body.velocity = body.velocity + direction * self.config["takeoff_speed"]
            child_body.position = Vec2d(body.position)

class KillOnTimer(Component):
    """ For objects that should be destroyed after a limited time. """
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
        self.lifetime = Timer(config["lifetime"])
    def update(self, dt):
        if self.lifetime.tick(dt):
            self.game_object.kill()

class ExplodesOnDeath(Component):
    """ For objects that spawn an explosion when they die. """
    def on_object_killed(self):
        body = self.get_component(Body)
        position = body.position
        explosion = self.create_game_object(self.config["explosion_config"])
        explosion.get_component(Body).position = position
        shake_factor = self.config.get_or_default("shake_factor", 1)
        self.game_services.get_camera().apply_shake(shake_factor, position)

class EndProgramOnDeath(Component):
    """ If the entity this is attached to is destroyed, the program will exit. """
    def on_object_killed(self):
        self.game_services.end_game()

class Hitpoints(Component):
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.

    def receive_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.game_object.kill()

class DamageOnContact(Component):
    def apply_damage(self, hitpoints):
        """ Apply damage to an object we've hit. """
        if self.config.get_or_default("destroy_on_hit", True):
            self.game_object.kill()
        if hitpoints is not None:
            hitpoints.receive_damage(self.config["damage"])

class DamageCollisionHandler(CollisionHandler):
    """ Collision handler to apply bullet damage. """
    def __init__(self):
        CollisionHandler.__init__(self, DamageOnContact, Hitpoints)
    def handle_matching_collision(self, dmg, hp):
        dmg.apply_damage(hp)

class Team(Component):
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
    def team(self):
        return self.config["team"]

class Text(Component):
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
        self.text = "Hello, world!"

class Thruster(object):
    def __init__(self, position, direction, max_thrust, name):
        self.__position = position
        self.__direction = direction
        self.__max_thrust = max_thrust
        self.__thrust = 0
        self.__name = name
    def go(self):
        self.__thrust = self.__max_thrust
    def stop(self):
        self.__thrust = 0
    def apply(self, body):
        if self.__thrust > 0:
            force = self.__direction * self.__thrust
            body.apply_force_at_local_point(force, self.__position)
    def world_position(self, body):
        return body.local_to_world(self.__position)
    def world_direction(self, body):
        return body.local_to_world(self.__direction+self.__position) - body.local_to_world(self.__position)
    def thrust(self):
        return self.__thrust
    def max_thrust(self):
        return self.__max_thrust
    def name(self):
        return self.name
    def on(self):
        return self.__thrust > 0

class Thrusters(Component):
    """ Thruster component. This allows an entity with a body to move itself.
    Eventually I intend to have the thrusters be configurable, but for now its
    hard coded."""

    def __init__(self, game_object, game_services, config):
        """ Initialise - set up the enginges. """
        Component.__init__(self, game_object, game_services, config)
        self.__top_left_thruster = \
            Thruster(Vec2d(-20, -20), Vec2d( 1,  0), config["max_thrust"] / 8, "top_left")
        self.__bottom_left_thruster = \
            Thruster(Vec2d(-20,  20), Vec2d( 1,  0), config["max_thrust"] / 8, "bottom_left")
        self.__top_right_thruster = \
            Thruster(Vec2d( 20, -20), Vec2d(-1,  0), config["max_thrust"] / 8, "top_right")
        self.__bottom_right_thruster = \
            Thruster(Vec2d( 20,  20), Vec2d(-1,  0), config["max_thrust"] / 8, "bottom_right")
        self.__top_thruster = \
            Thruster(Vec2d(  0, -20), Vec2d( 0,  1), config["max_thrust"] / 4, "top")
        self.__bottom_thruster = \
            Thruster(Vec2d(  0,  20), Vec2d( 0, -1), config["max_thrust"]    , "bottom")
        self.__thrusters = [self.__top_left_thruster, self.__top_right_thruster,
                            self.__top_thruster, self.__bottom_thruster,
                            self.__bottom_left_thruster, self.__bottom_right_thruster]
        self.__direction = Vec2d(0, 0)
        self.__dir_right = Vec2d(1, 0)
        self.__dir_backwards = Vec2d(0, 1)
        self.__turn = 0

    def go_forwards(self):
        self.__direction -= self.__dir_backwards

    def go_backwards(self):
        self.__direction += self.__dir_backwards

    def go_left(self):
        self.__direction -= self.__dir_right

    def go_right(self):
        self.__direction += self.__dir_right

    def turn_left(self):
        self.__turn += 1

    def turn_right(self):
        self.__turn -= 1

    def stop_all_thrusters(self):
        """ Stop all the engines. """
        for thruster in self.__thrusters:
            thruster.stop()

    def fire_correct_thrusters(self, body):
        """ Perform logic to determine what engines are firing based on the
        desired direction. Automatically counteract spin. """

        # By default the engines should be of.
        self.stop_all_thrusters()

        # X
        if self.__direction.x > 0:
            self.__top_left_thruster.go()
            self.__bottom_left_thruster.go()
        elif self.__direction.x < 0:
            self.__top_right_thruster.go()
            self.__bottom_right_thruster.go()

        #Y
        if self.__direction.y > 0:
            self.__top_thruster.go()
        elif self.__direction.y < 0:
            self.__bottom_thruster.go()

        # turning thrusters
        if self.__turn > 0:
            self.__top_right_thruster.go()
            self.__bottom_left_thruster.go()
        elif self.__turn < 0:
            self.__top_left_thruster.go()
            self.__bottom_right_thruster.go()

        # Counteract spin automatically.
        eps = 0.005 # LOLOLOL
        if (not self.__top_left_thruster.on()) and \
           (not self.__top_right_thruster.on()) and \
           (not self.__bottom_left_thruster.on()) and \
           (not self.__bottom_right_thruster.on()): 
            if body.angular_velocity > eps:
                self.__top_right_thruster.go()
                self.__bottom_left_thruster.go()
            elif body.angular_velocity < -eps:
                self.__top_left_thruster.go()
                self.__bottom_right_thruster.go()

    def update(self, dt):
        """ Override update to switch on right engines and apply their effect."""

        # Cant do much without a body.
        body = self.get_component(Body)
        if body is None:
            return

        # Switch the right engines on.
        self.fire_correct_thrusters(body)

        # Apply physical effect of thrusters.
        for t in self.__thrusters:
            t.apply(body)

    def thrusters(self):
        """ Get the engines - useful for e.g. drawing. """
        return self.__thrusters

class WaveSpawner(Component):
    """ Spawns waves of enemies. """

    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
        self.wave = 1
        self.spawned = []
        self.message = None
        self.done = False

    def update(self, dt):
        """ Update the spawner. """
        Component.update(self, dt)

        # Check for end condition and show game ending message if so.
        if self.done:
            return
        elif self.player_is_dead() or self.max_waves():
            self.done = True
            message = self.create_game_object("endgame_message.txt")
            message_text = message.get_component(Text)
            if self.max_waves():
                message_text.text = "VICTORY"
            else:
                message_text.text = "GAME OVER"

        # If the wave is dead and we're not yet preparing (which displays a timed message) then
        # start preparing a wave.
        if self.wave_is_dead() and self.message is None:
            self.prepare_for_wave()

        # If we're prepared to spawn i.e. the wave is dead and the message has gone, spawn a wave!
        if self.prepared_to_spawn():
            self.spawn_wave()

    def player_is_dead(self):
        """ Check whether the player is dead. """
        player = self.game_services.get_player()
        return player.is_garbage

    def spawn_wave(self):
        """ Spawn a wave of enemies, each one harder than the last."""
        player = self.game_services.get_player()
        player_body = player.get_component(Body)
        self.wave += 1
        for i in xrange(self.wave-1):
            carrier = self.create_game_object("enemies/carrier.txt")
            carrier.get_component(Body).position = \
                player_body.position + Vec2d((random.random()*100, random.random()*100))
            self.spawned.append(carrier)

    def wave_is_dead(self):
        """ Has the last wave been wiped out? """
        self.spawned = filter(lambda x: not x.is_garbage, self.spawned)
        return len(self.spawned) == 0

    def prepare_for_wave(self):
        """ Prepare for a wave. """
        from drawing import TextDrawable # nasty: avoid circular dependency.
        self.message = self.create_game_object("update_message.txt")
        self.message.get_component(Text).text = "WAVE %s PREPARING" % self.wave

    def prepared_to_spawn(self):
        """ Check whether the wave is ready. """
        if self.message is None or not self.wave_is_dead():
            return False
        if self.message.is_garbage:
            self.message = None
            return True
        return False

    def max_waves(self):
        """ Check whether the player has beaten enough waves. """
        return self.wave == 10
