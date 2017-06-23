""" Everything that draws itself on the screen is a drawable. A drawable is
a special kind of component that knows how to draw itself given a surface
and a camera. """

from pygame import Rect
import random

from .physics import *
from .behaviours import Hitpoints, Text, Thrusters, Shields, AnimationComponent, Weapon, Power
from .renderer import Renderer

class Drawing(ComponentSystem):
    """ A class that manages a set of things that can draw themselves. """

    def __init__(self, renderer):
        ComponentSystem.__init__(self)
        self.__background_image = None
        self.__font = None
        self.__renderer = renderer

    def set_background(self, image_name):
        """ Load a background image. """
        self.__background_image = self.game_services.get_resource_loader().load_image(image_name)

    def draw_graph(self, renderer, camera, values, maximum, position, size):
        """ Draw a graph from a list of values. """
        points = []
        for i, value in enumerate(values):
            x = position[0] + size[0] * (float(i)/(len(values)))
            y = position[1] + size[1] - size[1] * (value/float(maximum))
            points.append((x, y))
        if len(points) > 2:
            renderer.add_job_rect(Rect(position, size), width=1, colour=(255, 255, 255), coords=Renderer.COORDS_SCREEN)
            renderer.add_job_lines(points, width=2, colour=(200, 200, 200), coords=Renderer.COORDS_SCREEN)

    def draw_debug_info(self, renderer, camera):
        """ Draw the information. """

        # Check the debug level.
        if self.game_services.get_debug_level() <= 0:
            return

        # Load the font.
        if self.__font == None:
            self.__font = self.game_services.get_resource_loader().load_font(
                "res/fonts/nasdaqer/NASDAQER.ttf",
                12
            )

        game_info = self.game_services.get_info()

        # Draw the framerate.
        renderer.add_job_text(self.__font, "FPS (limited): %04.1f" % game_info.framerate, (10, 10))

        # Draw the unlimited framerate.
        renderer.add_job_text(self.__font, "FPS (raw): %04.1f" % game_info.raw_framerate, (10, 30))

        # Draw a graph of the framerate over time.
        self.draw_graph(renderer, camera, game_info.framerates, 70, (10, 50), (100, 15))

        # Draw the time ratio.
        renderer.add_job_text(self.__font, "Time scale: %03.1f" % game_info.time_ratio, (10, 70))

    def draw(self, renderer, camera):
        """ Draw the drawables in order of layer. """

        # Draw the background
        renderer.add_job_background(self.__background_image)

        # Draw each drawable.
        for drawable in self.components:
            drawable.draw(renderer, camera)

        # Draw the debug info.
        self.draw_debug_info(renderer, camera)

class Drawable(Component):
    """ Draws an entity on the screen. """

    def __init__(self, entity, game_services, config):
        """ Initialise the drawable """
        Component.__init__(self, entity, game_services, config)
        self.__text_drawer = None

    def manager_type(self):
        return Drawing

    def update(self, dt):
        if self.__text_drawer is not None:
            self.__text_drawer.update(dt)

    def draw(self, renderer, camera):
        """ Draw the entity. """

        # If it's a body draw various things.
        self.draw_body(renderer, camera)

        # If it's text draw text.
        self.draw_text(renderer, camera)

    def draw_body(self, renderer, camera):
        """ Draw the body on the screen. """

        # Get the body
        body = self.get_component(Body)
        if body is None:
            return

        # Draw any animation.
        self.draw_animation(body, renderer, camera)

        # Draw any thrusters affecting the body.
        self.draw_thrusters(body, renderer, camera)

        # Draw hitpoints.
        self.draw_hitpoints(body, renderer, camera)

        # Draw shields.
        self.draw_shields(body, renderer, camera)

        # Draw lasers
        self.draw_lasers(body, renderer, camera)

    def draw_lasers(self, body, renderer, camera):
        """ Draw laser beams. """
        children = body.entity.get_children()
        for child in children:
            weapon = child.get_component(Weapon)
            if weapon is not None:
                if weapon.weapon_type == "beam":
                    if weapon.shooting and weapon.impact_point is not None:
                        p0 = body.position
                        p1 = weapon.impact_point
                        radius = weapon.config.get_or_default("radius", 2)
                        red = (255,100,100)
                        white = (255,255,255)
                        renderer.add_job_line(p0, p1, colour=red, width=radius, brightness=2)
                        core_radius = radius//3
                        if core_radius > 0:
                            renderer.add_job_line(p0, p1, colour=white, width=core_radius, brightness=2)
                        size = int(radius+random.random()*radius*2)
                        renderer.add_job_circle(p1, size, colour=red, brightness=8)
                        renderer.add_job_circle(p1, size - 2, colour=white, brightness=8)

    def draw_shields(self, body, renderer, camera):
        """ Draw any shields the entity might have. """
        # Draw shields if we have them.
        shields = self.get_component(Shields)
        if shields is not None:
            width = int((shields.hp/float(shields.max_hp)) * 5)
            if width > 0:
                renderer.add_job_circle(body.position, int(body.size * 2), colour=(100, 100, 255), width=width, brightness=2)

    def draw_animation(self, body, renderer, camera):
        """ Draw an animation on the screen. """
        
        # See if there's an animation to draw.
        component = self.get_component(AnimationComponent)
        if component is None:
            return

        # Get the anim itself.
        anim = component.get_anim()

        # Draw the animation
        renderer.add_job_animation(
            -body.orientation,
            body.position,
            anim,
            brightness=component.config.get_or_default("brightness", 0.0)
        )

    def draw_thrusters(self, body, renderer, camera):
        """ Draw the thrusters affecting the body. """
        # If this body has thrusters then draw them.
        for thruster in body.thrusters():
            if thruster.on():
                pos = thruster.world_position(body)
                dir = thruster.world_direction(body)
                length = thruster.thrust() / 500.0
                length *= (1.0 + random.random()*0.1 - 0.2)
                poly = Polygon.make_bullet_polygon(pos, pos-(dir*length))
                renderer.add_job_polygon(poly, colour=(255, 255, 255), brightness=2)

    def draw_bar(self, arg_rect, fraction, col_back, col_0, col_1, renderer, camera):
        """ Draw a progress bar """

        # The background
        renderer.add_job_rect(arg_rect, colour=col_back, coords=Renderer.COORDS_SCREEN)

        # The empty portion.
        rect = Rect(arg_rect)
        rect.inflate_ip(-4, -4)
        renderer.add_job_rect(rect, colour=col_0, coords=Renderer.COORDS_SCREEN)

        # The full portion.
        rect.width = int(fraction * rect.width)
        renderer.add_job_rect(rect, colour=col_1, coords=Renderer.COORDS_SCREEN)

    def draw_hitpoints(self, body, renderer, camera):
        """ Draw the entity's hitpoints, or a marker showing where it
        is if it's off screen. """

        # If this body has hitpoints draw a health bar
        hitpoints = self.get_component(Hitpoints)
        if hitpoints is None:
            return

        # Draw health bar if it's on screen. Otherwise draw marker.
        rect = Rect(0, 0, body.size*2, 6)
        rect.center = rect.center = camera.world_to_screen(body.position)
        rect.top = rect.top - (body.size*1.2)
        self.draw_bar(rect,
                      hitpoints.hp/float(hitpoints.max_hp),
                      (255, 255, 255),
                      (255, 0, 0),
                      (0, 255, 0),
                      renderer,
                      camera)
        power = self.get_component(Power)
        if power is not None:
            rect.top += rect.height + 4
            self.draw_bar(rect,
                          power.power/float(power.capacity),
                          (255, 255, 255),
                          (100, 50, 0),
                          (255, 255, 0),
                          renderer,
                          camera)

    def draw_text(self, renderer, camera):
        """ Draw text using the text drawer. """
        if self.get_component(Text) is None:
            return
        if self.__text_drawer is None:
            self.__text_drawer = TextDrawer(self.entity, self.game_services)
        self.__text_drawer.draw(renderer, camera)

    def estimate_bounds(self):
        """ Return precomputed bounding box. """
        return self.rect

