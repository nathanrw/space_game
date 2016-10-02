from vector2d import Vec2d

import pygame

class InputHandling(object):
    def __init__(self):
        self.input_handlers = []
    def add_input_handler(self, handler):
        self.input_handlers.append(handler)
    def handle_input(self, event):
        self.input_handlers = [ x for x in self.input_handlers if not x.is_garbage() ]
        for handler in self.input_handlers:
            if handler.handle_input(event):
                return True
        return False

class InputHandler(object):
    def __init__(self, game_object):
        self.game_object = game_object
    def is_garbage(self):
        return self.game_object.is_garbage
    def handle_input(self, event):
        return False

class PlayerInputHandler(InputHandler):
    def __init__(self, player):
        InputHandler.__init__(self, player)
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
                player.dir -= kmap[e.key]
                return True
        elif e.type == pygame.KEYUP:
            if e.key in kmap:
                player.dir += kmap[e.key]
                return True
        elif e.type == pygame.MOUSEBUTTONDOWN:
            player.gun.start_shooting_screen(Vec2d(e.pos))
            return True
        elif e.type == pygame.MOUSEBUTTONUP:
            player.gun.stop_shooting()
            return True
        elif e.type == pygame.MOUSEMOTION:
            if player.gun.shooting:
                player.gun.start_shooting_screen(Vec2d(e.pos))
                return True
        return False
