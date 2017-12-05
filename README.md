Space Game
==========

A space game written in Python.

![A screenshot](screenshot.png?raw=true "Screenshot")

![A screenshot](screenshot_2.png?raw=true "Screenshot")

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

The easiest way to install the libraries is `pip3 install pygame pymunk scipy pyyaml`.

How to run
----------

"Space game" is a Python program. You run it with Python:

    ./run.py

or 

    python2 run.py

Controls
--------

    w: Move forwards
    s: Move backwards
    a: Move left
    d: Move right
    e: Rotate anticlockwise
    q: Rotate clockwise
    t: Zoom in
    g: Zoom out
    f8: Save
    f9: Load
    f11: Show keys
    pause: Pause / unpause
    escape: Quit
    `: Simulate one frame then pause
    Mouse 1: Shoot
    Mouse wheel: Zoom in / out

Profiling
---------

You can run with profiling enabled like so:

    ./run.py --profile

which will spit out a file called 'profile_results' in the current working 
directory. You can view the results with

    ./bin/print_profile_results

Running the Tests
-----------------

You can run the tests like so:

    ./bin/run_tests

or like so (or equivalent:)

    python2 -m unittest discover -p "*_test.py"

Why?
----

We'll see. Perhaps it will become a fun game. It's also an exercise in architecting a simple game reasonably cleanly. It's a work in progress.
