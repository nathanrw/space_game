#!/bin/python2

import pygame
import math
import random
import os
import json
import sys

from vector2d import Vec2d

from physics import *
from drawing import *
from utils import *
from loading_screen import *
from input_handling import *
                
def main():
    game = Game()
    game.run()

class Game(object):
    
    def __init__(self):
        """ Initialise the game systems. """

        # The player
        self.player = None

        # The main camera.
        self.camera = None

        # The enemy.
        self.carrier = None

        # The physics system.
        self.physics = Physics()

        # The drawing system.
        self.drawing = Drawing()

        # The input handling system.
        self.input_handling = InputHandling()

        # Currently existing objects and queue of objects to create.
        self.objects = []
        self.new_objects = []

        # The configuration.
        self.config = {}
        if (os.path.isfile("config.txt")):
            self.config = json.load(open("config.txt", "r"))

        # Configure the drawing.
        self.drawing.minimise_image_loading = self.load_config("minimise_image_loading", False)

    def add_new_object(self, obj):
        """ Add a new object. It is initialised, but not added to the game
        right away: that gets done at a certain point in the game loop."""
        obj.initialise(self)
        self.new_objects.append(obj)

    def get_camera(self):
        """ Get the camera. """
        return self.camera

    def get_player(self):
        """ Get the player. """
        return self.player

    def get_physics(self):
        """ Get the physics system. """
        return self.physics

    def get_drawing(self):
        """ Get the drawing system. """
        return self.drawing

    def get_input_handling(self):
        """ Get the input handling system. """
        return self.input_handling

    def garbage_collect(self):
        """ Remove all of the objects that have been marked for deletion."""
        self.objects = [ x for x in self.objects if not x.is_garbage ]

    def load_config(self, key, default):
        """ Read a value from the configuration, returning the default if it
        does not exist. """
        if key in self.config: return self.config[key]
        else: return default
    
    def run(self):
        """ The game loop. This performs initialisation including setting
        up pygame, and shows a loading screen while certain resources are
        preloaded. Then, we enter the game loop wherein we remain until the
        game is over. If the file "preload.txt" does not exist, then it will
        be filled with a list of resources to preload next time the game is
        run. """
        
        # Initialise
        pygame.init()
        screen = pygame.display.set_mode((self.load_config("screen_width", 1024), 
                                          self.load_config("screen_height", 768)))

        # Preload certain images.
        preload_name = "preload.txt"
        if self.drawing.minimise_image_loading:
            preload_name = "preload_min.txt"
        if os.path.isfile(preload_name):
            filenames = json.load(open(preload_name, "r"))
            loading = LoadingScreen(len(filenames), screen)
            for filename in filenames:
                self.drawing.load_image(filename)
                loading.increment()

        # Game state
        self.camera = Camera(screen)
        self.add_new_object(self.camera)
        
        self.player = Player(self.camera)
        self.add_new_object(self.player)
        
        self.drawing.add_drawable(BackgroundDrawable(self.camera, self.drawing.load_image("res/images/star--background-seamless-repeating9.jpg")))

        self.carrier = Carrier()
        self.add_new_object(self.carrier)
        self.carrier.body.position = Vec2d((0, 100))

        self.physics.add_collision_handler(BulletShooterCollisionHandler())

        # Main loop.
        running = True
        fps = 60
        clock = pygame.time.Clock()
        while running:

            ## Create any queued objects
            for o in self.new_objects:
                self.objects.append(o)
                self.new_objects = []

            # Input
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif self.input_handling.handle_input(e):
                    pass

            tick = 1.0/fps # Use idealised tick time.

            # Update
            for o in self.objects:
                o.update(tick) 

            # Collision detection.
            self.physics.update(tick)

            # Update the drawables.
            self.drawing.update(tick)

            # Destroy anything that is now dead.
            self.garbage_collect()

            # Draw
            screen.fill((0, 0, 0))
            self.drawing.draw(self.camera)
            pygame.display.update()

            # Maintaim frame rate.
            clock.tick(fps)

        # Finalise
        pygame.quit()

        # Save a list of images to preload next time.
        if not os.path.isfile(preload_name):
            json.dump(
                self.drawing.images.keys(),
                open(preload_name, "w"),
                indent=4,
                separators=(',', ': ')
            )

class GameObject(object):
    """ An object in the game. It knows whether it needs to be deleted, and
    has access to object / component creation services. """

    def __init__(self):
        """ Constructor. Since you don't have access to the game services
        in __init__, more complicated initialisation must be done in
        initialise()."""
        self.is_garbage = False
        self.game_services = None

    def initialise(self, game_services):
        """ Initialise the object: create drawables, physics bodies, etc. """
        self.game_services = game_services

    def update(self, dt):
        """ Perform a logical update: AI behaviours, game logic, etc. Note
        that physics simulation is done by adding a Body. """
        pass

    def kill(self):
        """ Mark the object for deletion and perform whatever game logic
        needs to be done when the object is destroyed e.g. spawn an
        explosion. """
        self.is_garbage = True

