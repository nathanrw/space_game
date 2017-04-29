import pygame
import OpenGL
import OpenGL.GL as GL
import math

from pymunk import Vec2d

from .renderer import *

class Texture(object):
    """ An OpenGL texture. """

    def __init__(self, filename):
        """ Constructor. """
        surface = pygame.image.load(filename).convert_alpha()
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
        GL.glEnable(GL.GL_TEXTURE_2D)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.__texture)
        GL.glColor3f(1, 1, 1)

    def end(self):
        """ Unset the state. """
        GL.glDisable(GL.GL_TEXTURE_2D)

    def get_width(self):
        """ Get the texture width in pixels. """
        return self.__width

    def get_height(self):
        """ Get the texture height in pixels. """
        return self.__height

class TextureSequence(object):
    """ A sequence of textures. """

    # Note: this is not really a practical implementation, we have lots of
    # large frames per anim so that's lots of textures. It would be good to
    # use a texture atlas or array texture for the frames rather than a
    # texture per frame.

    def __init__(self, filenames):
        """ Constructor. """
        self.__textures = [Texture(f) for f in filenames]
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
        return Texture(filename)

    def load_compatible_anim_frames(self, filename_list):
        """ Load the frames of an animation into a format compatible
        with the renderer.  The implementation can return its own
        image representation; the client should treat it as an opaque
        object. """
        return TextureSequence(filename_list)

    def load_compatible_font(self, filename, size):
        """ Load a pygame font. """
        return pygame.font.Font(filename, size)

    def screen_size(self):
        """ Get the display size. """
        return self.__surface.get_size()

    def screen_rect(self):
        """ Get the display size. """
        return self.__surface.get_rect()

    def render_RenderJobBackground(self, job):
        """ Render scrolling background. """
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

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
        npoi = max(int(circumference / 10), 6)
        for i in range(0, npoi):
            angle = i/float(npoi) * math.pi * 2
            point = job.position + job.radius * Vec2d(math.cos(angle), math.sin(angle))
            GL.glVertex2f(point[0], point[1])
        GL.glEnd()

    def render_RenderJobText(self, job):
        """ Render some text. """
        pass

    def render_RenderJobAnimation(self, job):
        """ Render an animation. """
        width = job.length_to_screen(job.anim.frames.get_width())
        height = job.length_to_screen(job.anim.frames.get_height())
        job.anim.frames.begin(job.anim.timer)
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(0, 0)
        GL.glVertex2f(*(job.position + Vec2d(-width/2, -height/2).rotated(math.radians(-job.orientation))))
        GL.glTexCoord2f(1, 0)
        GL.glVertex2f(*(job.position + Vec2d(width/2, -height/2).rotated(math.radians(-job.orientation))))
        GL.glTexCoord2f(1, 1)
        GL.glVertex2f(*(job.position + Vec2d(width/2, height/2).rotated(math.radians(-job.orientation))))
        GL.glTexCoord2f(0, 1)
        GL.glVertex2f(*(job.position + Vec2d(-width/2, height/2).rotated(math.radians(-job.orientation))))
        GL.glEnd()
        job.anim.frames.end()

    def render_RenderJobImage(self, job):
        """ Render an image. """
        width = job.length_to_screen(job.image.get_width())
        height = job.length_to_screen(job.image.get_height())
        job.image.begin()
        GL.glBegin(GL.GL_QUADS)
        GL.glTexCoord2f(0, 0)
        GL.glVertex2f(*(job.position + Vec2d(0, 0)))
        GL.glTexCoord2f(1, 0)
        GL.glVertex2f(*(job.position + Vec2d(width, 0)))
        GL.glTexCoord2f(1, 1)
        GL.glVertex2f(*(job.position + Vec2d(width, height)))
        GL.glTexCoord2f(0, 1)
        GL.glVertex2f(*(job.position + Vec2d(0, height)))
        GL.glEnd()
        job.image.end()

    def render_RenderJobWarning(self, job):
        """ Render a warning on the screen. """
        pass

    def colour_int_to_float(self, colour):
        """ Convert colour to float format. """
        return (float(colour[0])/255, float(colour[1])/255, float(colour[2])/255)
