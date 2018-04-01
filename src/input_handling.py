"""
Input handling scheme.

An operation that can be performed in response to user input is an Action. Different
inputs are mapped to actions in tables held by an InputHandling object.

While the keybindings are presently hard coded, the way mappings are represented
could easily be saved out and read back in, allowing for full customisation.

The scheme allows for keyboard, mouse and joystick input.
"""

from pymunk.vec2d import Vec2d

import pygame
import pynk
import collections
import inspect

from .physics import Physics
from .components import AnimationComponent, Thrusters, Player, Camera, Turrets, Turret
from .direction_providers import DirectionProviderScreen
from .ecs import EntityRef, EntityRefList
from .resource import Animation
from .utils import Timer

class InputResponse(object):
    """ The result of executing an Action.  This is bubbled back up to the
    main loop which can decide what to do - perhaps halt the program. """
    def __init__(self):
        self.quit_requested = False
        self.event_handled = False


class Action(object):
    """ An action in response to an input.  Tables of actions are used to
    respond to input events. 
    
    An action can be called in response to different types of inputs.  A button
    press will call execute(), which takes an input that stipulates whether the
    button is going up or down.  execute_position() is similar, but has a
    position as well - for instance, a mouse click will have this information.
    Finally some inputs are continuous; these will result in the execute_position()
    function being called.
    
    The more complex execute_*() by default call down to the basic execute(),
    meaning that a simple action can be bound to any type of input.   A more
    specialised action that only makes sense in response to continuous input
    might do nothing in response to execute().
    """

    def __init__(self, description):
        """ Constructor. """
        assert description is not None
        self.description = description

    def execute(self, alternate):
        """ Execute the action. If 'alternate' is true then an 'alternate'
        action should be performed - for instance if this action is handling
        a keyboard key, the 'keydown' even will execute with alternate=False,
        while the 'keyup' event will have alrenate=True, but both will be mapped
        to the same Action object. """
        return InputResponse()

    def execute_position(self, position, alternate):
        """ Execute with a position input.  The default implementation calls
        the regular execute(). """
        return self.execute(alternate)

    def execute_linear(self, value):
        """ Execute with a linear input.  The default implementation calls
        the regular execute(). """
        return self.execute(True)


class FuncAction(Action):
    """ An action that will execute one of two handler functions. 
    
    This will typically be used for actions that correspond naturally to key
    presses e.g. 'pause the game'.
    """

    def __init__(self, description, f1, f2 = None):
        """ Constructor.  If a single argument is supplied, then execute() will
        do nothing unless ***alternate==TRUE***.  This is useful for instance
        when something should only be done in response to a key UP event. """
        assert description is not None
        assert f1 is not None
        Action.__init__(self, description)
        if f2 is not None:
            self.__f1 = f1
            self.__f2 = f2
        else:
            def nothing(): pass
            self.__f1 = nothing
            self.__f2 = f1

    def execute(self, alternate):
        """ Execute our handler function. """
        ret = None
        if not alternate:
            ret = self.__f1()
        else:
            ret = self.__f2()
        if ret is None:
            ret = InputResponse()
            ret.event_handled = True
        return ret


class ShootAction(Action):
    """ An action to start shooting. """

    def __init__(self, description, handler):
        """ Constructor. """
        Action.__init__(self, description)
        self.handler = handler

    def execute_position(self, position, alternate):
        """ Start shooting at the given point. """
        if not alternate:
            self.handler.start_shooting(position)
        else:
            self.handler.stop_shooting()
        ret = InputResponse()
        ret.event_handled = True
        return ret

    def execute_linear(self, value):
        """ Keep looking in the right direction. """
        self.handler.maintain_aim(value)
        ret = InputResponse()
        ret.event_handled = True
        return ret


