import abc

from pygame import Rect
from sge.utils import Vec2d

class View(object):
    """ A view. """

    def __init__(self, renderer):
        """ Constructor. """
        self.__renderer = renderer

    @property
    def position(self):
        """ Get the position. """
        return Vec2d(0, 0)

    @property
    def orientation(self):
        """ Get the orientation. """
        return 0

    @property
    def zoom(self):
        """ Get the zoom factor. """
        return 1

    @property
    def size(self):
        """ Get the screen size. """
        return self.__renderer.screen_size()

    def world_to_screen(self, world):
        """ Convert from world coordinates to screen coordinates. """
        centre = Vec2d(self.__renderer.screen_size())/2
        return self.zoom * (world - self.position) + centre

    def scale_length(self, length_world):
        """ Scale a length into screen space. """
        return self.zoom * length_world

    def screen_to_world(self, screen):
        """ Convert from screen coordinates to world coordinates. """
        centre = Vec2d(self.__renderer.screen_size())/2
        return (screen - centre) / self.zoom + self.position

    def point_to_screen(self, point, coords):
        """ Convert a point to world coordinates. """
        if coords == Renderer.COORDS_SCREEN:
            return point
        else:
            return self.world_to_screen(point)

    def length_to_screen(self, length, coords):
        """ Convert a length to world coordinates. """
        if coords == Renderer.COORDS_SCREEN:
            return length
        else:
            return self.scale_length(length)

    def points_to_screen(self, points, coords):
        """ Convert a list of points to world coordinates. """
        if coords == Renderer.COORDS_SCREEN:
            return points
        else:
            return [ self.world_to_screen(p) for p in points ]

    def rect_to_screen(self, rect, coords):
        """ Convert a rectangle into screen coordinates. """
        if coords == Renderer.COORDS_SCREEN:
            return rect
        else:
            tl = self.world_to_screen(rect.topleft)
            br = self.world_to_screen(rect.bottomright)
            ret = Rect()
            ret.topleft = tl
            ret.bottomright = br
            return ret

    def size_to_screen(self, size, coords):
        """ Convert a size into screen coordinates """
        if coords == Renderer.COORDS_SCREEN:
            return size
        else:
            return (self.scale_length(size[0]),
                    self.scale_length(size[1]))


