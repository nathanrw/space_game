""" Basic building blocks of the game infrastructure. This includes a scheme
for assembly game objects from components, a system for loading game object
configuration from json data files, and other utilities. """

import random
import pygame
import sys
import json
import os
import math

from loading_screen import LoadingScreen
from vector2d import Vec2d

def fromwin(path):
    """Paths serialized on windows have \\ in them, so we need to convert
       them in order to read them on unix. Windows will happily read unix
       paths so we dont need to worry about going the other way."""
    return path.replace("\\", "/")

def bail():
    """ Bail out, ensuring the pygame windows goes away. """
    pygame.quit()
    sys.exit(1)

class GameServices(object):
    """ Functionality required of the game. """
    def __init__(self):
        pass
    def get_screen(self):
        """ Get the main drawing surface. """
        pass
    def get_player(self):
        """ Get the player's game object. """
        pass
    def get_camera(self):
        """ Get the camera. """
        pass
    def get_entity_manager(self):
        """ Get the entity manager. """
        pass
    def get_resource_loader(self):
        """ Get the object that can load images and so on. """
        pass
    def end_game(self):
        """ Tidy up and exit the program cleanly. """
        pass
    def lookup_type(self, class_path):
        """ Lookup a class by string name so that it can be dynamically
        instantiated. This is used for component and game object creation.
        This implementation has been pinched from an answer on stack overflow:
        http://stackoverflow.com/questions/16696225/dynamically-\
        instantiate-object-of-the-python-class-similar-to-php-new-classname"""

        try:
            module_path, class_name = class_path.rsplit(".", 1)
        except ValueError:
            print "**************************************************************"
            print "ERROR CREATING OBJECT: '%s'" % class_path
            print "Must specify e.g. module.class in path. Got: '%s'." % class_path
            print "**************************************************************"
            bail()           
            
        try:
            module = __import__(module_path, fromlist=[class_name])
        except ImportError:
            print "**************************************************************"
            print "ERROR CREATING OBJECT: '%s'" % class_path
            print "The module '%s' could not be imported." % module_path
            print "**************************************************************"
            bail()

        try:
            cls = getattr(module, class_name)
        except AttributeError:
            print "**************************************************************"
            print "ERROR CREATING OBJECT: '%s'" % class_path
            print "The attribute '%s' could not be found." % class_name
            print "**************************************************************"
            bail()

        # Might not actually be a class. But if it's a function that returns
        # an instance, who cares...
        return cls

class Timer(object):
    """ A simple stopwatch - you tell it how much time has gone by and it
    tells you when it's done. """
    def __init__(self, period):
        self.timer = 0
        self.period = period
    def advance_to_fraction(self, frac):
        self.timer += self.period * frac
    def tick(self, dt):
        self.timer += dt
        return self.expired()
    def expired(self):
        return self.timer >= self.period
    def pick_index(self, num_indices):
        n = num_indices-1
        return min(int((self.timer/float(self.period))*n), n)
    def reset(self):
        self.timer -= self.period
    def randomise(self):
        self.timer = self.period * random.random()

