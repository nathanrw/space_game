from pymunk.vec2d import Vec2d

import pygame

from .behaviours import Weapons, Thrusters

class InputResponse(object):
    def __init__(self):
        self.quit_requested = False
        self.event_handled = False

class InputHandling(object):
    """ Handles input. """

    def __init__(self, game_services, player):
        """ Initialise. """

        # Provides access to the bits of the game we want to manipulate.
        self.game_services = game_services
        self.player = player

        # Initialse pygame's joystick functionality
        pygame.joystick.init()
        self.js = None
        if pygame.joystick.get_count() > 0:
            self.js = pygame.joystick.Joystick(0)
            self.js.init()

        # Get components out of the player that we want to drive.
        self.weapons = player.get_component(Weapons)
        self.thrusters = player.get_component(Thrusters)

    def handle_input(self, e):
        """ Handle a pygame input event, and return our reponse i.e. whether we
        handled it, and whether 'quit' has been requested. """

        # The response to return.
        response = InputResponse()

        # A no op.
        def nothing(): pass

        # Request to quit the game.
        def request_quit():
            response.quit_requested = True

        # Keyboard controls.
        kmap = {

            # Movement controls
            pygame.K_w: (lambda: self.thrusters.go_forwards(),
                         lambda: self.thrusters.go_backwards()),
            pygame.K_a: (lambda: self.thrusters.go_left(),
                         lambda: self.thrusters.go_right()),
            pygame.K_s: (lambda: self.thrusters.go_backwards(),
                         lambda: self.thrusters.go_forwards()),
            pygame.K_d: (lambda: self.thrusters.go_right(),
                         lambda: self.thrusters.go_left()),
            pygame.K_q: (lambda: self.thrusters.turn_right(),
                         lambda: self.thrusters.turn_left()),
            pygame.K_e: (lambda: self.thrusters.turn_left(),
                         lambda: self.thrusters.turn_right()),

            # Zoom
            pygame.K_t: (nothing, lambda: self.zoom_in()),
            pygame.K_g: (nothing, lambda: self.zoom_out()),

            # Weapon switching
            pygame.K_r: (nothing, lambda: self.weapons.next_weapon()),
            pygame.K_f: (nothing, lambda: self.weapons.prev_weapon()),

            # Shooting
            pygame.K_SPACE: (lambda: self.start_shooting(),
                             lambda: self.stop_shooting()),

            # Quit.
            pygame.K_ESCAPE: (nothing, request_quit)
        }

        # Joystick (button) controls.
        jsmap = {

            # Shooting
            0: (lambda: self.start_shooting(),
                lambda: self.stop_shooting()),

            # Turning
            4: (lambda: self.thrusters.turn_left(),
                lambda: self.thrusters.turn_right()),
            5: (lambda: self.thrusters.turn_right(),
                lambda: self.thrusters.turn_left())
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

        elif e.type == pygame.MOUSEBUTTONDOWN:
            # Mouse down.
            self.start_shooting()
            response.event_handled = True

        elif e.type == pygame.MOUSEBUTTONUP:
            # Mouse up.
            self.stop_shooting()
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
            thrusters.set_direction(Vec2d(e.value[0], -e.value[1]))
            response.event_handled = True

        # Return the response.
        return response

    def start_shooting(self):
        """ Start shooting ahead. """
        weapon = self.weapons.get_weapon()
        if weapon is None:
            return
        weapon.start_shooting_coaxial()

    def stop_shooting(self):
        """ Stop the guns. """
        weapon = self.weapons.get_weapon()
        if weapon is None:
            return
        weapon.stop_shooting()

    def zoom_in(self):
        """ Zoom the camera in."""
        self.game_services.get_camera().zoom += 0.1

    def zoom_out(self):
        """ Zoom the camera out. """
        self.game_services.get_camera().zoom -= 0.1
