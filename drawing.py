import pygame
import os
import json

from vector2d import Vec2d

from utils import *

def fromwin(path):
    """Paths serialized on windows have \\ in them, so we need to convert
       them in order to read them on unix. Windows will happily read unix
       paths so we dont need to worry about going the other way."""
    return path.replace("\\", "/")

class Drawing(object):
    """ A class that manages a set of things that can draw themselves. """

    def __init__(self):
        self.drawables = []
        self.images = {}
        self.animations = {}
        self.minimise_image_loading = False

    def add_drawable(self, drawable):
        self.drawables.append(drawable)

    def draw(self, camera):
        for drawable in self.drawables:
            drawable.draw(camera)

    def update(self, dt):
        self.drawables = [x for x in self.drawables if not x.is_garbage()]
        for drawable in self.drawables:
            drawable.update(dt)

    def load_image(self, filename):
        filename = fromwin(filename)
        if not filename in self.images:
            self.images[filename] = pygame.image.load(filename).convert_alpha()
            print "Loaded image: %s" % filename
        return self.images[filename]

    def load_animation(self, filename):
        if not filename in self.animations:
            anim = json.load(open(filename))
            name_base = anim["name_base"]
            num_frames = anim["num_frames"]
            extension = anim["extension"]
            period = anim["period"]
            frames = []
            for i in range(num_frames):
                # If we want to load faster disable loading too many anims...
                if self.minimise_image_loading and num_frames > 10 and i % 10 != 0:
                    continue
                padded = (4-len(str(i)))*"0" + str(i)
                img_filename = os.path.join(os.path.dirname(filename), name_base + padded + extension)
                frames.append(self.load_image(img_filename))
            self.animations[filename] = (frames, period)
            print "Loaded animation: %s" % filename
        (frames, period) = self.animations[filename]
        return Animation(frames, period)

class Drawable(object):
    """ Base class for something that can be drawn. """
    def __init__(self, game_object):
        self.game_object = game_object
    def draw(self, camera):
        pass
    def update(self, dt):
        pass
    def is_garbage(self):
        return self.game_object.is_garbage

class AnimBodyDrawable(Drawable):
    """ Draws an animation at the position of a body. """
    def __init__(self, obj, anim, body):
        Drawable.__init__(self, obj)
        self.anim = anim
        self.body = body
        self.kill_on_finished = False
    def update(self, dt):
        if self.anim.tick(dt):
            if self.kill_on_finished:
                self.game_object.kill()
            else:
                self.anim.reset()
    def draw(self, camera):
        self.anim.draw(self.body.position, camera)

class HealthBarDrawable(Drawable):
    """ Draws a health bar above a body. """
    def __init__(self, obj, body):
        Drawable.__init__(self, obj)
        self.body = body
    def draw(self, camera):
        rect = pygame.Rect(0, 0, self.body.size*2, 6)
        rect.center = camera.world_to_screen(self.body.position)
        rect.top = rect.top - (self.body.size + 10)
        pygame.draw.rect(camera.surface(), (255, 0, 0), rect)
        rect.width = int(self.game_object.hp/float(self.game_object.max_hp) * rect.width)
        pygame.draw.rect(camera.surface(), (0, 255, 0), rect)

class BulletDrawable(Drawable):
    """ A drawable that draws an image aligned with the relative velocity
    of a body to the player """
    def __init__(self, bullet, image, body, player_body):
        Drawable.__init__(self, bullet)
        self.image = image
        self.body = body
        self.player_body = player_body
    def draw(self, camera):
        screen = camera.surface()
        relative_velocity = self.body.velocity - self.player_body.velocity
        rotation = relative_velocity.get_angle()
        rotated = pygame.transform.rotate(self.image, 90 - rotation)
        pos = camera.world_to_screen(self.body.position) - Vec2d(rotated.get_rect().center)
        screen.blit(rotated, pos)

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

class Animation(object):
    def __init__(self, frames, period):
        self.frames = frames
        self.timer = Timer(period)
        self.orientation = 0
    def tick(self, dt):
        return self.timer.tick(dt)
    def reset(self):
        self.timer.reset()
    def draw(self, world_pos, camera):
        img = self.frames[self.timer.pick_index(len(self.frames))]
        if (self.orientation != 0):
            img = img = pygame.transform.rotate(img, 90 - self.orientation)
        screen_pos = camera.world_to_screen(world_pos) - Vec2d(img.get_rect().center)
        camera.surface().blit(img, screen_pos)
    def randomise(self):
        self.timer.randomise()
