import random

class Timer(object):
    def __init__(self, period):
        self.timer = 0
        self.period = period
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
