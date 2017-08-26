""" Object behaviours for the game and entitys composed out of them.

See utils.py for the overall scheme this fits into.

"""

from .ecs import Component, EntityRef
from .physics import Body, Physics, CollisionHandler, CollisionResult, Thruster
from .renderer import View
from .utils import Timer, Vec2d

import random
import math

class FollowsTracked(Component):
    pass

class Weapons(Component):
    """ An entity with the 'weapons' component manages a set of child entities
    which have the 'weapon' component. """

    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)

        # Weapons.
        self.weapons = []
        self.current_weapon = -1

        # Auto firing.
        self.autofire = config.get_or_default("auto_fire", False)
        self.fire_timer = Timer(config.get_or_default("fire_period", 1))
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_timer = Timer(config.get_or_default("burst_period", 1))
        self.can_shoot = False

        # Initialise the weapons.
        weapons = config.get_or_default("weapons", [])
        for weapon_config in weapons:
            weapon = self.entity.ecs().create_entity(weapon_config, owner=self.entity)
            self.__weapons.append(EntityRef(weapon, Weapon))
        if len(self.weapons) > 0:
            self.current_weapon = 0

    def get_weapon(self):
        """ Get the weapon component of our sub-entity. """
        if self.__current_weapon < 0:
            return None
        return self.__weapons[self.__current_weapon].entity.get_component(Weapon)

    def cycle_weapon(self, amount):
        """ Cycle the selected weapon."""
        if self.__current_weapon < 0:
            return
        was_shooting = self.get_weapon().shooting
        if was_shooting: self.get_weapon().shooting_at = None
        self.__current_weapon = (self.__current_weapon+amount)%len(self.__weapons)
        if was_shooting : self.get_weapon().shooting_at = ShootingAtCoaxial(...)

    def next_weapon(self):
        """ Cycle to the next weapon. """
        self.cycle_weapon(1)

    def prev_weapon(self):
        """ Cycle to the previous weapon. """
        self.cycle_weapon(-1)

class Weapon(Component):
    """ Something that knows how to spray bullets.

    e0 (player)       e1 (weapon)
    ^       ^             ^
    |       |   owner     |
    Body    ------------- Weapon
    ...                   ...
    """

    def __init__(self, entity, game_services, config):
        """ Inject dependencies and set up default parameters. """
        Component.__init__(self, entity, game_services, config)
        self.owner = EntityRef(None)
        self.shooting_at = None
        self.shot_timer = 0
        self.weapon_type = self.config.get_or_default("type", "projectile_thrower")
        self.impact_point = None
        self.impact_normal = None

    def setup(self, **kwargs):
        Component.setup(self, **kwargs)
        if "owner" in kwargs:
            self.owner.entity = kwargs["owner"]

    @property
    def shooting(self):
        return self.shooting_at is not None

class Tracking(Component):
    """ Tracks something on the opposite team. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.tracked = EntityRef(None, Body)

class LaunchesFighters(Component):
    """ Launches fighters periodically. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.spawn_timer = Timer(config["spawn_period"])

class KillOnTimer(Component):
    """ For objects that should be destroyed after a limited time. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.lifetime = Timer(config["lifetime"])

class ExplodesOnDeath(Component):
    """ For objects that spawn an explosion when they die. """
    pass

class EndProgramOnDeath(Component):
    """ If the entity this is attached to is destroyed, the program will exit. """
    pass

class Hitpoints(Component):
    """ Object with hitpoints, can be damaged. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.

