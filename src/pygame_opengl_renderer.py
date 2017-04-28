import pygame
import OpenGL
import OpenGL.GL as GL

from .renderer import *

class Texture(object):
    def __init__(self, filename):
        pass
    def get_width(self):
        return 0
    def get_height(self):
        return 0

class TextureSequence(object):
    def __init__(self, filenames):
        pass

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
        GL.glColor3f(*job.colour)
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
        GL.glColor3f(*job.colour)
        GL.glBegin(GL.GL_LINES)
        GL.glVertex2f(job.p0[0], job.p0[1])
        GL.glVertex2f(job.p1[0], job.p1[1])
        GL.glEnd()

    def render_RenderJobLines(self, job):
        """ Render a polyline. """
        GL.glLineWidth(job.width)
        GL.glColor3f(*job.colour)
        GL.glBegin(GL.GL_LINE_STRIP)
        for point in job.points:
            GL.glVertex2f(point[0], point[1])
        GL.glEnd()

    def render_RenderJobPolygon(self, job):
        """ Render a polygon. """
        GL.glColor3f(*job.colour)
        GL.glBegin(GL.GL_POLYGON)
        for point in job.points:
            GL.glVertex2f(point[0], point[1])
        GL.glEnd()

    def render_RenderJobCircle(self, job):
        """ Render a circle. """
        pass

    def render_RenderJobText(self, job):
        """ Render some text. """
        pass

    def render_RenderJobAnimation(self, job):
        """ Render an animation. """
        pass

    def render_RenderJobImage(self, job):
        """ Render an image. """
        pass

    def render_RenderJobWarning(self, job):
        """ Render a warning on the screen. """
        pass
