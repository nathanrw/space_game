"""
Types of component that can be attached to entities.

A component is just a blob of data. It is like a table in a database. It tags
an entity with a particular aspect, and the state necessary to implement it.
The actual behaviour bestowed by a component is produced by a processing
system, which operates on a query on the full set of entities selecting for a
particular set of component types.

There is generally a 1-1 mapping between components and processing systems,
but this isn't a hard and fast rule - a single system can require multiple
component types, for instance.

Entity relationships are ad hoc. The general pattern is that a 1-1 relationship
is an 'EntityRef' field in a component. A 1-many relationship is a list of
'EntityRef's in the container and a corresponding back-reference 'EntityRef' in
each of the 'contained' components. The semantics of these relationships are
governed by the corresponding systems.

A component has two things: a 'config' and a set of fields.  The config contains
static data that will not change for the lifetime of the component.  It is
generally used to initialise the fields of the component.  The fields define the
current state of the component, and these are updated by processing systems.
"""

import math

from sge.ecs import Component, EntityRef, EntityRefList
from sge.utils import Timer, Vec2d


class Body(Component):
    """ A physical body. """

    class TemporaryPhysicsBody(object):
        def __init__(self):
            self.mass = 0
            self.size = 0
            self.is_collideable = False
            self.position = Vec2d(0, 0)
            self.velocity = Vec2d(0, 0)
            self.orientation = 0
            self.angular_velocity = 0

    def __init__(self, entity):
        Component.__init__(self, entity)
        self.physics_body = Body.TemporaryPhysicsBody()

        # todo: add setters

    @property
    def mass(self):
        return self.physics_body.mass

    @property
    def size(self):
        return self.physics_body.size

    @property
    def is_collideable(self):
        return self.physics_body.is_collideable

    @property
    def position(self):
        return self.physics_body.position

    @property
    def velocity(self):
        return self.physics_body.velocity

    @property
    def orientation(self):
        return self.physics_body.orientation

    @property
    def angular_velocity(self):
        return self.physics_body.angular_velocity


class Tracking(Component):
    """ Tracks something on the opposite team. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.tracked = EntityRef(None, Body)
        self.track_type = "team"


class FollowsTracked(Component):
    """ Follows the Tracked entity. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.follow_type = "accelerate"
        self.desired_distance_to_player = 0
        self.acceleration = 0


class Weapon(Component):
    """ The entity is a weapon that e.g. shoots bullets. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.owner = EntityRef(None)
        self.shooting_at = None
        self.shot_timer = 0
        self.weapon_type = "projectile_thrower"

        # guns only:
        self.shots_per_second = 0
        self.bullet_speed = 0
        self.bullet_spread = 0
        self.shot_sound = None
        self.bullet_template = None

        # beams only:
        self.impact_point = None
        self.impact_normal = None
        self.power_usage = 0
        self.range = 0
        self.radius = 0
        self.damage = 0


class LaunchesFighters(Component):
    """ Launches fighters periodically. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.__spawn_timer = None
        self.launched = EntityRefList()
        self.__spawn_period = 0
        self.num_fighters = 0
        self.takeoff_spread = 0
        self.fighter_template = None

    @property
    def spawn_timer(self):
        return self.__spawn_timer

    @property
    def spawn_period(self):
        return self.__spawn_period

    @spawn_period.setter
    def spawn_period(self, spawn_period):
        self.__spawn_period = spawn_period
        self.__spawn_timer = Timer(spawn_period)


class KillOnTimer(Component):
    """ For objects that should be destroyed after a limited time. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.__lifetimer = Timer(0)

    @property
    def lifetime(self):
        return self.__lifetimer.period

    @lifetime.setter
    def lifetime(self, time):
        self.__lifetimer = Timer(time)


class ExplodesOnDeath(Component):
    """ For objects that spawn an explosion when they die. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.explosion_template = None
        self.shake_factor = 1
        self.sound = None


