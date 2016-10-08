from vector2d import Vec2d

import pygame

class Behaviours(object):
    def __init__(self):
        self.behaviours = []
    def add_behaviour(self, behaviour):
        self.behaviours.append(behaviour)
    def update(self, dt):
        garbage = [x for x in self.drawables if not x.is_garbage()]
        for behaviour in garbage:
            self.behaviours.remove(behaviour)
            behaviour.on_object_killed()
        for behaviour in self.behaviours:
            behaviour.update(dt)

class Behaviour(object):
    def __init__(self, game_object, game_services, config):
        self.game_object = game_object
        self.game_services = game_services
        self.config = config
    def is_garbage(self):
        return self.game_object.is_garbage
    def update(self, dt):
        pass
    def on_object_killed(self):
        pass

class KillOnTimer(Behaviour):
    def __init__(self, game_object, game_services, config):
        Behaviour.__init__(self, game_object, game_services, config)
        self.lifetime = Timer(config["lifetime"])
    def update(self, dt):
        GameObject.update(self, dt)
        if self.lifetime.tick(dt):
            self.game_object.kill()

class ExplodesOnDeath(Behaviour):
    def on_object_killed(self):
        explosion = self.game_services.create_game_object(self.config["explosion_config"])
        explosion.body.position = Vec2d(self.game_object.body.position)
        
