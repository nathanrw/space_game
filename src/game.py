"""
A space game written in Python.

It currently depends on pygame for windowing, event handling etc, and on
pymunk for physics.

The program is structured with the intention than various distinct concerns
can be separated. The implementation of physics and the implementation of
drawing know nothing about one another, for instance. This is a work in progress
though. I'd like to make it realise this ideal more.

Entity creation is data-driven. Entities are defined in configuration
.txt files containing json data; these live under res/configs.

Things I would like to work on now:

1) Make it more of a game i.e. support controllers, add more types of enemy,
   weapon etc.

2) Make the use of pymunk more idiomatic. It's currently horrendous.
   
"""

import pygame
import os
import sys

from .physics import Physics
from .drawing import Drawing
from .behaviours import DamageCollisionHandler, Camera, WaveSpawner
from .utils import Config, GameServices, GameInfo, ResourceLoader, EntityManager
from .input_handling import InputHandling

class SpaceGameServices(GameServices):
    """ The services exposed to the entitys. This is separate from
    the game class itself to try and keep control of the interface - since
    this is basically global state you can get at from anywhere. """
    
    def __init__(self, game):
        self.game = game
        self.info = GameInfo()
        self.debug_level = 0

    def get_renderer(self):
        return self.game.renderer

    def get_player(self):
        """ Get the player. """
        return self.game.player

    def get_camera(self):
        """ Get the camera. """
        return self.game.camera.get_component(Camera)

    def get_entity_manager(self):
        """ Return the entity manager. """
        return self.game.entity_manager

    def get_resource_loader(self):
        """ Get the resource loader. """
        return self.game.resource_loader

    def get_info(self):
        """ Return the information. """
        return self.info

    def end_game(self):
        """ Stop the game from running. """
        self.game.stop_running()

    def get_debug_level(self):
        """ Return the debug level. """
        return self.debug_level
                
class Game(object):
    """ Class glueing all of the building blocks together into an actual
    game. """
    
    def __init__(self):
        """ Initialise the game systems. """

        # Change directory into the directory above this file - the
        # one containng the 'res' tree.  Note that if we've been built via
        # py2exe, we will actually be in a zip file so account for that.
        path = os.path.dirname(os.path.dirname(__file__))
        if (os.path.basename(path) == "library.zip"):
            path = os.path.dirname(path)
        os.chdir( path )
        sys.path += ["."]

        # Services exposed to the entities.
        self.game_services = SpaceGameServices(self)

        # The resource loader.
        self.resource_loader = ResourceLoader()

        # The configuration.
        if os.path.isfile("./config.txt"):
            self.config = self.resource_loader.load_config_file_from("./config.txt")
        else:
            self.config = self.resource_loader.load_config_file("base_config.txt")

        # Create the renderer.
        renderer_name = self.config.get_or_default("renderer", "src.pygame_renderer.PygameRenderer")
        renderer_class = self.game_services.lookup_type(renderer_name)
        screen_size = (self.config.get_or_default("screen_width", 1024),
                       self.config.get_or_default("screen_height", 768))
        self.renderer = renderer_class(screen_size, self.config, data_path="./res")

        # The resource loaded needs a renderer to load images etc.
        self.resource_loader.renderer = self.renderer

        # The player
        self.player = None

        # The input handling system.
        self.input_handling = None

        # The main camera.
        self.camera = None

        # The enemy.
        self.wave_spawner = None

        # The physics
        self.physics = Physics()

        # Plug the systems in. Note that systems can be created dynamically,
        # but we want to manipulate them so we specify them up front.
        self.entity_manager = EntityManager(self.game_services)
        self.entity_manager.register_component_system(self.physics)

        # Configure the resource loader.
        self.resource_loader.minimise_image_loading = \
            self.config.get_or_default("minimise_image_loading", False)

        # The drawing visitor.
        self.drawing = Drawing(self.game_services)

        # Is the game running?
        self.running = False

    def stop_running(self):
        """ Stop the game from running. """
        self.running = False

    def run_update_loop(self):
        """ Run an update loop. This sets self.running to True and
        exits when something sets it to false. Note that this is a
        separate function from run() since we might want a number of
        update loops - e.g. as a cheap way of having the loading
        screen use the same code as the rest of the game, or even
        maybe for implementing different modes (using the call stack
        to stack them.)"""

        # Main loop.
        self.running = True
        fps = 60
        clock = pygame.time.Clock()
        tick_time = 1.0/fps
        while self.running:

            ## Create any queued objects
            self.entity_manager.create_queued_objects()

            # Input
            for e in pygame.event.get():
                response = self.input_handling.handle_input(e)
                if response.quit_requested:
                    self.running = False

            # Update the systems.
            self.entity_manager.update(tick_time)

            # Draw
            self.renderer.pre_render(self.camera.get_component(Camera))
            self.drawing.draw(self.camera.get_component(Camera))
            self.renderer.post_render()
            self.renderer.flip_buffers()

            # Maintain frame rate.
            clock.tick(fps)

            # Calculate some metrics
            limited_fps = 1.0/(clock.get_time() / 1000.0)
            raw_fps = 1.0/(clock.get_rawtime() / 1000.0)
            time_ratio =  (1.0/fps) / (clock.get_time()/1000.0) 

            # Remember how long the frame took.
            self.game_services.info.update_framerate(limited_fps,
                                                     raw_fps,
                                                     time_ratio)

    def run(self):
        """ The game loop. This performs initialisation including setting
        up pygame, and shows a loading screen while certain resources are
        preloaded. Then, we enter the game loop wherein we remain until the
        game is over. If the file "preload.txt" does not exist, then it will
        be filled with a list of resources to preload next time the game is
        run. """
        
        # Initialise the pygame display.
        pygame.init()
        pygame.mixer.init()
        self.renderer.initialise()

        # Preload certain images.
        self.resource_loader.preload()

        # Make the camera. Im not 100% sure about this being a entity like any other
        # since it's clearly special - drawing requires one, the player moves it, etc. But
        # at the same time it's convenient to attach the background drawable to it, and we
        # might want to give it physical properties in future. We'll see.
        self.camera = self.entity_manager.create_entity_with(Camera)

        # Draw debug info if requested.
        self.game_services.debug_level = self.config.get_or_default("debug", 0)

        # Make the player
        self.player = self.entity_manager.create_entity("player.txt")

        # Make the input handling system.
        self.input_handling = InputHandling(self.game_services, self.player)

        # Make the camera follow the player.
        self.camera.get_component(Camera).track(self.player)

        # Create the wave spawner.
        if not self.config.get_or_default("peaceful_mode", False):
            self.wave_spawner = self.entity_manager.create_entity_with(WaveSpawner)

        # Make it so that bullets can damage things.
        self.physics.add_collision_handler(DamageCollisionHandler())

        # Set the scrolling background.
        self.drawing.set_background("res/images/857-tileable-classic-nebula-space-patterns/6.jpg")

        # Run the game loop.
        self.run_update_loop()

        # Finalise
        pygame.quit()
