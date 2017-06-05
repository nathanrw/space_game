import abc

from pygame import Rect
from pymunk.vec2d import Vec2d

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


class RenderJob(object):
    """ Describes a rendering job. """
    __metaclass__ = abc.ABCMeta

    def __init__(self, view, level, coords):
        """ Initialise the job data. """
        self.view = view
        self.level = level
        self.coords = coords
        self.colour = (0, 0, 0)

    @abc.abstractmethod
    def dispatch(self, renderer):
        """ Tell the renderer to render the job. """
        pass

class RenderJobBackground(RenderJob):
    """ Render a scrolling background image. """

    def __init__(self, view, level, coords, background_image):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.background_image = background_image

    def dispatch(self, renderer):
        """ Dispatch the job."""
        renderer.render_RenderJobBackground(self)

class RenderJobRect(RenderJob):
    """ Render a rectangle. """

    def __init__(self, view, level, coords, colour, rect, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.rect = rect.copy()
        self.width = width

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobRect(self)

class RenderJobLine(RenderJob):
    """ Render a line. """

    def __init__(self, view, level, coords, colour, p0, p1, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.p0 = p0
        self.p1 = p1
        self.width = width

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobLine(self)

class RenderJobLines(RenderJob):
    """ Render a polyline. """

    def __init__(self, view, level, coords, colour, points, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.points = points
        self.width = width

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobLines(self)

class RenderJobPolygon(RenderJob):
    """ Render a polygon. """

    def __init__(self, view, level, coords, colour, poly, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.poly = poly
        self.width = width

    @property
    def points(self):
        """ Get the points. """
        return self.poly.points

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobPolygon(self)

class RenderJobCircle(RenderJob):
    """ Render a circle. """

    def __init__(self, view, level, coords, colour, position, radius, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.position = position
        self.radius = radius
        self.width = width

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobCircle(self)

class RenderJobText(RenderJob):
    """ Render some text. """

    def __init__(self, view, level, coords, font, text, colour, position):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.font = font
        self.text = text
        self.colour = colour
        self.position = position

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobText(self)

class RenderJobAnimation(RenderJob):
    """ Render an animation. """

    def __init__(self, view, level, coords, orientation, position, anim):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.orientation = orientation
        self.position = position
        self.anim = anim

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobAnimation(self)

class RenderJobImage(RenderJob):
    """ Render an image. """

    def __init__(self, view, level, coords, position, image):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.position = position
        self.image = image

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobImage(self)

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

    def __init__(self):
        """ Constructor. """
        self.__levels = []
        for level in range(Renderer.LEVEL_BACK_FAR, Renderer.LEVEL_FORE_NEAR+1):
            self.__levels.append([])

    @abc.abstractmethod
    def initialise(self, screen_size, data_path):
        """ Initialise the renderer. """
        pass

    def post_preload(self):
        """ A hook to be executed when the game has finished loading. """
        pass

    def render_jobs(self, view):
        """ Render any queued jobs. This does not update the display. """
        for level in self.__levels:
            for job in level:
                job.dispatch(self)
            del level[:]

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

    def add_job(self, job):
        """ Queue a render job. """
        self.__levels[job.level].append(job)

    def add_job_background(self, view, background_image):
        """ Queue a job to render a background image. """
        self.add_job(RenderJobBackground(view,
                                         Renderer.LEVEL_BACK_FAR,
                                         Renderer.COORDS_SCREEN,
                                         background_image))

    def add_job_rect(self, view, rect, **kwargs):
        """ Queue a job to render a rectangle. """
        level=Renderer.LEVEL_MID
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_WORLD
        if "coords" in kwargs:
            coords=kwargs["coords"]
        width=0
        if "width" in kwargs:
            width=kwargs["width"]
        colour=(255, 255, 255)
        if "colour" in kwargs:
            colour=kwargs["colour"]
        self.add_job(RenderJobRect(view, level, coords, colour, rect, width))

    def add_job_line(self, view, p0, p1, **kwargs):
        """ Queue a job to render a line. """
        level=Renderer.LEVEL_MID
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_WORLD
        if "coords" in kwargs:
            coords=kwargs["coords"]
        width=0
        if "width" in kwargs:
            width=kwargs["width"]
        colour=(255, 255, 255)
        if "colour" in kwargs:
            colour=kwargs["colour"]
        self.add_job(RenderJobLine(view, level, coords, colour, p0, p1, width))

    def add_job_lines(self, view, points, **kwargs):
        """ Queue a job to render lines """
        level=Renderer.LEVEL_MID
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_WORLD
        if "coords" in kwargs:
            coords=kwargs["coords"]
        width=0
        if "width" in kwargs:
            width=kwargs["width"]
        colour=(255, 255, 255)
        if "colour" in kwargs:
            colour=kwargs["colour"]
        self.add_job(RenderJobLines(view, level, coords, colour, points, width))

    def add_job_polygon(self, view, poly, **kwargs):
        """ Queue a job to render a polygon. """
        level=Renderer.LEVEL_MID
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_WORLD
        if "coords" in kwargs:
            coords=kwargs["coords"]
        width=0
        if "width" in kwargs:
            width=kwargs["width"]
        colour=(255, 255, 255)
        if "colour" in kwargs:
            colour=kwargs["colour"]
        self.add_job(RenderJobPolygon(view, level, coords, colour, poly, width))

    def add_job_circle(self, view, position, radius, **kwargs):
        """ Queue a job to render a circle. """
        level=Renderer.LEVEL_MID
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_WORLD
        if "coords" in kwargs:
            coords=kwargs["coords"]
        width=0
        if "width" in kwargs:
            width=kwargs["width"]
        colour=(255, 255, 255)
        if "colour" in kwargs:
            colour=kwargs["colour"]
        self.add_job(RenderJobCircle(view, level, coords, colour, position, radius, width))

    def add_job_text(self, view, font, text, position, **kwargs):
        """ Queue a job to render text. """
        level=Renderer.LEVEL_FORE_NEAR
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_SCREEN
        if "coords" in kwargs:
            coords=kwargs["coords"]
        colour=(255, 255, 255)
        if "colour" in kwargs:
            colour=kwargs["colour"]
        self.add_job(RenderJobText(view, level, coords, font, text, colour, position))

    def add_job_animation(self, view, orientation, position, anim, **kwargs):
        """ Queue a job to render an animation. """
        level=Renderer.LEVEL_MID
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_WORLD
        if "coords" in kwargs:
            coords=kwargs["coords"]
        self.add_job(RenderJobAnimation(view, level, coords, orientation, position, anim))

    def add_job_image(self, view, position, image, **kwargs):
        """ Queue a job to render an image. """
        level=Renderer.LEVEL_FORE_NEAR
        if "level" in kwargs:
            level=kwargs["level"]
        coords=Renderer.COORDS_SCREEN
        if "coords" in kwargs:
            coords=kwargs["coords"]
        self.add_job(RenderJobImage(view, level, coords, position, image))

    @abc.abstractmethod
    def render_RenderJobBackground(self, job):
        """ Render a scrolling background. """
        pass

    @abc.abstractmethod
    def render_RenderJobRect(self, job):
        """ Render a rectangle. """
        pass

    @abc.abstractmethod
    def render_RenderJobLine(self, job):
        """ Render a line. """
        pass

    @abc.abstractmethod
    def render_RenderJobLines(self, job):
        """ Render a polyline. """
        pass

    @abc.abstractmethod
    def render_RenderJobPolygon(self, job):
        """ Render a polygon. """
        pass

    @abc.abstractmethod
    def render_RenderJobCircle(self, job):
        """ Render a circle. """
        pass

    @abc.abstractmethod
    def render_RenderJobText(self, job):
        """ Render text. """
        pass

    @abc.abstractmethod
    def render_RenderJobAnimation(self, job):
        """ Render an animation. """
        pass

    @abc.abstractmethod
    def render_RenderJobImage(self, job):
        """ Render an image. """
        pass
