""" Draw the game using a Renderer. """

from pygame import Rect
import math
import random

from .physics import Physics
from .components import Body, Thrusters, Thruster, Hitpoints, Text, Shields, \
                        AnimationComponent, Weapon, Power, Camera, CelestialBody, \
                        Planet, Star, Dockable, Player
from .renderer import Renderer, View
from .systems import get_team
from .ecs import EntityRef
from .utils import Vec2d, Polygon

class CameraView(View):
    """ A view defined by a camera entity. """

    def __init__(self, renderer, camera_entity):
        """ Set up the view. """
        View.__init__(self, renderer)
        self.__camera = EntityRef(camera_entity, Camera, Body)

    @property
    def position(self):
        """ Get the position of the camera, adjusted for shake. """
        return self.__body_component.position + Vec2d(self.__camera_component.horizontal_shake,
                                                      self.__camera_component.vertical_shake)

    @position.setter
    def position(self, value):
        """ Set the (actual) position of the camera. """
        self.__body_component.position = Vec2d(value)

    @property
    def zoom(self):
        """ Get the zoom level. """
        zoom_damping_factor = 2.0 # Arbitrary number chosen to slow down zoom.
        return math.pow(math.e, self.zoom_level / zoom_damping_factor)
        
    @property
    def zoom_level(self):
        """ Get the integer zoom level. """
        return self.__camera_component.zoom

    @property
    def __camera_component(self):
        return self.__camera.entity.get_component(Camera)

    @property
    def __body_component(self):
        return self.__camera.entity.get_component(Body)

