"""
An entity component system.

An 'entity' is an identity. It can be associated 'components'. A component
imbues an entity with an aspect of state and behaviour. A entity can be
associated with a single component of a given type.

Entities can be 'owned' by other entities. This ties their lifetimes together -
when a parent entity is destroyed, its children are destroyed too. The parents
and children of an entity can be enquired.

Entities live in an 'entity manager'. This is the central database that
associates entities with components.

Entity creation and component addition are done by calling methods on the
entity manager. This doesn't affect the current state of the entity manager
until the end of the current frame - this avoids adding items to the entity
manager in the middle of an update(),

If a config is passed into create_entity(), then components can be instantiated
dynamically. The '**kwargs' argument is forwarded to the setup() method on each
component as it is added.  Components types are read from the 'components' map
in the config, each component entry is passed into the created component as its
config.  For instance:

    components:
      src.behaviours.Team:
        team: player
      src.physics.Body:
        mass: 100
        size: 35

specifies an entity with two components, a Body and a Team.  The team defaults
to the 'player' team, and the body has a default mass and size.  If we do

    entity = ecs.create_entity("my_config.txt", team='enemy')

then the Team component's setup() method knows to instead be on the 'enemy'
team, which is extracted from the **kwargs.

Entity processing 'systems' can be registered with the entity manager. A system
operates on a subset of the entities in the manager, determined by a query.
Systems can be update()ed, allowing them to make changes to the entities they
operate on.

Global services are exposed via a 'game services' object.  This is injected
into each component.
"""

from .config import Config
from .utils import lookup_type

class GameInfo(object):
    """ Information about the running game. """
    def __init__(self):
        self.framerate = 0
        self.raw_framerate = 0
        self.max_framerate = 0
        self.min_framerate = 0
        self.time_ratio = 0
        self.framerates = []
    def update_framerate(self, framerate, raw_framerate, time_ratio):
        self.framerate = framerate
        self.min_framerate = min(self.min_framerate, framerate)
        self.max_framerate = max(self.max_framerate, framerate)
        self.raw_framerate = raw_framerate
        self.time_ratio = time_ratio
        self.framerates.append(framerate)
        if len(self.framerates) > 30:
            self.framerates.pop(0)

class GameServices(object):
    """ Functionality required of the game. """
    def __init__(self):
        pass
    def get_renderer(self):
        """ Get the renderer. """
        pass
    def get_player(self):
        """ Get the player's entity. """
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
    def get_info(self):
        """ Return information about the game. """
        return GameInfo()
    def get_debug_level():
        """ Get the debug level. """
        return 0

class EntityManager(object):
    """ Manages a set of components systems which themselves manage components. """

    def __init__(self, game_services):
        """ Initialise the entity manager. """

        # Currently existing objects and queue of objects to create.
        self.__entities = []
        self.__new_entities = []
        self.__new_parent_child_pairs = []

        # Map from component concrete type to component store.
        self.__component_store = ComponentStore()

        # Entity processing systems.
        self.__systems = []

        # The game services.  These get passed into the objects we create.
        self.__game_services = game_services

    def create_queued_objects(self):
        """ Create objects that have been queued. """

        # Move new entities to the working set.
        self.__entities += self.__new_entities
        del self.__new_entities[:]

        # Instate new parent-child relationships.
        for pair in self.__new_parent_child_pairs:
            pair[0].add_child(pair[1])
        del self.__new_parent_child_pairs[:]

    def __garbage_collect(self):
        """ Remove all of the objects that have been marked for deletion."""
        self.__component_store.garbage_collect(self.__systems)
        for o in self.__entities:
            if o.is_garbage:
                self.__entities.remove(o)

    def create_entity_with(self, *types, **kwargs):
        """ Create a new entity with a given list of components. """
        entity = self.create_entity()
        for t in types:
            component = t(entity, self.__game_services, Config())
            component.setup(**kwargs)
            entity.add_component(component)
        return entity

    def create_entity(self, config_name=None, **kwargs):
        """ Add a new object. It is initialised, but not added to the game
        right away: that gets done at a certain point in the game loop."""

        loader = self.__game_services.get_resource_loader()

        # load the config if specified.
        config = None
        if config_name is not None:
            if isinstance(config_name, Config):
                config = config_name
            else:
                config = loader.load_config_file(config_name)
        else:
            config = Config()

        # Instantiate the object.
        t = lookup_type(config.get_or_default("type", "src.ecs.Entity"))
        obj = t(self.__game_services)

        # Add components specified in the config.
        components = config.get_or_default("components", Config())
        for component in components:
            component_config = components[component]
            component_type = lookup_type(component)
            component = component_type(obj, self.__game_services, component_config)
            component.setup(**kwargs)
            obj.add_component(component)

        # Add the object to the creation queue, and return it to the caller.
        self.__new_entities.append(obj)

        # If the object needs to be added as a child, remember that.
        if "parent" in kwargs:
            self.__new_parent_child_pairs.append((kwargs["parent"], obj))

        return obj

    def register_component_system(self, system):
        """ Register a component system. """
        self.__systems.append(system)
        system.setup(self.__game_services)
        self.__systems = sorted(
            self.__systems,
            key = lambda x: x.priority
        )

    def add_component(self, component):
        """ Add a component to the appropriate store. """
        self.__component_store.add(component.entity, component)

        # Notify the systems.
        for system in self.__systems:
            if system.matches(component.__class__):
                system.on_component_add(component)

    def remove_component_by_concrete_type(self, entity, component_type):
        """ Remove the component of the given ***concrete*** type from the entity. """
        self.__component_store.remove(entity, component_type, self.__systems)

    def get_component_of_type(self, entity, t):
        """ Get the component of a particular type on a particular entity. """
        return self.__component_store.get(entity, t)

    def get_all_components(self, entity):
        """ Get all components of an entity. """
        return self.__component_store.get_all(entity)

    def query(self, type1, *types):
        """ Get all entities with a particular set of components. """

        # Get the matching entities.
        matches = self.__component_store.query_entities(type1, *types)

        # Don't expose entities that don't technically exist yet.
        return filter(lambda x: x not in self.__new_entities, matches)

    def get_system(self, system_type):
        """ Get a system by type. """
        for system in self.__systems:
            if isinstance(system, system_type):
                return system

    def update(self, dt):
        """ Update all of the systems in priority order. """
        for system in self.__systems:
            system.update(dt)
        self.__component_store.update(dt)
        self.__garbage_collect()