class EntityManager(object):
    """ Manages a set of components systems which themselves manage components. """

    def __init__(self, game_services):
        """ Initialise the entity manager. """

        # Currently existing objects and queue of objects to create.
        self.objects = []
        self.new_objects = []
        self.new_parents = []

        # System stuff
        self.systems = {}
        self.systems_list = []

        # The services we require from the game. This is a little circular as it
        # exposes the entity manager but there you go...
        self.game_services = game_services

        # The componet class has a method manager_type() which defines what type of
        # system is supposed to manage components of that type. If we get a component
        # that claims to be managed by type t, we assume all components of that type
        # are managed by type t, and record the mapping here.
        #
        # Note that we could probably express this relationship a lot more cleanly. But
        # this will do for now...
        self.component_type_mapping = {}

    def create_queued_objects(self):
        """ Create objects that have been queued. """
        for o in self.new_objects:
            self.objects.append(o)
        for pair in self.new_parents:
            pair[0].add_child(pair[1])
        self.new_objects = []
        self.new_parents = []

    def garbage_collect(self):
        """ Remove all of the objects that have been marked for deletion."""
        self.objects = [ x for x in self.objects if not x.is_garbage ]
        for s in self.systems_list:
            s.garbage_collect()

    def create_game_object(self, config_name, *args, **kwargs):
        """ Add a new object. It is initialised, but not added to the game
        right away: that gets done at a certain point in the game loop."""
        loader = self.game_services.get_resource_loader()
        config = loader.load_config_file(config_name)

        # Instantiate the object.
        t = self.game_services.lookup_type(config.get_or_default("type", "src.utils.GameObject"))
        obj = t(*args)
        obj.initialise(self.game_services, config)

        # Add components specified in the config.
        components = config.get_or_default("components", [])
        for component in components:
            component_config = None
            if "config" in component:
                component_config = loader.load_config_file(component["config"])
            else:
                component_config = Config(component)
            component_type = self.game_services.lookup_type(component_config["type"])
            obj.add_component(component_type(obj, self.game_services, component_config))

        # Add the object to the creation queue, and return it to the caller.
        self.new_objects.append(obj)

        # If the object needs to be added as a child, remember that.
        if "parent" in kwargs:
            self.new_parents.append((kwargs["parent"], obj))
        
        return obj
    
    def register_component_system(self, system):
        """ Register a component system. """
        self.systems[system.__class__] = system
        self.systems_list.append(system) # Note: could just insert at right place.
        self.systems_list = sorted(
            self.systems_list,
            lambda x, y: cmp(x.priority, y.priority)
        )

    def get_component_system(self, component):
        """ Get the system that should manage a given component. """
        return self.get_component_system_by_type(component.manager_type())
        
    def get_component_system_by_type(self, t):
        """ Get the component system of the given type. """
        if not t in self.systems:
            self.register_component_system(t())
        return self.systems[t]

    def add_component(self, component):
        """ Add a component to the appropriate managing system. Note that the component
        knows what game object it is attached to. """

        # See comment above.
        if not component.__class__ in self.component_type_mapping:
            self.component_type_mapping[component.__class__] = component.manager_type()

        # Do the business.
        self.get_component_system(component).add_component(component)

    def get_system_by_component_type(self, component_type):
        """ Get the component system meant to manage a given component type. """
        # If we haven't seen a component of this concrete type then
        # there is by definition nothing to remove.
        # Note: A potentially better way could be to instantiate the type and
        # as it what type is supposed to manage it, since it is the component
        # type the knows what its system should be. That would be more correct
        # than this since it would work for base classes too. Of course it
        # sounds a bit convoluted. If/when this becomes a problem im sure we
        # could shuffle the code into a more elegant solution.
        if component_type in self.component_type_mapping:
            system_type = self.component_type_mapping[component_type]
            system = self.get_component_system_by_type(system_type)
            return system
        return None

    def remove_component_by_concrete_type(self, game_object, component_type):
        """ Remove all components of the given ***concrete*** type from the game object. """
        system = self.get_system_by_component_type(component_type)
        if system is not None:
            system.remove_object_components(game_object, component_type)

    def get_component_of_type(self, game_object, t):
        """ Get the component of a particular type on a particular game object.
        Note: this will crash if the object has more than one component of this
        type."""
        system = self.get_system_by_component_type(t)
        if system is not None:
            return system.get_component(game_object, t)

    def get_components_of_type(self, game_object, t):
        """ Get the components of a particular type on a particular game object. """
        system = self.get_system_by_component_type(t)
        if system is not None:
            return system.get_components(game_object, t)

    def update(self, dt):
        """ Update all of the systems in priority order. """
        for system in self.systems_list:
            system.update(dt)
        for s in self.systems_list:
            s.do_on_object_killed()
        self.garbage_collect()

class MapList(object):
    def __init__(self):
        self.__map = {}
    def add(self, key, value):
        if not key in self.__map:
            self.__map[key] = []
        self.__map[key].append(value)
    def remove(self, key, value=None):
        if value is not None:
            if key in self.__map:
                self.__map[key].remove(value)
                if len(self.__map[key]) == 0:
                    del self.__map[key]
        else:
            del self.__map[key]
    def get(self, key):
        if key in self.__map:
            return self.__map[key]
        return []

