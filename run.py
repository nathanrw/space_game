#!/usr/bin/env python3

import src.game
import sys
import cProfile
import logging

def main():
    """ Run the game! """
    game = src.game.Game()
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