class ComponentStore(object):
    """ Data storage for components. """

    def __init__(self):
        """ Constructor. """
        self.__component_stores = {}

    def add(self, entity, component):
        """ Add a component to an entity """
        self.__ensure_store_exists(component.__class__)
        assert self.get(entity, component.__class__) is None
        self.__component_stores[component.__class__][entity] = component

    def get(self, entity, component_type):
        """ Get a component from an entity. """
        self.__ensure_store_exists(component_type)
        try:
            return self.__component_stores[component_type][entity]
        except KeyError:
            return None

    def remove(self, entity, component_type, systems):
        """ Remove a component from an entity. """
        self.__ensure_store_exists(component.__class__)
        store = self.__component_stores[component.__class]
        if entity in store:

            # Notify observers.
            for system in systems:
                if system.matches(component_type):
                    system.on_component_remove(store[entity])

            # Remove the component.
            del store[entity]

    def query_entities(self, type1, *types):
        """ Get the entities that have a particular set of components. """
        self.__ensure_store_exists(type1)
        ret = set(self.__component_stores[type1].keys())
        for t in types:
            self.__ensure_store_exists(t)
            ret = ret.intersection(set(self.__component_stores[t].keys()))
        return ret

    def get_all_components(self, entity):
        """ Get all of the components of a given entity. """
        return [c for c in map(
            lambda t: self.get(entity, t),
            self.__component_stores.keys()
        ) if c is not None]

    def update(self, dt):
        """ Update each component for a time step. """

        # Get a snapshot of the components that exist. This avoids updating
        # newly created components.
        cs = []
        for component_type in self.__component_stores:
            store = self.__component_stores[component_type]
            for entity in store:
                cs.append(store[entity])

        # Now do the update - but entities might get killed and we dont want
        # to update them.
        for c in cs:
            if not c.entity.is_garbage:
                c.update(dt)

    def garbage_collect(self, systems):
        """ Delete each component of each entity that is marked for deletion. """

        # First notify any observers that might be interested.
        for component_type in self.__component_stores:
            store = self.__component_stores[component_type]
            for entity in store:
                if entity.is_garbage:
                    for system in systems:
                        if system.matches(component_type):
                            system.on_component_remove(store[entity])
                    store[entity].on_object_killed()

        # Now perform the deletion.
        for component_type in self.__component_stores:
            store = self.__component_stores[component_type]
            entities = store.keys()
            for entity in entities:
                if entity.is_garbage:
                    del store[entity]

    def __ensure_store_exists(self, component_type):
        """ Ensure an object store exists for the component type. """
        if not component_type in self.__component_stores:
            self.__component_stores[component_type] = {}


class ComponentSystem(object):
    """ Entity processing system.  Can do updates on a set of entities with
    a given set of components. """

    def __init__(self, types, priority=0):
        """ Initialise. """
        self.__types = types
        self.__priority = priority

    def setup(self, game_services):
        """ Do any initial setup. """
        self.__game_services = game_services

    def entities(self):
        """ Get the entities managed by this system. """
        return self.__game_services.get_entity_manager().query(*self.__types)

    def update(self, dt):
        """ Update the system. """
        pass

    def matches(self, component_type):
        """ Does the component come under our remit? """
        return len(self.__types) == 0 or component_type in self.__types

    def on_component_add(self, component):
        """ Called when a component is added that matches our expression. """
        pass

    def on_component_remove(self, component):
        """ Called when a component is removed that matches our expression. """
        pass

    @property
    def priority(self):
        """ Priority - determines order of system update() calls. """
        return self.__priority