class ComponentSystem(object):
    """ Manages a set of game object components. It knows how to update the
    components over time, how to get the components out for a particular object,
    and how to remove components when their objects are dead. """

    def __init__(self):
        """ Initialise. """
        self.components = []
        self.priority = 0
        self.object_map = MapList()

    def do_on_object_killed(self):
        """ Fire on_object_killed() for components about to go."""
        for c in self.components:
            if c.is_garbage():
                c.on_object_killed()
        
    def add_component(self, component):
        """ Add a component. """
        self.components.append(component)
        self.object_map.add((component.game_object, component.__class__), component)
        
    def remove_component(self, component):
        """ Remove a particular component. """
        self.components.remove(component)
        self.object_map.remove((component.game_object, component.__class__), component)

    def get_component(self, game_object, component_type):
        """ Get a single component of a particular type."""
        components = self.get_components(game_object, component_type)
        if len(components) > 1:
            raise Exception("Expected there to be either 0 or 1 components attached to game object.")
        elif len(components) == 1:
            return components[0]
        else:
            return None
        
    def get_components(self, game_object, component_type):
        """ Get all components of a particular type attached to the given object. """
        return self.object_map.get((game_object, component_type))
    
    def remove_object_components(self, game_object, component_type):
        """ Remove all components of a particular concrete type from an object. """
        components = self.get_components(game_object, component_type)
        for c in components:
            self.remove_component(c)

    def garbage_collect(self):
        """ Remove all dead components. """
        to_remove = [x for x in self.components if x.is_garbage()]
        for component in to_remove:
            self.remove_component(component)
            
    def update(self, dt):
        """ Update the components. """
        for component in self.components:
            component.update(dt)

# You will notice some overlap between game objects and components e.g.
# create_game_object(), get_system_by_type(). I think eventually everything
# in GameObject apart from is_garbage() i.e. config and game services will
# move completely into components. Currently all that derived game objects
# do is initialise() themselves with different components.

class Component(object):
    """ A game object component. """
    
    def __init__(self, game_object, game_services, config):
        """ Initialise the component. """
        self.game_object = game_object
        self.game_services = game_services
        self.config = config
        
    def manager_type(self):
        """ Return the type of system that should be managing us. """
        return ComponentSystem
    
    def is_garbage(self):
        """ Is our entity dead? """
        return self.game_object.is_garbage
    
    def update(self, dt):
        """ Update the component. """
        pass
    
    def on_object_killed(self):
        """ Do something when the object is killed. """
        pass

    def get_system_by_type(self, t):
        """ Get the system of type "t". Note that there should not be more than
        one system of a given type."""
        return self.game_object.get_system_by_type(t)

    def create_game_object(self, *args):
        """ Create a new game object with the given config and args. """
        return self.game_object.create_game_object(*args)

    def get_component(self, t):
        """ Return the component of a given type. Note that eventually this
        should be restricted such that a component has a formal list of
        dependencies, and it can only get at components of those types. As
        it stands anything can fiddle with anything.

        Note: this will crash if the object contains more than one component
        of this type. """
        return self.game_object.get_component(t)

    def get_components(self, t):
        """ Return the components of a given type. Note that eventually this
        should be restricted such that a component has a formal list of
        dependencies, and it can only get at components of those types. As
        it stands anything can fiddle with anything. """
        return self.game_object.get_components(t)

class GameObject(object):
    """ An object in the game. It knows whether it needs to be deleted, and
    has access to object / component creation services. """

    def __init__(self):
        """ Constructor. Since you don't have access to the game services
        in __init__, more complicated initialisation must be done in
        initialise()."""
        self.is_garbage = False
        self.config = None
        self.game_services = None
        self.children = []

    def initialise(self, game_services, config):
        """ Initialise the object: create drawables, physics bodies, etc. """
        self.game_services = game_services
        self.config = config

    def kill(self):
        """ Mark the object for deletion. """
        self.is_garbage = True
        for child in self.children:
            child.kill()

    def add_component(self, component):
        """ Shortcut to add a component. """
        self.game_services.get_entity_manager().add_component(component)

    def get_system_by_type(self, t):
        """ Get the system of type "t". Note that there should not be more than
        one system of a given type."""
        return self.game_services.get_entity_manager().get_component_system_by_type(t)

    def create_game_object(self, *args):
        """ Create a new game object with the given config and args. """
        return self.game_services.get_entity_manager().create_game_object(*args)

    def get_component(self, t):
        """ Return the components of a given type. Note that eventually this
        should be restricted such that a component has a formal list of
        dependencies, and it can only get at components of those types. As
        it stands anything can fiddle with anything.

        Note: this will crash if the object contains more than one component
        of this type. """
        return self.game_services.get_entity_manager().get_component_of_type(self, t)

    def get_components(self, t):
        """ Return the components of a given type. Note that eventually this
        should be restricted such that a component has a formal list of
        dependencies, and it can only get at components of those types. As
        it stands anything can fiddle with anything. """
        return self.game_services.get_entity_manager().get_components_of_type(self, t)

    def add_child(self, obj):
        """ Add a child game object. """
        self.children.append(obj)

