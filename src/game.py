"""
A space game written in Python.

It currently depends on pygame for windowing, event handling etc, and on
pymunk for physics.

The program is structured with the intention than various distinct concerns
can be separated. The implementation of physics and the implementation of
drawing know nothing about one another, for instance. This is a work in progress
though. I'd like to make it realise this ideal more.

Game object creation is data-driven. Entities are defined in configuration
.txt files containing json data; these live under res/configs.

Things I would like to work on now:

1) Make it more of a game i.e. support controllers, add more types of enemy,
   weapon etc.

2) Make the use of pymunk more idiomatic. It's currently horrendous.
   
"""

import pygame
import math
import random
import os
import json
import sys

from vector2d import Vec2d

from physics import Physics, Body
from drawing import Drawing, TextDrawable
from behaviours import DamageCollisionHandler
from utils import GameServices, ResourceLoader, EntityManager, Timer
from input_handling import InputHandling

class SpaceGameServices(GameServices):
    """ The services exposed to the game objects. This is separate from
    the game class itself to try and keep control of the interface - since
    this is basically global state you can get at from anywhere. """
    
    def __init__(self, game):
        self.game = game

    def get_player(self):
        """ Get the player. """
        return self.game.player

    def get_camera(self):
        """ Get the camera. """
        return self.game.camera

    def get_entity_manager(self):
        """ Return the entity manager. """
        return self.game.entity_manager

    def get_resource_loader(self):
        """ Get the resource loader. """
        return self.game.resource_loader
                
class Game(object):
    """ Class glueing all of the building blocks together into an actual
    game. """
    
    def __init__(self):
        """ Initialise the game systems. """

        # Services exposed to the game objects.
        self.game_services = SpaceGameServices(self)

        # The resource loader.
        self.resource_loader = ResourceLoader()

        # The player
        self.player = None

        # The main camera.
        self.camera = None

        # The enemy.
        self.carrier = None

        # The physics
        self.physics = Physics()

        # The drawing system.
        self.drawing = Drawing()

        # The input handling system.
        self.input_handling = InputHandling()

        # Plug the systems in. Note that systems can be created dynamically,
        # but we want to manipulate them so we specify them up front.
        self.entity_manager = EntityManager(self.game_services)
        self.entity_manager.register_component_system(self.physics)
        self.entity_manager.register_component_system(self.drawing)
        self.entity_manager.register_component_system(self.input_handling)

        # The configuration.
        self.config = self.resource_loader.load_config_file("config.txt")

        # Configure the resource loader.
        self.resource_loader.minimise_image_loading = \
            self.config.get_or_default("minimise_image_loading", False)

    def run(self):
        """ The game loop. This performs initialisation including setting
        up pygame, and shows a loading screen while certain resources are
        preloaded. Then, we enter the game loop wherein we remain until the
        game is over. If the file "preload.txt" does not exist, then it will
        be filled with a list of resources to preload next time the game is
        run. """
        
        # Initialise the pygame display.
        pygame.init()
        screen = pygame.display.set_mode((self.config.get_or_default("screen_width", 1024), 
                                          self.config.get_or_default("screen_height", 768)))

        # Preload certain images.
        self.resource_loader.preload(screen)

        # Make the camera. Im not 100% sure about this being a game object like any other
        # since it's clearly special - drawing requires one, the player moves it, etc. But
        # at the same time it's convenient to attach the background drawable to it, and we
        # might want to give it physical properties in future. We'll see.
        self.camera = self.entity_manager.create_game_object("camera.txt", screen)

        # Make the player
        self.player = self.entity_manager.create_game_object("player.txt")

        # The enemy at present is just one carrier.
        self.carrier = self.entity_manager.create_game_object("enemies/carrier.txt")
        self.carrier.get_component(Body).position = Vec2d((0, 100))

        # Make it so that bullets can damage things.
        self.physics.add_collision_handler(DamageCollisionHandler())

        # Once the game is won (or lost) we stop the game after a timer elapses.
        self.won = False
        self.won_timer = Timer(10)

        # Main loop.
        running = True
        fps = 60
        clock = pygame.time.Clock()
        while running:

            ## Create any queued objects
            self.entity_manager.create_queued_objects()

            # Input
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                elif self.input_handling.handle_input(e):
                    pass

            # Update the systems.
            self.entity_manager.update(1.0/fps)

            # Draw
            screen.fill((0, 0, 0))
            self.drawing.draw(self.camera)
            pygame.display.update()

            # Maintaim frame rate.
            clock.tick(fps)

            # Check for win/lose.
            if not self.won and (self.player.is_garbage or self.carrier.is_garbage):
                self.won = True
                message = self.entity_manager.create_game_object("message.txt")
                if self.player.is_garbage:
                    message.get_component(TextDrawable).set_text("GAME OVER")
                else:
                    message.get_component(TextDrawable).set_text("VICTORY")

            # Close the game if we've won.
            if self.won:
                if self.won_timer.tick(1.0/fps):
                    running = False

        # Finalise
        pygame.quit()

        # Save a list of images to preload next time.
        self.resource_loader.save_preload()
