import unittest
from testing import *


class MockSystem(ComponentSystem):
    def __init__(self):
        ComponentSystem.__init__(self, [MockComponent])
        self.inited = False
    def setup(self, game_services):
        ComponentSystem.setup(self, game_services)
        self.inited = True
    def update(self, dt):
        entities = self.entities()
        for e in entities:
            c = e.get_component(MockComponent)
            c.last_dt = dt
    def on_component_add(self, component):
        component.added += 1
    def on_component_remove(self, component):
        component.removed += 1


class MockSystemB(ComponentSystem):
    pass


class MockComponent(Component):
    def __init__(self, entity, game_services, config):
        Component.__init__(self, entity, game_services, config)
        self.last_dt = 0
        self.added = 0
        self.removed = 0


class MockComponent2(Component):
    pass


class EntityManagerTest(unittest.TestCase):

    def test_create_queued_objects(self):
        """ Should move entities from 'new' set to working set. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity_with(MockComponent)
        assert entity not in entman.query(MockComponent)
        assert entity in entman.query_include_queued(MockComponent)
        entman.create_queued_objects()
        assert entity in entman.query(MockComponent)

    def test_garbage_collect(self):
        """ Should remove entities flagged as garbage. """
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity_with(MockComponent)
        entman.create_queued_objects()
        entity.kill()
        assert entity in entman.query(MockComponent) # not removed yet
        entman.update(0)
        assert not entity in entman.query(MockComponent) # removed now

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
        config = Config({"components": { "src.tests.ecs_test.MockComponent": {}}})
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
        assert entman.get_system(MockSystem) == system

    def test_get_system(self):
        """ Should return the registered system or register one. """

        # Register a system
        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        system = MockSystem()
        entman.register_component_system(system)

        # We should get the system we registered.
        assert entman.get_system(MockSystem) == system

        # Otherwise one should NOT get made.
        systemb = entman.get_system(MockSystemB)
        assert systemb is None
        
    def test_add_component(self):
        """ Adding a component should let us get that component. """

        game_services = create_entman_testing_services()
        entman = game_services.get_entity_manager()
        entity = entman.create_entity()
        component = MockComponent(entity, game_services, Config())
        entman.add_component(component)

        assert entman.get_component_of_type(entity, MockComponent) == component
        
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
        entity = entman.create_entity_with(MockComponent)
        assert entity in entman.query_include_queued(MockComponent)
        entity.kill()
        entman.update(1)
        assert not entity in entman.query_include_queued(MockComponent)


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

    def test_is_garbage(self):
        stuff = self.create_system_and_component()
        stuff.entman.add_component(stuff.component)
        stuff.entman.create_queued_objects()
        assert not stuff.component.is_garbage()
        stuff.entity.kill()
        assert stuff.component.is_garbage()


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
        ret.entman.update(1) # collect garbage

    def test_add_component(self):
        ret = self.create_system_and_component()
        ret.entman.create_queued_objects()
        ret.entity.add_component(ret.component)
        assert ret.entity.get_component(MockComponent) == ret.component