class Camera(Component):
    """ A camera, which drawing is done in relation to. """

    def __init__(self, game_object, game_services, config):
        """ Initialise the camera. """
        Component.__init__(self, game_object, game_services, config)
        self.__position = Vec2d(0, 0)
        self.__screen = game_services.get_screen()
        self.__max_shake = 20
        self.__damping_factor = 10
        self.__shake = 0
        self.__vertical_shake = 0
        self.__horizontal_shake = 0

    def surface(self):
        """ Get the surface drawing will be done on. """
        return self.__screen

    def world_to_screen(self, world):
        """ Convert from world coordinates to screen coordinates. """
        centre = Vec2d(self.__screen.get_size())/2
        return centre + world - self.position

    def screen_to_world(self, screen):
        """ Convert from screen coordinates to world coordinates. """
        centre = Vec2d(self.__screen.get_size())/2
        return screen + self.position - centre

    def check_bounds_world(self, bbox):
        """ Check whether a world space bounding box is on the screen. """
        if bbox is None: return True
        self_box = self.__screen.get_rect()
        self_box.center = self.position
        return bbox.colliderect(self_box)

    def check_bounds_screen(self, bbox):
        """ Check whether a screen space bounding box is on the screen. """
        if bbox is None: return True
        return self.__screen.get_rect().colliderect(bbox)

    def update(self, dt):
        """ Update the screen shake effect. """
        if self.__shake > 0:
            self.__shake -= dt * self.__damping_factor
        if self.__shake < 0:
            self.__shake = 0
        self.__vertical_shake = (1-2*random.random()) * self.__shake
        self.__horizontal_shake = (1-2*random.random()) * self.__shake

    def apply_shake(self, shake_factor, position):
        """ Apply a screen shake effect. """
        displacement = self.__position - position
        distance = displacement.length
        screen_diagonal = (Vec2d(self.__screen.get_size())/2).length
        max_dist = screen_diagonal * 2
        amount = max(shake_factor * (1.0 - distance/max_dist), 0)
        self.__shake = min(self.__shake+amount, self.__max_shake)

    @property
    def position(self):
        """ Get the position of the camera, adjusted for shake. """
        return self.__position + Vec2d(self.__horizontal_shake,
                                       self.__vertical_shake)

    @position.setter
    def position(self, value):
        """ Set the (actual) position of the camera. """
        self.__position = Vec2d(value)

class Config(object):
    """ A hierarchical data store. """
    
    def __init__(self, wrap=None):
        """ Initialise an empty data store, or a wrapping one if a dictionary
        is provided."""
        self.parent = None
        self.data = {}
        self.filename = None
        self.child_path = None

        if wrap is not None:
            self.data = wrap

    def create_child(self, path):
        """ Create a config wrapping a child node. """
        cfg = Config()
        cfg.parent = self.parent
        cfg.data = self.data
        cfg.filename = self.filename
        cfg.child_path = path
        return cfg
        
    def load(self, filename):
        """ Load data from a file. Remember the file so we can save it later. """
        self.filename = os.path.join("res/configs/", filename)
        print "Loading config: ", self.filename
        try:
            self.data = json.load(open(self.filename, "r"))
        except Exception, e:
            print e
            print "**************************************************************"
            print "ERROR LOADING CONFIG FILE: ", self.filename
            print "Probably either the file doesn't exist, or you forgot a comma!"
            print "**************************************************************"
            bail() # Bail - we might be in the physics thread which ignores exceptions
        parent_filename = self.__get("deriving")
        if parent_filename is not None:
            self.parent = Config()
            self.parent.load(parent_filename)
            
    def save(self):
        """ Save to our remembered filename. """
        json.dump(self.data, open(self.filename, "w"), indent=4, separators=(',', ': '))

    def __getitem__(self, key):
        """ Get some data out. """
        got = self.get_or_none(key)
        if got is None:
            print "**************************************************************"
            print "ERROR READING CONFIG ATTRIBUTE: %s" % key
            print "CONFIG FILE: %s" % self.filename
            print "It's probably not been added to the file, or there is a bug."
            print "**************************************************************"
            bail() # Bail - we might be in the physics thread which ignores exceptions
        return got
        
    def get_or_default(self, key, default):
        """ Get some data out. """
        got = self.get_or_none(key)
        if got is None:
            return default
        else:
            return got

    def get_or_none(self, key):
        """ Get some data, or None if it isnt found. """
        if self.child_path is not None:
            key = self.child_path + "." + key
        got = self.__get(key)
        if got is None and self.parent is not None:
            got = self.parent.get_or_none(key)
        return got

    def __get(self, key):
        """ Retrieve some data from our data store."""
        try:
            tokens = key.split(".")
            ret = self.data
            for tok in tokens:
                ret = ret[tok]
            return ret
        except:
            return None