class Renderer(object):
    """ An abstract render that knows how to draw things. """

    # The renderer is an abstract base class.
    __metaclass__ = abc.ABCMeta

    # Levels
    LEVEL_BACK_FAR = 0
    LEVEL_BACK = 1
    LEVEL_BACK_NEAR = 2
    LEVEL_MID_FAR = 3
    LEVEL_MID = 4
    LEVEL_MID_NEAR = 5
    LEVEL_FORE_FAR = 6
    LEVEL_FORE = 7
    LEVEL_FORE_NEAR = 8

    # Coordinate systems
    COORDS_WORLD = 0
    COORDS_SCREEN = 1

    def __init__(self, screen_size, options, **kwargs):
        """ Constructor. """
        pass

    @abc.abstractmethod
    def initialise(self):
        """ Initialise the renderer. """
        pass

    def post_preload(self):
        """ A hook to be executed when the game has finished loading. """
        pass

    @abc.abstractmethod
    def pre_render(self, view):
        """ Hook to set up any state necessary for rendering. """
        pass

    @abc.abstractmethod
    def post_render(self):
        """ Hook to do any work after all jobs have been submitted. """
        pass

    @abc.abstractmethod
    def flip_buffers(self):
        """ Update the display. """
        pass

    @abc.abstractmethod
    def load_compatible_image(self, filename):
        """ Load an image that can be rendered. The implementation can
        return its own image representation; the client should treat
        it as an opaque object. """
        pass

    @abc.abstractmethod
    def load_compatible_anim_frames(self, filename_list):
        """ Load the frames of an animation into a format compatible
        with the renderer.  The implementation can return its own
        image representation; the client should treat it as an opaque
        object. """
        pass

    @abc.abstractmethod
    def load_compatible_font(self, filename, size):
        """ Load a font that can be rendered. The implementation can return its
        own font representation; the client should treat it as an opaque object. """
        pass

    @abc.abstractmethod
    def load_compatible_gui_font(self, filename, size):
        """ Load a font that can be use by the GUI. """
        pass

    @abc.abstractmethod
    def compatible_image_from_text(self, text, font, colour):
        """ Create an image by rendering a text string. """
        pass

    @abc.abstractmethod
    def screen_size(self):
        """ Get the size of the display in pixels. """
        pass

    @abc.abstractmethod
    def screen_rect(self):
        """ Get the screen dimensions as a rect. """
        pass

    def add_job_rect(self, rect, **kwargs):
        """ Queue a job to render a rectangle. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_MID,
                            coords=Renderer.COORDS_WORLD,
                            colour=(255, 255, 255),
                            width=0)
        self.render_rect(rect, **kwargs)

    def add_job_line(self, p0, p1, **kwargs):
        """ Queue a job to render a line. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_MID,
                            coords=Renderer.COORDS_WORLD,
                            colour=(255, 255, 255),
                            width=0)
        self.render_line(p0, p1, **kwargs)

    def add_job_lines(self, points, **kwargs):
        """ Queue a job to render lines """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_MID,
                            coords=Renderer.COORDS_WORLD,
                            colour=(255, 255, 255),
                            width=0)
        self.render_lines(points, **kwargs)

    def add_job_polygon(self, poly, **kwargs):
        """ Queue a job to render a polygon. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_MID,
                            coords=Renderer.COORDS_WORLD,
                            colour=(255, 255, 255),
                            width=0)
        self.render_polygon(poly.points, **kwargs)

    def add_job_circle(self, position, radius, **kwargs):
        """ Queue a job to render a circle. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_MID,
                            coords=Renderer.COORDS_WORLD,
                            colour=(255, 255, 255),
                            width=0)
        self.render_circle(position, radius, **kwargs)

    def add_job_text(self, font, text, position, **kwargs):
        """ Queue a job to render text. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_FORE_NEAR,
                            coords=Renderer.COORDS_SCREEN,
                            colour=(255, 255, 255))
        self.render_text(font, text, position, **kwargs)

    def add_job_animation(self, orientation, position, anim, **kwargs):
        """ Queue a job to render an animation. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_MID,
                            coords=Renderer.COORDS_WORLD)
        self.render_animation(position, orientation, anim, **kwargs)

    def add_job_image(self, position, image, **kwargs):
        """ Queue a job to render an image. """
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_FORE_NEAR,
                            coords=Renderer.COORDS_SCREEN)
        self.render_image(position, image, **kwargs)

    def add_job_nuklear(self, nuklear, **kwargs):
        self.__set_defaults(kwargs,
                            level=Renderer.LEVEL_FORE_NEAR,
                            coords=Renderer.COORDS_SCREEN)
        self.render_nuklear(nuklear, **kwargs)

    def __set_defaults(self, got_kwargs, **kwargs):
        """ Set default kwargs."""
        for key in kwargs:
            if not key in got_kwargs:
                got_kwargs[key] = kwargs[key]

    @abc.abstractmethod
    def render_rect(self, rect, **kwargs):
        """ Render a rectangle. """
        pass

    @abc.abstractmethod
    def render_line(self, p0, p1, **kwargs):
        """ Render a line. """
        pass

    @abc.abstractmethod
    def render_lines(self, points, **kwargs):
        """ Render a polyline. """
        pass

    @abc.abstractmethod
    def render_polygon(self, points, **kwargs):
        """ Render a polygon. """
        pass

    @abc.abstractmethod
    def render_circle(self, position, radius, **kwargs):
        """ Render a circle. """
        pass

    @abc.abstractmethod
    def render_text(self, font, text, position, **kwargs):
        """ Render text. """
        pass

    @abc.abstractmethod
    def render_animation(self, position, orientation, animation, **kwargs):
        """ Render an animation. """
        pass

    @abc.abstractmethod
    def render_image(self, position, image, **kwargs):
        """ Render an image. """
        pass

    @abc.abstractmethod
    def render_nuklear(self, nuklear, **kwargs):
        """ Render the nuklear GUI. """
        pass
