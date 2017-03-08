import unittest
from ..utils import *
from testing import *

class Type1(object):
    pass

class GameServicesTest(unittest.TestCase):
    def test_lookup_type(self):
        gs = MockGameServices()
        if __name__ == '__main__':
            self.assertEquals(gs.lookup_type("__main__.Type1"), Type1)
        else:
            self.assertEquals(gs.lookup_type("src.tests.utils_test.Type1"), Type1)
        self.assertEquals(gs.lookup_type("src.tests.testing.MockGameServices"), MockGameServices)

class TimerTest(unittest.TestCase):
    def test_init(self):
        t0 = Timer(0)
        self.assertEquals(t0.timer, 0)
        self.assertEquals(t0.period, 0)
        t1 = Timer(1)
        self.assertEquals(t1.timer, 0)
        self.assertEquals(t1.period, 1)
    def test_advance_to_fraction(self):
        t0 = Timer(2)
        t0.advance_to_fraction(1)
        self.assertEquals(t0.timer, 2)
        t0.advance_to_fraction(0.75)
        self.assertEquals(t0.timer, 1.5)
        t0.advance_to_fraction(2)
        self.assertEquals(t0.timer, 4)
    def test_tick(self):
        t0 = Timer(1)
        assert not t0.tick(0.5)
        assert t0.tick(0.5)
        self.assertEquals(t0.timer, 1)
        assert t0.tick(0.5)
        self.assertEquals(t0.timer, 1.5)
    def test_expired(self):
        t0 = Timer(0)
        assert t0.expired()
        t0 = Timer(1)
        assert not t0.expired()
        t0.tick(1)
        assert t0.expired()
    def test_pick_index(self):
        t0 = Timer(1)
        self.assertEquals(t0.pick_index(10), 0)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 0)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 1)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 2)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 3)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 4)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 5)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 6)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 7)
        t0.tick(0.1)
        self.assertEquals(t0.pick_index(10), 8)
        t0.tick(10) # from now on returns n-1.
        self.assertEquals(t0.pick_index(10), 9)
    def test_reset(self):
        t0 = Timer(20)
        t0.tick(10)
        t0.reset()
        self.assertEquals(t0.timer, -10) # reset() subtracts the period.
        self.assertEquals(t0.period, 20)
    def test_randomise(self):
        t0 = Timer(20)
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period
        t0.randomise()
        assert 0 <= t0.timer and t0.timer <= t0.period

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
        pass
    def test_system_by_component_type(self):
        pass
    def test_remove_component_by_concrete_type(self):
        pass
    def test_get_component_of_type(self):
        pass
    def test_update(self):
        pass

class ComponentSystemTest(unittest.TestCase):
    def test_setup(self):
        pass
    def test_do_on_object_killed(self):
        pass
    def test_create_queued_components(self):
        pass
    def test_create_queued_component(self):
        pass
    def test_add_component(self):
        pass
    def test_remove_component(self):
        pass
    def test_get_component(self):
        pass
    def test_remove_object_component(self):
        pass
    def test_garbage_collect(self):
        pass
    def test_update(self):
        pass

class ComponentTest(unittest.TestCase):
    def test_manager_type(self):
        pass
    def test_is_garbage(self):
        pass
    def test_update(self):
        pass
    def test_on_object_killed(self):
        pass
    def test_get_system_by_type(self):
        pass
    def test_create_entity(self):
        pass
    def test_get_component(self):
        pass
    def test_get_components(self):
        pass

class EntityTest(unittest.TestCase):
    def test_kill(self):
        pass
    def test_add_component(self):
        pass
    def test_get_system_by_type(self):
        pass
    def test_create_entity(self):
        pass
    def test_get_component(self):
        pass
    def test_get_components(self):
        pass
    def test_add_child(self):
        pass
    def test_is_descendant(self):
        pass
    def test_is_ancestor(self):
        pass

class ConfigTest(unittest.TestCase):

    def test_init(self):
        """ Init should produce a valid config. """

        # Should be able to default-construct
        c1 = Config()

        # Should be able to specify dict.
        c2 = Config({"wibble": "wobble"})
        assert c2["wibble"] == "wobble"

        # Recursive dicts should become configs.
        c3 = Config({"fred": {"wibble" : "wobble"}})
        c4 = c3["fred"]
        assert isinstance(c4, Config)
        assert c4["wibble"] == "wobble"

        # Derivation should work. The path is rooted on res/configs.
        c5 = Config({"derive_from": "player.txt"})

        # Should remove the derive from entry
        assert c5.get_or_default("derive_from", "fred") == "fred"

        # Should have components.
        assert isinstance(c5["components"], Config)

    def test_load(self):
        c1 = Config()
        c1.load("player.txt")
        components = c1["components"]
        drawable = components["src.drawing.AnimBodyDrawable"]
        assert drawable["anim_name"] == "player_ship"
        
    def test_save(self):
        # Need to create temporary output dir then clean it up
        # afterwards, should be gitignored.
        pass

    def test_getitem(self):
        c1 = Config({"wibble": "wobble"})
        self.assertEquals(c1["wibble"], "wobble") # value -> value
        c2 = Config({"foo":{"bar":"qux"}})
        foo = c2["foo"] # dict -> Config
        assert isinstance(foo, Config)
        self.assertEquals(foo["bar"], "qux")

    def test_get_or_none(self):
        c1 = Config({"wibble": "wobble"})
        assert c1.get_or_none("barry") is None
        assert c1.get_or_none("wibble") == "wobble"

    def test_get_or_default(self):
        c1 = Config({"wibble": "wobble"})
        assert c1.get_or_default("barry", "fred") == "fred"
        assert c1.get_or_default("wibble", "fred") == "wibble"

class ResourceLoaderTest(unittest.TestCase):
    def test_preload(self):
        pass
    def test_load_font(self):
        pass
    def test_load_image(self):
        pass
    def test_load_animation(self):
        pass
    def test_load_config_file(self):
        pass

class AnimationTest(unittest.TestCase):
    def test_max_bounds(self):
        class SurfMock(object):
            def __init__(self, rect):
                self.__rect = rect
            def get_rect(self):
                return self.__rect
        anim = Animation([SurfMock(pygame.Rect(0,0,10,20)),
                          SurfMock(pygame.Rect(0,0,10,10))], 1)

        # get_max_bounds() returns the maximum size of any rotation of
        # the anim. It only considers the size of the first frame; the
        # assumption really is that all frames are the same size.
        size = anim.get_max_bounds()
        self.assertEquals(size.width, 22)
        self.assertEquals(size.height, 22)
    def test_draw(self):
        def do_test(game_services):
            anim = game_services.get_resource_loader().load_animation("enemy_destroyer")
            self.assertEquals(len(anim.frames), 1)

            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()

            anim.orientation = 20
            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()

            anim.orientation = 80
            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()

            anim.orientation = 90
            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()

            anim.orientation = 180
            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()

            anim.orientation = 270
            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()

            anim.orientation = 350
            game_services.get_screen().fill((0,0,0))
            anim.draw(Vec2d(0, 0), game_services.get_camera())
            pygame.display.update()
            
        run_pygame_test(do_test)

class fromwin_Test(unittest.TestCase):
    def test_fromwin(self):
        self.assertEquals(fromwin("wibble/wobble"), "wibble/wobble")
        self.assertEquals(fromwin("wibble\\wobble"), "wibble/wobble")

if __name__ == '__main__':
    unittest.main()
