from pymunk.vec2d import Vec2d

import pygame

from .components import Thrusters, Player, Camera

class InputResponse(object):
    def __init__(self):
        self.quit_requested = False
        self.event_handled = False

class InputHandling(object):
    """ Handles input. """

    def __init__(self, game_services):
        """ Initialise. """

        # Provides access to the bits of the game we want to manipulate.
        self.game_services = game_services

        # Initialse pygame's joystick functionality
        pygame.joystick.init()
        self.js = None
        if pygame.joystick.get_count() > 0:
            self.js = pygame.joystick.Joystick(0)
            self.js.init()

    def handle_input(self, e):
        """ Handle a pygame input event, and return our reponse i.e. whether we
        handled it, and whether 'quit' has been requested. """

        # The response to return.
        response = InputResponse()

        # A no op.
        def nothing(): pass
        def nothing1(x): pass

        # Request to quit the game.
        def request_quit():
            response.quit_requested = True

        # Directions.
        forwards = Vec2d(0, -1)
        backwards = Vec2d(0, 1)
        left = Vec2d(-1, 0)
        right = Vec2d(1, 0)
        turn_left = 1
        turn_right = -1

        # Keyboard controls.
        kmap = {

            # Movement controls
            pygame.K_w: (lambda: self.move(forwards),
                         lambda: self.move(backwards)),
            pygame.K_a: (lambda: self.move(left),
                         lambda: self.move(right)),
            pygame.K_s: (lambda: self.move(backwards),
                         lambda: self.move(forwards)),
            pygame.K_d: (lambda: self.move(right),
                         lambda: self.move(left)),
            pygame.K_q: (lambda: self.turn(turn_right),
                         lambda: self.turn(turn_left)),
            pygame.K_e: (lambda: self.turn(turn_left),
                         lambda: self.turn(turn_right)),

            # Zoom
            pygame.K_t: (nothing, lambda: self.zoom_in()),
            pygame.K_g: (nothing, lambda: self.zoom_out()),

            # Quit.
            pygame.K_ESCAPE: (nothing, request_quit),

            # Save.
            pygame.K_F8: (nothing, lambda: self.game_services.save()),

            # Load.
            pygame.K_F9: (nothing, lambda: self.game_services.load()),

            # Pause the game.
            pygame.K_PAUSE: (nothing, lambda: self.game_services.toggle_pause()),

            # Step forward one frame.
            pygame.K_BACKQUOTE: (nothing, lambda: self.game_services.step()),
        }

        # Joystick (button) controls.
        jsmap = {

            # Turning
            4: (lambda: self.turn(turn_left),
                lambda: self.turn(turn_right)),
            5: (lambda: self.turn(turn_right),
                lambda: self.turn(turn_left))
        }

        # Mouse controls.
        mousemap = {

            # Zoom in / out with mouse wheel.
            4: (nothing1, lambda pos: self.zoom_in()),
            5: (nothing1, lambda pos: self.zoom_out()),
        }

        if e.type == pygame.QUIT:
            # Quit requested from window manager.
            response.quit_requested = True
            response.event_handled = True

        elif e.type == pygame.KEYDOWN or e.type == pygame.KEYUP:
            # Handle a key press.
            if e.key in kmap:
                kmap[e.key][e.type == pygame.KEYUP]()
                response.event_handled = True

        elif e.type == pygame.MOUSEBUTTONDOWN or e.type == pygame.MOUSEBUTTONUP:
            if e.button in mousemap:
                mousemap[e.button][e.type == pygame.MOUSEBUTTONUP](e.pos)
                response.event_handled = True

        elif e.type == pygame.JOYAXISMOTION:
            # We don't use this yet, but print out info.
            print( "axis: ", e.axis, e.value )
            response.event_handled = True

        elif e.type == pygame.JOYBALLMOTION:
            # We don't use this yet, but print out info.
            print( "ball: ", e.ball, e.rel )
            response.event_handled = True

        elif e.type == pygame.JOYBUTTONDOWN or e.type == pygame.JOYBUTTONUP:
            # Joystick button.
            print( "button: ", e.button )
            if e.button in jsmap:
                jsmap[e.button][e.type == pygame.JOYBUTTONUP]()
                response.event_handled = True

        elif e.type == pygame.JOYHATMOTION:
            # D-pad movement.
            print( "hat: ", e.hat, e.value )
            self.move(Vec2d(e.value[0], -e.value[1]))
            response.event_handled = True

        # Return the response.
        return response

    def zoom_in(self):
        """ Zoom the camera in."""
        cameras = self.game_services.get_entity_manager().query(Camera)
        for camera in cameras:
            camera.get_component(Camera).zoom += 0.1

    def zoom_out(self):
        """ Zoom the camera out. """
        cameras = self.game_services.get_entity_manager().query(Camera)
        for camera in cameras:
            camera.get_component(Camera).zoom -= 0.1

    def move(self, direction):
        """ Move the player in a direction. """
        players = self.game_services.get_entity_manager().query(Player)
        for player in players:
            thrusters = player.get_component(Thrusters)
            if thrusters is not None:
                thrusters.direction += direction

    def turn(self, direction):
        """ Turn the player in a direction. """
        players = self.game_services.get_entity_manager().query(Player)
        for player in players:
            thrusters = player.get_component(Thrusters)
            if thrusters is not None:
                thrusters.turn += direction
