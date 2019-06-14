"""
A space game written in Python.
"""

# Standard imports.
import pygame
import os
import sys
import pynk
import pynk.nkpygame

# Local imports.
import config
import components
import drawing
import ecs
import input_handling
import physics
import planets
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

    def get_renderer(self):
        return self.game.renderer

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

    def load(self):
        """ Load the game. """
        self.game.load()

    def save(self):
        """ Save the game. """
        self.game.save()

    def paused(self):
        """ Is the game paused? """
        return self.game.paused()

    def toggle_pause(self):
        """ Pause the game. """
        self.game.toggle_pause()

    def step(self):
        """ Simulate one frame and then pause. """
        self.game.step()


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
        if len(path) > 0:
            os.chdir( path )
        if not os.path.isdir("res"):
            raise Exception("Unable to locate resource tree.")
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

        # The input handling system.
        self.input_handling = None

        # The enemy.
        self.wave_spawner = None

        # Create the entity manager.
        self.entity_manager = ecs.EntityManager(self.game_services)

        # Configure the resource loader.
        self.resource_loader.set_minimise_image_loading(
            self.config.get_or_default("minimise_image_loading", False)
        )

        # The drawing visitor.
        self.drawing = drawing.Drawing(self.game_services)

        # Is the game running?
        self.running = False

        # Should we load the game?
        self.want_load = False

        # Should we pause the game?
        self.want_pause = False

        # Should we unpause the game?
        self.want_resume = False

        # Should we simulate one frame and then pause?
        self.want_step = False

        # The GUI
        self.nkpygame = None

    def stop_running(self):
        """ Stop the game from running. """
        self.running = False

    def run(self):
        """ The game loop. This performs initialisation including setting
        up pygame, and shows a loading screen while certain resources are
        preloaded. Then, we enter the game loop wherein we remain until the
        game is over. """

        # Initialise the pygame display.
        pygame.init()
        pygame.mixer.init()
        self.renderer.initialise()

        # Create the game systems.
        self.entity_manager.register_component_system(physics.Physics())
        self.entity_manager.register_component_system(systems.FollowsTrackedSystem())
        self.entity_manager.register_component_system(systems.TrackingSystem())
        self.entity_manager.register_component_system(systems.LaunchesFightersSystem())
        self.entity_manager.register_component_system(systems.KillOnTimerSystem())
        self.entity_manager.register_component_system(systems.PowerSystem())
        self.entity_manager.register_component_system(systems.ShieldSystem())
        self.entity_manager.register_component_system(systems.TextSystem())
        self.entity_manager.register_component_system(systems.AnimSystem())
        self.entity_manager.register_component_system(systems.ThrusterSystem())
        self.entity_manager.register_component_system(systems.ThrustersSystem())
        self.entity_manager.register_component_system(systems.CameraSystem())
        self.entity_manager.register_component_system(systems.TurretSystem())
        self.entity_manager.register_component_system(systems.TurretsSystem())
        self.entity_manager.register_component_system(systems.WeaponSystem())
        self.entity_manager.register_component_system(systems.SolarSystem())
        self.entity_manager.register_component_system(systems.PlayerSystem())
        
        # Add a planet.
        sun = planets.create_planet(self.entity_manager, planets.SUN_DEF)
        mercury = planets.create_planet(self.entity_manager, planets.MERCURY_DEF)
        venus = planets.create_planet(self.entity_manager, planets.VENUS_DEF)
        earth = planets.create_planet(self.entity_manager, planets.EARTH_DEF)
        mars = planets.create_planet(self.entity_manager, planets.MARS_DEF)
        jupiter = planets.create_planet(self.entity_manager, planets.JUPITER_DEF)

        # Preload certain images.
        self.resource_loader.preload()

        # Make the camera.
        camera = self.entity_manager.create_entity_with(components.Camera,
                                                             components.Body,
                                                             components.Tracking,
                                                             components.FollowsTracked)
        camera.get_component(components.FollowsTracked).follow_type = "instant"
        camera.name = "Camera"

        # Draw debug info if requested.
        self.game_services.debug_level = self.config.get_or_default("debug", 0)

        # Make the player
        player = self.entity_manager.create_entity("player.txt")
        player.name = "Player"
        mercury_body = mercury.get_component(components.Body)
        systems.teleport(player, mercury_body.position, mercury_body.velocity)
        camera.get_component(components.Tracking).tracked.entity = player

        # Create a view to pass to the input handling - this lets it map between
        # world and screen coordinates.
        view = drawing.CameraView(self.renderer, camera)

        # Make the input handling system.
        self.input_handling = input_handling.InputHandling(view, self.game_services)

        # Create the wave spawner.
        if not self.config.get_or_default("peaceful_mode", False):
            self.entity_manager.register_component_system(systems.WaveSpawnerSystem())

        # Make it so that bullets can damage things.
        self.entity_manager.get_system(physics.Physics).add_collision_handler(
            DamageCollisionHandler()
        )

        # Set the scrolling background.
        self.drawing.set_background("res/images/857-tileable-classic-nebula-space-patterns/6.jpg")

        # Make the GUI
        nkfont = self.renderer.load_compatible_gui_font(
            "res/fonts/xolonium/Xolonium-Regular.ttf",
            12
        )
        self.nkpygame = pynk.nkpygame.NkPygame(nkfont)
        self.nkpygame.setup()

        # Run the game loop.
        self.running = True
        fps = 60
        clock = pygame.time.Clock()
        tick_time = 1.0/fps
        while self.running:

            # Has a load been requested?
            if self.want_load:
                self.entity_manager.load(open("space_game.save", "r"))
                self.want_load = False

            # If a pause has been scheduled then pause the game.
            if self.want_pause:
                self.want_pause = False
                self.entity_manager.pause()

            # If an unpause has been scheduled then unpause the game.
            if self.want_resume:
                self.want_resume = False
                self.entity_manager.unpause()

            # If a step has been scheduled then advance a frame and schedule a
            # pause.
            if self.want_step:
                self.entity_manager.unpause()
                self.want_pause = True
                self.want_step = False

            # Input
            events = []
            for e in pygame.event.get():
                response = self.input_handling.handle_input(e)
                if response.quit_requested:
                    self.running = False
                if not response.event_handled:
                    events.append(e)
            self.nkpygame.handle_events(events)
            self.input_handling.handle_gui_input(self.nkpygame)

            # Update the systems.
            self.entity_manager.update(tick_time)

            # Draw
            self.renderer.pre_render(view)
            self.drawing.draw(view)
            self.renderer.add_job_nuklear(self.nkpygame)
            self.renderer.post_render()
            self.renderer.flip_buffers()
            pynk.lib.nk_clear(self.nkpygame.ctx)

            # Maintain frame rate.
            clock.tick(fps)

            # Remember how long the frame took.
            limited_fps = 1.0/(clock.get_time() / 1000.0)
            raw_fps = 1.0/(clock.get_rawtime() / 1000.0)
            time_ratio =  (1.0/fps) / (clock.get_time()/1000.0)
            self.game_services.info.update_framerate(limited_fps,
                                                     raw_fps,
                                                     time_ratio)

        # Finalise
        self.nkpygame.teardown()
        pygame.quit()

    def load(self):
        """ Schedule a load. """
        self.want_load = True

    def save(self):
        """ Save the game. """
        self.entity_manager.save(open("space_game.save", "w"))

    def paused(self):
        """ Is the game paused? """
        return self.entity_manager.paused()

    def toggle_pause(self):
        """ Schedule a pause. """
        if self.entity_manager.paused():
            self.want_resume = True
        else:
            self.want_pause = True

    def step(self):
        """ Schedule a step. """
        self.want_step = True


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

        # Delegate to the function in 'systems'.
        systems.handle_damage_collision(dmg, hp)

        # Return the result ( we handled the collision. )
        return physics.CollisionResult(True, True)