class Actions(object):
    """ A table of actions. """

    def __init__(self, handler):
        """ Constructor.  Create the actions. """

        # Directions.
        forwards = Vec2d(0, -1)
        backwards = Vec2d(0, 1)
        left = Vec2d(-1, 0)
        right = Vec2d(1, 0)
        turn_left = 1
        turn_right = -1

        # A function to request the program halt.
        def quit():
            ret = InputResponse()
            ret.event_handled = True
            ret.quit_requested = True
            return ret

        # Handlers
        self.MOVE_FORWARDS = FuncAction("Move forwards",
                                        lambda: handler.move(forwards),
                                        lambda: handler.move(backwards))
        self.MOVE_BACKWARDS = FuncAction("Move backwards",
                                         lambda: handler.move(backwards),
                                         lambda: handler.move(forwards))
        self.MOVE_LEFT = FuncAction("Move left",
                                    lambda: handler.move(left),
                                    lambda: handler.move(right))
        self.MOVE_RIGHT = FuncAction("Move right",
                                     lambda: handler.move(right),
                                     lambda: handler.move(left))
        self.ROTATE_CLOCKWISE = FuncAction("Rotate clockwise",
                                           lambda: handler.turn(turn_right),
                                           lambda: handler.turn(turn_left))
        self.ROTATE_ANTICLOCKWISE = FuncAction("Rotate anticlockwise",
                                               lambda: handler.turn(turn_left),
                                               lambda: handler.turn(turn_right))
        self.ZOOM_IN = FuncAction("Zoom in",
                                  lambda: handler.zoom_in())
        self.ZOOM_OUT = FuncAction("Zoom out",
                                   lambda: handler.zoom_out())
        self.QUIT = FuncAction("Quit", quit)
        self.SAVE = FuncAction("Save",
                               lambda: handler.game_services.save())
        self.LOAD = FuncAction("Load",
                               lambda: handler.game_services.load())
        self.TOGGLE_PAUSE = FuncAction("Pause / unpause",
                                       lambda: handler.game_services.toggle_pause())
        self.TOGGLE_INPUT = FuncAction("Toggle input",
                                       lambda: handler.toggle_input())
        self.STEP = FuncAction("Simulate one frame then pause",
                               lambda: handler.game_services.step())
        self.SHOW_KEYS = FuncAction("Show keys",
                                    lambda: handler.print_keybindings())
        self.SHOOT = ShootAction("Shoot", handler)


class KeyMap(object):
    """ A mapping from keys to actions. """

    def __init__(self, name, mapping):
        """ Constructor. 'mapping' should be a dict-like mapping from keys
        to actions to be executed. """
        self.__name = name
        self.__mapping = mapping

    def execute(self, key, alternate):
        """ If this key is mapped to an action, execute the corresponding action
        and return the response. """
        if key in self.__mapping:
            return self.__mapping[key].execute(alternate)
        return InputResponse()

    def execute_position(self, key, position, alternate):
        """ If this key is mapped to an action, execute the corresponding
        action and return the response. """
        if key in self.__mapping:
            return self.__mapping[key].execute_position(position, alternate)
        return InputResponse()

    def execute_linear(self, key, value):
        """ If this key is mapped to an action, execute the corresponding
        action and return the response. """
        if key in self.__mapping:
            return self.__mapping[key].execute_linear(value)
        return InputResponse()

    def print_keybindings(self, key_display_func):
        """ Print out the key bindings. """
        if len(self.__mapping) == 0:
            return
        print ""
        print self.__name
        print "-" * len(self.__name)
        print ""
        for key in sorted(self.__mapping):
            print "    " + key_display_func(key) + ": " + self.__mapping[key].description


