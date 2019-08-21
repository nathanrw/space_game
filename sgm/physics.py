"""
Physics system & related code.

The Physics system manages Body. The system maintains a
mapping between objects in a pymunk physics simulation and the logical
components attached to entities.
"""


from sge.ecs import ComponentSystem
from sge.utils import Vec2d
from sgm.components import Body

import pymunk
import math


class PhysicsBody(object):
    """ The pymunk simulation body / shape that represents a logical (ecs)
    body component. """

    def __init__(self, entity, definition):
        """ Constructor. """

        self.entity = entity

        # Moment of inertia.
        mass = float(definition.mass)
        size = float(definition.size)
        moment = pymunk.moment_for_circle(mass, 0, size)

        # Initialise body and shape.
        body_type = pymunk.Body.DYNAMIC
        if definition.kinematic:
            body_type = pymunk.Body.KINEMATIC
        self.body = pymunk.Body(mass, moment, body_type)
        self.shape = pymunk.Circle(self.body, size)
        self.shape.friction = 0.8

        # Collision type for non-collidable bodies.
        if definition.is_collideable:
            self.shape.collision_type = 1
        else:
            self.shape.collision_type = 0

        # Squirell ourself away inside the shape, so we can map back
        # later. Note that we're modifying the shape with a new field on
        # the fly here, which could be seen as a bit hacky, but I think
        # it's fairly legit - it's just as if we were to derive from
        # pymunk.Shape and extend it, just without all the code...
        self.body.game_body = self
        self.shape.game_body = self

    @property
    def mass(self):
        return self.body.mass

    @property
    def size(self):
        return self.shape.radius

    @property
    def is_collideable(self):
        return self.shape.collision_type == 1

    @property
    def position(self):
        return self.body.position

    @property
    def velocity(self):
        return self.body.velocity

    @property
    def orientation(self):
        return math.degrees(self.body.angle)

    @property
    def angular_velocity(self):
        return math.degrees(self.body.angular_velocity)


