GUI
===

How to do GUI?

pyui?
-----

I had a look at pyui - two versions of it. There's a zip file on the website
that contains what appears to be an out of date version. There's a github
fork that contains a more recent version. Neither of them work.

I had a little bit of a look into making them work - one of them I get
GLUT errors and I believe this is simply because GLUT isn't installed by
default. But I was getting other OpenGL errors as well. I don't think I can
just plug it in and have it work - I'd need to do some serious work to get
it working robustly.

Which is a shame because it's rather well designed, and is very lightweight.

Others?
-------

There are a million and one GUI libraries for pygame, but they're all little
one-man projects that aren't really finished. They also don't have the concept
of abstracting away the rendering backend, so that immediately writes much of
what's out there.

I've thought about using QT - the game could render into an OpenGL canvas
and I'm pretty sure QT supports creating widgets inside one of those.  But this
worries me as it's a large dependency, would not allow me to use pygame, and
might not give me exactly what I want anyway.

DIY?
----

The problem with these things is that they tend to re-implement half of MS
Windows but worse.

It might be possible to do something *simple* gives me what I want without
doing that.

There might be something out there that does just that but I haven't seen it.

nuklear
-------

A header-only c library. This is an immediate-mode GUI with no dependencies,
input is specified via function call, drawing is done into an intermediate
'command buffer' representation and state is stored in a context object.

This looks fantastic, exactly what I want, but it's in C. However, because
it's in simple C, it should be fairly simple to call it from python either
via ctypes or via a SWIG wrapper.

I would have to create both linux & windows builds. It would probably be
helpful to get it on pypi.
