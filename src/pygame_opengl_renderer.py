import pygame
import OpenGL
import OpenGL.GL as GL
import math

from pymunk import Vec2d

from .renderer import *

class Texture(object):
    """ An OpenGL texture. """

    @classmethod
    def from_file(klass, filename):
        """ Create a texture from a file. """
        surface = pygame.image.load(filename).convert_alpha()
        return Texture(surface)

    @classmethod
    def from_surface(klass, surface):
        """ Create a texture from a surface. """
        return Texture(surface)

    def __init__(self, surface):
        """ Constructor. """
        data = pygame.image.tostring(surface, "RGBA", 1)
        self.__width = surface.get_width()
        self.__height = surface.get_height()
        self.__texture = GL.glGenTextures(1)
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.__texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, self.get_width(), self.get_height(),
                        0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, data)
        GL.glDisable(GL.GL_TEXTURE_2D)

    def begin(self):
        """ Set OpenGL state. """
        assert self.__texture is not None
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.__texture)
        GL.glColor3f(1, 1, 1)

    def end(self):
        """ Unset the state. """
        assert self.__texture is not None
        GL.glDisable(GL.GL_TEXTURE_2D)

    def get_width(self):
        """ Get the texture width in pixels. """
        assert self.__texture is not None
        return self.__width

    def get_height(self):
        """ Get the texture height in pixels. """
        assert self.__texture is not None
        return self.__height

    def get_size(self):
        """ Get the texture size in pixels. """
        assert self.__texture is not None
        return (self.__width, self.__height)

    def delete(self):
        """ Free the texture. """
        if self.__texture is not None:
            GL.glDeleteTextures(self.__texture)
            self.__texture = None

    def __del__(self):
        """ Ensure the OpenGL texture gets deleted. """
        self.delete()

class TextureSequence(object):
    """ A sequence of textures. """

    # Note: this is not really a practical implementation, we have lots of
    # large frames per anim so that's lots of textures. It would be good to
    # use a texture atlas or array texture for the frames rather than a
    # texture per frame.

    def __init__(self, filenames):
        """ Constructor. """
        self.__textures = [Texture.from_file(f) for f in filenames]
        self.__bound_texture = None

    def begin(self, timer):
        """ Set the state. """
        assert self.__bound_texture is None
        idx = timer.pick_index(len(self.__textures))
        self.__bound_texture = self.__textures[idx]
        self.__bound_texture.begin()

    def end(self):
        """ Unset the state. """
        assert self.__bound_texture is not None
        self.__bound_texture.end()
        self.__bound_texture = None

    def get_width(self):
        """ The texture width. """
        return self.__textures[0].get_width()

    def get_height(self):
        """ The texture height. """
        return self.__textures[0].get_height()

    def get_frame(self, timer):
        """ Get a frame from a timer. """
        idx = timer.pick_index(len(self.__textures))
        return self.__textures[idx]