class Physics(ComponentSystem):
    """ Physics system. It's now implemented using pymunk, but that fact should
        not leak out of this file! Entitys that need to be simulated should
        be given Body components which will be managed by a Physics system.
        """

    def __init__(self):
        """ Initialise physics. """
        ComponentSystem.__init__(self, [Body])

        # List of collision handlers. These operate in terms of types of
        # entity. We implement them using a pymunk collision handler.
        self.__collision_handlers = []

        # The pymunk space.
        self.__space = pymunk.Space()

        # Note: the this function assumes we have snuck a reference to our
        # own body into the pymunk shape. Which we have: see Body(). Here
        # we try each handler in turn till we find one that is compatible.
        def collide_begin(arbiter, space, data):
            go1 = arbiter.shapes[0].game_body.entity
            go2 = arbiter.shapes[1].game_body.entity
            for handler in self.__collision_handlers:
                result = handler.handle_collision(go1, go2)
                if result.handled:
                    return result.wants_physical_simulation
            return True

        # Setup our simple pymunk collision handler.
        self.__pymunk_handler = self.__space.add_collision_handler(1, 1)
        self.__pymunk_handler.begin = lambda a, s, d: collide_begin(a, s, d)

        # Setup a default handler for non-collideable objects.
        self.__default_handler = self.__space.add_default_collision_handler()
        self.__default_handler.begin = lambda a, s, d: False

    def add_collision_handler(self, handler):
        """ Add a logical collision handler for the game. """
        self.__collision_handlers.append(handler)

    def __get_physics_body(self, entity):
        """ Get the physics body from an entity"""
        body_component = entity.get_component(Body)
        if not body_component: return None
        if not isinstance(body_component.physics_body, PhysicsBody):
            body_component.physics_body = PhysicsBody(entity, body_component.definition)
        return body_component.physics_body

    def update(self, dt):
        """ Advance the simulation. """

        # Ensure each entity has a physics body associated with it.
        # Note: we don't do this in on_component_add() to give some time
        # for the body to be initialised without causing instability.
        for e in self.entities():
            self.__get_physics_body(e)

        # Advance the simulation.
        self.__space.step(dt)

    def on_component_remove(self, component):
        """ Remove physics representation for dead entities. """
        if isinstance(component.physics_body, PhysicsBody):
            pb = component.physics_body
            self.__space.remove(pb.body, pb.shape)

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
        pqs = self.__space.point_query(point, 5, pymunk.ShapeFilter())
        for pq in pqs:
            if pq.shape is not None:
                body = pq.shape.game_body
                return body.entity
        return None

    def hit_scan(
        self,
        from_entity,
        local_origin=Vec2d(0,0),
        local_direction=Vec2d(0,-1),
        distance=1000,
        radius=1,
        filter_func=lambda x: True
    ):
        """
        Do a hit scan computation. Return the bodies and hit locations of
        entities that intersect the line. Return: [(body, pos)].

        Note: the 'from_entity' will not be hit, *nor will any entity that is
        attached to it by a chain of joints*, nor will non-collideable entities,
        nor will entities for which the given filter function returns false.
        """
        start = self.local_to_world(from_entity, local_origin)
        end = self.local_to_world(from_entity, local_direction*distance)
        results = self.__space.segment_query(start, end, radius, pymunk.ShapeFilter())
        attached = set(self.get_attached_entities(from_entity))
        for result in results:
            hit_entity = result.shape.game_body.entity
            hit_body = hit_entity.get_component(Body)
            assert hit_body is not None
            if hit_entity != from_entity and \
               hit_body.is_collideable and \
               not hit_entity in attached and \
               filter_func(hit_entity):
                return (hit_entity, result.point, result.normal)
        return (None, end, None)

    def world_to_local(self, entity, point):
        """ Convert a world point to local coordinates. """
        pbody = self.__get_physics_body(entity)
        if pbody is not None:
            return pbody.body.world_to_local(point)
        else:
            return point

    def local_to_world(self, entity, point):
        """ Convert a local point to world coordinates. """
        pbody = self.__get_physics_body(entity)
        if pbody is not None:
            return pbody.body.local_to_world(point)
        else:
            return point

    def local_dir_to_world(self, entity, direction):
        """ Convert a local direction to world coordinates. """
        pb = self.__get_physics_body(entity)
        if pb is not None:
            return pb.body.local_to_world(direction) - pb.body.position
        else:
            return direction

    def apply_force_at_local_point(self, entity, force, point):
        """ Apply a force to the body."""
        pbody = self.__get_physics_body(entity)
        if pbody is not None:
            pbody.body.apply_force_at_local_point(force, point)

    def create_joint(self, e0, p0, e1, p1):
        """
        Attach two entities together using a pin joint.
        :param e0: The first entity.
        :param p0: Point on the first entity to pin.
        :param e1: The second entity.
        :param p1: Point on the second entity to pin.
        """
        pb0 = self.__get_physics_body(e0)
        pb1 = self.__get_physics_body(e1)
        joint = pymunk.constraint.PinJoint(pb0.body, pb1.body, p0, p1)
        joint.collide_bodies = False
        self.__space.add(joint)

    def teleport(self, entity, **kwargs):
        """
        Bypass the physics simulation to directly set the position or velocity
        of the physics body corresponding to an entity.

        :param entity: The entity whose body is to be moved.
        :param kwargs: Properties of the body to fiddle.

        The following keyword argument are accepted:

          to_position - New position for body
          to_velocity - New velocity for body
          to_orientation - New orientation for body
          to_angular_velocity - New spin for body
          move_attached - If true, move bodies attached by joints. Defaults to
                          true.
        """
        to_position = kwargs.get("to_position", None)
        to_velocity = kwargs.get("to_velocity", None)
        to_orientation = kwargs.get("to_orientation", None)
        to_angular_velocity = kwargs.get("to_angular_velocity", None)
        move_attached = kwargs.get("move_attached", True)

        # Can only teleport a body!
        body = entity.get_component(Body)
        if body is None:
            return

        # Change in position for attached bodies.
        relative_movement = None
        if to_position is not None:
            relative_movement = to_position - body.position
        relative_rotation = None
        if to_orientation is not None:
            relative_rotation = to_orientation - body.orientation
        relative_delta_v = None
        if to_velocity is not None:
            relative_delta_v = to_velocity - body.velocity
        relative_spin = None
        if to_angular_velocity is not None:
            relative_spin = to_angular_velocity - body.angular_velocity

        # Move each attached entity the same distance and apply the same change
        # in orientation.
        to_move = self.get_attached_entities(entity) if move_attached else [entity]
        for attached_entity in to_move:
            pbb = self.__get_physics_body(attached_entity).body
            pbb.position += relative_movement
            if relative_delta_v is not None:
                pbb.velocity += relative_delta_v
            if relative_rotation is not None:
                pbb.orientation += math.radians(relative_rotation)
            if relative_spin is not None:
                pbb.angular_velocity += math.radians(relative_spin)

    def get_attached_entities(self, entity):
        """
        Get all entities attached by joints to 'entity'.
        """
        seen = set(entity)
        processed = []
        es = [entity]
        while len(es) > 0:
            new = []
            for e0 in es:
                e0_physics_body = self.__get_physics_body(e0)
                e0_pymunk_body = e0_physics_body.body
                cs = e0_pymunk_body.constraints
                for c in cs:
                    e1_pymunk_body = c.a if c.b == e0_pymunk_body else c.b
                    e1_physics_body = e1_pymunk_body.game_body
                    e1 = e1_physics_body.entity
                    if not e1 in seen:
                        seen.add(e1)
                        new.append(e1)
            processed.extend(es)
            es = new
        return processed

    def load(self, state):
        self.__space = state.get("space", self.__space)

    def save(self, state):
        state["space"] = self.__space


class CollisionResult(object):
    """ The result of a logical collision handler being applied. """
    def __init__(self, handled, wants_physical_simulation):
        self.handled = handled
        self.wants_physical_simulation = wants_physical_simulation


class CollisionHandler(object):
    """ A logical collision handler. While physical collision handling is
    dealt with by the physics implementation, game components must be added
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