class ResourceLoader(object):
    """ A resource loader - loads and caches resources which can be requested by the game. """
    
    def __init__(self):
        """ Initialise the resource loader. """
        self.images = {}
        self.animations = {}
        self.fonts = {}
        self.configs = {}
        self.minimise_image_loading = False
        self.preload_name = None

    def preload(self, screen):
        """ Preload certain resources to reduce game stutter. """
        self.preload_name = "preload.txt"
        if self.minimise_image_loading:
            self.preload_name = "preload_min.txt"
        if os.path.isfile(self.preload_name):
            filenames = json.load(open(self.preload_name, "r"))
            loading = LoadingScreen(len(filenames), screen)
            for filename in filenames:
                self.load_image(filename)
                loading.increment()

    def save_preload(self):
        """ Save a list of what to preload next time. """
        if self.preload_name is not None and not os.path.isfile(self.preload_name):
            json.dump(
                self.images.keys(),
                open(self.preload_name, "w"),
                indent=4,
                separators=(',', ': ')
            )

    def load_font(self, filename, size):
        """ Load a font from the file system. """
        if not (filename, size) in self.fonts:
            self.fonts[(filename, size)] = pygame.font.Font(filename, size)
        return self.fonts[(filename, size)]
        
    def load_image(self, filename):
        """ Load an image from the file system. """
        filename = fromwin(filename)
        if not filename in self.images:
            self.images[filename] = pygame.image.load(filename).convert_alpha()
            print "Loaded image: %s" % filename
        return self.images[filename]

    def load_animation(self, filename):
        """ Load an animation from the filesystem. """
        if not filename in self.animations:
            fname = os.path.join(os.path.join("res/anims", filename), "anim.txt")
            anim = json.load(open(fname))
            name_base = anim["name_base"]
            num_frames = anim["num_frames"]
            extension = anim["extension"]
            period = anim["period"]
            frames = []
            for i in range(num_frames):
                # If we want to load faster disable loading too many anims...
                if self.minimise_image_loading and num_frames > 10 and i % 10 != 0:
                    continue
                padded = (4-len(str(i)))*"0" + str(i)
                img_filename = os.path.join(os.path.dirname(fname), name_base + padded + extension)
                frames.append(self.load_image(img_filename))
            self.animations[filename] = (frames, period)
            print "Loaded animation: %s" % filename
        (frames, period) = self.animations[filename]
        return Animation(frames, period)

    def load_config_file(self, filename):
        """ Read in a configuration file. """
        if not filename in self.configs:
            c = Config()
            c.load(filename)
            self.configs[filename] = c
        return self.configs[filename]

class Animation(object):
    """ A set of images with a timer which determines what image gets drawn
    at any given moment. """
    def __init__(self, frames, period):
        self.frames = frames
        self.timer = Timer(period)
        self.orientation = 0
    def tick(self, dt):
        return self.timer.tick(dt)
    def reset(self):
        self.timer.reset()
    def draw(self, world_pos, camera):
        img = self.frames[self.timer.pick_index(len(self.frames))]
        if (self.orientation != 0):
            img = img = pygame.transform.rotate(img, self.orientation)
        screen_pos = camera.world_to_screen(world_pos) - Vec2d(img.get_rect().center)
        camera.surface().blit(img, screen_pos)
    def randomise(self):
        self.timer.randomise()
    def get_max_bounds(self):
        # Assume all frames the same size. Return biggest rect considering
        # all possible rotations.
        rect = self.frames[0].get_rect()
        size = math.sqrt(rect.width*rect.width + rect.height+rect.height)
        rect.width = size
        rect.height = size
        return rect
        
