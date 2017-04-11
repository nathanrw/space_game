""" Everything that draws itself on the screen is a drawable. A drawable is
a special kind of component that knows how to draw itself given a surface
and a camera. """

import pygame

from physics import *
from behaviours import Hitpoints, Text, Thrusters

class Drawing(ComponentSystem):
    """ A class that manages a set of things that can draw themselves. """

    def __init__(self):
        ComponentSystem.__init__(self)
        self.background_image = None

    def set_background(self, image_name):
        self.background_image = self.game_services.get_resource_loader().load_image(image_name)

    def draw_background(self, camera):
        if self.background_image is None:
            return
        screen = camera.surface()
        (image_width, image_height) = self.background_image.get_size()
        (screen_width, screen_height) = screen.get_size()
        pos = camera.position
        x = int(pos.x)
        y = int(pos.y)
        start_i = -(x%image_width)
        start_j = -(y%image_width)
        for i in xrange(start_i, screen_width, image_width):
            for j in xrange(start_j, screen_height, image_height):
                screen.blit(self.background_image, (i, j))

    def draw(self, camera):
        """ Draw the drawables in order of layer. """
        self.draw_background(camera)
        self.components = sorted(self.components, lambda x, y: cmp(x.level, y.level))
        for drawable in self.components:
            if not drawable.visible():
                continue
            if not camera.check_bounds_world(drawable.estimate_bounds()):
                continue
            drawable.draw(camera)

class Drawable(Component):
    """ Base class for something that can be drawn. """
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.level = 0
    def manager_type(self):
        return Drawing
    def draw(self, camera):
        pass
    def visible(self):
        return True
    def estimate_bounds(self):
        return None

class DebugInfoDrawable(Drawable):
    """ Draws debug information on the screen. """

    def __init__(self, entity, game_services, config):
        """ Initialise the drawable """
        Drawable.__init__(self, entity, game_services, config)
        self.__font = game_services.get_resource_loader().load_font("res/fonts/nasdaqer/NASDAQER.ttf", 12)

    def draw_graph(self, values, maximum, position, size, camera):
        """ Draw a graph from a list of values. """
        points = []
        for i, value in enumerate(values):
            x = position[0] + size[0] * (float(i)/(len(values)))
            y = position[1] + size[1] - size[1] * (value/float(maximum))
            points.append((x, y))
        if len(points) > 2:
            pygame.draw.rect(camera.surface(), (255, 255, 255), pygame.Rect(position, size), 1)
            pygame.draw.lines(camera.surface(), (200,200,200), False, points, 2)

    def draw(self, camera):
        """ Draw the information. """
        game_info = self.game_services.get_info()
        fps = self.__font.render("FPS (limited): %04.1f" % game_info.framerate, True, (255, 255, 255))
        camera.surface().blit(fps, (10, 10))
        raw_fps = self.__font.render("FPS (raw): %04.1f" % game_info.raw_framerate, True, (255, 255, 255))
        camera.surface().blit(raw_fps, (10, 30))
        self.draw_graph(game_info.framerates, 70, (10, 50), (100, 15), camera)
        time_ratio = self.__font.render("Time scale: %03.1f" % game_info.time_ratio, True, (255, 255, 255))
        camera.surface().blit(time_ratio, (10, 70))

class AnimBodyDrawable(Drawable):
    """ Draws an animation at the position of a body. """

    def __init__(self, entity, game_services, config):
        """ Initialise the drawable """
        Drawable.__init__(self, entity, game_services, config)
        self.anim = game_services.get_resource_loader().load_animation(config["anim_name"])
        self.kill_on_finished = config.get_or_default("kill_on_finish", False)
        self.rect = self.anim.get_max_bounds()

    def update(self, dt):
        """ Update our bounding box and kill timer. """
        if self.anim.tick(dt):
            if self.kill_on_finished:
                self.entity.kill()
            else:
                self.anim.reset()
        self.rect.center = self.get_component(Body).position

    def draw(self, camera):
        """ Draw the body on the screen. """

        # Get the body
        body = self.get_component(Body)
        if body is None:
            return
        
        # Draw the animation.
        self.anim.orientation = -body.orientation
        self.anim.draw(body.position, camera)

        # If this body has thrusters then draw them.
        for thruster in body.thrusters():
            if thruster.on():
                pos = thruster.world_position(body)
                dir = thruster.world_direction(body)
                length = thruster.thrust() / 500.0
                poly = Polygon.make_bullet_polygon(pos, pos-(dir*length))
                poly.draw(camera)

        # If this body has hitpoints draw a health bar
        hitpoints = self.get_component(Hitpoints)
        if hitpoints is None:
            return

        # Draw health bar if it's on screen. Otherwise draw marker.
        rect = pygame.Rect(0, 0, body.size*2, 12)
        rect.center = rect.center = camera.world_to_screen(body.position)
        rect.top = rect.top - (body.size*1.2)
        if camera.check_bounds_screen(rect):
            pygame.draw.rect(camera.surface(), (255, 255, 255), rect)
            rect.inflate_ip(-4, -4)
            pygame.draw.rect(camera.surface(), (255, 0, 0), rect)
            rect.width = int(hitpoints.hp/float(hitpoints.max_hp) * rect.width)
            pygame.draw.rect(camera.surface(), (0, 255, 0), rect)
        else:
            (w, h) = camera.surface().get_size()
            rect.width = 5
            rect.height = 5
            rect.left = max(5, rect.left)
            rect.right = min(w-5, rect.right)
            rect.top = max(5, rect.top)
            rect.bottom = min(h-5, rect.bottom)
            pygame.draw.rect(camera.surface(), (255, 0, 0), rect)

    def estimate_bounds(self):
        """ Return precomputed bounding box. """
        return self.rect

