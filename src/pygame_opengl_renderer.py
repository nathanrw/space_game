import pygame
import OpenGL
import OpenGL.GL as GL
import math

from pymunk import Vec2d

from .renderer import *

class Texture(object):
    def __init__(self, filename):
        self.__surface = pygame.image.load(filename)
    def get_width(self):
        return self.__surface.get_width()
    def get_height(self):
        return self.__surface.get_height()

class TextureSequence(object):
    def __init__(self, filenames):
        self.__surface = pygame.image.load(filenames[0])
    def get_width(self):
        return self.__surface.get_width()
    def get_height(self):
        return self.__surface.get_height()

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
        GL.glDisable(GL.GL_DEPTH_TEST)

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
        GL.glColor3f(1, 1, 1)
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(*(job.position + Vec2d(-width/2, -height/2).rotated(math.radians(-job.orientation))))
        GL.glVertex2f(*(job.position + Vec2d(width/2, -height/2).rotated(math.radians(-job.orientation))))
        GL.glVertex2f(*(job.position + Vec2d(width/2, height/2).rotated(math.radians(-job.orientation))))
        GL.glVertex2f(*(job.position + Vec2d(-width/2, height/2).rotated(math.radians(-job.orientation))))
        GL.glEnd()

    def render_RenderJobImage(self, job):
        """ Render an image. """
        width = job.length_to_screen(job.image.get_width())
        height = job.length_to_screen(job.image.get_height())
        GL.glColor3f(1, 1, 1)
        GL.glBegin(GL.GL_QUADS)
        GL.glVertex2f(*(job.position + Vec2d(0, 0)))
        GL.glVertex2f(*(job.position + Vec2d(width, 0)))
        GL.glVertex2f(*(job.position + Vec2d(width, height)))
        GL.glVertex2f(*(job.position + Vec2d(0, height)))
        GL.glEnd()

    def render_RenderJobWarning(self, job):
        """ Render a warning on the screen. """
        pass

    def colour_int_to_float(self, colour):
        """ Convert colour to float format. """
        return (float(colour[0])/255, float(colour[1])/255, float(colour[2])/255)