class Component(object):
    """
    A entity component.

    A component imbues an entity with a particular chunk of functionality.

    An entity can have a single component of a given concrete type.

    Components have state, and can also update() themselves. (This is an impure
    shortcut to avoid defining a system per component, and makes the code more
    object oriented - it could be a mistake though.  A 'pure' ecs would have
    this update() and on_object_killed() stuff in a system.)

    The initial state of a component is read in from a config object.
    """

    def __init__(self, entity, game_services, config):
        """ Initialise the component. """
        self.__entity = entity
        self.__game_services = game_services
        self.__config = config

    def setup(self, **kwargs):
        """ Do any extra initialisation based on optional arguments. """
        pass

    @property
    def entity(self):
        """ Get the entity containing this component. """
        return self.__entity

    @property
    def config(self):
        """ Get the config used to initialise this component. """
        return self.__config

    def is_garbage(self):
        """ Is our entity dead? """
        return self.entity.is_garbage

    def update(self, dt):
        """ Update the component. """
        pass

    def on_object_killed(self):
        """ Do something when the object is killed. """
        pass


class EntityRef(object):
    """ A reference to an entity that resets itself when the entity is killed. """

    def __init__(self, entity, *types):
        """ Construct a reference. """
        self.__entity = entity
        self.__types = types

    @property
    def entity(self):
        """ The wrapped entity.  It will only not be None if it has the right
        components and isnt dead. """
        if self.__entity:
            if self.__entity.is_garbage:
                self.__entity = None
            else:
                for t in self.__types:
                    if not self.__entity.has_component(t):
                        self.__entity = None
                        break
        return self.__entity

    @entity.setter
    def entity(self, entity):
        """ Set the wrapped entity. """
        self.__entity = entity


class Entity(object):
    """
    An object in the game. It knows whether it needs to be deleted, and
    has access to object / component creation services.

    An entity is just an identity.  It has no specific functionality as such,
    all of that is imbued by components.  No classes should be derived from
    Entity, and instances should only be created by the EntityManager.

    An entity can be kill()ed. This will mark it for deletion.  'is_garbage'
    will then be True. At the end of the current frame, on_object_killed() will
    be called for that entity, and the entity will be removed from the entity
    manager.

    Entities can 'own' other entities.  When a parent entity is kill()ed, all
    of its children will be kill()ed too.  Additionally if you have an entity,
    you can query its parent and children.
    """

    def __init__(self, game_services):
        """ Constructor. """
        self.__is_garbage = False
        self.__game_services = game_services
        self.__children = []
        self.__parent = None

    @property
    def is_garbage(self):
        """ Is this entity scheduled for deletion? """
        return self.__is_garbage

    @property
    def parent(self):
        """ Get the parent entity, if any. """
        return self.__parent

    @property
    def game_services(self):
        """ Get the game services. """
        return self.__game_services

    def ecs(self):
        """ Get the entity manager. """
        return self.__game_services.get_entity_manager()

    def kill(self):
        """ Mark the object for deletion. """
        # Note: I'm not sure whether objects being kill()ed twice should
        # count as a bug. I was getting exceptions in physics engine
        # callbacks due to this happening. Checking whether the object
        # is garbage before doing the business solves the problem - but
        # it could be I've just "fixed the symptom." I'm treating it as
        # not a bug, since kill() is a "public" API and I don't think it
        # makes sense to have the caller check is_garbage before calling it.
        if not self.__is_garbage:

            # Set the garbage flag.
            self.__is_garbage = True

            # Kill all of our children. Note that we copy the list because
            # killing a child removes it from the parent.
            children = self.__children[:]
            for child in children:
                child.kill()

            # If we are a child, break the link with our parent.
            if self.__parent is not None:
                self.__parent.__children.remove(self)
            self.__parent = None

    def add_component(self, component):
        """ Shortcut to add a component. """
        self.ecs().add_component(component)

    def get_component(self, t):
        """ Return the component of the given type - or None, if this entity
        has no such component. """
        return self.ecs().get_component_of_type(self, t)

    def has_component(self, t):
        """ Does the entity have a component of a particular type? """
        return self.get_component(t) is not None

    def get_ancestor_with_component(self, t):
        """ See if an ancestor of this entity has a particular component.

        This returns the first such ancestor, or None.
        """
        if self.__parent is not None:
            c = self.__parent.get_component(t)
            if c is not None:
                return self.__parent
            else:
                return self.__parent.get_ancestor_with_component(t)
        else:
            return None

    def get_children_with_component(self, t):
        """ Get each (direct) child entity with a given component type. """
        for entity in self.__children:
            if entity.get_component(t) is not None:
                yield entity

    def get_children(self):
        """ Get all of the children. """
        for entity in self.__children:
            yield entity

    def add_child(self, obj):
        """ Add a child entity. """
        assert obj.parent is None
        self.__children.append(obj)
        obj.__parent = self

    def is_descendant(self, obj):
        """ Is this object descended from that one? """
        return obj.is_ancestor(self)

    def is_ancestor(self, obj):
        """ Is that object descended from this one? """
        if obj == self:
            return True
        for c in self.__children:
            if c.is_ancestor(obj):
                return True
        return False


