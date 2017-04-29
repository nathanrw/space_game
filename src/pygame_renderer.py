import pygame

from .renderer import *

class PygameRenderer(Renderer):
    """ A pygame software renderer. """

    def __init__(self):
        """ Constructor. """
        Renderer.__init__(self)
        self.__surface = None

    def initialise(self, screen_size):
        """ Initialise the pygame display. """
        self.__surface = pygame.display.set_mode(screen_size)

    def flip_buffers(self):
        """ Update the pygame display. """
        pygame.display.update()

    def load_compatible_image(self, filename):
        """ Load a pygame image. """
        return pygame.image.load(filename).convert_alpha()

    def load_compatible_anim_frames(self, filename_list):
        """ Load the frames of an animation into a format compatible
        with the renderer.  The implementation can return its own
        image representation; the client should treat it as an opaque
        object. """
        return [self.load_compatible_image(x) for x in filename_list]

    def load_compatible_font(self, filename, size):
        """ Load a pygame font. """
        return pygame.font.Font(filename, size)

    def compatible_image_from_text(self, text, font, colour):
        """ Create an image by rendering a text string. """
        return font.render(text, True, colour)

    def screen_size(self):
        """ Get the display size. """
        return self.__surface.get_size()

    def screen_rect(self):
        """ Get the display size. """
        return self.__surface.get_rect()

    def render_RenderJobBackground(self, job):
        """ Render scrolling background. """
        screen = self.__surface
        (image_width, image_height) = job.background_image.get_size()
        (screen_width, screen_height) = screen.get_size()
        pos = job.view.position
        x = int(pos.x)
        y = int(pos.y)
        start_i = -(x%image_width)
        start_j = -(y%image_width)
        for i in range(start_i, screen_width, image_width):
            for j in range(start_j, screen_height, image_height):
                screen.blit(job.background_image, (i, j))

    def render_RenderJobRect(self, job):
        """ Render rectangle. """
        pygame.draw.rect(self.__surface, job.colour, job.rect, job.width)

    def render_RenderJobLine(self, job):
        """ Render a line. """
        pygame.draw.line(self.__surface, job.colour, job.p0, job.p1, job.width)

    def render_RenderJobLines(self, job):
        """ Render a polyline. """
        pygame.draw.lines(self.__surface, job.colour, False, job.points, job.width)

    def render_RenderJobPolygon(self, job):
        """ Render a polygon. """
        pygame.draw.polygon(self.__surface, job.colour, job.points)

    def render_RenderJobCircle(self, job):
        """ Render a circle. """
        pygame.draw.circle(self.__surface,
                           job.colour,
                           (int(job.position[0]), int(job.position[1])),
                           int(job.radius),
                           int(job.width))

    def render_RenderJobText(self, job):
        """ Render some text. """
        text_surface = job.font.render(job.text, True, job.colour)
        self.__surface.blit(text_surface, job.position)

    def render_RenderJobAnimation(self, job):
        """ Render an animation. """
        img = job.anim.frames[job.anim.timer.pick_index(len(job.anim.frames))]
        if (job.orientation != 0):
            img = pygame.transform.rotate(img, job.orientation)
        if (job.view.zoom != 1):
            size = job.scale_size(img.get_size())
            img = pygame.transform.scale(img, (int(size[0]), int(size[1])))
        screen_pos = job.position - Vec2d(img.get_rect().center)
        self.__surface.blit(img, screen_pos)

    def render_RenderJobImage(self, job):
        """ Render an image. """
        self.__surface.blit(job.image, job.position)
