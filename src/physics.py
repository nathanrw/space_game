from .ecs import ComponentSystem, Component
from .utils import Vec2d
from .behaviours import Body, Joint

import pymunk
import math


class Physics(ComponentSystem):
    """ Physics system. It's now implemented using pymunk, but that fact should
        not leak out of this file! Entitys that need to be simulated should
        be given Body components which will be managed by a Physics system. """

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

        # Map from body components to pymunk body objects
        self.__pymunk_bodies = {}

        # Map from joint components to pymunk joint objects.
        self.__pymunk_joints = {}

    def add_collision_handler(self, handler):
        """ Add a logical collision handler for the game. """
        self.__collision_handlers.append(handler)

    def update(self, dt):
        """ Advance the simulation. """

        # Ensure bodies are added to the simulation, and that dead bodies are
        # removed from the simulation.
        seen = set(self.__pymunk_bodies.keys())
        for e in self.entities():
            body = e.get_component(Body)
            if not body in seen:
                pymunk_body = PymunkBody(body)
                self.__space.add(pymunk_body.body, pymunk_body.shape)
            else:
                seen.remove(body)
        for body in seen:
            pymunk_body = self.__pymunk_bodies[body]
            self.__space.remove(pymunk_body.body, pymunk_body.shape)
            del self.__pymunk_bodies[body]

        # Apply any updates that have been made to physics components.
        for body_component in self.__pymunk_bodies:
            pymunk_body = self.__pymunk_bodies[body_component]
            pymunk_body.body.position = body_component.position
            pymunk_body.body.velocity = body_component.velocity
            pymunk_body.shape.radius = body_component.size
            pymunk_body.body.mass = body_component.mass
            pymunk_body.body.force = body_component.force
            if body_component.collideable:
                pymunk_body.shape.collision_type = 1
            else:
                pymunk_body.shape.collision_type = 0
            pymunk_body.body.angle = math.radians(body_component.orientation)
            pymunk_body.body.angular_velocity = math.radians(body_component.angular_velocity)

        # Do the same for joints - add joints to the simulation where components
        # have been added, remove them where components have been deleted.
        joints = self.game_services.get_entity_manager().query(Joint)
        for e in joints:
            joint = e.get_component(Joint)
            if joint.entity_a.entity is None or joint.entity_b.entity is None:
                e.kill()
                continue
        seen_joints = set(self.__pymunk_joints.keys())
        joints = self.game_services.get_entity_manager().query(Joint) # some will be dead.
        for e in joints:
            component = e.get_component(Joint)
            b1 = component.entity_a.get_component(Body)
            b2 = component.entity_b.get_component(Body)
            if not e in seen_joints:
                joint = pymunk.constraint.PinJoint(
                    self.__pymunk_bodies[b1].body,
                    self.__pymunk_bodies[b2].body,
                    (0, 0),
                    body.world_to_local(b1.position)
                )
                joint.collide_bodies = False
                self.__pymunk_joints[e] = joint
                self.__space.add(joint)
            else:
                seen_joints.remove(e)
        for e in seen_joints:
            joint = self.__pymunk_joints[e]
            self.__space.remove(joint)
            del self.__pymunk_joints[e]

        # Advance the simulation.
        self.__space.step(dt)

        # Copy simulation state back to components.
        for body_component in self.__pymunk_bodies:
            pymunk_body = self.__pymunk_bodies[body_component]
            body_component.position = pymunk_body.body.position
            body_component.velocity = pymunk_body.body.velocity
            body_component.size = pymunk_body.shape.radius
            body_component.mass = pymunk_body.body.mass
            body_component.force = pymunk_body.body.force
            body_component.collideable = pymunk_body.shape.collision_type == 1
            body_component.orientation = math.degrees(pymunk_body.body.angle)
            body_component.angular_velocity = math.degrees(pymunk_body.body.angular_velocity)

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
        assert False # Use component.
        body = entity.get_component[Body]
        pymunk_body = self.__pymunk_bodies[body]
        return pymunk_body.body.world_to_local(point)

    def local_to_world(self, entity, point):
        assert False # Use component.
        body = entity.get_component[Body]
        pymunk_body = self.__pymunk_bodies[body]
        return pymunk_body.body.local_to_world(point)

    def local_dir_to_world(self, entity, direction):
        assert False # Use component.
        body = entity.get_component[Body]
        pymunk_body = self.__pymunk_bodies[body]
        return pymunk_body.body.local_to_world(direction) - pymunk_body.body.position

    def apply_force_at_local_point(self, entity, force, point):
        """ Apply a force to the body."""
        assert False # Use component.  May need to store moment.
        body = entity.get_component[Body]
        pymunk_body = self.__pymunk_bodies[body]
        pymunk_body.apply_force_at_local_point(force, point)


class PymunkBody(object):
    """ Physical body attached to a entity. """

    def __init__(self, body_component):
        """ Constructor. """

        # Store the entity.
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

        # Squirell ourself away inside the shape, so we can map back later. Note
        # that we're modifying the shape with a new field on the fly here, which
        # could be seen as a bit hacky, but I think it's fairly legit - it's just
        # as if we were to derive from pymunk.Shape and extend it, just without all
        # the code...
        self.shape.game_body = self


class CollisionResult(object):
    """ The result of a logical collision handler being applied. """
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
