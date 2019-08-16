"""
An entity component system.

An 'entity' is an identity. It can be associated 'components'. A component
imbues an entity with an aspect of state and behaviour. A entity can be
associated with a single component of a given type.

Entities live in an 'entity manager'. This is the central database that
associates entities with components.

Entity creation and component addition are done by calling methods on the
entity manager.

Entity processing 'systems' can be registered with the entity manager. A system
operates on a subset of the entities in the manager, determined by a query.
Systems can be update()ed, allowing them to make changes to the entities they
operate on.

Global services are exposed via a 'game services' object.  This is injected
into each component.
"""

import pickle

from sge.utils import bail

class GameInfo(object):
    """ Information about the running game. """

    def __init__(self):
        """ Initialise the info object. """
        self.framerate = 0
        self.raw_framerate = 0
        self.max_framerate = 0
        self.min_framerate = 0
        self.time_ratio = 0
        self.framerates = []

    def update_framerate(self, framerate, raw_framerate, time_ratio):
        """ Update the framerate tracking data. """
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
        self.debug_level = 0

    def get_renderer(self):
        """ Get the renderer. """
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

    def load(self):
        """ Load the game. """
        pass

    def save(self):
        """ Save the game. """
        pass

    def paused(self):
        """ Is the game paused? """
        return False

    def toggle_pause(self):
        """ Pause the game. """
        pass

    def step(self):
        """ Move forward one frame and then pause. """
        pass

    def get_info(self):
        """ Return information about the game. """
        return GameInfo()


class EntityManager(object):
    """ Manages a set of components systems which themselves manage components. """

    def __init__(self, game_services):
        """ Initialise the entity manager. """

        # Currently existing objects and queue of objects to create.
        self.__entities = []

        # Map from component concrete type to component store.
        self.__component_store = ComponentStore()

        # Entity processing systems.
        self.__systems = []

        # The game services.  These get passed into the objects we create.
        self.__game_services = game_services

        # Is the simulation paused?
        self.__paused = False

        # Next unique entity ID.
        self.__next_id = 0

    def pause(self):
        """ Pause the simulation. """
        self.__paused = True

    def unpause(self):
        """ Unpause the simulation. """
        self.__paused = False

    def paused(self):
        """ Is the simulation paused? """
        return self.__paused

    def save(self, output_file):
        """ Save the state of the entity manager. """
        self.__garbage_collect()
        output = {
            "entities" : self.__entities,
            "components" : self.__component_store
        }
        pickle.dump(output, output_file)

    def load(self, input_file):
        """ Restore the state of the entity manager. """
        try:
            old_state = pickle.load(input_file)
            entities = old_state["entities"]
            for e in entities:
                e.just_unpickled(self.__game_services)
            components = old_state["components"]
            self.__entities = entities
            self.__component_store = components
        except:
            bail()

    def __garbage_collect(self):
        """ Remove all of the objects that have been marked for deletion."""
        self.__component_store.garbage_collect(self.__systems)
        for o in self.__entities:
            if o.is_garbage:
                self.__entities.remove(o)

    def create_component(self, entity, component_type, data={}):
        component = component_type(entity, self.__game_services, data)
        entity.add_component(component)
        return component

    def create_entity_with(self, *types):
        """ Create a new entity with a given list of components. """
        entity = self.create_entity()
        for t in types:
            component = t(entity, self.__game_services, {})
            entity.add_component(component)
        return entity

    def create_entity(self):
        """ Add a new entity. """
        obj = Entity(self.__game_services)
        obj.id = self.__next_id
        self.__next_id += 1
        self.__entities.append(obj)
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
        return self.__component_store.get_all_components(entity)

    def query(self, type1, *types):
        """ Get all entities with a particular set of components. """
        return self.__component_store.query_entities(type1, *types)

    def get_system(self, system_type):
        """ Get a system by type. """
        for system in self.__systems:
            if isinstance(system, system_type):
                return system

    def update(self, dt):
        """ Update all of the systems in priority order. """
        for system in self.__systems:
            if not self.__paused or system.updates_when_paused:
                system.update(dt)
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
        self.__ensure_store_exists(component_type)
        store = self.__component_stores[component_type]
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
        self.__game_services = None

    def setup(self, game_services):
        """ Do any initial setup. """
        self.__game_services = game_services

    @property
    def game_services(self):
        return self.__game_services

    def ecs(self):
        """ Get the ECS """
        return self.game_services.get_entity_manager()

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

    @property
    def updates_when_paused(self):
        """ Does this system keep going when the game is paused? """
        return False


class Component(object):
    """
    A entity component.

    A component imbues an entity with a particular chunk of functionality.

    An entity can have a single component of a given concrete type.

    The initial state of a component is read in from a config object.
    """

    def __init__(self, entity, game_services, config):
        """ Initialise the component. """
        self.__entity = entity
        self.__config = config
        self.cache = {}

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

    def ecs(self):
        """ Get the ECS """
        return self.entity.ecs()

    def __getstate__(self):
        """ We override __getstate__ to get rid of cached data that we can't pickle."""
        ret = self.__dict__.copy()
        assert "cache" in ret
        ret["cache"] = {}
        return ret


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


class EntityRefList(object):
    """ A list of entity references. """

    def __init__(self, *types):
        """ Constructor. """
        self.__list = []
        self.__types = types

    def add_ref_to(self, entity):
        """ Add a reference to an entity. """
        self.__list.append(EntityRef(entity, *self.__types))

    def __len__(self):
        """ Get the length of the list. """
        self.__garbage_collect()
        return len(self.__list)

    def __getitem__(self, index):
        """ Get the reference. """
        self.__garbage_collect()
        return self.__list[index].entity

    def __iter__(self):
        """ Get the iterator. """
        self.__garbage_collect()
        for item in self.__list:
            yield item.entity

    def __garbage_collect(self):
        """ Remove all dead references. """
        self.__list = [ref for ref in self.__list if ref.entity is not None]

    def kill_all(self):
        """ Kill all entities in the list. """
        self.__garbage_collect()
        for ent in self.__list:
            ent.entity.kill()


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
    """

    def __init__(self, game_services):
        """ Constructor. """
        self.__is_garbage = False
        self.__game_services = game_services
        self.id = 0
        self.name = ""

    @property
    def is_garbage(self):
        """ Is this entity scheduled for deletion? """
        return self.__is_garbage

    @property
    def game_services(self):
        """ Get the game services. """
        return self.__game_services

    def ecs(self):
        """ Get the entity manager. """
        return self.__game_services.get_entity_manager()

    def kill(self):
        """ Mark the object for deletion. """
        self.__is_garbage = True

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

    def just_unpickled(self, game_services):
        """ After an entity is unpickled it needs its game services to be set. """
        self.__game_services = game_services

    def __getstate__(self):
        """ We can't serialize the game services. """
        ret = self.__dict__.copy()
        field_name = "_Entity__game_services"
        assert field_name in ret
        ret[field_name] = None
        return ret
