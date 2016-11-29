from vector2d import Vec2d

from utils import *

import pymunk
import math

def vec2tup(vec):
    """ Convert a vector defining the get operator into a tuple. """
    return (vec[0], vec[1])

class Physics(ComponentSystem):
    """ Physics system. It's now implemented using pymunk, but that fact should
        not leak out of this file! Game objects that need to be simulated should
        be given Body components which will be managed by a Physics system. """

    def __init__(self):
        """ Initialise physics. """
        ComponentSystem.__init__(self)
        
        # List of collision handlers. These operate in terms of types of
        # game object. We implement them using a pymunk collision handler.
        self.collision_handlers = []

        # The pymunk space.
        self.space = pymunk.Space()

        # Note: the this function assumes we have snuck a reference to our
        # own body into the pymunk shape. Which we have: see Body(). Here
        # we try each handler in turn till we find one that is compatible.
        def collide_begin(arbiter, space, data):
            go1 = arbiter.shapes[0].game_body.game_object
            go2 = arbiter.shapes[1].game_body.game_object
            for handler in self.collision_handlers:
                if handler.handle_collision(go1, go2):
                    return handler.wants_physical_simulation()
            return True

        # Setup our simple pymunk collision handler.
        self.pymunk_handler = self.space.add_collision_handler(1, 1)
        self.pymunk_handler.begin = lambda a, s, d: collide_begin(a, s, d)

        # Setup a default handler for non-collideable objects.
        self.default_handler = self.space.add_default_collision_handler()
        self.default_handler.begin = lambda a, s, d: False

    def create_queued_component(self, body):
        """ Add a body to the simulation, initialising it. """
        body.create(self.space)
        ComponentSystem.create_queued_component(self, body)

    def add_body(self, body):
        """ As above. """
        self.add_component(self, body)

    def remove_component(self, body):
        """ Remove a body from the simulation, deinitialising it. """
        ComponentSystem.remove_component(self, body)
        body.destroy()

    def remove_body(self, body):
        """ As above. """
        self.remove_component(self, body)

    def add_collision_handler(self, handler):
        """ Add a logical collision handler for the game. """
        self.collision_handlers.append(handler)

    def update(self, dt):
        """ Advance the simulation. """
        ComponentSystem.update(self, dt)
        self.space.step(dt)

    def closest_body_with(self, point, f):
        """ Find the closest body of a given predicate. """
        bodies = filter(f, self.components)
        best_yet = None
        best_length_yet = None
        for b in bodies:
            length = (b.position - point).length
            if not best_yet or length < best_length_yet:
                best_yet = b
                best_length_yet = length
        return best_yet