class TextDrawable(Drawable):
    """ Draws text in the middle of the screen. Note that you don't set the text on the
    drawable, it gets stored in a Text component. This means that logic code doesn't need
    to mess with the drawable. """

    def __init__(self, entity, game_services, config):
        """Load the font."""
        Drawable.__init__(self, entity, game_services, config)
        self.__font = game_services.get_resource_loader().load_font(config["font_name"], config["font_size"])
        self.__small_font = game_services.get_resource_loader().load_font(config["font_name"], 14)
        colour_dict = config["font_colour"]
        self.__colour = (colour_dict["red"], colour_dict["green"], colour_dict["blue"])
        self.__text = None
        self.__image = None
        self.__warning = self.__small_font.render("WARNING", True, self.__colour)
        self.__level = 999
        self.__blink = config.get_or_default("blink", 0)
        self.__blink_timer = Timer(config.get_or_default("blink_period", 0.5))
        self.__visible = True
        self.__offs = 0
        self.__scroll_speed = 300
        self.__padding = 20

    def update(self, dt):
        """ Update: support blinking. """
        Drawable.update(self, dt)
        if self.__blink:
            if self.__blink_timer.tick(dt):
                self.__blink_timer.reset()
                self.__visible = not self.__visible

        self.__offs += self.__scroll_speed * dt
        self.__offs = self.__offs % (self.__warning.get_width()+self.__padding)

    def draw_warning(self, camera, forwards, y):
        # Draw scrolling warning
        if self.__blink:
            screen = camera.surface()
            (image_width, image_height) = self.__warning.get_size()
            (screen_width, screen_height) = screen.get_size()
            x = self.__offs
            if not forwards:
                x = -x
            start_i = -(x%(image_width+self.__padding))
            for i in xrange(int(start_i), screen_width, image_width + self.__padding):
                screen.blit(self.__warning, (i, y))
            rect = screen.get_rect()
            rect.height = 5
            rect.bottom = y-5
            pygame.draw.rect(camera.surface(), self.__colour, rect)
            rect.top=y+self.__warning.get_height()+5
            pygame.draw.rect(camera.surface(), self.__colour, rect)

    def draw(self, camera):
        """Draw the text to the screen."""

        # Try to obtain some text to draw.
        text = None
        text_component = self.get_component(Text)
        if text_component is not None:
            text = text_component.text

        # Now cache the rendered text, if the text differs to what we had before. Note
        # that since the text can be null we have to handle that by unsetting the image.
        if self.__text != text:
            self.__image = None
            if text is not None:
                self.__image = self.__font.render(text, True, self.__colour)
            self.__text = text

        # Now draw the cached image, if we have one.
        if self.__visible and self.__image is not None:
            screen = camera.surface()
            pos = Vec2d(screen.get_rect().center) - Vec2d(self.__image.get_size()) / 2
            screen.blit(self.__image, (int(pos.x), int(pos.y)))

        if self.__image is not None:
            screen = camera.surface()
            pos = Vec2d(screen.get_rect().center) - Vec2d(self.__image.get_size()) / 2
            self.draw_warning(camera, True, int(pos.y-self.__warning.get_height()-10))
            self.draw_warning(camera, False, int(pos.y+self.__image.get_height()+10))

class Polygon(object):
    """ A polygon. Used to be used for bullets. """
    @classmethod
    def make_bullet_polygon(klass, a, b):
        perp = (a-b).perpendicular_normal() * (a-b).length * 0.1
        lerp = a + (b - a) * 0.1
        c = lerp + perp
        d = lerp - perp
        return Polygon((a,c,b,d,a))
    def __init__(self, points):
        self.points = [p for p in points]
        self.colour = (255, 255, 255)
    def draw(self, camera):
        transformed = [camera.world_to_screen(x) for x in self.points]
        pygame.draw.polygon(camera.surface(), self.colour, transformed)