class Explosion(GameObject):
    """ An explosion. It will play an animation and then disappear. """

    def __init__(self, filename):
        """ The filename should be the name of an animation. """
        GameObject.__init__(self)
        self.anim_name = filename

    def initialise(self, game_services):
        """ Create a body and a drawable for the explosion. """
        GameObject.initialise(self, game_services)
        anim = game_services.get_drawing().load_animation(self.anim_name)
        self.body = Body(self)
        self.body.collideable = False
        self.drawable = AnimBodyDrawable(self, anim, self.body)
        self.drawable.kill_on_finished = True
        game_services.get_physics().add_body(self.body)
        game_services.get_drawing().add_drawable(self.drawable)

class Bullet(GameObject):

    def __init__(self, image_name, explosion_anim_name):
        """ Initialise the bullet with its image and explosion name. """
        GameObject.__init__(self)
        self.image_name = image_name
        self.explosion_anim_name = explosion_anim_name
        self.lifetime = Timer(2)

    def initialise(self, game_services):
        """ Build a body and drawable. The bullet will be destroyed after
        a few seconds. """
        GameObject.initialise(self, game_services)
        self.body = Body(self)
        self.body.size = 2
        img = self.game_services.get_drawing().load_image(self.image_name)
        player_body = game_services.get_player().body
        drawable = BulletDrawable(self, img, self.body, player_body)
        game_services.get_physics().add_body(self.body)
        game_services.get_drawing().add_drawable(drawable)

    def update(self, dt):
        GameObject.update(self, dt)
        if self.lifetime.tick(dt):
            self.kill()

    def kill(self):
        """ Spawn an explosion when the bullet dies. """
        GameObject.kill(self)
        explosion = Explosion(self.explosion_anim_name)
        self.game_services.add_new_object(explosion)
        explosion.body.position = Vec2d(self.body.position)

class ShootingBullet(Bullet):
    """ A bullet that is a gun! """
    def __init__(self, track_type, image_name, explosion_anim_name,
                 sub_bullet_image_name, sub_bullet_explosion_anim_name):
        Bullet.__init__(self, image_name, explosion_anim_name)
        self.gun = None
        self.gunner = None
        self.track_type = track_type
        self.sub_bullet_image_name = sub_bullet_image_name
        self.sub_bullet_explosion_anim_name = sub_bullet_explosion_anim_name
    def initialise(self, game_services):
        Bullet.initialise(self, game_services)
        self.gun = Gun(self.body, game_services,
                       self.sub_bullet_image_name, self.sub_bullet_explosion_anim_name)
        self.gun.shots_per_second = 20
        self.gunner = BurstFireGunnery(self.gun)
        self.gunner.fire_timer = Timer(0.1)
    def update(self, dt):
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

class Gun(object):
    """ Something that knows how to spray bullets. Note that this is not a
    game object, it's something game objects can use to share code. """

    def __init__(self, body, game_services, bullet_image_name, bullet_explosion_anim_name):
        """ Inject dependencies and set up default parameters. """
        self.body = body
        self.game_services = game_services
        self.shooting = False
        self.shooting_at = Vec2d(0, 0)
        self.shooting_at_screen = False
        self.shot_timer = 0
        self.shots_per_second = 5
        self.bullet_speed = 1500
        self.bullet_image_name = bullet_image_name
        self.bullet_explosion_anim_name = bullet_explosion_anim_name
        self.spread = 5

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

    def create_bullet(self):
        return Bullet(self.bullet_image_name, self.bullet_explosion_anim_name)

    def update(self, dt):
        """ Create bullets if shooting. Our rate of fire is governed by a timer. """
        if self.shot_timer > 0:
            self.shot_timer -= dt
        if self.shooting:
            shooting_at_world = self.shooting_at_world()
            shooting_at_dir = (shooting_at_world - self.body.position).normalized()
            while self.shot_timer <= 0:
                self.shot_timer += 1.0/self.shots_per_second
                bullet = self.create_bullet()
                self.game_services.add_new_object(bullet)
                muzzle_velocity = shooting_at_dir * self.bullet_speed
                muzzle_velocity.rotate(random.random() * self.spread - self.spread/2)
                bullet.body.velocity = self.body.velocity + muzzle_velocity
                bullet.body.position = Vec2d(self.body.position) + shooting_at_dir * (self.body.size+bullet.body.size+1)