class Body(Component):
    """ Physical body attached to a game object. Note that it's implemented
    in terms of pymunk now. It will need to change since we're currently
    using pymunk in a pretty horrendous way: this was to preserve the original
    interface while integrating pymunk. But we should stop mucking around with
    position / velocity / size (!) and use forces instead. """
    
    def __init__(self, game_object, game_services, config):
        """ Initialise the body, attached to the given game object. """

        Component.__init__(self, game_object, game_services, config)
        self.__position = Vec2d(0, 0)
        self.__velocity = Vec2d(0, 0)
        self.__angle_radians = 0
        self.__size = config.get_or_default("size", 5)
        self.__mass = config.get_or_default("mass", 1)
        self.__collideable = config.get_or_default("is_collideable", True)
        self.__body = None
        self.shape = None
        self.space = None

    def manager_type(self):
        return Physics

    def create(self, space):
        """ Actually add the body to the simulation. """
        if self.__body is None:
            self.space = space
            moment = pymunk.moment_for_circle(float(self.__mass), 0, float(self.__size))
            self.__body = pymunk.Body(float(self.__mass), moment)
            self.__body.position = vec2tup(self.__position)
            self.__body.velocity = vec2tup(self.__velocity)
            self.__body.angle = self.__angle_radians
            self.shape = pymunk.Circle(self.__body, float(self.__size))
            self.shape.friction = 0.8
            if self.collideable:
                self.shape.collision_type = 1
            else:
                self.shape.collision_type = 0
            self.shape.game_body = self
            self.space.add(self.__body, self.shape)

    def destroy(self):
        """ Remove the body from the simulation. """
        if self.__body is not None:
            self.space.remove(self.__body, self.shape)
            self.__body = None
            self.shape = None

    def world_to_local(self, point):
        if self.__body is not None:
            return Vec2d(self.__body.world_to_local(vec2tup(point)))
        return None

    def local_to_world(self, point):
        if self.__body is not None:
            return Vec2d(self.__body.local_to_world(vec2tup(point)))
        return None

    def local_dir_to_world(self, direction):
        if self.__body is not None:
            return self.local_to_world(direction) - self.position
        return None

    def apply_force_at_local_point(self, force, point):
        """ Apply a force to the body."""
        if self.__body is not None:
            self.__body.apply_force_at_local_point(vec2tup(force), vec2tup(point))

    def pin_to(self, body):
        """ Pin this body to that one. They will become inseparable, and will
        not collide with one another. They will be able to rotate relative to
        one another however. """
        # Note: What is the lifetime of the pin joint? What if both bodies are
        # removed from the space? What if we want to remove the pin joint later?
        # Questions for another day.
        joint = pymunk.constraint.PinJoint(
            self.__body,
            body.__body,
            (0, 0),
            vec2tup(body.world_to_local(self.position))
        )
        joint.collide_bodies = False
        self.space.add(joint)
        
    @property
    def position(self):
        if self.__body is not None:
            return Vec2d(self.__body.position)
        else:
            return self.__position

    @position.setter
    def position(self, value):
        if self.__body is not None:
            self.__body.position = vec2tup(value)
        else:
            self.__position = value

    @property
    def velocity(self):
        if self.__body is not None:
            return Vec2d(self.__body.velocity)
        else:
            return self.__velocity

    @velocity.setter
    def velocity(self, value):
        if self.__body is not None:
            self.__body.velocity = vec2tup(value)
        else:
            self.__velocity = value

    @property
    def size(self):
        if self.shape is not None:
            return self.shape.radius
        else:
            return self.__size

    @size.setter
    def size(self, value):
        if self.shape is not None:
            self.shape.unsafe_set_radius(float(value))
        else:
            self.__size = value

    @property
    def mass(self):
        if self.__body is not None:
            return self.__body.mass
        else:
            return self.__mass

    @mass.setter
    def mass(self, value):
        if self.__body is not None:
            self.__body.mass = float(value)
        else:
            self.__mass = value


    @property
    def force(self):
        """ Note: force gets reset with each tick so no point caching it. """
        if self.__body is not None:
            return Vec2d( self.__body.force )
        else:
            return Vec2d(0, 0)

    @force.setter
    def force(self, value):
        """ Note: force gets reset with each tick so no point caching it. """
        if self.__body is not None:
            self.__body.force = vec2tup(value)

    @property
    def collideable(self):
        return self.__collideable

    @collideable.setter
    def collideable(self, value):
        if value == self.collideable:
            return
        self.__collideable = value
        if self.shape is not None:
            if self.collideable:
                self.shape.collision_type = 1
            else:
                self.shape.collision_type = 0

    @property
    def orientation(self):
        """ Note: Expose degrees because pygame likes degrees. """
        if self.__body is not None:
            return math.degrees(self.__body.angle)
        else:
            return math.degrees(self.__angle_radians)

    @orientation.setter
    def orientation(self, value):
        """ Note: Expose degrees because pygame likes degrees. """
        if self.__body is not None:
            self.__body.angle = math.radians(value)
        else:
            self.__angle_radians = math.radians(value)

    @property
    def angular_velocity(self):
        """ Note: Expose degrees because pygame likes degrees. """
        if self.__body is not None:
            return math.degrees(self.__body.angular_velocity)
        return 0

    @angular_velocity.setter
    def angular_velocity(self, value):
        """ Note: Expose degrees because pygame likes degrees. """
        if self.__body is not None:
            self.__body.angular_velocity = math.radians(value)

class CollisionHandler(object):
    """ A logical collision handler. While physical collision handling is
    dealt with by the physics implementation, game behaviours must be added
    by adding instances of this matching game object types. """
    
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
        if c1 is not None and c2 is not None:
            self.handle_matching_collision(c1, c2)
            return True
        elif c3 is not None and c4 is not None:
            self.handle_matching_collision(c4, c3)
            return True
        return False
    
    def handle_matching_collision(self, c1, c2):
        """ These components are colliding, so the game should do something. """
        pass

    def wants_physical_simulation(self):
        """ If this returns true then physical as well as logical collision
        handling will be applied. """
        return True
