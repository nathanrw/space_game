from vector2d import Vec2d

import pygame

from utils import ComponentSystem, Component
from physics import Body
from behaviours import ManuallyShootsBullets

class InputHandling(ComponentSystem):
    """ A system for input handlers: components that know how to deal
    with input. """
    def handle_input(self, event):
        self.garbage_collect()
        for handler in self.components:
            if handler.handle_input(event):
                return True
        return False

class InputHandler(Component):
    """ An input handling component. """
    def manager_type(self):
        return InputHandling
    def handle_input(self, event):
        return False

class PlayerInputHandler(InputHandler):
    """ Deals with input to the player's ship. """

    def __init__(self, game_object, game_services, config):
        InputHandler.__init__(self, game_object, game_services, config)
        self.dir = Vec2d(0, 0)

    def start_shooting(self, pos):
        """ Start shooting at a particular screen space point. """
        guns = self.get_components(ManuallyShootsBullets)
        for g in guns:
            g.start_shooting_screen(pos)

    def stop_shooting(self):
        """ Stop the guns. """
        guns = self.get_components(ManuallyShootsBullets)
        for g in guns:
            g.stop_shooting()

    def is_shooting(self):
        """ Are the guns firing? If one is they both are. """
        guns = self.get_components(ManuallyShootsBullets)
        return guns[0].shooting

    def handle_input(self, e):
        if InputHandler.handle_input(self, e):
            return True
        kmap = {
            pygame.K_w: Vec2d(0, 1),
            pygame.K_a: Vec2d(1, 0),
            pygame.K_s: Vec2d(0, -1),
            pygame.K_d: Vec2d(-1, 0)
        }
        player = self.game_object
        if e.type == pygame.KEYDOWN:
            if e.key in kmap:
                self.dir -= kmap[e.key]
                return True
        elif e.type == pygame.KEYUP:
            if e.key in kmap:
                self.dir += kmap[e.key]
                return True
        elif e.type == pygame.MOUSEBUTTONDOWN:
            self.start_shooting(Vec2d(e.pos))
            return True
        elif e.type == pygame.MOUSEBUTTONUP:
            self.stop_shooting()
            return True
        elif e.type == pygame.MOUSEMOTION:
            if self.is_shooting():
                self.start_shooting(Vec2d(e.pos))
                return True
        return False

    def update(self, dt):
        body = self.get_component(Body)
        if body is not None:
            body.velocity += self.dir.normalized() * dt * 500 