class TextDrawer(object):
    """ Draws text in the middle of the screen. Note that you don't set the text on the
    drawable, it gets stored in a Text component. This means that logic code doesn't need
    to mess with the drawable. """

    def __init__(self, entity, game_services):
        """Load the font."""
        self.entity = entity
        self.game_services = game_services
        text = self.entity.get_component(Text)
        self.__font = game_services.get_resource_loader().load_font(
            text.font_name(),
            text.large_font_size()
        )
        self.__small_font = game_services.get_resource_loader().load_font(
            text.font_name(),
            text.small_font_size()
        )
        self.__blink = text.blink()
        self.__blink_timer = Timer(text.blink_period())
        self.__visible = True
        self.__offs = 0
        self.__scroll_speed = 300
        self.__padding = 20
        self.__image = None
        self.__warning = None
        self.__colour = (255, 255, 255)

    def update(self, dt):
        """ Update: support blinking. """
        if self.__blink:
            if self.__blink_timer.tick(dt):
                self.__blink_timer.reset()
                self.__visible = not self.__visible
        if self.__warning is not None:
            self.__offs += self.__scroll_speed * dt
            self.__offs = self.__offs % (self.__warning.get_width()+self.__padding)

    def draw(self, renderer, camera):
        """Draw the text to the screen."""

        # Try to obtain some text to draw.
        text = None
        text_component = self.entity.get_component(Text)
        if text_component is not None:
            text = text_component.text

        # Render text.
        if self.__image is None:
            self.__image = renderer.compatible_image_from_text(text, self.__font, self.__colour)
        if self.__warning is None:
            self.__warning = renderer.compatible_image_from_text("WARNING", self.__small_font, self.__colour)

        # Now draw the image, if we have one.
        if self.__visible:
            pos = Vec2d(renderer.screen_rect().center) - Vec2d(self.__image.get_size()) / 2
            renderer.add_job_image(pos, self.__image, coords=Renderer.COORDS_SCREEN, brightness=0.25)

        # Get positions of the 'WARNING' strips
        pos = Vec2d(renderer.screen_rect().center) - Vec2d(self.__image.get_size()) / 2
        y0 = int(pos.y-self.__warning.get_height()-10)
        y1 = int(pos.y+self.__image.get_height()+10)

        # Draw a scrolling warning.
        if self.__blink:
            for (forwards, y) in ((True, y0), (False, y1)):
                (image_width, image_height) = self.__warning.get_size()
                (screen_width, screen_height) = renderer.screen_size()
                x = self.__offs
                if not forwards:
                    x = -x
                start_i = -(x%(image_width+self.__padding))
                for i in range(int(start_i), screen_width, image_width + self.__padding):
                    renderer.add_job_image((i, y), self.__warning, coords=Renderer.COORDS_SCREEN, brightness=0.25)
                rect = renderer.screen_rect()
                rect.height = 5
                rect.bottom = y-5
                renderer.add_job_rect(rect, colour=self.__colour, coords=Renderer.COORDS_SCREEN, brightness=0.25)
                rect.top=y+self.__warning.get_height()+5
                renderer.add_job_rect(rect, colour=self.__colour, coords=Renderer.COORDS_SCREEN, brightness=0.25)
