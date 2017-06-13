import pygame
from pymunk.vec2d import Vec2d

from .renderer import Renderer, View

class LoadingScreen(object):
    """ A loading screen to display while the resources are read in. It assumes
    direct control over the pygame display. The intention is you count your
    resources, construct the loading screen, and then just increment it after
    each resource is read. """

    def __init__(self, total, renderer):
        """ Constructor. This actually does the initial draw. """
        self.total = total
        self.progress = 0
        self.renderer = renderer
        self.view = View(renderer)
        self.title = renderer.load_compatible_image("res/images/title.bmp")
        self.__draw()

    def increment(self):
        """ Increment the progress and refresh the screen. We also deal with
        events to keep the program responsive. """
        self.progress += 1
        for e in pygame.event.get():
            if e == pygame.QUIT:
                sys.exit(1)
        self.__draw()

    def __draw(self):
        """ Do the actual drawing and screen refresh. """

        # Prepare the renderer.
        self.renderer.pre_render(self.view)

        # Define the geometry of the loading bar.
        screen_rect = self.renderer.screen_rect()
        bar_rect = pygame.Rect((0, 0), (0, 0))
        bar_rect.width = screen_rect.width-60
        bar_rect.height = 60
        bar_rect.center = screen_rect.center
        bar_rect.top += self.title.get_height() / 2
        brightness = 2.0 * (float(self.progress)/self.total)

        # Draw the title image above the loading bar.
        self.renderer.add_job_image(Vec2d(bar_rect.center[0], bar_rect.top)
                                    - Vec2d(self.title.get_width() / 2, self.title.get_height() + 10), self.title,
                                    coords=Renderer.COORDS_SCREEN,
                                    brightness=brightness)

        # Draw the loading bar
        sz = 8
        self.renderer.add_job_rect(bar_rect,
                                   colour=(255, 255, 255),
                                   coords=Renderer.COORDS_SCREEN,
                                   brightness=brightness)
        bar_rect.inflate_ip(-sz, -sz)
        self.renderer.add_job_rect(bar_rect,
                                   colour=(0, 0, 0),
                                   coords=Renderer.COORDS_SCREEN)
        bar_rect.inflate_ip(-sz, -sz)
        left = bar_rect.left
        bar_rect.width = int(bar_rect.width * (float(self.progress)/self.total))
        bar_rect.left = left
        self.renderer.add_job_rect(bar_rect,
                                   colour=(255, 255, 255),
                                   coords=Renderer.COORDS_SCREEN,
                                   brightness=brightness)

        # Refresh the screen.
        self.renderer.post_render()
        self.renderer.flip_buffers()
