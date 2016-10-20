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
        Component.__init__(self, game_object)
        self.game_services = game_services
        self.config = config

class EnemyBehaviour(Behaviour):
    def towards_player(self):
        """ Get the direction towards the player. """
        player = self.game_services.get_player()
        player_pos = player.body.position
        displacement = player_pos - self.game_object.body.position
        direction = displacement.normalized()
        return direction

class FollowsPlayer(EnemyBehaviour):
	def __init__(self, game_object, game_services, config):
		EnemyBehaviour.__init__(self, game_object, game_services, config)
		self.thrust = self.game_object.body.mass * self.config["acceleration"]
		self.target_dist = self.config["desired_distance_to_player"]

	def update(self, dt):
		# Accelerate towards the player.
		# Todo: make it accelerate faster if moving away from the player.
		player = self.game_services.get_player()
		displacement = player.body.position - self.game_object.body.position
		rvel = player.body.velocity - self.game_object.body.velocity
		# distality is a mapping of distance onto the interval [0,1) to interpolate between two behaviours
		distality = 1 - 2 ** ( - displacement.length / self.target_dist )
		direction = ( 1 - distality ) * rvel.normalized() + distality * displacement.normalized()
		force = min( [ max( [displacement.length / self.target_dist, rvel.length/200 ] ), 1] ) * self.thrust * direction
		# self.game_object.body.body.apply_force_at_local_point( force, ( 0, 0 ) )
		self.game_object.body.body.force = force
		# print "rvel " + str( rvel )

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
                bullet = self.create_game_object(self.config["bullet_config"])
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

        # Update tracking.
        if not self.tracking:
            closest = self.get_system_by_type(Physics).closest_body_of_type(
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
        self.game_services.get_camera().position = Vec2d(self.game_object.body.position)

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
            child.body.velocity = self.game_object.body.velocity + direction * self.config["takeoff_speed"]
            child.body.position = Vec2d(self.game_object.body.position)

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
        explosion.body.position = Vec2d(self.game_object.body.position)

class Explosion(GameObject):
    """ An explosion. It will play an animation and then disappear. """

    def initialise(self, game_services, config):
        """ Create a body and a drawable for the explosion. """
        GameObject.initialise(self, game_services, config)
        anim = game_services.get_resource_loader().load_animation(config["anim_name"])
        self.body = Body(self)
        self.body.collideable = False
        self.drawable = AnimBodyDrawable(self, anim, self.body)
        self.drawable.kill_on_finished = True
        self.add_component(self.body)
        self.add_component(self.drawable)

class Bullet(GameObject):
    """ A projectile. """

    def initialise(self, game_services, config):
        """ Build a body and drawable. The bullet will be destroyed after
        a few seconds. """
        GameObject.initialise(self, game_services, config)
        self.body = Body(self)
        self.body.size = config["size"]
        self.lifetime = Timer(config["lifetime"])
        img = self.game_services.get_resource_loader().load_image(config["image_name"])
        player_body = game_services.get_player().body
        self.add_component(self.body)
        self.add_component(BulletDrawable(self, img, self.body, player_body))
        self.add_component(ExplodesOnDeath(self, game_services, config))
        self.add_component(KillOnTimer(self, game_services, config))

    def apply_damage(self, to):
        """ Apply damage to an object we've hit. """
        if self.config.get_or_default("destroy_on_hit", True):
            self.kill()
        to.receive_damage(self.config["damage"])

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
        anim = game_services.get_resource_loader().load_animation(config["anim_name"])
        anim.randomise()
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.
        self.body = Body(self)
        self.body.mass = config["mass"]
        self.body.size = config["size"]
        self.drawable = AnimBodyDrawable(self, anim, self.body)
        self.hp_drawable = HealthBarDrawable(self, self.body)
        self.add_component(self.body)
        self.add_component(self.drawable)
        self.add_component(self.hp_drawable)
        self.add_component(ExplodesOnDeath(self, game_services, config))

    def receive_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()

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
        self.normal_gun = ManuallyShootsBullets(self,
                                  game_services,
                                  game_services.get_resource_loader().load_config_file(config["gun_config"]))
        self.torpedo_gun = ManuallyShootsBullets(self,
                                  game_services,
                                  game_services.get_resource_loader().load_config_file(config["torpedo_gun_config"]))
        self.guns = [ self.normal_gun, self.torpedo_gun ]
        self.add_component(PlayerInputHandler(self))
        self.add_component(self.normal_gun)
        self.add_component(self.torpedo_gun)
        self.add_component(MovesCamera(self, game_services, config))

    def start_shooting(self, pos):
        """ Start shooting at a particular screen space point. """
        for g in self.guns:
            g.start_shooting_screen(pos)

    def stop_shooting(self):
        """ Stop the guns. """
        for g in self.guns:
            g.stop_shooting()

    def is_shooting(self):
        """ Are the guns firing? If one is they both are. """
        return self.normal_gun.shooting

class BulletShooterCollisionHandler(CollisionHandler):
    """ Collision handler to apply bullet damage. """
    def __init__(self):
        CollisionHandler.__init__(self, Bullet, Shooter)
    def handle_matching_collision(self, bullet, shooter):
        bullet.apply_damage(shooter)
        