class InputContext(object):
    """ A context for input. """

    def __init__(self, actions, keyboard_actions={},
                                joystick_actions={},
                                joystick_axis_actions={},
                                joystick_ball_actions={},
                                joystick_hat_actions={},
                                mouse_actions={},
                                mouse_motion_actions={}):
        self.actions = actions

        # Keyboard controls.
        self.kmap = KeyMap("Keyboard", keyboard_actions)

        # Joystick (button) controls.
        self.js_map = KeyMap("Joystick buttons", joystick_actions)

        # Joystick (axis) controls.
        self.js_axis_map = KeyMap("Joystick axes", joystick_axis_actions)

        # Joystick (ball) controls.
        self.js_ball_map = KeyMap("Joystick balls", joystick_ball_actions)

        # Joystick (hat) controls.
        self.js_hat_map = KeyMap("Joystick hats", joystick_hat_actions)

        # Mouse controls.
        self.mouse_map = KeyMap("Mouse", mouse_actions)

        # Mouse motion.
        self.mouse_motion_map = KeyMap("Mouse motion", mouse_motion_actions)

    def print_keybindings(self):
        """ Output the keybindings. """
        for map in (self.kmap,
                    self.mouse_map,
                    self.js_map,
                    self.js_hat_map,
                    self.js_axis_map,
                    self.js_ball_map):
            key_display_func = lambda x: str(x)
            if map == self.kmap:
                key_display_func = pygame.key.name
            map.print_keybindings(key_display_func)

    def handle_input(self, e):
        """ Dispatch a pygame input event to the relevant key mapping table
         and return the response. """

        if e.type == pygame.QUIT:
            # Quit requested from window manager.
            return self.actions.QUIT.execute(True)
        elif e.type == pygame.KEYDOWN or e.type == pygame.KEYUP:
            return self.kmap.execute(e.key, e.type == pygame.KEYUP)
        elif e.type == pygame.MOUSEMOTION:
            ret = InputResponse()
            for button in e.buttons:
                ret1 = self.mouse_motion_map.execute_linear(button, e.pos)
                if ret1.event_handled == True:
                    ret = ret1
            return ret
        elif e.type == pygame.MOUSEBUTTONDOWN or e.type == pygame.MOUSEBUTTONUP:
            return self.mouse_map.execute_position(e.button,
                                                   e.pos,
                                                   e.type == pygame.MOUSEBUTTONUP)
        elif e.type == pygame.JOYAXISMOTION:
            return self.js_axis_map.execute_linear(e.axis, e.value)
        elif e.type == pygame.JOYBALLMOTION:
            return self.js_axis_map.execute_linear(e.ball, e.rel)
        elif e.type == pygame.JOYBUTTONDOWN or e.type == pygame.JOYBUTTONUP:
            return self.kmap.execute(e.button, e.type == pygame.JOYBUTTONUP)
        elif e.type == pygame.JOYHATMOTION:
            return self.js_hat_map.execute_linear(e.hat, e.value)

        return InputResponse()


class InputContextFlight(InputContext):
    """ Flying a spaceship """

    def __init__(self, actions):
        InputContext.__init__(
            self,
            actions,

            # Keyboard controls.
            keyboard_actions = {
                pygame.K_w: actions.MOVE_FORWARDS,
                pygame.K_a: actions.MOVE_LEFT,
                pygame.K_s: actions.MOVE_BACKWARDS,
                pygame.K_d: actions.MOVE_RIGHT,
                pygame.K_q: actions.ROTATE_CLOCKWISE,
                pygame.K_e: actions.ROTATE_ANTICLOCKWISE,
                pygame.K_t: actions.ZOOM_IN,
                pygame.K_g: actions.ZOOM_OUT,
                pygame.K_ESCAPE: actions.QUIT,
                pygame.K_F8: actions.SAVE,
                pygame.K_F9: actions.LOAD,
                pygame.K_PAUSE: actions.TOGGLE_PAUSE,
                pygame.K_BACKQUOTE: actions.STEP,
                pygame.K_F11: actions.SHOW_KEYS,
                pygame.K_F12: actions.TOGGLE_INPUT
            },

            # Joystick (button) controls.
            joystick_actions = {
                4: actions.ROTATE_CLOCKWISE,
                5: actions.ROTATE_ANTICLOCKWISE,
            },

            # Mouse controls.
            mouse_actions = {
                1: actions.SHOOT,
                4: actions.ZOOM_IN,
                5: actions.ZOOM_OUT,
            },

            # Mouse motion.
            mouse_motion_actions = {
                1: actions.SHOOT
            }
        )


class InputContextMenu(InputContext):
    """ GUI interaction context. """
    pass

    def __init__(self, actions):
        InputContext.__init__(
            self,
            actions,
            keyboard_actions = {
                pygame.K_PAUSE: actions.TOGGLE_PAUSE,
                pygame.K_BACKQUOTE: actions.STEP,
                pygame.K_F11: actions.SHOW_KEYS,
                pygame.K_F12: actions.TOGGLE_INPUT
            }
        )