class ShootingBulletGun(Gun):
    """ A gun that fires bullets that are themselves guns!! """
    def __init__(self, body, game_services, bullet_image_name, bullet_explosion_anim_name,
                 sub_bullet_image_name, sub_bullet_explosion_anim_name, track_type):
        Gun.__init__(self, body, game_services, bullet_image_name, bullet_explosion_anim_name)
        self.track_type = track_type
        self.bullet_speed = 400
        self.shots_per_second = 0.5
        self.sub_bullet_image_name = sub_bullet_image_name
        self.sub_bullet_explosion_anim_name = sub_bullet_explosion_anim_name
    def create_bullet(self):
        return ShootingBullet(self.track_type, self.bullet_image_name, self.bullet_explosion_anim_name,
                              self.sub_bullet_image_name, self.sub_bullet_explosion_anim_name)

class Shooter(GameObject):
    """ An object with a health bar that can shoot bullets. """

    def __init__(self, bullet_image_name, bullet_explosion_anim_name, self_anim_name):
        """ Inject dependencies and setup default parameters. """
        GameObject.__init__(self)
        self.self_anim_name = self_anim_name
        self.bullet_image_name = bullet_image_name
        self.bullet_explosion_anim_name = bullet_explosion_anim_name
        self.max_hp = 50
        self.hp = self.max_hp
        self.gun = None
        self.guns = []

    def initialise(self, game_services):
        """ Create a body and some drawables. We also set up the gun. """
        GameObject.initialise(self, game_services)
        anim = game_services.get_drawing().load_animation(self.self_anim_name)
        anim.randomise()
        self.body = Body(self)
        self.body.mass = 100
        self.drawable = AnimBodyDrawable(self, anim, self.body)
        self.hp_drawable = HealthBarDrawable(self, self.body)
        game_services.get_physics().add_body(self.body)
        game_services.get_drawing().add_drawable(self.drawable)
        game_services.get_drawing().add_drawable(self.hp_drawable)
        self.gun = Gun(self.body,
                       game_services,
                       self.bullet_image_name,
                       self.bullet_explosion_anim_name)
        self.guns = [self.gun]

    def update(self, dt):
        """ Overidden to update the gun. """
        GameObject.update(self, dt)
        for g in self.guns:
            g.update(dt)

    def kill(self):
        """ Spawn an explosion on death. """
        GameObject.kill(self)
        explosion = Explosion("res/anims/big_explosion/explosion.txt")
        self.game_services.add_new_object(explosion)
        explosion.body.position = Vec2d(self.body.position)

class BurstFireGunnery(object):
    """ Shoots at something in bursts. """
    def __init__(self, gun):
        self.gun = gun
        self.fire_timer = Timer(5)
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_timer = Timer(0.5)
        self.tracking = None
    def track(self, body):
        self.tracking = body
    def update(self, dt):
        if self.tracking:
            if self.tracking.is_garbage():
                self.tracking = None
        if self.tracking:
            if not self.gun.shooting:
                if self.fire_timer.tick(dt):
                    self.fire_timer.reset()
                    self.gun.start_shooting_world(self.tracking.position)
            else:
                if self.burst_timer.tick(dt):
                    self.burst_timer.reset()
                    self.gun.stop_shooting()
                else:
                    # Maintain aim.
                    self.gun.start_shooting_world(self.tracking.position)
                    

class Target(Shooter):
    """ An enemy than can fly around shooting bullets. """

    def __init__(self, anim_name):
        """ Inject dependencies and setup default parameters. """
        Shooter.__init__(self, "res/images/pewpewgreen.png", "res/anims/green_explosion/explosion.txt", anim_name)
        self.gunner = None

    def initialise(self, game_services):
        """ Overidden to configure the body and the gun. """
        Shooter.initialise(self, game_services)
        self.gunner = BurstFireGunnery(self.gun)

    def towards_player(self):
        """ Get the direction towards the player. """
        player = self.game_services.get_player()
        player_pos = player.body.position
        displacement = player_pos - self.body.position
        direction = displacement.normalized()
        return direction
                
    def update(self, dt):
        """ Logical update: shoot in bursts, fly towards the player and spawn
        more enemies. """

        # Call base class.
        Shooter.update(self, dt)

        # Accelerate towards the player.
        # Todo: make it accelerate faster if moving away from the player.
        player = self.game_services.get_player()
        player_pos = player.body.position
        displacement = player_pos - self.body.position
        direction = displacement.normalized()
        if displacement.length > 500:
            acceleration = direction * 100
            self.body.velocity += acceleration * dt
        else:
            self.body.velocity += (player.body.velocity - self.body.velocity)*dt

        # Shoot!
        self.gunner.track(player.body)
        self.gunner.update(dt)

