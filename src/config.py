from .utils import ordered_load, bail
import collections

class Config(object):
    """ A hierarchical data store. """

    def __init__(self, a_dict=None):
        """ Initialise an empty data store, or a wrapping one if a dictionary
        is provided."""

        # If this node is not a leaf, then this will contain the data
        # that defines the child nodes.
        self.__data = collections.OrderedDict()

        # If this node is a leaf, then this will contain its value.
        self.__value = None

        # If this tree was read from a file, this will be the filename.
        self.__filename = None

        # Name of the parent file.
        self.__parent_filename = None

        # If data specified, build a config.
        if a_dict is not None:
            self.__data = self.__build_config_dict(a_dict).__data

    def load(self, filename):
        """ Load data from a file. Remember the file so we can save it later.

        The filename here is relative to the game 'res' dir.

        If there is an error loading the file, noisily abort the program - it's
        probably a silly mistake that needs fixing. And config loading can
        happen inside physics callbacks, wherein exceptions get ignored for
        some reason!

        If the file contains a 'derive_from' key then load a parent config
        recursively until there is no more derivation. """

        self.load_from(os.path.join("res/configs", filename))

    def load_from(self, filename):
        """ Load data from a file. Remember the file so we can save it later.

        If there is an error loading the file, noisily abort the program - it's
        probably a silly mistake that needs fixing. And config loading can
        happen inside physics callbacks, wherein exceptions get ignored for
        some reason!

        If the file contains a 'derive_from' key then load a parent config
        recursively until there is no more derivation. """

        self.__filename = filename

        # Try to load the config from the file.
        print( "Loading config: ", self.__filename )
        data = collections.OrderedDict()
        try:
            data = ordered_load(open(self.__filename, "r"))
        except Exception as e:
            print( e )
            print( "**************************************************************" )
            print( "ERROR LOADING CONFIG FILE: ", self.__filename )
            print( "Probably either the file doesn't exist, or you forgot a comma!" )
            print( "**************************************************************" )
            bail() # Bail - we might be in the physics thread which ignores exceptions

        # Transform the data into a Config tree.
        self.__data = self.__build_config_dict(data).__data

    def save(self):
        """ Save to our remembered filename. """
        self.save_as(self.__filename)

    def save_as(self, filename):
        """ Save to given filename. """
        data = self.__config_to_dict()
        yaml.safe_dump(data, open(filename, "w"))

    def get_dict(self):
        """ Get the config as a dictionary. """
        return self.__config_to_dict()

    def __getitem__(self, key):
        """ Get some data out. """
        got = self.get_or_none(key)
        if got is None:
            print( "**************************************************************" )
            print( self.__data )
            print( "ERROR READING CONFIG ATTRIBUTE: %s" % key )
            print( "CONFIG FILE: %s" % self.__filename )
            print( "It's probably not been added to the file, or there is a bug." )
            print( "**************************************************************" )
            bail() # Bail - we might be in the physics thread which ignores exceptions
        return got

    def __iter__(self):
        """ Iterate the key-value pairs in the config. """
        if self.__data is not None:
            for key in self.__data:
                yield key

    def get_or_default(self, key, default):
        """ Get some data out. """
        ret = self.__get(key)
        if ret is not None:
            return ret
        else:
            return default

    def get_or_none(self, key):
        """ Get some data, or None if it isnt found. """
        return self.__get(key)

    def __get(self, key):
        """ Retrieve some data from our data store."""
        ret = self.__get_config(key)
        if ret is not None:
            if ret.__value is not None:
                return ret.__value
        return ret

    def __get_config(self, key):
        """ Retrieve some data from our data store."""
        if key in self.__data:
            return self.__data[key]
        else:
            return None

    def __build_config_dict(self, data):
        """ Build a config tree from a dictionary or leaf value. """

        # Use a temporary config.
        ret = Config()

        # Determine what sort of data we have
        is_dict = False
        try:
            for key in data:
                value = data[key]
                pass
            is_dict = True
        except:
            pass

        # Build config based on input type.
        if is_dict:

            # Build the tree.
            for key in data:
                value = data[key]
                ret.__data[key] = self.__build_config_dict(value)

            # If there is a parent config then load and merge it in.
            if "derive_from" in data:

                # Load the parent config
                ret.__parent_filename = data["derive_from"]
                parent = Config()
                parent.load(ret.__parent_filename)

                # Merge the config we just built with our parent.
                tmp = Config()
                tmp.__data = ret.__data
                parent.__merge_in(tmp)
                ret.__data = parent.__data

                # Remove the 'derive_from' entry as it has been dealt with.
                del ret.__data["derive_from"]
        else:
            ret.__value = data

        return ret

    def __merge_in(self, config):
        """ Overlay another config onto ourself. """
        if config.__value is not None:
            self.__value = config.__value
            return
        for key in config.__data:
            child = config.__data[key]
            self_child = self.__get_config(key)
            if self_child is not None:
                self_child.__merge_in(child)
            else:
                self.__data[key] = child

    def __config_to_dict(self):
        """ Turn the config tree into a plain dictionary. """
        if self.__value is not None:
            return self.__value
        ret = collections.OrderedDict()
        for key in self.__data:
            child = self.__data[key]
            ret[key] = child.__config_to_dict()
        return ret
