from vector2d import Vec2d

class Physics(object):

    def __init__(self):
        self.bodies = []
        self.collision_handlers = []

    def add_body(self, body):
        self.bodies.append(body)

    def add_collision_handler(self, handler):
        self.collision_handlers.append(handler)

    def update(self, dt):
        self.bodies = [x for x in self.bodies if not x.is_garbage()]
        for body in self.bodies:
            body.update(dt)
        self.__handle_collisions()

    def closest_body_of_type(self, point, t):
        bodies_of_type = filter(lambda x: isinstance(x.game_object, t), self.bodies)
        best_yet = None
        best_length_yet = None
        for b in bodies_of_type:
            length = (b.position - point).length
            if not best_yet or length < best_length_yet:
                best_yet = b
                best_length_yet = length
        return best_yet

    def __handle_collisions(self):
        bodies = filter(lambda x: x.collideable, self.bodies)
        collisions = []
        for b1 in bodies:
            for b2 in bodies:
                if b1 == b2:                  continue
                if (b2, b1) in collisions:    continue
                if b1.collides_with(b2):      collisions.append((b1, b2))
        for (b1, b2) in collisions:
            self.__handle_collision(b1, b2)

    def __handle_collision(self, b1, b2):
        b1.handle_collision(b2)
        for handler in self.collision_handlers:
            handler.handle_collision(b1.game_object, b2.game_object)

class Body(object):
    def __init__(self, game_object):
        self.position = Vec2d(0, 0)
        self.velocity = Vec2d(0, 0)
        self.orientation = 0
        self.angular_velocity = 0
        self.size = 5
        self.mass = 1.0
        self.collideable = True
        self.game_object = game_object
    def is_garbage(self):
        return self.game_object.is_garbage
    def update(self, dt):
        self.position += self.velocity * dt
        self.orientation += self.angular_velocity * dt
    def collides_with(self, that):
        return (self.position - that.position).length < self.size + that.size
    def handle_collision(self, that):
        pass

class CollisionHandler(object):
    def __init__(self, t1, t2):
        self.t1 = t1
        self.t2 = t2
    def handle_collision(self, o1, o2):
        if (isinstance(o1, self.t1) and isinstance(o2, self.t2)):
            self.handle_matching_collision(o1, o2)
        elif (isinstance(o2, self.t1) and isinstance(o1, self.t2)):
            self.handle_matching_collision(o2, o1)
    def handle_matching_collision(self, o1, o2):
        pass
