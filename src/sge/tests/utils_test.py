import unittest


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


if __name__ == '__main__':
    unittest.main()
