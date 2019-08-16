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

    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.physics_body = None

    @property
    def mass(self):
        return self.physics_body.body.mass

    @property
    def size(self):
        return self.physics_body.shape.radius

    @property
    def is_collideable(self):
        return self.physics_body.shape.collision_type == 1

    @property
    def position(self):
        return self.physics_body.body.position

    @property
    def velocity(self):
        return self.physics_body.body.velocity

    @property
    def orientation(self):
        return math.degrees(self.physics_body.body.angle)

    @property
    def angular_velocity(self):
        return math.degrees(self.physics_body.body.angular_velocity)


class Tracking(Component):
    """ Tracks something on the opposite team. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.tracked = EntityRef(None, Body)
        self.track_type = config.get("track_type", "team")


class FollowsTracked(Component):
    """ Follows the Tracked entity. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.follow_type = config.get("follow_type", "accelerate")


class Weapon(Component):
    """ The entity is a weapon that e.g. shoots bullets. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.owner = EntityRef(None)
        self.shooting_at = None
        self.shot_timer = 0
        self.weapon_type = self.config.get("type", "projectile_thrower")
        self.impact_point = None
        self.impact_normal = None


class LaunchesFighters(Component):
    """ Launches fighters periodically. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.spawn_timer = Timer(config["spawn_period"])
        self.launched = EntityRefList()


class KillOnTimer(Component):
    """ For objects that should be destroyed after a limited time. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.lifetime = Timer(config["lifetime"])


class ExplodesOnDeath(Component):
    """ For objects that spawn an explosion when they die. """
    pass


class Hitpoints(Component):
    """ Object with hitpoints, can be damaged. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"]


class Power(Component):
    """ The entity stores / produces power. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.capacity = config["capacity"]
        self.power = self.capacity
        self.recharge_rate = config["recharge_rate"]
        self.overloaded = False
        self.overload_timer = Timer(config.get("overload_time", 5))


class Shields(Component):
    """ The entity has shields that protect it from damage. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.hp = self.config["hp"]
        self.max_hp = self.config["hp"] # Rendundant, but code uses this.
        self.recharge_rate = config["recharge_rate"]
        self.overloaded = False
        self.overload_timer = Timer(config.get("overload_time", 5))


class DamageOnContact(Component):
    """ The entity damages other entities on contact. """
    pass


class Team(Component):
    """ The entity is on a team. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.team = config.get("team")
        self.parent = EntityRef(None, Team)


class Text(Component):
    """ The entity contains text. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.text = config.get("text", "Hello, world!")
        self.visible = True
        self.offset = 0
        self.scroll_speed = 300
        self.padding = 20
        self.colour = (255, 255, 255)
        self.font_name = self.config["font_name"]
        self.small_font_size = config.get("small_font_size", 14)
        self.large_font_size = config.get("font_size", 32)
        colour = self.config.get("font_colour", {"red":255, "green":255, "blue":255})
        self.font_colour = (colour["red"], colour["green"], colour["blue"])
        self.blink = self.config.get("blink", 0)
        self.blink_period = self.config.get("blink_period", 1)
        self.blink_timer = Timer(self.blink_period)


class AnimationComponent(Component):
    """ The entity has an animation. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.level = None

    @property
    def anim(self):
        """ Get the anim, loading it if necessary. """
        if not "anim" in self.cache:
            self.cache["anim"] = self.entity.game_services.get_resource_loader().load_animation(self.config["anim_name"])
        return self.cache["anim"]


class Thruster(Component):
    """ The logical definition of a thruster on a Body. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.position = Vec2d(config.get("position", (0, 0)))
        self.direction = Vec2d(config.get("orientation", (0, 1)))
        self.max_thrust = config.get("max_thrust", 0)
        self.thrust = 0
        self.attached_to = EntityRef(None, Thrusters)


class Thrusters(Component):
    """ The entity has thrusters & a target direction. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.direction = Vec2d(0, 0)
        self.turn = 0
        self.thrusters = EntityRefList(Thruster)
        self.thruster_configurations = {}


class Turret(Component):
    """ The entity is a turret affixed to another entity. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.position = Vec2d(0, 0)
        self.attached_to = EntityRef(None, Turrets)
        self.weapon = EntityRef(None, Weapon)
        self.fire_timer = Timer(config.get("fire_period", 1))
        self.fire_timer.advance_to_fraction(0.8)
        self.burst_timer = Timer(config.get("burst_period", 1))
        self.can_shoot = False
        self.shooting_at = None


class Turrets(Component):
    """ The entity has a set of turrets. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.turrets = EntityRefList(Turret)


class Camera(Component):
    """ A camera, which drawing is done in relation to. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        renderer = game_services.get_renderer()
        self.max_shake = 20
        self.damping_factor = 10
        self.shake = 0
        self.vertical_shake = 0
        self.horizontal_shake = 0
        self.tracking = EntityRef(None, Body)
        self.zoom = 0
        self.screen_diagonal = (Vec2d(renderer.screen_size())/2).length


class Player(Component):
    """ An entity with this component is controlled by the player. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.docked_with = EntityRef(None, Dockable)


class CelestialBody(Component):
    """ A celestial sphere. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.name = config.get("name", "Unknown Celestial Body")


class Star(Component):
    """ A star. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        
        
class Planet(Component):
    """ A planet. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)


class Dockable(Component):
    """ A dockable entity. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.title = config.get("title", "Docked")
        self.description = config.get("description", "An object in space.")