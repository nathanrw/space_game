from vector2d import Vec2d

import pygame

from utils import ComponentSystem, Component
from behaviours import ManuallyShootsBullets, Thrusters

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
        thrusters = self.get_component(Thrusters)
        if thrusters is None:
            return False
        kmap = {
            pygame.K_w: (lambda: thrusters.go_forwards(), lambda: thrusters.go_backwards()),
            pygame.K_a: (lambda: thrusters.go_left(), lambda: thrusters.go_right()),
            pygame.K_s: (lambda: thrusters.go_backwards(), lambda: thrusters.go_forwards()),
            pygame.K_d: (lambda: thrusters.go_right(), lambda: thrusters.go_left()),
            pygame.K_q: (lambda: thrusters.turn_left(), lambda: thrusters.turn_right()),
            pygame.K_e: (lambda: thrusters.turn_right(), lambda: thrusters.turn_left())
        }
        player = self.game_object
        if e.type == pygame.KEYDOWN:
            if e.key in kmap:
                kmap[e.key][0]()
                return True
        elif e.type == pygame.KEYUP:
            if e.key in kmap:
                kmap[e.key][1]()
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
