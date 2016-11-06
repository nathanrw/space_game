""" Everything that draws itself on the screen is a drawable. A drawable is
a special kind of component that knows how to draw itself given a surface
and a camera. """

import pygame

from physics import *
from behaviours import Hitpoints, Text

class Drawing(ComponentSystem):
    """ A class that manages a set of things that can draw themselves. """

    def draw(self, camera):
        """ Draw the drawables in order of layer. """
        self.components = sorted(self.components, lambda x, y: cmp(x.level, y.level))
        for drawable in self.components:
            if drawable.visible():
                drawable.draw(camera)

class Drawable(Component):
    """ Base class for something that can be drawn. """
    def __init__(self, game_object, game_services, config):
        Component.__init__(self, game_object, game_services, config)
        self.level = 0
    def manager_type(self):
        return Drawing
    def draw(self, camera):
        pass
    def visible(self):
        return True

class AnimBodyDrawable(Drawable):
    """ Draws an animation at the position of a body. """
    def __init__(self, game_object, game_services, config):
        Drawable.__init__(self, game_object, game_services, config)
        self.anim = game_services.get_resource_loader().load_animation(config["anim_name"])
        self.kill_on_finished = config.get_or_default("kill_on_finish", False)
    def update(self, dt):
        if self.anim.tick(dt):
            if self.kill_on_finished:
                self.game_object.kill()
            else:
                self.anim.reset()
    def draw(self, camera):
        body = self.get_component(Body)
        self.anim.orientation = body.orientation
        self.anim.draw(body.position, camera)

class HealthBarDrawable(Drawable):
    """ Draws a health bar above a body. """
    def __init__(self, game_object, game_services, config):
        Drawable.__init__(self, game_object, game_services, config)
    def draw(self, camera):
        body = self.get_component(Body)
        if body is None:
            return
        hitpoints = self.get_component(Hitpoints)
        if hitpoints is None:
            return
        rect = pygame.Rect(0, 0, body.size*2, 6)
        rect.center = camera.world_to_screen(body.position)
        rect.top = rect.top - (body.size + 10)
        pygame.draw.rect(camera.surface(), (255, 0, 0), rect)
        rect.width = int(hitpoints.hp/float(hitpoints.max_hp) * rect.width)
        pygame.draw.rect(camera.surface(), (0, 255, 0), rect)

class BulletDrawable(Drawable):
    """ A drawable that draws an image aligned with the relative velocity
    of a body to the player """
    def __init__(self, game_object, game_services, config):
        Drawable.__init__(self, game_object, game_services, config)
        self.image = game_services.get_resource_loader().load_image(config["image_name"])
    def draw(self, camera):
        screen = camera.surface()
        player_velocity = Vec2d(0, 0)
        body = self.get_component(Body)
        player_body = self.game_services.get_player().get_component(Body)
        if player_body is not None:
            player_velocity = player_body.velocity
        relative_velocity = body.velocity - player_velocity
        rotation = relative_velocity.get_angle()
        rotated = pygame.transform.rotate(self.image, 90 - rotation + 180)
        pos = camera.world_to_screen(body.position) - Vec2d(rotated.get_rect().center)
        screen.blit(rotated, pos)

class TextDrawable(Drawable):
    """ Draws text in the middle of the screen. Note that you don't set the text on the
    drawable, it gets stored in a Text component. This means that logic code doesn't need
    to mess with the drawable. """

    def __init__(self, game_object, game_services, config):
        """Load the font."""
        Drawable.__init__(self, game_object, game_services, config)
        self.__font = game_services.get_resource_loader().load_font(config["font_name"], config["font_size"])
        colour_dict = config["font_colour"]
        self.__colour = (colour_dict["red"], colour_dict["green"], colour_dict["blue"])
        self.__text = None
        self.__image = None
        self.__level = 999
        self.__blink = config.get_or_default("blink", 0)
        self.__blink_timer = Timer(config.get_or_default("blink_period", 0.5))
        self.__visible = True

    def visible(self):
        """ Override to support blinking. """
        return self.__visible

    def update(self, dt):
        """ Update: support blinking. """
        Drawable.update(self, dt)
        if self.__blink:
            if self.__blink_timer.tick(dt):
                self.__blink_timer.reset()
                self.__visible = not self.__visible

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
        if self.__image is not None:
            screen = camera.surface()
            pos = Vec2d(screen.get_rect().center) - Vec2d(self.__image.get_size()) / 2
            screen.blit(self.__image, (int(pos.x), int(pos.y)))

class BackgroundDrawable(Drawable):
    """ A drawable for a scrolling background. """
    def __init__(self, game_object, game_services, config):
        Drawable.__init__(self, game_object, game_services, config)
        self.image = game_services.get_resource_loader().load_image(config["image_name"])
        self.level = -999
    def draw(self, camera):
        screen = camera.surface()
        (image_width, image_height) = self.image.get_size()
        (screen_width, screen_height) = screen.get_size()
        pos = camera.position
        x = int(pos.x)
        y = int(pos.y)
        start_i = -(x%image_width)
        start_j = -(y%image_width)
        for i in xrange(start_i, screen_width, image_width):
            for j in xrange(start_j, screen_height, image_height):
                screen.blit(self.image, (i, j))

class Polygon(object):
    """ A polygon. Used to be used for bullets. """
    @classmethod
    def make_bullet_polygon(a, b):
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