class Hitpoints(Component):
    """ Object with hitpoints, can be damaged. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.__hp = 0
        self.max_hp = 0

    @property
    def hp(self):
        return self.__hp

    @hp.setter
    def hp(self, hp):
        self.__hp = hp
        self.max_hp = max(self.max_hp, hp)


class Power(Component):
    """ The entity stores / produces power. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.capacity = 0
        self.power = self.capacity
        self.recharge_rate = 0
        self.overloaded = False
        self.overload_time = 5
        self.overload_timer = Timer(self.overload_time)


class Shields(Component):
    """ The entity has shields that protect it from damage. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.__hp = 0
        self.max_hp = 0
        self.recharge_rate = 0
        self.overloaded = False
        self.overload_time = 5
        self.overload_timer = Timer(self.overload_time)

    @property
    def hp(self):
        return self.__hp

    @hp.setter
    def hp(self, hp):
        self.__hp = hp
        self.max_hp = max(self.max_hp, hp)


class DamageOnContact(Component):
    """ The entity damages other entities on contact. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.destroy_on_hit = True
        self.damage = 0


class Team(Component):
    """ The entity is on a team. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.team = None
        self.parent = EntityRef(None, Team)


class Text(Component):
    """ The entity contains text. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.text = "Hello, world!"
        self.visible = True
        self.offset = 0
        self.scroll_speed = 300
        self.padding = 20
        self.colour = (255, 255, 255)
        self.font_name = "nasdaqer"
        self.small_font_size = 14
        self.large_font_size = 32
        self.font_colour = (255, 255, 255)
        self.blink = False
        self.__blink_period = 1
        self.blink_timer = Timer(self.blink_period)

    @property
    def blink_period(self):
        return self.__blink_period

    @blink_period.setter
    def blink_period(self, period):
        self.__blink_period = period
        self.blink_timer = Timer(period)


class AnimationComponent(Component):
    """ The entity has an animation. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.level = None
        self.kill_on_finish = False
        self.anim_name = None

    @property
    def anim(self):
        """ Get the anim, loading it if necessary. """
        if not "anim" in self.cache:
            self.cache["anim"] = self.entity.game_services.get_resource_loader().load_animation(self.anim_name)
        return self.cache["anim"]


class Thruster(Component):
    """ The logical definition of a thruster on a Body. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.position = Vec2d(0, 0)
        self.direction = Vec2d(0, 1)
        self.max_thrust = 0
        self.thrust = 0
        self.attached_to = EntityRef(None, Thrusters)


class Thrusters(Component):
    """ The entity has thrusters & a target direction. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.direction = Vec2d(0, 0)
        self.turn = 0
        self.thrusters = EntityRefList(Thruster)
        self.thruster_configurations = {}


class Turret(Component):
    """ The entity is a turret affixed to another entity. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.position = Vec2d(0, 0)
        self.attached_to = EntityRef(None, Turrets)
        self.weapon = EntityRef(None, Weapon)
        self.fire_period = 1
        self.fire_timer = Timer(self.fire_period)
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_period = 1
        self.burst_timer = Timer(self.burst_period)
        self.can_shoot = False
        self.shooting_at = None


class Turrets(Component):
    """ The entity has a set of turrets. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.turrets = EntityRefList(Turret)


class Camera(Component):
    """ A camera, which drawing is done in relation to. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.max_shake = 20
        self.damping_factor = 10
        self.shake = 0
        self.vertical_shake = 0
        self.horizontal_shake = 0
        self.tracking = EntityRef(None, Body)
        self.zoom = 0


class Player(Component):
    """ An entity with this component is controlled by the player. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.docked_with = EntityRef(None, Dockable)


class CelestialBody(Component):
    """ A celestial sphere. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.name = "Unknown celestial body"


class Star(Component):
    """ A star. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        
        
class Planet(Component):
    """ A planet. """
    def __init__(self, entity):
        Component.__init__(self, entity)


class Dockable(Component):
    """ A dockable entity. """
    def __init__(self, entity):
        Component.__init__(self, entity)
        self.title = "Docked"
        self.description = "An object in space"