class PygameOpenGLRenderer(Renderer):
    """ A pygame software renderer. """

    def __init__(self):
        """ Constructor. """
        Renderer.__init__(self)
        self.__surface = None

    def initialise(self, screen_size):
        """ Initialise the pygame display. """
        self.__surface = pygame.display.set_mode(screen_size, pygame.DOUBLEBUF|pygame.OPENGL)
        GL.glViewport(0, 0, self.__surface.get_width(), self.__surface.get_height())
        GL.glMatrixMode(GL.GL_PROJECTION)
        GL.glLoadIdentity()
        GL.glOrtho(0, self.__surface.get_width(), self.__surface.get_height(), 0, 0, 1)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

    def flip_buffers(self):
        """ Update the pygame display. """
        pygame.display.flip()

    def load_compatible_image(self, filename):
        """ Load a pygame image. """
        return Texture.from_file(filename)

    def load_compatible_anim_frames(self, filename_list):
        """ Load the frames of an animation into a format compatible
        with the renderer.  The implementation can return its own
        image representation; the client should treat it as an opaque
        object. """
        return TextureSequence(filename_list)

    def load_compatible_font(self, filename, size):
        """ Load a pygame font. """
        return pygame.font.Font(filename, size)

    def compatible_image_from_text(self, text, font, colour):
        """ Create an image by rendering a text string. """
        return Texture.from_surface(font.render(text, True, colour))

    def screen_size(self):
        """ Get the display size. """
        return self.__surface.get_size()

    def screen_rect(self):
        """ Get the display size. """
        return self.__surface.get_rect()

    def render_RenderJobBackground(self, job):
        """ Render scrolling background. """
        (w, h) = self.screen_size()
        self.render_image(job.background_image, w, h, Vec2d(0, 0))

    def render_RenderJobRect(self, job):
        """ Render rectangle. """
        rect = job.rect
        tl = rect.topleft
        tr = rect.topright
        br = rect.bottomright
        bl = rect.bottomleft
        GL.glColor3f(*self.colour_int_to_float(job.colour))
        if job.width == 0:
            GL.glBegin(GL.GL_QUADS)
        else:
            GL.glLineWidth(job.width)
            GL.glBegin(GL.GL_LINE_LOOP)
        GL.glVertex2f(tl[0], tl[1])
        GL.glVertex2f(tr[0], tr[1])
        GL.glVertex2f(br[0], br[1])
        GL.glVertex2f(bl[0], bl[1])
        GL.glEnd()

    def render_RenderJobLine(self, job):
        """ Render a line. """
        GL.glLineWidth(job.width)
        GL.glColor3f(*self.colour_int_to_float(job.colour))
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(job.p0[0], job.p0[1])
        GL.glVertex2f(job.p1[0], job.p1[1])
        GL.glEnd()

    def render_RenderJobLines(self, job):
        """ Render a polyline. """
        GL.glLineWidth(job.width)
        GL.glColor3f(*self.colour_int_to_float(job.colour))
        GL.glBegin(GL.GL_LINE_STRIP)
        for point in job.points:
            GL.glVertex2f(point[0], point[1])
        GL.glEnd()

    def render_RenderJobPolygon(self, job):
        """ Render a polygon. """
        GL.glColor3f(*self.colour_int_to_float(job.colour))
        GL.glBegin(GL.GL_POLYGON)
        for point in job.points:
            GL.glVertex2f(point[0], point[1])
        GL.glEnd()

    def render_RenderJobCircle(self, job):
        """ Render a circle. """
        GL.glColor3f(*self.colour_int_to_float(job.colour))
        if job.width == 0:
            GL.glBegin(GL.GL_TRIANGLE_FAN)
        else:
            GL.glLineWidth(job.width)
            GL.glBegin(GL.GL_LINE_LOOP)
        circumference = 2*math.pi*job.radius
        points = []
        npoi = max(int(math.sqrt(circumference)), 6)
        for i in range(0, npoi):
            angle = i/float(npoi) * math.pi * 2
            point = job.position + job.radius * Vec2d(math.cos(angle), math.sin(angle))
            GL.glVertex2f(point[0], point[1])
        GL.glEnd()

    def render_RenderJobText(self, job):
        """ Render some text. """
        text_surface = job.font.render(job.text, True, job.colour)
        texture = Texture.from_surface(text_surface)
        self.render_image(texture, texture.get_width(), texture.get_height(), job.position)
        texture.delete()

    def render_RenderJobAnimation(self, job):
        """ Render an animation. """
        width = job.length_to_screen(job.anim.frames.get_width())
        height = job.length_to_screen(job.anim.frames.get_height())
        self.render_image(
            job.anim.frames.get_frame(job.anim.timer),
            width,
            height,
            job.position,
            origin=Vec2d(width/2, height/2),
            orientation = math.radians(-job.orientation)
        )

    def render_RenderJobImage(self, job):
        """ Render an image. """
        width = job.length_to_screen(job.image.get_width())
        height = job.length_to_screen(job.image.get_height())
        self.render_image(job.image, width, height, job.position)

    def render_image(self, texture, width, height, position, **kwargs):
        """ Render an image. """
        texture.begin()
        self.render_quad(width, height, position, **kwargs)
        texture.end()

    def render_quad(self, width, height, position, **kwargs):
        """ Render a quad. """

        # Rotation about origin.
        orientation = 0
        if "orientation" in kwargs:
            orientation = kwargs["orientation"]

        # Origin position in local coordinates.
        origin = Vec2d(0, 0)
        if "origin" in kwargs:
            origin = kwargs["origin"]

        # Get quad corners in local coordinates, relative to position.
        tl = Vec2d(0, 0) - origin
        tr = Vec2d(width, 0) - origin
        br = Vec2d(width, height) - origin
        bl = Vec2d(0, height) - origin

        # Render the quad.
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(0, 0); GL.glVertex2f(*(position + tl.rotated(orientation)))
        GL.glTexCoord2f(1, 0); GL.glVertex2f(*(position + tr.rotated(orientation)))
        GL.glTexCoord2f(1, 1); GL.glVertex2f(*(position + br.rotated(orientation)))
        GL.glTexCoord2f(0, 1); GL.glVertex2f(*(position + bl.rotated(orientation)))
        GL.glEnd()

    def colour_int_to_float(self, colour):
        """ Convert colour to float format. """
        return (float(colour[0])/255, float(colour[1])/255, float(colour[2])/255)
