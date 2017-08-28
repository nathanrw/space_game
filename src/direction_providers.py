
class DirectionProvider(object):
    """ An object that defines a direction in which to shoot. """

    def __init__(self):
        """ Constructor. """
        pass

    def direction(self):
        """ Get the direction. """
        return Vec2d(0, 0)


class DirectionProviderScreen(object):
    """ Towards a point in screen space. """
    def __init__(self, pos, body_entity, view):
        self.__pos = pos
        self.__view = view
        self.__body_entity = EntityRef(body_entity, Body)
    def direction(self):
        body = self.__body_entity.entity.get_component(Body)
        return (self.__camera.screen_to_world(self.__pos) - body.position).normalized()


class DirectionProviderWorld(object):
    """ Shooting at a point in world space. """
    def __init__(self, pos, body_entity):
        self.__pos = pos
        self.__body_entity = EntityRef(body_entity, Body)
    def direction(self):
        body = self.__body_entity.entity.get_component(Body)
        return (self.__pos - body.position).normalized()


class DirectionProviderDirection(object):
    """ Shooting in a particular direction. """
    def __init__(self, direction):
        self.__direction = direction
    def direction(self):
        return self.__direction


class DirectionProviderBody(object):
    """ Shooting at a body. """
    def __init__(self, from_body_entity, to_body_entity):
        self.__from_body_entity = EntityRef(from_body, Body)
        self.__to_body_entity = EntityRef(to_body, Body)
    def direction(self):
        from_body = self.__from_body_entity.entity.get_component(Body)
        to_body = self.__to_body_entity.entity.get_component(Body)
        return (-to_body.position + from_body.position).normalized()


class DirectionProviderCoaxial(object):
    """ Shooting in line with a body. """
    def __init__(self, from_body_entity):
        self.__from_body_entity = EntityRef(from_body, Body)
    def direction(self):
        from_body = self.__from_body_entity.entity.get_component(Body)
        return Vec2d(0, -1).rotated(math.radians(from_body.orientation))
