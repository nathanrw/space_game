import pygame

from .renderer import *

import pynk.nkpygame

class PygameRenderer(Renderer):
    """ A pygame software renderer. """

    def __init__(self, screen_size, options, **kwargs):
        """ Constructor. """
        Renderer.__init__(self, screen_size, options, **kwargs)
        self.__screen_size = screen_size
        self.__options = options
        self.__surface = None
        self.__view = None
        self.__jobs = {}

    def initialise(self):
        """ Initialise the pygame display. """
        self.__surface = pygame.display.set_mode(self.__screen_size)

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

    def load_compatible_gui_font(self, filename, size):
        """ Load a font for the GUI. """
        return pynk.nkpygame.NkPygameFont(self.load_compatible_font(filename, size))

    def compatible_image_from_text(self, text, font, colour):
        """ Create an image by rendering a text string. """
        return font.render(text, True, colour)

    def screen_size(self):
        """ Get the display size. """
        return self.__surface.get_size()

    def screen_rect(self):
        """ Get the display size. """
        return self.__surface.get_rect()

    def pre_render(self, view):
        """ Start rendering. """
        self.__view = view

    def post_render(self):
        """ Finish rendering. """
        for key in sorted(self.__jobs.keys()):
            jobs = self.__jobs[key]
            for job in jobs:
                job(self.__view)
        self.__jobs = {}

    def render_background(self, background_image, **kwargs):
        """ Render scrolling background. """
        def do_it(the_view):
            screen = self.__surface
            (image_width, image_height) = background_image.get_size()
            (screen_width, screen_height) = screen.get_size()
            pos = the_view.position
            x = int(pos.x)
            y = int(pos.y)
            start_i = -(x%image_width)
            start_j = -(y%image_width)
            for i in range(start_i, screen_width, image_width):
                for j in range(start_j, screen_height, image_height):
                    screen.blit(background_image, (i, j))
        self.__add_job((Renderer.COORDS_SCREEN, Renderer.LEVEL_BACK_FAR), do_it)

    def render_rect(self, rect, **kwargs):
        """ Render rectangle. """
        (coords, level) = self.__parse_kwargs(kwargs)
        colour = self.__get_or_default(kwargs, "colour", (255, 255, 255))
        width = self.__get_or_default(kwargs, "width", 0)
        rect = rect.copy()
        def do_it(view):
            pygame.draw.rect(self.__surface,
                             colour,
                             view.rect_to_screen(rect, coords),
                             int(view.length_to_screen(width, coords)))
        self.__add_job((level, coords), do_it)

    def render_line(self, p0, p1, **kwargs):
        """ Render a line. """
        (coords, level) = self.__parse_kwargs(kwargs)
        colour = self.__get_or_default(kwargs, "colour", (255, 255, 255))
        width = self.__get_or_default(kwargs, "width", 0)
        def do_it(view):
            pygame.draw.line(self.__surface,
                             colour,
                             view.point_to_screen(p0, coords),
                             view.point_to_screen(p1, coords),
                             max(1, int(view.length_to_screen(width, coords))))
        self.__add_job((level, coords), do_it)

    def render_lines(self, points, **kwargs):
        """ Render a polyline. """
        (coords, level) = self.__parse_kwargs(kwargs)
        colour = self.__get_or_default(kwargs, "colour", (255, 255, 255))
        width = self.__get_or_default(kwargs, "width", 0)
        def do_it(view):
            pygame.draw.lines(self.__surface,
                              colour,
                              False,
                              view.points_to_screen(points, coords),
                              int(view.length_to_screen(width, coords)))
        self.__add_job((level, coords), do_it)

    def render_polygon(self, points, **kwargs):
        """ Render a polygon. """
        (coords, level) = self.__parse_kwargs(kwargs)
        colour = self.__get_or_default(kwargs, "colour", (255, 255, 255))
        def do_it(view):
            pygame.draw.polygon(self.__surface,
                                colour,
                                view.points_to_screen(points, coords))
        self.__add_job((level, coords), do_it)

    def render_circle(self, position, radius, **kwargs):
        """ Render a circle. """
        (coords, level) = self.__parse_kwargs(kwargs)
        colour = self.__get_or_default(kwargs, "colour", (255, 255, 255))
        def do_it(view):
            pos = view.point_to_screen(position, coords)
            width = self.__get_or_default(kwargs, "width", 0)
            scaled_width = int(view.length_to_screen(width, coords))
            scaled_radius = max(1, int(view.length_to_screen(radius, coords)))
            if scaled_width > scaled_radius:
                scaled_width = 0
            if scaled_radius <= 0:
                return
            pygame.draw.circle(self.__surface,
                               colour,
                               (int(pos[0]), int(pos[1])),
                               scaled_radius,
                               scaled_width)
        self.__add_job((level, coords), do_it)

    def render_text(self, font, text, position, **kwargs):
        """ Render some text. """
        (coords, level) = self.__parse_kwargs(kwargs)
        colour = self.__get_or_default(kwargs, "colour", (255, 255, 255))
        def do_it(view):
            text_surface = font.render(text, True, colour)
            self.__surface.blit(text_surface,
                                view.point_to_screen(position, coords))
        self.__add_job((level, coords), do_it)

    def render_animation(self, position, orientation, anim, **kwargs):
        """ Render an animation. """
        (coords, level) = self.__parse_kwargs(kwargs)
        def do_it(view):
            img = anim.frames[anim.timer.pick_index(len(anim.frames))]
            if (orientation != 0):
                img = pygame.transform.rotate(img, orientation)
            if (view.zoom != 1):
                size = view.size_to_screen(img.get_size(), coords)
                img = pygame.transform.scale(img, (int(size[0]), int(size[1])))
            screen_pos = view.point_to_screen(position, coords) - Vec2d(img.get_rect().center)
            self.__surface.blit(img, screen_pos)
        self.__add_job((level, coords), do_it)

    def render_image(self, position, image, **kwargs):
        """ Render an image. """
        (coords, level) = self.__parse_kwargs(kwargs)
        def do_it(view):
            self.__surface.blit(image, view.point_to_screen(position, coords))
        self.__add_job((level, coords), do_it)

    def render_nuklear(self, nuklear, **kwargs):
        (coords, level) = self.__parse_kwargs(kwargs)
        def do_it(view):
            nuklear.render_to_surface(self.__surface)
        self.__add_job((level, coords), do_it)

    def __parse_kwargs(self, kwargs_dict):
        """ Extract level and coordinate system, map colour. """
        coords = self.__get_or_default(kwargs_dict, "coords", Renderer.COORDS_WORLD)
        level = self.__get_or_default(kwargs_dict, "level", Renderer.LEVEL_MID)
        del kwargs_dict["level"]
        del kwargs_dict["coords"]
        return (coords, level)

    def __get_or_default(self, dictionary, name, default):
        """ Get a value from a dictionary. """
        if name in dictionary:
            return dictionary[name]
        else:
            return default

    def __add_job(self, key, job):
        """ Add a job to the appropriate list. """
        if not key in self.__jobs:
            self.__jobs[key] = []
        self.__jobs[key].append(job)
