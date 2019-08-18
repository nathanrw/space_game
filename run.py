#!/usr/bin/env python3

import os
import sys
import cProfile
import logging

import sgm

def main():
    """ Run the game! """

    # Change directory into the directory of this file - the
    # one containng the 'res' tree.  Note that if we've been built via
    # py2exe, we will actually be in a zip file so account for that.
    path = os.path.dirname(__file__)
    if (os.path.basename(path) == "library.zip"):
        path = os.path.dirname(path)
    if len(path) > 0:
        os.chdir(path)
    if not os.path.isdir("res"):
        raise Exception("Unable to locate resource tree.")
    sys.path += ["."]

    game = sgm.game.Game()
    try:
        game.run()
    except KeyboardInterrupt:
        # Don't show a stack trace.
        pass

if __name__ == '__main__':

    # Braindead arg parsing.
    do_profile=False
    do_logging=False
    for arg in sys.argv[1:]:
        if arg == "--profile":
            do_profile = True
        elif arg == "--log":
            do_logging = True

    # Set up logging.
    if do_logging:
        logging.basicConfig(filename="debug_log")

    # Do profiling if we've asked for it.
    if do_profile:
        cProfile.run("main()", "profile_results")
    else:
        main()
