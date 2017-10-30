"""
A space game written in Python.
"""

# Standard imports.
import pygame
import os
import sys

# Local imports.
import components
import drawing
import ecs
import input_handling
import physics
import resource
import systems
import utils


class SpaceGameServices(ecs.GameServices):
    """ The services exposed to the entities. This is separate from
    the game class itself to try and keep control of the interface - since
    this is basically global state you can get at from anywhere. """

    def __init__(self, game):
        self.game = game
        self.info = ecs.GameInfo()
        self.debug_level = 0

    def get_renderer(self):
        return self.game.renderer

    def get_player(self):
        """ Get the player. """
        return self.game.player

    def get_camera(self):
        """ Get the camera. """
        return self.game.camera.get_component(components.Camera)

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
        self.resource_loader = resource.ResourceLoader()

        # The configuration.
        if os.path.isfile("./config.txt"):
            self.config = self.resource_loader.load_config_file_from("./config.txt")
        else:
            self.config = self.resource_loader.load_config_file("base_config.txt")

        # Create the renderer.
        renderer_name = self.config.get_or_default("renderer", "src.pygame_renderer.PygameRenderer")
        renderer_class = utils.lookup_type(renderer_name)
        screen_size = (self.config.get_or_default("screen_width", 1024),
                       self.config.get_or_default("screen_height", 768))
        self.renderer = renderer_class(screen_size, self.config, data_path="./res")

        # The resource loaded needs a renderer to load images etc.
        self.resource_loader.set_renderer(self.renderer)

        # The player
        self.player = None

        # The input handling system.
        self.input_handling = None

        # The main camera.
        self.camera = None

        # The enemy.
        self.wave_spawner = None

        # The physics
        self.physics = physics.Physics()

        # Plug the systems in. Note that systems can be created dynamically,
        # but we want to manipulate them so we specify them up front.
        self.entity_manager = ecs.EntityManager(self.game_services)
        self.entity_manager.register_component_system(self.physics)

        # Configure the resource loader.
        self.resource_loader.set_minimise_image_loading(
            self.config.get_or_default("minimise_image_loading", False)
        )

        # The drawing visitor.
        self.drawing = drawing.Drawing(self.game_services)

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
            view = drawing.CameraView(self.renderer, self.camera)
            self.renderer.pre_render(view)
            self.drawing.draw(view)
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

        # Create the game systems.
        self.entity_manager.register_component_system(systems.FollowsTrackedSystem())
        self.entity_manager.register_component_system(systems.ShootsAtTrackedSystem())
        self.entity_manager.register_component_system(systems.WeaponSystem())
        self.entity_manager.register_component_system(systems.TrackingSystem())
        self.entity_manager.register_component_system(systems.LaunchesFightersSystem())
        self.entity_manager.register_component_system(systems.KillOnTimerSystem())
        self.entity_manager.register_component_system(systems.PowerSystem())
        self.entity_manager.register_component_system(systems.ShieldSystem())
        self.entity_manager.register_component_system(systems.TextSystem())
        self.entity_manager.register_component_system(systems.AnimSystem())
        self.entity_manager.register_component_system(systems.ThrusterSystem())
        self.entity_manager.register_component_system(systems.ThrustersSystem())
        self.entity_manager.register_component_system(systems.WaveSpawnerSystem())
        self.entity_manager.register_component_system(systems.CameraSystem())
        self.entity_manager.register_component_system(systems.TurretSystem())
        self.entity_manager.register_component_system(systems.TurretsSystem())

        # Preload certain images.
        self.resource_loader.preload()

        # Make the camera.
        self.camera = self.entity_manager.create_entity_with(components.Camera,
                                                             components.Body,
                                                             components.Tracking,
                                                             components.FollowsTracked)
        self.camera.get_component(components.FollowsTracked).follow_type = "instant"

        # Draw debug info if requested.
        self.game_services.debug_level = self.config.get_or_default("debug", 0)

        # Make the player
        self.player = self.entity_manager.create_entity("player.txt")
        self.camera.get_component(components.Tracking).tracked.entity = self.player

        # Make the input handling system.
        self.input_handling = input_handling.InputHandling(self.game_services, self.player)

        # Create the wave spawner.
        if not self.config.get_or_default("peaceful_mode", False):
            self.entity_manager.register_component_system(systems.WaveSpawnerSystem())

        # Make it so that bullets can damage things.
        self.physics.add_collision_handler(DamageCollisionHandler())

        # Set the scrolling background.
        self.drawing.set_background("res/images/857-tileable-classic-nebula-space-patterns/6.jpg")

        # Run the game loop.
        self.run_update_loop()

        # Finalise
        pygame.quit()


class DamageCollisionHandler(physics.CollisionHandler):
    """ Collision handler to apply bullet damage. """

    def __init__(self):
        """ Constructor. """

        # Match entities that cause damage on contact to entities that can be
        # damaged.
        physics.CollisionHandler.__init__(
            self,
            components.DamageOnContact,
            components.Hitpoints
        )

    def handle_matching_collision(self, dmg, hp):
        """ Apply the logical effect of the collision and return the result. """

        # If our entity is about to die we might be about to spawn an
        # explosion. If that's the case it should be travelling at the same
        # speed as the thing we hit. So match velocities before our entity is
        # killed.
        if dmg.config.get_or_default("destroy_on_hit", True):
            b1 = dmg.entity.get_component(components.Body)
            b2 = hp.entity.get_component(components.Body)
            if b1 is not None and b2 is not None:
                b1.velocity = b2.velocity
            dmg.entity.kill()

        # Apply the damage.
        systems.apply_damage_to_entity(dmg.config["damage"], hp.entity)

        # Return the result ( we handled the collision. )
        return physics.CollisionResult(True, True)
