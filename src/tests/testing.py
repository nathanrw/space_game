""" Utilities to aid testing. """

import pygame

from ..utils import GameServices, Entity, EntityManager, ResourceLoader, Config
from ..components import Camera

class MockGameServices(GameServices):
    """ Mock game services implementation. """
    def __init__(self):
        self.screen = None
        self.player = None
        self.camera = None
        self.entity_manager = None
        self.resource_loader = None
        self.on_end_game = None
    def get_screen(self):
        """ Get the main drawing surface. """
        return self.screen
    def get_player(self):
        """ Get the player's entity. """
        return self.player
    def get_camera(self):
        """ Get the camera. """
        return self.camera
    def get_entity_manager(self):
        """ Get the entity manager. """
        return self.entity_manager
    def get_resource_loader(self):
        """ Get the object that can load images and so on. """
        return self.resource_loader
    def end_game(self):
        """ Tidy up and exit the program cleanly. """
        if self.on_end_game is not None:
            self.on_end_game

# We only want to initialise pygame once, and then have subsequent tests
# re-use it. This is because if you keep turning it off and on again, it
# segfaults.
global_screen = None

def run_pygame_test(test_func, size=(640,480)):
    """ Run a pygame test. This is a minimal test without an entity manager,
    but with a camera (because much drawing relies on there being one.) """
    global global_screen
    if global_screen is None:
        pygame.init()
        global_screen = pygame.display.set_mode(size)
    game_services = MockGameServices()
    game_services.screen = global_screen
    game_services.camera = Camera(Entity(game_services), game_services, Config())
    game_services.resource_loader = ResourceLoader()
    test_func(game_services)

def create_entman_testing_services():
    game_services = MockGameServices()
    game_services.resource_loader = ResourceLoader()
    game_services.entity_manager = EntityManager(game_services)
    return game_services
