from .ecs import ComponentSystem, Component
from .utils import Vec2d

import pymunk
import math

import numpy
import scipy.optimize

class Physics(ComponentSystem):
    """ Physics system. It's now implemented using pymunk, but that fact should
        not leak out of this file! Entitys that need to be simulated should
        be given Body components which will be managed by a Physics system. """

    def __init__(self):
        """ Initialise physics. """
        ComponentSystem.__init__(self, [Body])

        # List of collision handlers. These operate in terms of types of
        # entity. We implement them using a pymunk collision handler.
        self.collision_handlers = []

        # The pymunk space.
        self.space = pymunk.Space()

        # Note: the this function assumes we have snuck a reference to our
        # own body into the pymunk shape. Which we have: see Body(). Here
        # we try each handler in turn till we find one that is compatible.
        def collide_begin(arbiter, space, data):
            go1 = arbiter.shapes[0].game_body.entity
            go2 = arbiter.shapes[1].game_body.entity
            for handler in self.collision_handlers:
                result = handler.handle_collision(go1, go2)
                if result.handled:
                    return result.wants_physical_simulation
            return True

        # Setup our simple pymunk collision handler.
        self.pymunk_handler = self.space.add_collision_handler(1, 1)
        self.pymunk_handler.begin = lambda a, s, d: collide_begin(a, s, d)

        # Setup a default handler for non-collideable objects.
        self.default_handler = self.space.add_default_collision_handler()
        self.default_handler.begin = lambda a, s, d: False

    def on_component_add(self, component):
        """ Called when a component is added that matches our expression. """
        assert isinstance(component, Body)
        component.create(self.space)

    def on_component_remove(self, component):
        """ Called when a component is removed that matches our expression. """
        assert isinstance(component, Body)
        component.destroy()

    def add_collision_handler(self, handler):
        """ Add a logical collision handler for the game. """
        self.collision_handlers.append(handler)

    def update(self, dt):
        """ Advance the simulation. """
        ComponentSystem.update(self, dt)
        self.space.step(dt)

    def closest_body_with(self, point, f):
        """ Find the closest body of a given predicate. """
        bodies = filter(f, map(lambda e: e.get_component(Body), self.entities()))
        best_yet = None
        best_length_yet = None
        for b in bodies:
            length = (b.position - point).length
            if not best_yet or length < best_length_yet:
                best_yet = b
                best_length_yet = length
        return best_yet

    def get_entity_at(self, point):
        """ Get the entity at a point. """
        pqs = self.space.point_query(point, 5, pymunk.ShapeFilter())
        for pq in pqs:
            if pq.shape is not None:
                body = pq.shape.game_body
                return body.entity
        return None


