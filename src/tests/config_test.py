import unittest
from ..config import *

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
        c5 = Config({"derive_from": "enemies/destroyer.txt"})

        # Should remove the derive from entry
        assert c5.get_or_default("derive_from", "fred") == "fred"

        # Should have components.
        assert isinstance(c5["components"], Config)

    def test_load(self):
        c1 = Config()
        c1.load("enemies/destroyer.txt")
        components = c1["components"]
        drawable = components["src.components.AnimationComponent"]
        assert drawable["anim_name"] == "enemy_destroyer"

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
        assert c1.get_or_default("wibble", "fred") == "wobble"
