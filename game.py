#!/bin/python2

"""
A space game written in Python.

It currently depends on pygame for windowing, event handling etc, and on
pymunk for physics.

The program is structured with the intention than various distinct concerns
can be separated. The implementation of physics and the implementation of
drawing no nothing about one another, for instance. This is a work in progress
though. I'd like to make it realise this ideal more.

Game object creation is data-driven. Entities are defined in configuration
.txt files containing json data; these live under res/configs.

Things I would like to work on now:

1) Make it more of a game i.e. add win/lose conditions, support controllers,
   add more types of enemy, weapon etc.

2) Make the object creation scheme more robust and efficient. There's a lot
   of string wrangling and the current approach to error handling is "YOLO".

3) Decompose logical behaviours defined in this file into composable
   behaviour components, and delete most of the classes. Make components
   data driven so they can be added in the config files.

4) Make the use of pymunk more idiomatic. It's currently horrendous.

I'll probably do (1) first and do the others as necessary to facillitate it.
   
"""

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
from behaviours import *
                
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

        # The behaviour handlers.
        self.behaviours = Behaviours()

        # Currently existing objects and queue of objects to create.
        self.objects = []
        self.new_objects = []

        # The configuration.
        self.config = Config()
        self.config.load("config.txt")

        # Configure the drawing.
        self.drawing.minimise_image_loading = self.config.get_or_default("minimise_image_loading", False)

        # Cached configurations.
        self.configs = {}

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

    def get_behaviours(self):
        """ Get the behaviour handling system. """
        return self.behaviours

    def garbage_collect(self):
        """ Remove all of the objects that have been marked for deletion."""
        self.objects = [ x for x in self.objects if not x.is_garbage ]

    def load_config_file(self, filename):
        """ Read in a configuration file. """
        if not filename in self.configs:
            c = Config()
            c.load(filename)
            self.configs[filename] = c
        return self.configs[filename]

    def lookup_type(self, typename):
        return globals()[typename]

    def create_game_object(self, config_name, *args):
        """ Add a new object. It is initialised, but not added to the game
        right away: that gets done at a certain point in the game loop."""
        config = self.load_config_file(config_name)
        t = self.lookup_type(config["type"])
        obj = t(*args)
        obj.initialise(self, config)
        self.new_objects.append(obj)
        return obj
    
    def run(self):
        """ The game loop. This performs initialisation including setting
        up pygame, and shows a loading screen while certain resources are
        preloaded. Then, we enter the game loop wherein we remain until the
        game is over. If the file "preload.txt" does not exist, then it will
        be filled with a list of resources to preload next time the game is
        run. """
        
        # Initialise
        pygame.init()
        screen = pygame.display.set_mode((self.config.get_or_default("screen_width", 1024), 
                                          self.config.get_or_default("screen_height", 768)))

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
        self.camera = self.create_game_object("camera.txt", screen)
        
        self.player = self.create_game_object("player.txt")
        
        background_name = "res/images/star--background-seamless-repeating9.jpg"
        self.drawing.add_drawable(
            BackgroundDrawable(self.camera, self.drawing.load_image(background_name)))

        self.carrier = self.create_game_object("enemies/carrier.txt")
        self.carrier.body.position = Vec2d((0, 100))

        self.physics.add_collision_handler(BulletShooterCollisionHandler())

        self.won = False
        self.won_timer = Timer(10)

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

            # Update input handlers.
            self.input_handling.update(tick)

            # Collision detection.
            self.physics.update(tick)

            # Update the drawables.
            self.drawing.update(tick)

            # Update the behaviours
            self.behaviours.update(tick)

            # Update the camera.
            self.camera.update(tick)

            # Destroy anything that is now dead.
            self.garbage_collect()

            # Draw
            screen.fill((0, 0, 0))
            self.drawing.draw(self.camera)
            pygame.display.update()

            # Maintaim frame rate.
            clock.tick(fps)

            # Check for win/lose.
            if not self.won and (self.player.is_garbage or self.carrier.is_garbage):
                self.won = True
                image_name = "res/images/youwin.png"
                if self.player.is_garbage:
                    image_name = "res/images/youlose.png"
                self.drawing.add_drawable(WinLoseDrawable(self.camera, self.drawing.load_image(image_name)))

            # Close the game if we've won.
            if self.won:
                if self.won_timer.tick(tick):
                    running = False

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

    def initialise(self, game_services, config):
        """ Initialise the object: create drawables, physics bodies, etc. """
        self.game_services = game_services
        self.config = config

    def kill(self):
        """ Mark the object for deletion. """
        self.is_garbage = True

