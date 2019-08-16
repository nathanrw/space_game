import unittest
from testing import *


class ResourceLoaderTest(unittest.TestCase):
    def test_preload(self):
        def do_test(game_services):
            rl = game_services.get_resource_loader()
            rl.minimise_image_loading = True
            rl.preload()
        run_pygame_test(do_test)
    def test_load_font(self):
        def do_test(game_services):
            rl = game_services.get_resource_loader()
            font = rl.load_font("res/fonts/nasdaqer/NASDAQER.ttf", 10)
            font2 = rl.load_font("res/fonts/nasdaqer/NASDAQER.ttf", 10)
            font3 = rl.load_font("res/fonts/nasdaqer/NASDAQER.ttf", 11)
            assert font == font2
            assert font != font3
        run_pygame_test(do_test)
    def test_load_image(self):
        def do_test(game_services):
            rl = game_services.get_resource_loader()
            img = rl.load_image("res/images/background.png")
            img2 = rl.load_image("res/images/background.png")
            assert img == img2
        run_pygame_test(do_test)
    def test_load_animation(self):
        def do_test(game_services):
            rl = game_services.get_resource_loader()
            anim = rl.load_animation("enemy_ship")
            anim2 = rl.load_animation("enemy_ship")
            assert anim.frames == anim2.frames
        run_pygame_test(do_test)


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