class GUIElement(object):
    """ State and logic for a chunk of GUI. """

    def __init__(self, game_services, actions, view):
        """ Constructor. """
        self.game_services = game_services
        self.actions = actions
        self.view = view

    def process(self, nkpygame):
        """ Define the structure and behaviour of the GUI. """
        pass

    def tree_push(self, ctx, tree_type, title, state, number=0):
        """ The 'nk_tree_push' macro generates a unique ID for your tree based on the
        current line number and file name.  But in Python we don't have the C preprocessor,
        but we can get this information by inspecting the call stack. """
        # See https://stackoverflow.com/questions/6810999/how-to-determine-file-function-and-line-number/6811020
        callerframerecord = inspect.stack()[1]
        frame = callerframerecord[0]
        info = inspect.getframeinfo(frame)
        string = info.filename + str(info.lineno)
        return pynk.lib.nk_tree_push_hashed(ctx, tree_type, title, state, string, len(string), number)

    @property
    def always_visible(self):
        """ Should the element always be shown even if not in GUI context? """
        return False


class GUIElementDebugInfo(GUIElement):
    """ A debug output area. """

    def process(self, nkpygame):
        """ Display the debug info. """

        ret = InputResponse()

        if self.game_services.debug_level <= 0:
            return ret

        game_info = self.game_services.get_info()

        average_fps = sum(game_info.framerates) / (len(game_info.framerates)+1)

        rect = pynk.lib.nk_rect(10, 60, 200, 260)
        wflags = pynk.lib.NK_WINDOW_MOVABLE | pynk.lib.NK_WINDOW_TITLE
        if pynk.lib.nk_begin(nkpygame.ctx, "Debug Info", rect, wflags):
            pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 2)
            pynk.lib.nk_label(nkpygame.ctx, "FPS (average)", pynk.lib.NK_TEXT_LEFT)
            pynk.lib.nk_label(nkpygame.ctx, "%.2f" % average_fps, pynk.lib.NK_TEXT_RIGHT)
            pynk.lib.nk_label(nkpygame.ctx, "FPS (limited)", pynk.lib.NK_TEXT_LEFT)
            pynk.lib.nk_label(nkpygame.ctx, "%.2f" % game_info.framerate, pynk.lib.NK_TEXT_RIGHT)
            pynk.lib.nk_label(nkpygame.ctx, "FPS (raw)", pynk.lib.NK_TEXT_LEFT)
            pynk.lib.nk_label(nkpygame.ctx, "%.2f" % game_info.raw_framerate, pynk.lib.NK_TEXT_RIGHT)
            pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 100, 1)
            pynk.lib.nk_chart_begin(nkpygame.ctx, pynk.lib.NK_CHART_LINES, len(game_info.framerates), 0, 60)
            for value in game_info.framerates:
                pynk.lib.nk_chart_push(nkpygame.ctx, value)
            pynk.lib.nk_chart_end(nkpygame.ctx)
        pynk.lib.nk_end(nkpygame.ctx)
        return ret

    @property
    def always_visible(self):
        """ The debug info should always be visible when switched on. """
        return True


class GUIElementMenu(GUIElement):
    """ A menu for the game. """

    def process(self, nkpygame):
        """ Display a menu bar. """
        ret = InputResponse()
        rect = pynk.lib.nk_rect(10, 10, 60, 35)
        if pynk.lib.nk_begin(nkpygame.ctx, "Menu Bar", rect, pynk.lib.NK_WINDOW_NO_SCROLLBAR):
            pynk.lib.nk_menubar_begin(nkpygame.ctx)
            pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 1)
            if pynk.lib.nk_menu_begin_label(nkpygame.ctx, "Menu", pynk.lib.NK_TEXT_LEFT, pynk.lib.nk_vec2(120, 200)):
                pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 1)
                flag = pynk.ffi.new("int*", self.game_services.debug_level)
                pynk.lib.nk_checkbox_label(nkpygame.ctx, "Debug Mode", flag);
                self.game_services.debug_level = flag[0]

                pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 1)
                if pynk.lib.nk_menu_item_label(nkpygame.ctx, "Quit", pynk.lib.NK_TEXT_LEFT):
                    ret = self.actions.QUIT.execute(True)

                pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 1)
                if pynk.lib.nk_menu_item_label(nkpygame.ctx, "Hide GUI", pynk.lib.NK_TEXT_LEFT):
                    ret = self.actions.TOGGLE_INPUT.execute(True)
                pynk.lib.nk_menu_end(nkpygame.ctx)

        pynk.lib.nk_end(nkpygame.ctx)
        return ret


