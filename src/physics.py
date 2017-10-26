"""
Physics system & related code.

The Physics system manages Body and Joint components. The system maintains a
mapping between objects in a pymunk physics simulation and the logical
components attached to entities (which are what get serialised.) The relevant
data is copied back and forth between the simulation and the game state
periodically to keep them in sync.
"""


from .ecs import ComponentSystem, Component
from .utils import Vec2d
from .components import Body, Joint

import pymunk
import math


class Physics(ComponentSystem):
    """ Physics system. It's now implemented using pymunk, but that fact should
        not leak out of this file! Entitys that need to be simulated should
        be given Body components which will be managed by a Physics system.
        """

    class PymunkBody(object):
        """ The pymunk simulation body / shape that represents a logical (ecs)
        body component.  These aren't exposed outside of the 'Physics' system;
        we maintain a mapping and copy data back and forth as required. Edits to
        the Body component will be forwarded to the pymunk body at the start of
        an update, while the updated simulation will be copied back to the
        components at the end of each update(). """

        def __init__(self, body_component):
            """ Constructor. """

            self.entity = body_component.entity

            # Moment of inertia.
            moment = pymunk.moment_for_circle(
                float(body_component.mass),
                0,
                float(body_component.size)
            )

            # Initialise body and shape.
            self.body = pymunk.Body(float(body_component.mass), moment)
            self.shape = pymunk.Circle(self.body, float(body_component.size))
            self.shape.friction = 0.8

            # Collision type for non-collidable bodies.
            if body_component.is_collideable:
                self.shape.collision_type = 1
            else:
                self.shape.collision_type = 0

            # Squirell ourself away inside the shape, so we can map back
            # later. Note that we're modifying the shape with a new field on
            # the fly here, which could be seen as a bit hacky, but I think
            # it's fairly legit - it's just as if we were to derive from
            # pymunk.Shape and extend it, just without all the code...
            self.shape.game_body = self
        def copy_from_component(self):
            """ Copy body data from components to simulation. """
            body_component = self.entity.get_component(Body)
            pymunk_body = self
            pymunk_body.body.position = body_component.position
            pymunk_body.body.velocity = body_component.velocity
            #pymunk_body.shape.radius = body_component.size
            pymunk_body.body.mass = body_component.mass
            if body_component.is_collideable:
                pymunk_body.shape.collision_type = 1
            else:
                pymunk_body.shape.collision_type = 0
            pymunk_body.body.angle = math.radians(
                body_component.orientation)
            pymunk_body.body.angular_velocity = math.radians(
                body_component.angular_velocity)
            for (force, local_point) in body_component.impulses:
                pymunk_body.body.apply_force_at_local_point(force, local_point)

        def copy_to_component(self):
            """ Copy simulation state back to components """
            body_component = self.entity.get_component(Body)
            pymunk_body = self
            body_component.position = pymunk_body.body.position
            body_component.velocity = pymunk_body.body.velocity
            body_component.size = pymunk_body.shape.radius
            body_component.mass = pymunk_body.body.mass
            body_component.is_collideable = pymunk_body.shape.collision_type == 1
            body_component.orientation = math.degrees(
                pymunk_body.body.angle)
            body_component.angular_velocity = math.degrees(
                pymunk_body.body.angular_velocity)
            body_component.impulses = []

    class PymunkBodyMapping(object):
        """ Manages the mapping between Body components and simulation 
        objects. """

        def __init__(self, space):
            """ Constructor. """
            self.__mapping = {}
            self.__space = space

        def __getitem__(self, item):
            """ Look up a pymunk body from an entity. """
            return self.__mapping[item]

        def update(self, entities):
            """ Update the mapping, creating new simulation bodies where needed
            and deleting ones that we are done with. """

            # The set of entities that need a corresponding simulation
            # object. We remove entities where we see them, and create
            # simulation objects where necessary.
            to_remove = set(self.__mapping.keys())
            for e in entities:
                if e in to_remove:
                    to_remove.remove(e)
                else:
                    body = e.get_component(Body)
                    assert body
                    pymunk_body = Physics.PymunkBody(body)
                    self.__mapping[e] = pymunk_body
                    self.__space.add(pymunk_body.body, pymunk_body.shape)

            # Now, the set contains all of the entities that had simulation
            # bodies but shouldn't any more.
            for e in to_remove:
                pymunk_body = self.__mapping[e]
                self.__space.remove(pymunk_body.body, pymunk_body.shape)
                del self.__mapping[e]

        def copy_from_components(self):
            """ Copy body data from components to simulation. """
            for entity in self.__mapping:
                self.__mapping[entity].copy_from_component()

        def copy_to_components(self):
            """ Copy simulation state back to components """
            for entity in self.__mapping:
                self.__mapping[entity].copy_to_component()

    class PymunkJointMapping(object):
        """ Manages the mapping between Joint components and physical joints
        between physical bodies. """

        def __init__(self, space, pymunk_body_mapping):
            """ Constructor. """
            self.__space = space
            self.__pymunk_bodies = pymunk_body_mapping
            self.__mapping = {}

        def update(self, entities):
            """ Update the mapping. """

            # If a joint no longer has correspond entities, then delete the
            # joint.
            for e in entities:
                joint = e.get_component(Joint)
                if joint.entity_a.entity is None or \
                                joint.entity_b.entity is None:
                    e.kill()
                    entities.remove(e)
                    continue

            # Create simulation joints.
            to_remove = set(self.__mapping.keys())
            for e in entities:
                component = e.get_component(Joint)
                e1 = component.entity_a.entity
                e2 = component.entity_b.entity
                if not e in to_remove:
                    joint = pymunk.constraint.PinJoint(
                        self.__pymunk_bodies[e1].body,
                        self.__pymunk_bodies[e2].body,
                        component.entity_a_local_point,
                        component.entity_b_local_point
                    )
                    joint.collide_bodies = False
                    self.__mapping[e] = joint
                    self.__space.add(joint)
                else:
                    to_remove.remove(e)

            # Delete simulation joints.
            for e in to_remove:
                joint = self.__mapping[e]
                self.__space.remove(joint)
                del self.__mapping[e]

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

        # Map Body and Joint components to simulation objects.
        self.__pymunk_bodies = Physics.PymunkBodyMapping(self.__space)
        self.__pymunk_joints = Physics.PymunkJointMapping(self.__space,
                                                          self.__pymunk_bodies)

    def add_collision_handler(self, handler):
        """ Add a logical collision handler for the game. """
        self.__collision_handlers.append(handler)

    def update(self, dt):
        """ Advance the simulation. """

        # Update the body mapping & copy simulation state from the components.
        self.__pymunk_bodies.update(self.entities())
        self.__pymunk_bodies.copy_from_components()
        self.__pymunk_joints.update(
            self.game_services.get_entity_manager().query(Joint)
        )

        # Advance the simulation.
        self.__space.step(dt)

        # Copy simulation state back to components.
        self.__pymunk_bodies.copy_to_components()

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
        """ Do a hit scan computation. Return the bodies and hit locations of
        entities that intersect the line. Return: [(body, pos)]. """
        body = from_entity.get_component(Body)
        start = body.local_to_world(local_origin)
        end = body.local_to_world(local_direction*distance)
        results = self.__space.segment_query(start, end, radius, pymunk.ShapeFilter())
        for result in results:
            if result.shape.game_body.collideable and filter_func(result.shape.game_body.entity):
                return (result.shape.game_body, result.point, result.normal)
        return (None, end, None)

    def world_to_local(self, entity, point):
        """ Convert a world point to local coordinates. """
        # Note: uses data from component for correctness since might not have
        # been copied to pymunk body yet. But copy to temporary pymunk body to
        # avoid duplicating the code. This is inefficient, we should probably
        # duplicate the logic & enforce its correctness via tests.
        component = entity.get_component(Body)
        if component is not None:
            pb = Physics.PymunkBody(component)
            pb.copy_from_component()
            return pb.body.world_to_local(point)
        else:
            return point

    def local_to_world(self, entity, point):
        """ Convert a local point to world coordinates. """
        # Note: see above.
        component = entity.get_component(Body)
        if component is not None:
            pb = Physics.PymunkBody(component)
            pb.copy_from_component()
            return pb.body.local_to_world(point)
        else:
            return point

    def local_dir_to_world(self, entity, direction):
        """ Convert a local direction to world coordinates. """
        # Note: see above.
        component = entity.get_component(Body)
        if component is not None:
            pb = Physics.PymunkBody(component)
            pb.copy_from_component()
            return pb.body.local_to_world(direction) - pb.body.position
        else:
            return direction

    def apply_force_at_local_point(self, entity, force, point):
        """ Apply a force to the body."""
        component = entity.get_component(Body)
        if component is not None:
            component.impulses.append((force, point))


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
