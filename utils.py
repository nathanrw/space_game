import random
import pygame
import sys
import json
import os

class Timer(object):
    def __init__(self, period):
        self.timer = 0
        self.period = period
    def advance_to_fraction(self, frac):
        self.timer += self.period * frac
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

class Config(object):
    """ A hierarchical data store. """
    
    def __init__(self):
        """ Initialise an empty data store. """
        self.parent = None
        self.data = {}
        self.filename = None
        
    def load(self, filename):
        """ Load data from a file. Remember the file so we can save it later. """
        self.filename = os.path.join("res/configs/", filename)
        print "Loading config: ", self.filename
        try:
            self.data = json.load(open(self.filename, "r"))
        except Exception, e:
            print e
            print "**************************************************************"
            print "ERROR LOADING CONFIG FILE: ", self.filename
            print "Probably either the file doesn't exist, or you forgot a comma!"
            print "**************************************************************"
            pygame.quit()
            sys.exit(1)
        parent_filename = self.__get("deriving")
        if parent_filename is not None:
            self.parent = Config()
            self.parent.load(parent_filename)
            
    def save(self):
        """ Save to our remembered filename. """
        json.dump(self.data, open(self.filename, "w"), indent=4, separators=(',', ': '))

    def __getitem__(self, key):
        """ Get some data out. """
        got = self.__get(key)
        if got is None and self.parent is not None:
            return self.parent[key]
        else:
            return got
        
    def get_or_default(self, key, default):
        """ Get some data out. """
        got = self[key]
        if got is None:
            return default
        else:
            return got

    def __get(self, key):
        """ Retrieve some data from our data store."""
        try:
            tokens = key.split(".")
            ret = self.data
            for tok in tokens:
                ret = ret[tok]
            return ret
        except:
            return None