class Carrier(Target):
    """ A large craft that launches fighters. """

    def __init__(self):
        """ Inject dependencies and setup default parameters. """
        Target.__init__(self, "res/anims/enemy_ship/anim.txt")
        self.spawn_timer = Timer(10)
        self.spawn_timer.advance_to_fraction(0.8)

    def initialise(self, game_services):
        """ Overidden to configure the body and the gun. """
        Target.initialise(self, game_services)
        self.hp = 200
        self.max_hp = self.hp
        self.body.size = 64
        self.gun.shots_per_second = 40
        self.gun.spead = 40
    
    def update(self, dt):
        """ Overidden to launch fighters. """
        Target.update(self, dt)
        
        # Launch fighters!
        if self.spawn_timer.tick(dt):
            self.spawn_timer.reset()
            self.spawn()
            
    def spawn(self):
        """ Spawn more enemies! """
        for i in xrange(20):
            direction = self.towards_player()
            spread = 30
            direction.rotate(spread*random.random()-spread/2.0)
            child = Fighter()
            self.game_services.add_new_object(child)
            child.body.velocity = self.body.velocity + direction * 700
            child.body.position = Vec2d(self.body.position)

class Fighter(Target):
    """ A small craft that shoots lasers. """

    def __init__(self):
        """ Inject dependencies and setup default parameters. """
        Target.__init__(self, "res/anims/enemy_fighter/anim.txt")

    def initialise(self, game_services):
        """ Overidden to configure the hp """
        Target.initialise(self, game_services)
        self.hp = 4
        self.max_hp = self.hp
        self.body.size = 20

class Camera(GameObject):
    """ A camera, which drawing is done in relation to. """

    def __init__(self, screen):
        """ Initialise the camera. """
        GameObject.__init__(self)
        self.position = Vec2d(0, 0)
        self.target_position = self.position
        self.screen = screen

    def surface(self):
        """ Get the surface drawing will be done on. """
        return self.screen

    def update(self, dt):
        """ Update the camera. """
        self.position = self.target_position

    def world_to_screen(self, world):
        """ Convert from world coordinates to screen coordinates. """
        centre = Vec2d(self.screen.get_size())/2
        return centre + world - self.position

    def screen_to_world(self, screen):
        """ Convert from screen coordinates to world coordinates. """
        centre = Vec2d(self.screen.get_size())/2
        return screen + self.position - centre

class Player(Shooter):
    """ The player! """

    def __init__(self, camera):
        """ The player needs to know the camera so the camera can be made to
        follow us. """
        Shooter.__init__(self, "res/images/pewpew.png", "res/anims/red_explosion/explosion.txt", "res/anims/player_ship/anim.txt")
        self.hp = 400
        self.max_hp = self.hp
        self.dir = Vec2d(0, 0)
        self.camera = camera

    def initialise(self, game_services):
        """ Initialise with the game services: create an input handler so
        the player can drive us around. """
        Shooter.initialise(self, game_services)
        game_services.get_input_handling().add_input_handler(PlayerInputHandler(self))
        self.body.size = 32
        self.normal_gun = Gun(self.body,
                              game_services,
                              self.bullet_image_name,
                              self.bullet_explosion_anim_name)
        self.torpedo_gun = ShootingBulletGun(self.body,
                                             game_services,
                                             "res/images/rocket.png",
                                             "res/anims/big_explosion/explosion.txt",
                                             self.bullet_image_name,
                                             self.bullet_explosion_anim_name,
                                             Target)
        self.guns = [self.normal_gun, self.torpedo_gun]
        self.gun = self.normal_gun

    def update(self, dt):
        """ Logical update: ajust velocity based on player input. """
        Shooter.update(self, dt)
        self.body.velocity -= (self.body.velocity * dt * 0.8)
        self.body.velocity += self.dir.normalized() * dt * 500 
        self.camera.target_position = Vec2d(self.body.position)

    def start_shooting(self, pos):
        for g in self.guns:
            g.start_shooting_screen(pos)

    def stop_shooting(self):
        for g in self.guns:
            g.stop_shooting()

    def is_shooting(self):
        return self.gun.is_shooting

class BulletShooterCollisionHandler(CollisionHandler):
    """ Collision handler to apply bullet damage. """
    def __init__(self):
        CollisionHandler.__init__(self, Bullet, Shooter)
    def handle_matching_collision(self, bullet, shooter):
        bullet.kill()
        shooter.hp -= 1
        if shooter.hp <= 0:
            shooter.kill()

if __name__ == '__main__':
    main()
