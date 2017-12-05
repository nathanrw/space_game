import unittest
from ..ecs import *
from testing import *


class MockSystem(ComponentSystem):
    def __init__(self):
        ComponentSystem.__init__(self)
        self.inited = False
    def setup(self, game_services):
        ComponentSystem.setup(self, game_services)
        self.inited = True

class MockSystemB(ComponentSystem):
    pass

class MockComponent(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.killed = False
        self.last_dt = 0
    def manager_type(self):
        return MockSystem
    def on_object_killed(self):
        self.killed = True
    def update(self, dt):
        self.last_dt = dt

class MockComponent2(Component):
    def manager_type(self):
        return MockSystem

class EntityManagerTest(unittest.TestCase):

    def test_create_queued_objects(self):
        """ Should move entities from 'new' set to working set. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        assert entity in entman.new_objects
        entman.create_queued_objects()
        assert entity in entman.objects

    def test_garbage_collect(self):
        """ Should remove entities flagged as garbage. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        entman.create_queued_objects()
        entity.kill()
        assert entity in entman.objects # not removed yet
        entman.garbage_collect()
        assert not entity in entman.objects # removed now

    def test_create_entity(self):
        """ Should create an entity in the 'new' set. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        self.assertEquals(entity.game_services, game_services)
        assert not entity.is_garbage

    def test_create_entity_from_config(self):
        """ Should create an entity with the specified components. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        config = Config({"components": { "src.tests.utils_test.MockComponent": {}}})
        entity = entman.create_entity(config)
        entman.create_queued_objects()
        component = entman.get_component_of_type(entity, MockComponent)
        assert component is not None
        assert isinstance(component, MockComponent)

    def test_register_component_system(self):
        """ Should register the component system and set it up. """

        # Register a system
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        system = MockSystem()
        entman.register_component_system(system)

        # Setup() should be called.
        # The system should be registered.
        # It should be registered by concrete type.
        assert system.inited
        assert system in entman.systems_list
        assert entman.systems[MockSystem] == system

    def test_get_component_system(self):
        """ Should return the registered component system of the right type."""

        # Create a component managed by a system.
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        system = MockSystem()
        entman.register_component_system(system)
        entity = entman.create_entity()
        component = MockComponent(entity, game_services, Config())
        entman.add_component(component)

        # The system should be returned.
        assert entman.get_component_system(component) == system

    def test_get_component_system_by_type(self):
        """ Should return the registered system or register one. """

        # Register a system
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        system = MockSystem()
        entman.register_component_system(system)

        # We should get the system we registered.
        assert entman.get_component_system_by_type(MockSystem) == system

        # Otherwise one should get made.
        systemb = entman.get_component_system_by_type(MockSystemB)
        assert isinstance(systemb, MockSystemB)
        assert entman.get_component_system_by_type(MockSystemB) == systemb

    def test_add_component(self):
        """ Adding a component should let us get that component. """

        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        component = MockComponent(entity, game_services, Config())
        entman.add_component(component)

        assert entman.get_component_of_type(entity, MockComponent) == component

    def test_get_system_by_component_type(self):
        """ Should be possible to get a system from a component type. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        component = MockComponent(entity, game_services, Config())
        entman.add_component(component)
        assert isinstance(entman.get_system_by_component_type(MockComponent), MockSystem)
        
    def test_remove_component_by_concrete_type(self):
        """ Should remove the component we add. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        component = MockComponent(entity, game_services, Config())
        entman.add_component(component)
        entman.create_queued_objects() # Wont work otherwise!
        entman.remove_component_by_concrete_type(entity, MockComponent)
        assert entman.get_component_of_type(entity, MockComponent) == None

    def test_get_component_of_type(self):
        """ Should get the component if present, return None otherwise. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        assert entman.get_component_of_type(entity, MockComponent) == None
        component = MockComponent(entity, game_services, Config())
        entman.add_component(component)
        assert entman.get_component_of_type(entity, MockComponent) == component

    def test_update__does_garbage_collection(self):
        """ Should update the systems. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        entity.kill()
        entman.update(1)
        assert not entity in entman.objects

class ComponentSystemTest(unittest.TestCase):

    def create_system_and_component(self):
        """ Setup a test. """
        class Ret(object):
            def __init__(self):
                self.game_services = create_entman_testing_services()
                self.entman = self.game_services.get_entity_manager()
                self.entity = self.entman.create_entity()
                self.component = MockComponent(self.entity, self.game_services, Config())
                self.system = MockSystem()
                self.entman.register_component_system(self.system)
                self.entman.add_component(self.component)
        return Ret()
        
    def test_do_on_object_killed(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        stuff.entity.kill()
        stuff.system.do_on_object_killed()
        assert stuff.component.killed
        
    def test_create_queued_components(self):
        stuff = self.create_system_and_component()
        stuff.system.create_queued_components()
        assert stuff.component in stuff.system.components
        assert len(stuff.system.components_to_add) == 0
        
    def test_add_component(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        component = MockComponent2(stuff.entity, stuff.game_services, Config())
        stuff.system.add_component(component)
        assert component in stuff.system.components_to_add
        assert stuff.system.object_map[stuff.entity, MockComponent2] == component

    def test_remove_component(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        stuff.system.remove_component(stuff.component)
        assert not stuff.component in stuff.system.components
        
    def test_get_component(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        stuff.entman.create_queued_objects()
        assert stuff.system.get_component(stuff.entity, MockComponent) == stuff.component

    def test_remove_object_component(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        stuff.system.remove_object_component(stuff.entity, MockComponent)
        assert not stuff.component in stuff.system.components

    def test_garbage_collect(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        stuff.entity.kill()
        stuff.system.garbage_collect()
        assert not stuff.component.killed # do_on_object_killed() is called by entman
        assert not stuff.component in stuff.system.components

    def test_update(self):
        stuff = self.create_system_and_component()
        stuff.entman.create_queued_objects()
        stuff.system.update(10)
        assert stuff.component.last_dt == 10

class ComponentTest(unittest.TestCase):

    def create_system_and_component(self):
        """ Setup a test. """
        class Ret(object):
            def __init__(self):
                self.game_services = create_entman_testing_services()
                self.entman = self.game_services.get_entity_manager()
                self.entity = self.entman.create_entity()
                self.component = MockComponent(self.entity, self.game_services, Config())
                self.system = MockSystem()
                self.entman.register_component_system(self.system)
        return Ret()

    def test_manager_type(self):
        stuff = self.create_system_and_component()
        assert stuff.component.manager_type() == MockSystem
        c = Component(stuff.entity, stuff.game_services, Config())
        assert c.manager_type() == ComponentSystem

    def test_is_garbage(self):
        stuff = self.create_system_and_component()
        stuff.entman.add_component(stuff.component)
        stuff.entman.create_queued_objects()
        assert not stuff.component.is_garbage()
        stuff.entity.kill()
        assert stuff.component.is_garbage()
        
    def test_get_system_by_type(self):
        stuff = self.create_system_and_component()
        assert stuff.component.get_system_by_type(MockSystem) == stuff.system

    def test_create_entity(self):
        stuff = self.create_system_and_component()
        stuff.entman.add_component(stuff.component)
        stuff.entman.create_queued_objects()
        assert stuff.component.create_entity() != stuff.entity
        
    def test_get_component(self):
        stuff = self.create_system_and_component()
        stuff.entman.add_component(stuff.component)
        stuff.entman.add_component(MockComponent2(stuff.entity, stuff.game_services, Config()))
        stuff.entman.create_queued_objects()
        assert isinstance(stuff.component.get_component(MockComponent2), MockComponent2)

class EntityTest(unittest.TestCase):
    def create_system_and_component(self):
        """ Setup a test. """
        class Ret(object):
            def __init__(self):
                self.game_services = create_entman_testing_services()
                self.entman = self.game_services.get_entity_manager()
                self.entity = self.entman.create_entity()
                self.component = MockComponent(self.entity, self.game_services, Config())
                self.system = MockSystem()
                self.entman.register_component_system(self.system)
        return Ret()

    def test_kill(self):

        ret = self.create_system_and_component()
        ret.entman.create_queued_objects()
        ret.entity.kill()
        assert ret.entity.is_garbage
        ret.entman.garbage_collect()

        ent2 = ret.entman.create_entity()
        ent3 = ret.entman.create_entity(parent=ent2)
        ret.entman.create_queued_objects()
        ent2.kill()
        assert ent2.is_garbage
        assert ent3.is_garbage
        ret.entman.garbage_collect()

    def test_add_component(self):
        ret = self.create_system_and_component()
        ret.entman.create_queued_objects()
        ret.entity.add_component(ret.component)
        assert ret.entity.get_component(MockComponent) == ret.component

    def test_get_system_by_type(self):
        ret = self.create_system_and_component()
        assert ret.entity.get_system_by_type(MockSystem) == ret.system
        
    def test_create_entity(self):
        ret = self.create_system_and_component()
        ret.entman.create_queued_objects()
        assert ret.entity.create_entity() != ret.entity

    def test_add_child(self):
        ret = self.create_system_and_component()
        ent2 = ret.entman.create_entity()
        ret.entman.create_queued_objects()
        ret.entity.add_child(ent2)
        assert ent2.is_descendant(ret.entity)
        assert ret.entity.is_ancestor(ent2)