class GUIElementInfoTooltip(GUIElement):
    """ An info tooltip for entities. """

    def __init__(self, game_services, actions, view):
        """ Constructor. """
        GUIElement.__init__(self, game_services, actions, view)
        self.entity = None
        self.tt_rect = None

    def process(self, nkpygame):
        """ Display the tooltip. """

        ret = InputResponse()

        if self.game_services.debug_level <= 0:
            return ret

        # Get the mouse position and find the entity we're hovering over, if
        # any.
        ecs = self.game_services.get_entity_manager()
        physics = ecs.get_system(Physics)
        screen_pos = pygame.mouse.get_pos()
        world_pos = self.view.screen_to_world(screen_pos)
        entity = physics.get_entity_at(world_pos)

        # If the mouse is interacting with the tooltip, we don't want to change
        # the tooltip.  Otherwise, we can update the tooltip.
        padding = 5
        outside_tooltip = self.tt_rect is None or \
                         (screen_pos[0]+padding < self.tt_rect.x or
                          screen_pos[0]-padding > self.tt_rect.x+self.tt_rect.w or
                          screen_pos[1]+padding < self.tt_rect.y or
                          screen_pos[1]-padding > self.tt_rect.x+self.tt_rect.h)
        if outside_tooltip:
            self.entity = entity
            if entity is None:
                self.tt_rect = None
            else:
                vw, vh = self.view.size
                w, h = (400, 350)
                x, y = screen_pos
                if x+w > vw:
                    x = vw-w
                if y+h > vh:
                    y = vh-h
                self.tt_rect = pynk.lib.nk_rect(x, y, w, h)

        # Define the tooltip.
        if self.entity is not None:
            if pynk.lib.nk_begin(nkpygame.ctx, "Entity Info", self.tt_rect, pynk.lib.NK_WINDOW_TITLE):
                title = self.entity.name + " (%s)" % self.entity.id
                pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 1);
                pynk.lib.nk_label(nkpygame.ctx, title, pynk.lib.NK_TEXT_LEFT)
                components = ecs.get_all_components(self.entity)
                for i, component in enumerate(components):
                    name = component.__class__.__name__
                    if self.tree_push(nkpygame.ctx, pynk.lib.NK_TREE_TAB, name, pynk.lib.NK_MAXIMIZED, i):
                        keys = filter(lambda x: not "__" in x, component.__dict__.keys())
                        if isinstance(component, AnimationComponent):
                            keys.append("anim")
                        for key in keys:
                            value = getattr(component, key)
                            if isinstance(value, EntityRef):
                                pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 2);
                                pynk.lib.nk_label(nkpygame.ctx, key, pynk.lib.NK_TEXT_LEFT)
                                if value.entity is not None:
                                    outstr = "%s (%s)" % (value.entity.name, value.entity.id)
                                    if pynk.lib.nk_button_label(nkpygame.ctx, outstr):
                                        self.entity = value.entity
                                else:
                                    pynk.lib.nk_label(nkpygame.ctx, "None", pynk.lib.NK_TEXT_RIGHT)
                            elif isinstance(value, EntityRefList):
                                if self.tree_push(nkpygame.ctx, pynk.lib.NK_TREE_TAB, key, pynk.lib.NK_MINIMIZED):
                                    pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 1);
                                    for ent in value:
                                        outstr = "%s (%s)" % (ent.name, ent.id)
                                        if pynk.lib.nk_button_label(nkpygame.ctx, outstr):
                                            self.entity = ent
                                    pynk.lib.nk_tree_pop(nkpygame.ctx)

                            else:
                                pynk.lib.nk_layout_row_dynamic(nkpygame.ctx, 0, 2);
                                pynk.lib.nk_label(nkpygame.ctx, key, pynk.lib.NK_TEXT_LEFT)
                                value_str = ""
                                if isinstance(value, Timer):
                                    value_str = "%.2f/%.2f" % (value.timer, value.period)
                                elif isinstance(value, Animation):
                                    value_str = "%.2f/%.2f" % (value.timer.timer, value.timer.period)
                                elif isinstance(value, Vec2d):
                                    value_str = "%.2f, %.2f" % (value.x, value.y)
                                else:
                                    value_str = str(value)
                                pynk.lib.nk_label(nkpygame.ctx, value_str, pynk.lib.NK_TEXT_RIGHT)
                        pynk.lib.nk_tree_pop(nkpygame.ctx)
            pynk.lib.nk_end(nkpygame.ctx)

        return ret