class Body(Component):
    """ Physical body attached to a entity. Note that it's implemented
    in terms of pymunk now. It will need to change since we're currently
    using pymunk in a pretty horrendous way: this was to preserve the original
    interface while integrating pymunk. But we should stop mucking around with
    position / velocity / size (!) and use forces instead. """

    def __init__(self, entity, game_services, config):
        """ Initialise the body, attached to the given entity. """

        Component.__init__(self, entity, game_services, config)

        # Moment of inertia.
        moment = pymunk.moment_for_circle(float(config.get_or_default("mass", 1)),
                                          0,
                                          config.get_or_default("size", 5))

        # Initialise body and shape.
        self.__body = pymunk.Body(float(config.get_or_default("mass", 1)), moment)
        self.__shape = pymunk.Circle(self.__body, float(config.get_or_default("size", 5)))
        self.__shape.friction = 0.8

        # Collision type for non-collidable bodies.
        if config.get_or_default("is_collideable", True):
            self.__shape.collision_type = 1
        else:
            self.__shape.collision_type = 0

        # Squirell ourself away inside the shape, so we can map back later. Note
        # that we're modifying the shape with a new field on the fly here, which
        # could be seen as a bit hacky, but I think it's fairly legit - it's just
        # as if we were to derive from pymunk.Shape and extend it, just without all
        # the code...
        self.__shape.game_body = self

        # We will need the space eventually.
        self.__space = None

        # Remember joints
        self.__joints = []

    def setup(self, **kwargs):
        """ Allow an initial position to be specified. """
        if "position" in kwargs:
            self.position = kwargs["position"]
        if "velocity" in kwargs:
            self.velocity = kwargs["velocity"]
            if self.velocity.length > 0:
                self.orientation = self.velocity.normalized().get_angle_degrees()+90
        if "orientation" in kwargs:
            self.orientation = kwargs["orientation"]

    def create(self, space):
        """ Actually add the body to the simulation. """
        if self.__space is None:
            self.__space = space
            self.__space.add(self.__body, self.__shape, *self.__joints)

    def destroy(self):
        """ Remove the body from the simulation. """
        if self.__space is not None:
            self.__space.remove(self.__body, self.__shape, *self.__joints)
            self.__space = None

    def world_to_local(self, point):
        return self.__body.world_to_local(point)

    def local_to_world(self, point):
        return self.__body.local_to_world(point)

    def local_dir_to_world(self, direction):
        return self.local_to_world(direction) - self.position

    def apply_force_at_local_point(self, force, point):
        """ Apply a force to the body."""
        self.__body.apply_force_at_local_point(force, point)

    def pin_to(self, body):
        """ Pin this body to that one. They will become inseparable, and will
        not collide with one another. They will be able to rotate relative to
        one another however. """

        # Setup the joint.
        joint = pymunk.constraint.PinJoint(
            self.__body,
            body.__body,
            (0, 0),
            body.world_to_local(self.position)
        )
        joint.collide_bodies = False

        # Remember the joint so it can be added and removed.
        self.__joints.append(joint)

        # If the body has already been created then add the joint to the simulation.
        if self.__space:
            self.__space.add(joint)

    def hit_scan(self, local_origin=Vec2d(0,0), local_direction=Vec2d(0,-1), distance=1000, radius=1):
        """ Do a hit scan computation. Return the bodies and hit locations of
        entities that intersect the line. Return: [(body, pos)]. """
        start = self.local_to_world(local_origin)
        end = self.local_to_world(local_direction*distance)
        results = self.__space.segment_query(start, end, radius, pymunk.ShapeFilter())
        for result in results:
            if not result.shape.game_body.entity.is_ancestor(self.entity):
                if result.shape.game_body.collideable:
                    return (result.shape.game_body, result.point, result.normal)
        return (None, end, None)
        
    @property
    def position(self):
        return self.__body.position

    @position.setter
    def position(self, value):
        self.__body.position = value

    @property
    def velocity(self):
        return self.__body.velocity

    @velocity.setter
    def velocity(self, value):
        self.__body.velocity = value

    @property
    def size(self):
        return self.__shape.radius

    @property
    def mass(self):
        return self.__body.mass

    @property
    def force(self):
        """ Note: force gets reset with each tick so no point caching it. """
        return self.__body.force

    @force.setter
    def force(self, value):
        """ Note: force gets reset with each tick so no point caching it. """
        self.__body.force = value

    @property
    def collideable(self):
        return self.__shape.collision_type == 1

    @collideable.setter
    def collideable(self, value):
        if value:
            self.__shape.collision_type = 1
        else:
            self.__shape.collision_type = 0

    @property
    def orientation(self):
        """ Note: Expose degrees because pygame likes degrees. """
        return math.degrees(self.__body.angle)

    @orientation.setter
    def orientation(self, value):
        """ Note: Expose degrees because pygame likes degrees. """
        self.__body.angle = math.radians(value)

    @property
    def angular_velocity(self):
        """ Note: Expose degrees because pygame likes degrees. """
        return math.degrees(self.__body.angular_velocity)

    @angular_velocity.setter
    def angular_velocity(self, value):
        """ Note: Expose degrees because pygame likes degrees. """
        self.__body.angular_velocity = math.radians(value)

class CollisionResult(object):
    def __init__(self, handled, wants_physical_simulation):
        self.handled = handled
        self.wants_physical_simulation = wants_physical_simulation

class CollisionHandler(object):
    """ A logical collision handler. While physical collision handling is
    dealt with by the physics implementation, game behaviours must be added
    by adding instances of this matching entity types. """
    
    def __init__(self, t1, t2):
        """ Initialise with a pair of types. """
        self.t1 = t1
        self.t2 = t2
        
    def handle_collision(self, o1, o2):
        """ Handle type colliding bodies if they have components of
        matching types. """
        c1 = o1.get_component(self.t1)
        c2 = o2.get_component(self.t2)
        c3 = o1.get_component(self.t2)
        c4 = o2.get_component(self.t1)
        # Note: behaviour undefined if both objects have both components. Need
        # to sort that out.
        if c1 is not None and c2 is not None:
            return self.handle_matching_collision(c1, c2)
        elif c3 is not None and c4 is not None:
            return self.handle_matching_collision(c4, c3)
        return CollisionResult(False, True)
    
    def handle_matching_collision(self, c1, c2):
        """ These components are colliding, so the game should do something. """
        return CollisionResult(False, True)