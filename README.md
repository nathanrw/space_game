Space Game
==========

A space game written in Python.

![A screenshot](screenshot.png?raw=true "Screenshot")

What
----

It's currently a very simple arcade space shooter. But it does have BULLETS THAT ARE GUNS THAT SHOOT MORE BULLETS. Beat that eh.

Dependencies
------------

In order to run "Space game," you will need the following packages installed:

* Python 2.7
* pygame
* pymunk
* scipy / numpy
* pyYAML

How to run
----------

"Space game" is a Python program. You run it with Python:

    ./run.py

or

    python2 run.py

Controls
--------

WASD - Move.

QE - Rotate.

TG - Zoom.

RF - Cycle weapons.

Mouse - Shoot.

Running the tests
-----------------

At present, you would do e.g.

    python2 -m unittest src.tests.utils_test

from the root directory. I haven't yet invesitgated a better or more automatic way of doing this.

Profiling
---------

You can run with profiling enabled like so:

    ./run.py --profile

which will spit out a file called 'profile_results' in the current working 
directory. You can view the results with

    ./bin/print_profile_results

Why?
----

We'll see. Perhaps it will become a fun game. It's also an exercise in architecting a simple game reasonably cleanly. It's a work in progress.