class Power(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.capacity = config["capacity"]
        self.power = self.capacity
        self.recharge_rate = config["recharge_rate"]
        self.overloaded = False
        self.overload_timer = Timer(config.get_or_default("overload_time", 5))
    def consume(self, amount):
        if amount <= self.power:
            self.power -= amount
            return amount
        else:
            self.overloaded = True
            return 0

class Shields(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.
        self.recharge_rate = config["recharge_rate"]
        self.overloaded = False
        self.overload_timer = Timer(config.get_or_default("overload_time", 5))

class DamageOnContact(Component):
    pass

class Team(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.team = config.get_or_none("team")
    def setup(self, **kwargs):
        if "team" in kwargs:
            self.__team = kwargs["team"]
    def on_same_team(self, that):
        return self.__team == None or that.__team == None or self.__team == that.__team

class Text(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.text = config.get_or_default("text", "Hello, world!")
        self.blink_timer = Timer(self.blink_period())
        self.visible = True
        self.offs = 0
        self.scroll_speed = 300
        self.padding = 20
        self.image = None
        self.warning = None
        self.colour = (255, 255, 255)
        self.warning = None
        self.image = None
        self.font_name = self.config["font_name"]
        self.small_font_size = config.get_or_default("small_font_size", 14)
        self.large_font_size = config.get_or_default("font_size", 32)
        colour = self.config.get_or_default("font_colour", {"red":255, "green":255, "blue":255})
        self.font_colour = (colour["red"], colour["green"], colour["blue"])
        self.blink = self.config.get_or_default("blink", 0)
        self.blink_period = self.config.get_or_default("blink_period", 1)

    def setup(self, **kwargs):
        Component.setup(self, **kwargs)
        if "text" in kwargs:
            self.__text = kwargs["text"]

class AnimationComponent(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.anim = game_services.get_resource_loader().load_animation(config["anim_name"])

class Thrusters(Component):
    """ Thruster component. This allows an entity with a body to move itself.
    Eventually I intend to have the thrusters be configurable, but for now its
    hard coded."""

    DIR_LEFT = Vec2d(-1, 0)
    DIR_RIGHT = Vec2d(1, 0)
    DIR_BACKWARDS = Vec2d(0, 1)
    DIR_FORWARDS = Vec2d(0, -1)
    TURN_CCW = -1
    TURN_CW = 1

    def __init__(self, entity, game_services, config):
        """ Initialise - set up the enginges. """
        Component.__init__(self, entity, game_services, config)
        self.direction = Vec2d(0, 0)
        self.turn = 0

    def setup(self, **kwargs):
        Component.setup(self, **kwargs)

        # Note: this is hard coded for now, but in future we could specify the
        # thruster layout in the config.
        body = self.entity.get_component(Body)
        body.add_thruster(Thruster(Vec2d(-20, -20), Vec2d( 1,  0), self.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d(-20,  20), Vec2d( 1,  0), self.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d( 20, -20), Vec2d(-1,  0), self.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d( 20,  20), Vec2d(-1,  0), self.config["max_thrust"] / 8))
        body.add_thruster(Thruster(Vec2d(  0, -20), Vec2d( 0,  1), self.config["max_thrust"] / 4))
        body.add_thruster(Thruster(Vec2d(  0,  20), Vec2d( 0, -1), self.config["max_thrust"]    ))

class HardPoint(object):
    """ A slot that can contain a weapon. """

    def __init__(self, position):
        """ Initialise the hardpoint. """
        self.__position = position
        self.__weapon = None

    def set_turret(self, weapon_entity, body_to_add_to):
        """ Set the weapon, freeing any existing weapon. """

        # If there is already a weapon then we need to delete it.
        if self.__weapon is not None:
            self.__weapon.kill()

        # Ok, set the new weapon.
        self.__weapon = weapon_entity

        # If the weapon has been unset, then our work is done.
        if self.__weapon is None:
            return

        # If a new weapon has been added then pin it to our body.
        weapon_body = self.__weapon.get_component(Body)
        point = body_to_add_to.local_to_world(self.__position)
        weapon_body.position = point
        weapon_body.velocity = body_to_add_to.velocity
        weapon_body.pin_to(body_to_add_to)

class Turrets(Component):

    def __init__(self, entity, game_services, config):
        """ Initialise the turrets. """
        Component.__init__(self, entity, game_services, config)
        self.__hardpoints = []
        hardpoints = config.get_or_default("hardpoints", [])
        for hp in hardpoints:
            if not "x" in hp or not "y" in hp:
                continue
            self.__hardpoints.append(HardPoint(Vec2d(hp["x"], hp["y"])))
            weapon_config = "enemies/turret.txt"
            if "weapon_config" in hp:
                weapon_config = hp["weapon_config"]
            self.set_turret(len(self.__hardpoints)-1, weapon_config)

    def num_hardpoints(self):
        """ Get the number of hardpoints. """
        return len(self.__hardpoints)

    def set_turret(self, hardpoint_index, weapon_config_name):
        """ Set the weapon on a hardpoint. Note that the weapon is an actual
        entity, which is set up as a child of the entity this component is
        attached to. It is assumed to have a Body component, which is pinned
        to our own Body."""
        entity = self.entity.ecs().create_entity(weapon_config_name,
                                         parent=self.entity,
                                         team=self.entity.get_component(Team).get_team())
        self.__hardpoints[hardpoint_index].set_turret(entity, self.entity.get_component(Body))

class Camera(Component, View):
    """ A camera, which drawing is done in relation to. """

    def __init__(self, entity, game_services, config):
        """ Initialise the camera. """
        renderer = game_services.get_renderer()
        Component.__init__(self, entity, game_services, config)
        View.__init__(self, renderer)
        self.__position = Vec2d(0, 0)
        self.__max_shake = 20
        self.__damping_factor = 10
        self.__shake = 0
        self.__vertical_shake = 0
        self.__horizontal_shake = 0
        self.__tracking = EntityRef(None, Body)
        self.__zoom = 1
        self.__screen_diagonal = (Vec2d(renderer.screen_size())/2).length

    def track(self, entity):
        """ Make the camera follow a particular entity. """
        self.__tracking.entity = entity

    def apply_shake(self, shake_factor, position):
        """ Apply a screen shake effect. """
        displacement = self.__position - position
        distance = displacement.length
        max_dist = self.__screen_diagonal * 2
        amount = max(shake_factor * (1.0 - distance/max_dist), 0)
        self.__shake = min(self.__shake+amount, self.__max_shake)

    def play_sound(self, body, sound):
        """ Play a sound at a position. """
        sound = self.entity.game_services.get_resource_loader().load_sound(sound)
        sound.play_positional(body.position - self.__position)

    @property
    def position(self):
        """ Get the position of the camera, adjusted for shake. """
        return self.__position + Vec2d(self.__horizontal_shake,
                                       self.__vertical_shake)

    @position.setter
    def position(self, value):
        """ Set the (actual) position of the camera. """
        self.__position = Vec2d(value)

    @property
    def zoom(self):
        """ Get the zoom level. """
        return self.__zoom

    @zoom.setter
    def zoom(self, value):
        """ Set the zoom level. """
        if value > 0:
            self.__zoom = value


class ShootingAt(object):
    """ An object that defines a direction in which to shoot. """
    def __init__(self):
        pass
    def direction(self):
        pass

class ShootingAtScreen(object):
    """ Shooting at a point in screen space. """
    def __init__(self, pos, body, camera):
        self.__pos = pos
        self.__camera = camera
        self.__body = body
    def direction(self):
        return (self.__camera.screen_to_world(self.__pos) - self.__body.position).normalized()

class ShootingAtWorld(object):
    """ Shooting at a point in world space. """
    def __init__(self, pos, body):
        self.__pos = pos
        self.__body = body
    def direction(self):
        return (self.__pos - self.__body.position).normalized()

class ShootingAtDirection(object):
    """ Shooting in a particular direction. """
    def __init__(self, direction):
        self.__direction = direction
    def direction(self):
        return self.__direction

class ShootingAtBody(object):
    """ Shooting at a body. """
    def __init__(self, from_body, to_body):
        self.__from_body = from_body
        self.__to_body = to_body
    def direction(self):
        return (-self.__to_body.position + self.__from_body.position).normalized()

class ShootingAtCoaxial(object):
    """ Shooting in line with a body. """
    def __init__(self, from_body):
        self.__from_body = from_body
    def direction(self):
        return Vec2d(0, -1).rotated(math.radians(self.__from_body.orientation))
