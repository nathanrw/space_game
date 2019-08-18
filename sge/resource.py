"""
Resource loading code.  Resources are read once and then cached, keyed on
their filename.

Resources live in the 'res' tree in the same directory as 'run.py'.

The capabilities to read cetain resources are injected.  For instance,
image and font loading are specific to the renderer being used, so
the renderer must be injected via a setter method.  This must be done
before images are loaded.

The 'minimise_image_loading' flag is intended to speed load times and reduce
memory usage by only reading in a fraction of an animation's frames.

To prevent stutter, all resources can be read at once using preload(),
this will display a loading screen via the injected renderer and read
all resources in the 'res' tree.
"""

from sge.utils import Timer

import math
import pygame
import os
import yaml

class ResourceLoader(object):
    """ A resource loader - loads and caches resources which can be requested by the game. """

    def __init__(self):
        """ Initialise the resource loader. """
        self.__renderer = None
        self.__minimise_image_loading = True
        self.__images = {}
        self.__image_aliases = yaml.load("res/images/aliases.yaml")
        self.__animations = {}
        self.__fonts = {}
        self.__font_aliases = yaml.load("res/fonts/aliases.yaml")
        self.__sounds = {}

    def set_renderer(self, renderer):
        """ Set the renderer to use to load images. """
        self.__renderer = renderer

    def set_minimise_image_loading(self, yes):
        """ Minimise image loading. """
        self.__minimise_image_loading = yes

    def preload(self, loading_screen_factory, font, background):
        """ Preload certain resources to reduce game stutter. """

        # List all animation frames.
        anims = self.__list_animations()

        # Number of steps.
        count = len(anims)
        assert count > 0
        loading = loading_screen_factory(count, self.__renderer, font, background)

        # Read in the frames.
        for anim in anims:
            self.load_animation(anim)
            loading.increment()

        # The renderer might like to return us proxy objects and initialise
        # them in one go, so let it do that.
        self.__renderer.post_preload()

    def load_font(self, filename, size):
        """ Load a font from the file system. """
        if filename in self.__font_aliases:
            filename = os.path.join("res/fonts", self.__font_aliases[filename])
        if not (filename, size) in self.__fonts:
            self.__fonts[(filename, size)] = self.__renderer.load_compatible_font(filename, size)
        return self.__fonts[(filename, size)]

    def load_gui_font(self, filename, size):
        """ Load a font from the file system for use with the GUI. """
        if filename in self.__font_aliases:
            filename = os.path.join("res/fonts", self.__font_aliases[filename])
        if not (filename, size) in self.__fonts:
            self.__fonts[(filename, size)] = self.__renderer.load_compatible_gui_font(filename, size)
        return self.__fonts[(filename, size)]

    def load_image(self, filename):
        """ Load an image from the file system. """
        if filename in self.__image_aliases:
            filename = os.path.join("res/images", self.__image_aliases[filename])
        if not filename in self.__images:
            self.__images[filename] = self.__renderer.load_compatible_image(filename)
            print( "Loaded image: %s" % filename )
        return self.__images[filename]

    def __list_animations(self):
        """ List all of the available animations. """
        anims = []
        dirname = "res/anims"
        for anim_name in os.listdir(dirname):
            anim_file = os.path.join(dirname, os.path.join(anim_name, "anim.txt"))
            if os.path.isfile(anim_file):
                anims.append(anim_name)
        return anims

    def __load_animation_definition(self, name):
        """ Load the definition of an animation, included the names of all
        frames. """
        fname = os.path.join(os.path.join("res/anims", name), "anim.txt")
        anim = yaml.load(open(fname))
        anim["frames"] = []
        for i in range(anim["num_frames"]):
            # If we want to load faster disable loading too many anims...
            if self.__minimise_image_loading and anim["num_frames"] > 10 and i % 10 != 0:
                continue
            padded = (4-len(str(i)))*"0" + str(i)
            img_name = anim["name_base"] + padded + anim["extension"]
            img_filename = os.path.join(os.path.dirname(fname), img_name)
            anim["frames"].append(img_filename)
        return anim

    def load_animation(self, filename):
        """ Load an animation from the filesystem. """
        if not filename in self.__animations:
            anim = self.__load_animation_definition(filename)
            frames = self.__renderer.load_compatible_anim_frames(anim["frames"])
            self.__animations[filename] = (frames, anim["period"])
            print( "Loaded animation: %s" % filename )
        (frames, period) = self.__animations[filename]
        return Animation(frames, period)

    def load_sound(self, filename):
        """ Load a sound. """
        if not filename in self.__sounds:
            dirname = "res/sounds"
            self.__sounds[filename] = Sound(os.path.join(dirname, filename))
        return self.__sounds[filename]

class Sound(object):
    """ A sound that can be played. """

    def __init__(self, filename):
        """ Load the pygame sound. """
        self.__sound = pygame.mixer.Sound(filename)

    def play_positional(self, position_wrt_listener):
        """ Play at a volume related to the position. """

        # Just use linear attenuation.
        dist = position_wrt_listener.length
        max_dist = 750
        volume = min(max(1.0 - dist/max_dist, 0), 1)

        # Play at the attenuated volume.
        self.play(volume)

    def play(self, volume=1.0):
        """ Play at a fraction of the volume. """
        assert 0 <= volume and volume <= 1
        # Note: this is probably not quite correct, since if the sound
        # is already playing then set_volume() will set the volume on
        # it. I'm not sure if you can play the same sound multiple
        # times simultaneously. Might need to create copies of the
        # sound, I'm not sure.
        if volume > 0.05:
            self.__sound.set_volume(volume)
            self.__sound.play()

class Animation(object):
    """ A set of images with a timer which determines what image gets drawn
    at any given moment. """
    def __init__(self, frames, period):
        self.frames = frames
        self.timer = Timer(period)
    def tick(self, dt):
        return self.timer.tick(dt)
    def reset(self):
        self.timer.reset()
    def randomise(self):
        self.timer.randomise()
    def get_max_bounds(self):
        # Assume all frames the same size. Return biggest rect considering
        # all possible rotations.
        rect = self.frames[0].get_rect()
        size = math.sqrt(rect.width*rect.width + rect.height*rect.height)
        rect.width = size
        rect.height = size
        return rect
