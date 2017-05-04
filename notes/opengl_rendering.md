OpenGL Rendering
================

The most inefficient part of the game at the moment is drawing.  We load in
loads of individual images to represent animation frames, and each (game) frame
we indepdently rotate, scale and draw each sprite frame. With more than a few
sprites this takes a lot of time.

It would be better to use hardware acceleration to take care of this for us.
Pygame doesn't do this for us, we'd either have to port to pyglet or roll our
own OpenGL drawing.

Target OpenGL version
---------------------

If we were to 'roll our own' (I imagine pyglet takes care of this) we'd have to
decide what standard to target. My shit laptop running arch linux reports the
following:

    $ glxinfo | grep -i version
    server glx version string: 1.4
    client glx version string: 1.4
    GLX version: 1.4
        Version: 13.0.4
        Max core profile version: 3.3
        Max compat profile version: 3.0
        Max GLES1 profile version: 1.1
        Max GLES[23] profile version: 3.0
    OpenGL core profile version string: 3.3 (Core Profile) Mesa 13.0.4
    OpenGL core profile shading language version string: 3.30
    OpenGL version string: 3.0 Mesa 13.0.4
    OpenGL shading language version string: 1.30
    OpenGL ES profile version string: OpenGL ES 3.0 Mesa 13.0.4
    OpenGL ES profile shading language version string: OpenGL ES GLSL ES 3.00

OpenGL 3.3 seems reasonable enough.

Rolling our own
---------------

* All drawing is now down inside drawing.py. Make it so that drawing calls are
  delegated to an abstract 'renderer' and derive one for software pygame.

* Derive one for opengl and do the necessary faff to have it initialised in the
  right place.

* Each 'true' animation becomes an array texture.

* Collate single frame animations into a single array texture.

* OpenGL 3.3 specifies a minimum of 256 as the maximum array size, this should
  be plenty but we might have to get clever and say one anim could be
  potentially several array textures if there are many frames.

* Sort and batch calls by (layer, texture).

* Draw using a simple shader.

### renderer.py

* Abstract class 'Renderer' which is passed 'jobs' each of which specifies
  a single drawing operation.  Jobs are buffered, and executed when a method
  'render_jobs()' is called.  The renderer is free to process and reorder the
  jobs for greater efficiency.

* Derived class 'PygameRenderer' implements pygame software rendering.

* Derived class 'PygameOpenGLRenderer' uses OpenGL to do drawing into a
  pygame window.

### PygameOpenGLRenderer

A simple old-school OpenGL renderer. It's very slow, a lot of the work of
transforming vertices is done in software and lots of draw calls and state
changes are made.

### Plan for efficient sprite rendering

* Sort jobs by (layer, ...) Combine jobs together into batches.

* Maximise size of batches using array textures and instancing.

* At first, I envisage 1 array texture per animation, but the max frame
  count is very high so we could potentially have more. Or have a 3d
  texture atlas, have *all* data in a single 3d texture.

* Render sprites using instancing. Upload a triangle strip for a
  unit quad, and upload the (position, width, height, texture z,
  texture offset) separately. Do this via glDrawArraysInstanced,
  this way the other data comes in as vertex attributes and not
  as uniform data (of which you can only have so much.)


Pyglet
------

I haven't really looked into this, but it looks like a fairly thin wrapper
over OpenGL, with some nice sprite batching and other goodies. This may well
be the most sensible thing to do since we'll probably end up re-implementing
half of this otherwise!

(The derived renderer concept probably still applies here, it would be good
to keep the pygame drawing code we already have while porting.)