class Explosion(GameObject):
    """ An explosion. It will play an animation and then disappear. """

    def initialise(self, game_services, config):
        """ Create a body and a drawable for the explosion. """
        GameObject.initialise(self, game_services, config)
        anim = game_services.get_drawing().load_animation(config["anim_name"])
        self.body = Body(self)
        self.body.collideable = False
        self.drawable = AnimBodyDrawable(self, anim, self.body)
        self.drawable.kill_on_finished = True
        game_services.get_physics().add_body(self.body)
        game_services.get_drawing().add_drawable(self.drawable)

class Bullet(GameObject):
    """ A projectile. """

    def initialise(self, game_services, config):
        """ Build a body and drawable. The bullet will be destroyed after
        a few seconds. """
        GameObject.initialise(self, game_services, config)
        self.body = Body(self)
        self.body.size = config["size"]
        self.lifetime = Timer(config["lifetime"])
        img = self.game_services.get_drawing().load_image(config["image_name"])
        player_body = game_services.get_player().body
        drawable = BulletDrawable(self, img, self.body, player_body)
        game_services.get_physics().add_body(self.body)
        game_services.get_drawing().add_drawable(drawable)
        game_services.get_behaviours().add_behaviour(ExplodesOnDeath(self, game_services, config))
        game_services.get_behaviours().add_behaviour(KillOnTimer(self, game_services, config))

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
        game_services.get_behaviours().add_behaviour(AutomaticallyShootsBullets(self, game_services, config))

class Shooter(GameObject):
    """ An object with a health bar that can shoot bullets. """

    def initialise(self, game_services, config):
        """ Create a body and some drawables. We also set up the gun. """
        GameObject.initialise(self, game_services, config)
        anim = game_services.get_drawing().load_animation(config["anim_name"])
        anim.randomise()
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.
        self.body = Body(self)
        self.body.mass = config["mass"]
        self.body.size = config["size"]
        self.drawable = AnimBodyDrawable(self, anim, self.body)
        self.hp_drawable = HealthBarDrawable(self, self.body)
        game_services.get_physics().add_body(self.body)
        game_services.get_drawing().add_drawable(self.drawable)
        game_services.get_drawing().add_drawable(self.hp_drawable)
        game_services.get_behaviours().add_behaviour(ExplodesOnDeath(self, game_services, config))

    def receive_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()

class Target(Shooter):
    """ An enemy than can fly around shooting bullets. """

    def initialise(self, game_services, config):
        """ Overidden to configure the body and the gun. """
        Shooter.initialise(self, game_services, config)
        game_services.get_behaviours().add_behaviour(AutomaticallyShootsBullets(self, game_services, config))
        game_services.get_behaviours().add_behaviour(FollowsPlayer(self, game_services, config))
                
class Carrier(Target):
    """ A large craft that launches fighters. """

    def initialise(self, game_services, config):
        """ Overidden to configure the body and the gun. """
        Target.initialise(self, game_services, config)
        game_services.get_behaviours().add_behaviour(LaunchesFighters(self, game_services, config))

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

    def initialise(self, game_services, config):
        """ Initialise with the game services: create an input handler so
        the player can drive us around. """
        Shooter.initialise(self, game_services, config)
        game_services.get_input_handling().add_input_handler(PlayerInputHandler(self))
        behaviours = game_services.get_behaviours()
        self.normal_gun = behaviours.add_behaviour(
            ManuallyShootsBullets(self,
                                  game_services,
                                  game_services.load_config(config["gun_config"])))
        self.torpedo_gun = behaviours.add_behaviour(
            ManuallyShootsBullets(self,
                                  game_services,
                                  game_services.load_config(config["torpedo_gun_config"])))
        self.guns = [ self.normal_gun, self.torpedo_gun ]
        behaviours.add_behaviour(MovesCamera(self, game_services, config))

    def start_shooting(self, pos):
        for g in self.guns:
            g.start_shooting_screen(pos)

    def stop_shooting(self):
        for g in self.guns:
            g.stop_shooting()

    def is_shooting(self):
        return self.normal_gun.is_shooting

class BulletShooterCollisionHandler(CollisionHandler):
    """ Collision handler to apply bullet damage. """
    def __init__(self):
        CollisionHandler.__init__(self, Bullet, Shooter)
    def handle_matching_collision(self, bullet, shooter):
        bullet.apply_damage(shooter)

if __name__ == '__main__':
    main()
