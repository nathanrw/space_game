from distutils.core import setup
import py2exe
import numpy
import pymunk
import pygame
import os
import OpenGL
import shutil

data_files = [
    ('.', [os.path.join(os.path.dirname(pymunk.__file__), 'chipmunk.dll')]),
    ('.', [os.path.join(os.path.dirname(pygame.__file__), 'libogg-0.dll')]),
    ('.', [os.path.join(os.path.dirname(pygame.__file__), 'SDL_ttf.dll')]),
    ('.', [os.path.join(os.path.dirname(pygame.__file__), 'libfreetype-6.dll')])
]

includes = ['scipy',
            'scipy.integrate',
            'scipy.special.*',
            'scipy.linalg.*',
            'scipy.sparse.csgraph._validation',
            'src.pygame_renderer',
            'src.pygame_opengl_renderer']

options = {
    "py2exe": {
        "dll_excludes": ["MSVCP90.dll"],
        "includes": includes,
        "excludes": ["OpenGL"]
    }
}

setup(
    windows=["run.py"],
    data_files=data_files,
    options=options
)

if not os.path.isdir("dist/OpenGL"):
    print "Copying pyOpenGL..."
    shutil.copytree(os.path.dirname(OpenGL.__file__), "dist/OpenGL")
    print "Done."

# Note: The more idiomatic way to do this would be via 'data_files' but life is too short.
print "Copying resources..."
shutil.rmtree("dist/res", True)
shutil.copytree("res", "dist/res")
print "Done."