class InputHandling(object):
    """ Handles input. """

    def __init__(self, view, game_services):
        """ Initialise. """

        # Provides access to the bits of the game we want to manipulate.
        self.game_services = game_services

        # The view.
        self.__view = view

        # Initialse pygame's joystick functionality
        pygame.joystick.init()
        self.js = None
        if pygame.joystick.get_count() > 0:
            self.js = pygame.joystick.Joystick(0)
            self.js.init()

        # The actions table.
        self.__actions = Actions(self)

        # Input contexts
        self.__in_menu = False
        self.__ctx_flight = InputContextFlight(self.__actions)
        self.__ctx_menu = InputContextMenu(self.__actions)

        # GUI
        self.__gui_elements = [
            GUIElementMenu(self.game_services, self.__actions, self.__view),
            GUIElementInfoTooltip(self.game_services, self.__actions, self.__view),
            GUIElementDebugInfo(self.game_services, self.__actions, self.__view)
        ]

        self.__zoom_increment = 0.03

        self.__shooting = False

    def print_keybindings(self):
        """ Output the keybindings. """
        print "Flight"
        print "======"
        self.__ctx_flight.print_keybindings()
        print "Menu"
        print "===="
        self.__ctx_menu.print_keybindings()

    def handle_input(self, e):
        """ Dispatch a pygame input event to the relevant key mapping table
         and return the response. """
        ctx = self.__ctx_flight if not self.__in_menu else self.__ctx_menu
        return ctx.handle_input(e)

    def handle_gui_input(self, nkpygame):
        """ Show the GUI. """
        for element in self.__gui_elements:
            if self.__in_menu or element.always_visible:
                element.process(nkpygame)

    def toggle_input(self):
        """ Toggle the input mode. """
        self.__in_menu = not self.__in_menu

    def zoom_in(self):
        """ Zoom the camera in."""
        cameras = self.game_services.get_entity_manager().query(Camera)
        for camera in cameras:
            camera.get_component(Camera).zoom += self.__zoom_increment

    def zoom_out(self):
        """ Zoom the camera out. """
        cameras = self.game_services.get_entity_manager().query(Camera)
        for camera in cameras:
            c = camera.get_component(Camera)
            c.zoom -= self.__zoom_increment
            if c.zoom <= self.__zoom_increment:
                c.zoom = self.__zoom_increment


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

    def start_shooting(self, point):
        """ Start shooting at a given point. """
        self.__shooting = True
        players = self.game_services.get_entity_manager().query(Player)
        for player in players:
            at = DirectionProviderScreen(point, player, self.__view)
            turrets = player.get_component(Turrets)
            for turret_ent in turrets.turrets:
                turret = turret_ent.get_component(Turret)
                turret.shooting_at = at

    def stop_shooting(self):
        """ Stop shooting. """
        self.__shooting = False
        players = self.game_services.get_entity_manager().query(Player)
        for player in players:
            turrets = player.get_component(Turrets)
            for turret_ent in turrets.turrets:
                turret = turret_ent.get_component(Turret)
                turret.shooting_at = None

    def maintain_aim(self, point):
        """ Keep aiming at the given point. """
        if self.__shooting:
            self.start_shooting(point)
