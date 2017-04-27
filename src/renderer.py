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

    def check_bounds_world(self, bbox):
        """ Check whether a world space bounding box is on the screen. """
        if bbox is None: return True
        self_box = self.__renderer.screen_rect()
        self_box.width /= self.zoom
        self_box.height /= self.zoom
        self_box.center = self.position
        return bbox.colliderect(self_box)

    def check_bounds_screen(self, bbox):
        """ Check whether a screen space bounding box is on the screen. """
        if bbox is None: return True
        return self.__renderer.screen_rect().colliderect(bbox)

class RenderJob(object):
    """ Describes a rendering job. """
    __metaclass__ = abc.ABCMeta

    def __init__(self, view, level, coords):
        """ Initialise the job data. """
        self.view = view
        self.level = level
        self.coords = coords

    def point_to_screen(self, point):
        """ Ensure a point is in screen coordinates. """
        if self.coords == Renderer.COORDS_SCREEN:
            return point
        else:
            return self.view.world_to_screen(point)

    def rect_to_screen(self, rect):
        """ Ensure a rect is in screen coordinates. """
        if self.coords == Renderer.COORDS_SCREEN:
            return rect
        else:
            ret = rect.copy()
            ret.width = self.view.scale_length(ret.width)
            ret.height = self.view.scale_length(ret.height)
            ret.center = self.view.world_to_screen(ret.center)
            return ret

    def points_to_screen(self, points):
        """ Ensure a set of points is in screen coordinates. """
        return [ self.point_to_screen(p) for p in points ]

    def length_to_screen(self, length):
        """ Ensure a length is in screen coordinates. """
        if self.coords == Renderer.COORDS_SCREEN:
            return length
        else:
            return self.view.scale_length(length)

    def scale_size(self, size):
        """ Scale a size. """
        return Vec2d(self.length_to_screen(size[0]),
                     self.length_to_screen(size[1]))

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
        self.__rect = rect.copy()
        self.__width = width

    @property
    def rect(self):
        """ Get the rectangle. """
        return self.rect_to_screen(self.__rect)

    @property
    def width(self):
        """ Get the width. """
        return self.length_to_screen(self.__width)

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobRect(self)

class RenderJobLine(RenderJob):
    """ Render a line. """

    def __init__(self, view, level, coords, colour, p0, p1, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.__p0 = p0
        self.__p1 = p1
        self.__width = width

    @property
    def p0(self):
        """ Get the start point. """
        return self.point_to_screen(self.__p0)

    @property
    def p1(self):
        """ Get the end point. """
        return self.point_to_screen(self.__p1)

    @property
    def width(self):
        """ Get the width. """
        return self.length_to_screen(self.__width)
        
    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobLine(self)

class RenderJobLines(RenderJob):
    """ Render a polyline. """

    def __init__(self, view, level, coords, colour, points, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.__points = points
        self.__width = width

    @property
    def points(self):
        """ Get the points. """
        return self.points_to_screen(self.__points)

    @property
    def width(self):
        """ Get the width. """
        return self.length_to_screen(self.__width)

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobLines(self)

class RenderJobPolygon(RenderJob):
    """ Render a polygon. """

    def __init__(self, view, level, coords, colour, poly, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.__poly = poly
        self.__width = width

    @property
    def points(self):
        """ Get the points. """
        return self.points_to_screen(self.__poly.points)

    @property
    def width(self):
        """ Get the width. """
        return self.length_to_screen(self.__width)

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobPolygon(self)

class RenderJobCircle(RenderJob):
    """ Render a circle. """

    def __init__(self, view, level, coords, colour, position, radius, width):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.colour = colour
        self.__position = position
        self.__radius = radius
        self.__width = width

    @property
    def position(self):
        """ Get the position. """
        return self.point_to_screen(self.__position)

    @property
    def radius(self):
        """ Get the radius. """
        return self.length_to_screen(self.__radius)

    @property
    def width(self):
        """ Get the width. """
        return self.length_to_screen(self.__width)

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
        self.__position = position

    @property
    def position(self):
        """ Get the position. """
        return self.point_to_screen(self.__position)

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobText(self)

class RenderJobAnimation(RenderJob):
    """ Render an animation. """

    def __init__(self, view, level, coords, orientation, position, anim):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.orientation = orientation
        self.__position = position
        self.anim = anim

    @property
    def position(self):
        """ Get the position. """
        return self.point_to_screen(self.__position)

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobAnimation(self)

class RenderJobImage(RenderJob):
    """ Render an image. """

    def __init__(self, view, level, coords, position, image):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.__position = position
        self.image = image

    @property
    def position(self):
        """ Get the position. """
        return self.point_to_screen(self.__position)

    def dispatch(self, renderer):
        """ Dispatch the job. """
        renderer.render_RenderJobImage(self)

class RenderJobWarning(RenderJob):

    def __init__(self, view, level, coords, large_font, small_font,
                 text, colour, blink, offset, padding, visible):
        """ Constructor. """
        RenderJob.__init__(self, view, level, coords)
        self.large_font = large_font
        self.small_font = small_font
        self.colour = colour
        self.blink = blink
        self.offset = offset
        self.padding = padding
        self.visible = visible
        self.text = text

    def dispatch(self, renderer):
        renderer.render_RenderJobWarning(self)

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
    COORDS_WORLD = 1
    COORDS_SCREEN = 2

    def __init__(self):
        """ Constructor. """
        self.__jobs = []

    @abc.abstractmethod
    def initialise(self, screen_size):
        """ Initialise the renderer. """
        pass

    def render_jobs(self):
        """ Render any queued jobs. This does not update the display. """
        for job in self.__jobs:
            job.dispatch(self)
        self.__jobs = []

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
    def screen_size(self):
        """ Get the size of the display in pixels. """
        pass

    @abc.abstractmethod
    def screen_rect(self):
        """ Get the screen dimensions as a rect. """
        pass

    def add_job(self, job):
        """ Queue a render job. """
        self.__jobs.append(job)

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

    def add_job_warning(self, view, large_font, small_font, text, **kwargs):
        """ Queue a job to render a warning. """

        # Parse arguments.
        level=Renderer.LEVEL_FORE_NEAR
        coords=Renderer.COORDS_SCREEN
        colour=(255,255,255)
        if "colour" in kwargs:
            colour = kwargs["colour"]
        blink=True
        if "blink" in kwargs:
            blink = kwargs["blink"]
        offset=0
        if "offset" in kwargs:
            offset = kwargs["offset"]
        padding=0
        if "padding" in kwargs:
            padding = kwargs["padding"]
        visible=True
        if "visible" in kwargs:
            visible = kwargs["visible"]

        # Add the job.
        self.add_job(RenderJobWarning(view, level, coords, large_font, small_font,
                                      text, colour, blink, offset, padding, visible))

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

    @abc.abstractmethod
    def render_RenderJobWarning(self, job):
        """ Render a warning. """
        pass
