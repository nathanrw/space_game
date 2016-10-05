from vector2d import Vec2d

import pymunk

def vec2tup(vec):
    """ Convert a vector defining the get operator into a tuple. """
    return (vec[0], vec[1])

class Physics(object):
    """ Physics system. It's now implemented using pymunk, but that fact should
        not leak out of this file!"""

    def __init__(self):
        """ Initialise physics. """

        # List of body components. These encapsulate pymunk bodies/shapes.
        self.bodies = []

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

    def add_body(self, body):
        """ Add a body to the simulation, initialising it. """
        self.bodies.append(body)
        body.create(self.space)

    def remove_body(self, body):
        """ Remove a body from the simulation, deinitialising it. """
        self.bodies.remove(body)
        body.destroy()

    def add_collision_handler(self, handler):
        """ Add a logical collision handler for the game. """
        self.collision_handlers.append(handler)

    def update(self, dt):
        """ Advance the simulation. """
        to_remove = [x for x in self.bodies if x.is_garbage()]
        for b in to_remove:
            self.remove_body(b)
        self.space.step(dt)

    def closest_body_of_type(self, point, t):
        """ Find the closest body of a given type. """
        bodies_of_type = filter(lambda x: isinstance(x.game_object, t), self.bodies)
        best_yet = None
        best_length_yet = None
        for b in bodies_of_type:
            length = (b.position - point).length
            if not best_yet or length < best_length_yet:
                best_yet = b
                best_length_yet = length
        return best_yet

class Body(object):
    """ Physical body attached to a game object. Note that it's implemented
    in terms of pymunk now. It will need to change since we're currently
    using pymunk in a pretty horrendous way: this was to preserve the original
    interface while integrating pymunk. But we should stop mucking around with
    position / velocity / size (!) and use forces instead. """
    
    def __init__(self, game_object):
        """ Initialise the body, attached to the given game object. """
        self.__position = Vec2d(0, 0)
        self.__velocity = Vec2d(0, 0)
        self.__size = 5
        self.__mass = 1.0
        self.__collideable = True
        self.body = None
        self.shape = None
        self.game_object = game_object
        self.space = None

    def create(self, space):
        """ Actually add the body to the simulation. """
        if self.body is None:
            self.space = space
            moment = pymunk.moment_for_circle(self.__mass, 0, self.__size)
            self.body = pymunk.Body(self.__mass, moment)
            self.body.position = vec2tup(self.__position)
            self.body.velocity = vec2tup(self.__velocity)
            self.shape = pymunk.Circle(self.body, self.__size)
            if self.collideable:
                self.shape.collision_type = 1
            else:
                self.shape.collision_type = 0
            self.shape.game_body = self
            self.space.add(self.body, self.shape)

    def destroy(self):
        """ Remove the body from the simulation. """
        if self.body is not None:
            self.space.remove(self.body, self.shape)
            self.body = None
            self.shape = None

    def is_garbage(self):
        """ If a body's corresponding game object has been removed, then
        the body should be removed from the simulation. """
        return self.game_object.is_garbage
        
    @property
    def position(self):
        if self.body is not None:
            return Vec2d(self.body.position)
        else:
            return self.__position

    @position.setter
    def position(self, value):
        if self.body is not None:
            self.body.position = vec2tup(value)
        else:
            self.__position = value

    @property
    def velocity(self):
        if self.body is not None:
            return Vec2d(self.body.velocity)
        else:
            return self.__velocity

    @velocity.setter
    def velocity(self, value):
        if self.body is not None:
            self.body.velocity = vec2tup(value)
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
            self.shape.unsafe_set_radius(value)
        else:
            self.__size = value

    @property
    def mass(self):
        if self.body is not None:
            return self.body.mass
        else:
            return self.__mass

    @mass.setter
    def mass(self, value):
        if self.body is not None:
            self.body.mass = value
        else:
            self.__mass = value

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

    # Note: orientation and angular velocity are not implemented
    # properly yet.
    @property
    def orientation(self): return 0

    @orientation.setter
    def orientation(self, value): pass

    @property
    def angular_velocity(self): return 0

    @angular_velocity.setter
    def angular_velocity(self, value): pass

class CollisionHandler(object):
    """ A logical collision handler. While physical collision handling is
    dealt with by the physics implementation, game behaviours must be added
    by adding instances of this matching game object types. """
    
    def __init__(self, t1, t2):
        """ Initialise with a pair of types. """
        self.t1 = t1
        self.t2 = t2
        
    def handle_collision(self, o1, o2):
        """ Handle type colliding bodies if they are of matching types. """
        if (isinstance(o1, self.t1) and isinstance(o2, self.t2)):
            self.handle_matching_collision(o1, o2)
            return True
        elif (isinstance(o2, self.t1) and isinstance(o1, self.t2)):
            self.handle_matching_collision(o2, o1)
            return True
        return False
    
    def handle_matching_collision(self, o1, o2):
        """ These objects are colliding, so the game should do something. """
        pass

    def wants_physical_simulation(self):
        """ If this returns true then physical as well as logical collision
        handling will be applied. """
        return True
