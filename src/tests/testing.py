""" Utilities to aid testing. """

import pygame

from ..ecs import GameServices, Entity, EntityManager
from ..resource import ResourceLoader
from ..config import Config
from ..pygame_renderer import PygameRenderer


# We only want to initialise pygame once, and then have subsequent tests
# re-use it. This is because if you keep turning it off and on again, it
# segfaults.
global_renderer = None


class MockGameServices(GameServices):
    """ Mock game services implementation. """
    def __init__(self):
        self.entity_manager = None
        self.resource_loader = ResourceLoader()
        
        global global_renderer
        if global_renderer is None:
            pygame.init()
            global_renderer = PygameRenderer((640, 480), Config(), data_path="../../res/")
            global_renderer.initialise()
            
        self.renderer = global_renderer
        self.resource_loader.set_renderer(self.renderer)
        
    def get_renderer(self):
        return self.renderer

    def get_entity_manager(self):
        """ Return the entity manager. """
        return self.entity_manager

    def get_resource_loader(self):
        """ Get the resource loader. """
        return self.resource_loader


def run_pygame_test(test_func):
    """ Run a pygame test. This is a minimal test without an entity manager,
    but with a renderer.  """
    game_services = MockGameServices()
    test_func(game_services)

    
def create_entman_testing_services():
    game_services = MockGameServices()
    game_services.entity_manager = EntityManager(game_services)
    return game_services