class Drawing(object):
    """ An object that can draw the state of the game using a renderer. """

    def __init__(self, game_services):
        self.__entity_manager = game_services.get_entity_manager()
        self.__renderer = game_services.get_renderer()
        self.__resource_loader = game_services.get_resource_loader()
        self.__background_image = None
        self.__game_services = game_services
        self.__text_cache = {}

    def set_background(self, image_name):
        """ Load a background image. """
        self.__background_image = self.__resource_loader.load_image(image_name)

    def draw(self, camera):
        """ Draw the drawables in order of layer. """

        # Draw the background
        self.__draw_background(camera)

        # Draw the things we can draw.
        zoom_map_threshold = -6
        if camera.zoom_level > zoom_map_threshold:
            self.__draw_planets(camera)
            self.__draw_animations(camera)
            self.__draw_thrusters(camera)
            self.__draw_shields(camera)
            self.__draw_lasers(camera)
            self.__draw_hitpoints(camera)
            self.__draw_dock_icon(camera)
        else:
            self.__draw_map(camera)
        self.__draw_text(camera)

    def __draw_background(self, the_view):
        """ Draw the background. """
        (image_width, image_height) = self.__background_image.get_size()
        (screen_width, screen_height) = the_view.size
        pos = the_view.position
        x = int(pos.x / 1000.0)
        y = int(pos.y / 1000.0)
        start_i = -(x%image_width)
        start_j = -(y%image_width)
        for i in range(start_i, screen_width, image_width):
            for j in range(start_j, screen_height, image_height):
                self.__renderer.add_job_image(
                    (i, j),
                    self.__background_image,
                    coords=Renderer.COORDS_SCREEN,
                    level=Renderer.LEVEL_BACK_FAR
                )

    def __draw_dock_icon(self, camera):
        """ Draw a docking indicator. """
        dockable_entities = self.__entity_manager.query(Dockable, Body)
        player_entities = self.__entity_manager.query(Player, Body)
        player = player_entities[0]
        player_body = player.get_component(Body)
        for entity in dockable_entities:
            dockable_body = entity.get_component(Body)
            distance = (player_body.position - dockable_body.position).length
            separation = distance - player_body.size - dockable_body.size - 10
            if separation <= 0:
                self.__draw_static_text(camera, player_body.position, "Dockable object in range")
                return

    def __draw_static_text(self, camera, position, text):
        """ Draw a text string that doesn't change very often. It will be cached
        for the lifetime of the program. """
        if not text in self.__text_cache:
            font = self.__resource_loader.load_font(
                "res/fonts/xolonium/Xolonium-Regular.ttf",  # Fix
                14
            )
            self.__text_cache[text] = self.__renderer.compatible_image_from_text(
                text,
                font,
                (255, 255, 255)
            )
        image = self.__text_cache[text]
        image_size = image.get_size()
        pos = camera.world_to_screen(position)
        pos[0] -= image_size[0] / 2
        pos[1] += image_size[1]
        self.__renderer.add_job_image(
            pos,
            image,
            coords=Renderer.COORDS_SCREEN,
            brightness=0.25
        )

    def __draw_planets(self, camera):
        """ Draw celestial bodies. """
        entities = self.__entity_manager.query(CelestialBody, Body)
        for entity in entities:
            celestial_body = entity.get_component(CelestialBody)
            body = entity.get_component(Body)
            planet = entity.get_component(Planet)
            star = entity.get_component(Star)
            colour = (255, 255, 255)
            brightness = 0.5
            if star is not None:
                brightness = 2
                colour = (255, 255, 200)
            if planet is not None:
                colour = (100, 100, 20)
            self.__renderer.add_job_circle(
                body.position,
                body.size,
                colour=colour,
                width=0,
                brightness=brightness,
            )
        
    def __draw_map(self, camera):
        """ Draw map icons for entities that are too small to see. """
        body_entities = self.__entity_manager.query(Body)
        for entity in body_entities:
            body = entity.get_component(Body)
            if entity.get_component(CelestialBody) is not None:
                continue
            colour = (255, 255, 255)
            team = get_team(entity)
            if team == "player":
                colour = (100, 255, 100)
            elif team == "enemy":
                colour = (255, 100, 100)
            self.__renderer.add_job_circle(
                camera.world_to_screen(body.position),
                5,
                colour=colour,
                width=0,
                brightness=0.2,
                coords=Renderer.COORDS_SCREEN,
                level=Renderer.LEVEL_FORE,
            )
        planet_entities = self.__entity_manager.query(CelestialBody, Body)
        for entity in planet_entities:
            celestial_body = entity.get_component(CelestialBody)
            body = entity.get_component(Body)
            planet = entity.get_component(Planet)
            star = entity.get_component(Star)
            colour = (255, 255, 255)
            brightness = 0.5
            radius = 5
            if star is not None:
                brightness = 2
                colour = (255, 255, 200)
                radius = 10
            if planet is not None:
                colour = (100, 100, 20)
            self.__renderer.add_job_circle(
                camera.world_to_screen(body.position),
                radius,
                colour=colour,
                width=0,
                brightness=0.2,
                coords=Renderer.COORDS_SCREEN,
                level=Renderer.LEVEL_FORE,
            )
            orbit_radius = body.position.length
            length = camera.length_to_screen(orbit_radius, Renderer.COORDS_WORLD)
            if length > 0:
                self.__renderer.add_job_circle(
                    camera.world_to_screen(Vec2d(0, 0)),
                    camera.length_to_screen(orbit_radius, Renderer.COORDS_WORLD),
                    colour=(10, 10, 60),
                    width=2,
                    brightness=0.2,
                    coords=Renderer.COORDS_SCREEN,
                    level=Renderer.LEVEL_BACK
                )
            if not "label_image" in celestial_body.cache:
                font = self.__resource_loader.load_font(
                    "res/fonts/xolonium/Xolonium-Regular.ttf", #  Fix
                    14
                )
                celestial_body.cache["label_image"] = self.__renderer.compatible_image_from_text(
                  celestial_body.name,
                  font,
                  (255, 255, 255)
                )
            image = celestial_body.cache["label_image"]
            image_size = image.get_size()
            pos = camera.world_to_screen(body.position)
            pos[0] -= image_size[0] / 2
            pos[1] += image_size[1]
            self.__renderer.add_job_image(
                pos,
                image,
                coords=Renderer.COORDS_SCREEN,
                brightness=0.25
            )

    def __draw_lasers(self, camera):
        """ Draw laser beams. """
        entities = self.__entity_manager.query(Weapon)
        for entity in entities:

            # We want weapons that are attached to a parent entity with a Body,
            # for position.
            weapon = entity.get_component(Weapon)
            parent = weapon.owner.entity
            if parent is None:
                continue
            body = parent.get_component(Body)
            if body is None:
                continue

            # We only care about beam weapons that are currently firing.
            if weapon.weapon_type != "beam":
                continue
            if weapon.shooting_at is None:
                continue
            if weapon.impact_point is None:
                continue

            # Ok, draw the laser beam.
            p0 = body.position
            p1 = weapon.impact_point
            radius = weapon.config.get("radius", 2)
            red = (255,100,100)
            white = (255,255,255)
            self.__renderer.add_job_line(
                p0,
                p1,
                colour=red,
                width=radius,
                brightness=2
            )
            core_radius = radius//3
            if core_radius > 0:
                self.__renderer.add_job_line(
                    p0,
                    p1,
                    colour=white,
                    width=core_radius,
                    brightness=2
                )

            # If something is being hit, draw an impact effect.
            dir = weapon.impact_normal
            if dir is not None:
                impact_size = radius * 15 * (1.0 + random.random()*0.6-0.8)
                poly1 = Polygon.make_bullet_polygon(p1, p1 + (dir * impact_size))
                self.__renderer.add_job_polygon(poly1, colour=white, brightness=5)
                poly2 = Polygon.make_bullet_polygon(p1, p1 + (dir * impact_size * 0.8))
                self.__renderer.add_job_polygon(poly2, colour=red, brightness=5)

    def __draw_shields(self, camera):
        """ Draw any shields the entity might have. """
        entities = self.__entity_manager.query(Body, Shields)
        for entity in entities:
            shields = entity.get_component(Shields)
            body = entity.get_component(Body)
            width = int((shields.hp/float(shields.max_hp)) * 5)
            if width > 0:
                self.__renderer.add_job_circle(
                    body.position,
                    int(body.size * 2),
                    colour=(100, 100, 255),
                    width=width,
                    brightness=2
                )

    def __draw_animations(self, camera):
        """ Draw an animation on the screen. """
        entities = self.__entity_manager.query(Body, AnimationComponent)
        for entity in entities:
            body = entity.get_component(Body)
            animation = entity.get_component(AnimationComponent)
            kwargs = {
                "brightness": animation.config.get("brightness", 0.0)
            }
            if animation.level is not None:
                kwargs["level"] = animation.level
            self.__renderer.add_job_animation(
                -body.orientation,
                body.position,
                animation.anim,
                **kwargs
            )

    def __draw_thrusters(self, camera):
        """ Draw the thrusters affecting the body. """
        physics = self.__entity_manager.get_system(Physics)
        entities = self.__entity_manager.query(Body, Thrusters)
        for entity in entities:
            thrusters = entity.get_component(Thrusters)
            for thruster_ent in thrusters.thrusters:
                thruster = thruster_ent.get_component(Thruster)
                if thruster.thrust > 0:
                    pos = physics.local_to_world(entity, thruster.position)
                    dir = physics.local_dir_to_world(entity, thruster.direction)
                    length = thruster.thrust / 500.0
                    length *= (1.0 + random.random()*0.1 - 0.2)
                    poly = Polygon.make_bullet_polygon(pos, pos-(dir*length))
                    self.__renderer.add_job_polygon(
                        poly,
                        colour=(255, 255, 255),
                        brightness=2
                    )

    def __draw_hitpoints(self, camera):
        """ Draw the entity's hitpoints, or a marker showing where it
        is if it's off screen. """
        entities = self.__entity_manager.query(Body, Hitpoints)
        for entity in entities:
            body = entity.get_component(Body)
            hitpoints = entity.get_component(Hitpoints)

            # Draw health bar if it's on screen. Otherwise draw marker.
            rect = Rect(0, 0, body.size*2, 6)
            rect.center = rect.center = camera.world_to_screen(body.position)
            rect.top = rect.top - (body.size*1.2)
            self.__draw_bar(
                camera,
                rect,
                hitpoints.hp/float(hitpoints.max_hp),
                (255, 255, 255),
                (255, 0, 0),
                (0, 255, 0)
            )

            # Sneakily draw a power bar as well if the entity has it.
            power = entity.get_component(Power)
            if power is not None:
                rect.top += rect.height + 4
                self.__draw_bar(
                    camera,
                    rect,
                    power.power/float(power.capacity),
                    (255, 255, 255),
                    (100, 50, 0),
                    (255, 255, 0)
                )

    def __draw_text(self, camera):
        """ Draw text on the screen. """

        entities = self.__entity_manager.query(Text)
        for entity in entities:
            component = entity.get_component(Text)

            # Cache an image of the rendered text.
            if not "image" in component.cache:
                font = self.__resource_loader.load_font(
                    component.font_name,
                    component.large_font_size
                )
                component.cache["image"] = self.__renderer.compatible_image_from_text(
                    component.text,
                    font,
                    component.colour
                )
            image = component.cache["image"]

            # Render the text.
            if component.visible:
                pos = Vec2d(self.__renderer.screen_rect().center) \
                        - Vec2d(image.get_size()) / 2
                self.__renderer.add_job_image(
                    pos,
                    image,
                    coords=Renderer.COORDS_SCREEN,
                    brightness=0.25
                )

            # Draw a scrolling warning.
            if component.blink:

                # Cache an image of the rendered 'warning' string.
                if not "warning" in component.cache:
                    small_font = self.__resource_loader.load_font(
                        component.font_name,
                        component.small_font_size
                    )
                    component.cache["warning"] = self.__renderer.compatible_image_from_text(
                        "WARNING",
                        small_font,
                        component.colour
                    )
                warning = component.cache["warning"]

                # Get positions of the 'WARNING' strips
                pos = Vec2d(self.__renderer.screen_rect().center) \
                      - Vec2d(image.get_size()) / 2
                y0 = int(pos.y-warning.get_height()-10)
                y1 = int(pos.y+image.get_height()+10)

                # Draw a row of 'warnings' at the top and bottom.
                for (forwards, y) in ((True, y0), (False, y1)):

                    # Draw a row of 'WARNING's.
                    (image_width, image_height) = warning.get_size()
                    (screen_width, screen_height) = self.__renderer.screen_size()
                    x = component.offset
                    if not forwards:
                        x = -x
                    start_i = -(x%(image_width+component.padding))
                    for i in range(int(start_i), screen_width, image_width + component.padding):
                        self.__renderer.add_job_image(
                            (i, y),
                            warning,
                            coords=Renderer.COORDS_SCREEN,
                            brightness=0.25
                        )

                    # Draw the top bar.
                    rect = self.__renderer.screen_rect()
                    rect.height = 5
                    rect.bottom = y-5
                    self.__renderer.add_job_rect(
                        rect,
                        colour=component.colour,
                        coords=Renderer.COORDS_SCREEN,
                        brightness=0.25
                    )

                    # Draw the bottom bar.
                    rect.top=y+warning.get_height()+5
                    self.__renderer.add_job_rect(
                        rect,
                        colour=component.colour,
                        coords=Renderer.COORDS_SCREEN,
                        brightness=0.25
                    )

    def __draw_bar(self, camera, arg_rect, fraction,
                   col_back, col_0, col_1):
        """ Draw a progress bar """

        # The background
        self.__renderer.add_job_rect(
            arg_rect,
            colour=col_back,
            coords=Renderer.COORDS_SCREEN,
            level=Renderer.LEVEL_FORE,
            brightness=0.2
        )

        # The empty portion.
        rect = Rect(arg_rect)
        rect.inflate_ip(-4, -4)
        self.__renderer.add_job_rect(
            rect,
            colour=col_0,
            coords=Renderer.COORDS_SCREEN,
            level=Renderer.LEVEL_FORE,
            brightness=0.2
        )

        # The full portion.
        rect.width = int(fraction * rect.width)
        self.__renderer.add_job_rect(
            rect,
            colour=col_1,
            coords=Renderer.COORDS_SCREEN,
            level=Renderer.LEVEL_FORE,
            brightness=0.2
        )
