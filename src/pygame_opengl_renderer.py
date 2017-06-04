import pygame
import OpenGL

# Switch on more debugging facilities
#OpenGL.FULL_LOGGING = True

import OpenGL.GL as GL
import math
import os
import os.path
import numpy
import re

from pymunk import Vec2d

from .renderer import *

class ShaderProgram(object):
    """ Manages an OpenGL shader program.

    Note that the program will currently never be deleted. My thinking
    is that there won't be many shaders, and so we will leave them to be
    cleaned up when the program terminates.

    Uniform and attribute locations are determined automatically by
    parsing the shader source, the same is true of vertex buffer format
    information. You can get a set of vertex buffers compatible with
    the shader by calling create_vertex_buffers().

    """

    def __init__(self, shader_dir):
        """ Constructor - create and initialise a shader program.
        """

        # Note: see the following, which was referenced in the PyOpenGL
        # documentation:
        #       https://bitbucket.org/rndblnch/opengl-programmable/src/tip/10-g
        #       l3.2core.py?fileviewer=file-view-default

        # Create the program object.
        self.__shader_program = GL.glCreateProgram()

        # We're going to build up a list of inputs.
        program_uniforms = set()
        program_attributes = set()
        self.__attribute_types = {}

        # Compile all of the source files and attach the resulting
        # shader objects to our shader program.
        for (filename, shader_type) in self.__list_shader_files(shader_dir):
            (file_uniforms, file_attributes, attribute_types) = \
                self.__parse_uniforms_and_attributes(filename)
            program_uniforms.update(file_uniforms);
            program_attributes.update(file_attributes);
            self.__attribute_types.update(attribute_types)
            shader = GL.glCreateShader(shader_type)
            GL.glShaderSource(shader, open(filename, 'r').read())
            GL.glCompileShader(shader)
            if GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS) != GL.GL_TRUE:
                raise Exception(GL.glGetShaderInfoLog(shader))
            GL.glAttachShader(self.__shader_program, shader)

        # Assign locations to vertex attributes. We'll bind them in the program later...
        self.__attrib_locations = dict((k, v) for (v, k) in enumerate(program_attributes))

        # Uniform locations will be determined by OpenGL, we'll get them later.
        self.__uniform_locations = {}

        # Now we can bind all of the vertex attributes to their
        # assigned locations.
        for attrib in program_attributes:
            GL.glBindAttribLocation(self.__shader_program,
                                    self.__attrib_locations[attrib],
                                    attrib)

        # Now link the program.
        GL.glLinkProgram(self.__shader_program)
        if GL.glGetProgramiv(self.__shader_program, GL.GL_LINK_STATUS) != GL.GL_TRUE:
            raise Exception(GL.glGetProgramInfoLog(self.__shader_program))

        # Retrieve the uniform locations and remember them.
        for uniform in program_uniforms:
            self.__uniform_locations[uniform] = GL.glGetUniformLocation(self.__shader_program, uniform)
            if self.__uniform_locations[uniform] == -1:
                print ("Warning: Uniform '%s' does not exist." % uniform)

    def create_vertex_buffers(self):
        """ Create a set of vertex buffers compatible with the shader. """
        buffer_formats = []
        for name in self.__attribute_types:
            size, data_type = self.__attribute_types[name]
            buffer_formats.append((name, size, data_type))
        return VertexData(self, buffer_formats)

    def __parse_uniforms_and_attributes(self, filename):
        """ Given a shader source file, return the names of attribute and
        uniform inputs. """
        uniforms = set()
        attributes = set()
        attribute_types = {}
        stream = open(filename, 'r')
        for line in stream:
            # NOTE: Here we assume a simple subset of the syntax for glsl
            # declarations, this is all I am using at the moment and we can
            # handle more cases as needed. We're also using the old 'attribute'
            # form, not 'in'. This is because we're targetting glsl 130 (opengl
            # 3.0) since that's what my laptop supports!
            pattern = "(attribute|uniform) ([a-zA-Z0-9_]+) ([a-zA-Z0-9_]+)"
            match = re.match(pattern, line)
            if match:
                storage_type = match.group(1)
                data_type = match.group(2)
                variable_name = match.group(3)
                if storage_type == "attribute":
                    attributes.add(variable_name)
                    data_dims = 0
                    data_array_type = None
                    if data_type == "float":
                        data_dims = 1
                        data_array_type = "f"
                    elif data_type == "vec2":
                        data_dims = 2
                        data_array_type = "f"
                    elif data_type == "vec3":
                        data_dims = 3
                        data_array_type = "f"
                    else:
                        raise Exception("Unknown attribute data type: %s" % data_type)
                    attribute_types[variable_name] = (data_dims, data_array_type)
                elif storage_type == "uniform":
                    uniforms.add(variable_name)
        return (uniforms, attributes, attribute_types)

    def __list_shader_files(self, dirname):
        """ List the shader files in a directory, inferring their types. """
        files = os.listdir(dirname)
        for filename in files:
            pattern = ".*\\.(v|f)\\.glsl$"
            match = re.match(pattern, filename)
            if match:
                type_str = match.group(1)
                type_enum = None
                if type_str == 'v':
                    type_enum = GL.GL_VERTEX_SHADER
                elif type_str == 'f':
                    type_enum = GL.GL_FRAGMENT_SHADER
                else:
                    continue
                yield (os.path.join(dirname, filename), type_enum)

    def begin(self):
        """ Render using the shader program. """
        GL.glUseProgram(self.__shader_program)

    def get_uniform_location(self, name):
        """ Get the location of a uniform. """
        if not name in self.__uniform_locations: return -1
        return self.__uniform_locations[name]

    def get_attribute_location(self, name):
        """ Get the location of an attribute. """
        if not name in self.__attrib_locations: return -1
        return self.__attrib_locations[name]

    def end(self):
        """ Render using the fixed function pipeline. """
        GL.glUseProgram(0)

class Texture(object):
    """ An OpenGL texture. """

    @classmethod
    def from_file(klass, filename):
        """ Create a texture from a file. """
        surface = pygame.image.load(filename).convert_alpha()
        return Texture(surface)

    @classmethod
    def from_surface(klass, surface):
        """ Create a texture from a surface. """
        return Texture(surface)

    def __init__(self, surface):
        """ Constructor. """
        data = pygame.image.tostring(surface, "RGBA", 1)
        self.__width = surface.get_width()
        self.__height = surface.get_height()
        self.__texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.__texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA, self.get_width(), self.get_height(),
                        0, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, data)

    def begin(self):
        """ Set OpenGL state. """
        assert self.__texture is not None
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.__texture)

    def end(self):
        """ Unset the state. """
        assert self.__texture is not None

    def get_width(self):
        """ Get the texture width in pixels. """
        assert self.__texture is not None
        return self.__width

    def get_height(self):
        """ Get the texture height in pixels. """
        assert self.__texture is not None
        return self.__height

    def get_size(self):
        """ Get the texture size in pixels. """
        assert self.__texture is not None
        return (self.__width, self.__height)

    def delete(self):
        """ Free the texture. """
        if self.__texture is not None:
            GL.glDeleteTextures(self.__texture)
            self.__texture = None


class AnimFrames(object):
    """ A sequence of textures. """

    def __init__(self, frames):
        """ Constructor. """
        self.__frames = frames

    def get_size(self):
        """ The texture size. """
        return (self.get_width(), self.get_height())

    def get_width(self):
        """ The texture width. """
        return self.get_frame_by_index(0).get_width()

    def get_height(self):
        """ The texture height. """
        return self.get_frame_by_index(0).get_height()

    def get_frame_by_index(self, index):
        """ Get texture coordinates for the frame. """
        return self.__frames[index]

    def get_frame(self, timer):
        """ Get a frame from a timer. """
        idx = timer.pick_index(len(self.__frames))
        return self.get_frame_by_index(idx)


class VirtualTexture(object):
    """ A reference to a location in a texture. """

    def __init__(self, atlas, x, y, w, h, level):
        """ Constructor. """
        self.__atlas = atlas
        self.__min = Vec2d(x, y)
        self.__max = Vec2d(x+w, y+h)
        self.__level = level

    @classmethod
    def create_null_texture(klass):
        """ Create a texture that returns dummy texcoords. """
        return VirtualTexture(None, 0, 0, 0, 0, -1)

    def get_texcoord(self, i):
        """ 'i' corresponds to a rectangle corner, and is a number between 0 and 3. """
        ret = None
        if i == 3:
            ret = (self.__min[0], self.__min[1], self.__level)
        elif i == 2:
            ret = (self.__max[0], self.__min[1], self.__level)
        elif i == 1:
            ret = (self.__max[0], self.__max[1], self.__level)
        elif i == 0:
            ret = (self.__min[0], self.__max[1], self.__level)
        else:
            raise Exception("Expected 0 <= i <= 3, got %s" % i)
        if self.__atlas is not None:
            return (ret[0] / float(self.__atlas.get_width()),
                    ret[1] / float(self.__atlas.get_height()),
                    ret[2])
        else:
            return ret

    def get_size(self):
        """ Get the size of the texture section. """
        return self.__max - self.__min

    def get_width(self):
        """ Get the width of the texture section. """
        return self.get_size()[0]

    def get_height(self):
        """ Get the height of the texture section. """
        return self.get_size()[1]

    def get_level(self):
        """ Get the level of the texture section. """
        return self.__level


class TextureArray(object):
    """ A texture array for rendering many sprites without changing
    textures. """

    def __init__(self):
        """ Initialise the texture array, this creates storage for the
        array but does not load any textures. """

        # Dimensions of the texture array.
        self.__width = 1024
        self.__height = 1024
        self.__depth = 20

        # Allocate the texture array.
        # NOTE: If this goes wrong, we're probably trying to do this before
        # the opengl context has been created, and things will go horribly
        # wrong later! For some reason glGetError() is returning 0 anyway.
        self.__texture = GL.glGenTextures(1)

        # Ok, initialise the texture.
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, self.__texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D_ARRAY, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D_ARRAY, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D_ARRAY, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D_ARRAY, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage3D(
            GL.GL_TEXTURE_2D_ARRAY,
            0, #level
            GL.GL_RGBA8, # internal format
            self.__width,
            self.__height,
            self.__depth,
            0, #border
            GL.GL_RGBA, # format
            GL.GL_UNSIGNED_BYTE, # data type
            None # The data.
        )

        # Each page of the atlas has a cursor, this is the point where a new
        # texture should be inserted.
        self.__current_page = 0
        self.__row_x = 0
        self.__row_y = 0
        self.__row_height = 0

        # Map from filenames to virtual textures.
        self.__filename_map = {}

    def get_width(self):
        """ Get the width of the atlas. """
        return self.__width

    def get_height(self):
        """ Get the height of the atlas. """
        return self.__height

    def load_file(self, filename):
        """ Load a texture from a file. """
        image = pygame.image.load(filename)
        virtual_texture = self.load_image(image)
        self.__filename_map[filename] = virtual_texture
        return virtual_texture

    def load_image(self, image):
        """ Load a texture from a pygame surface. """

        # If the image is too big then tough luck...
        if image.get_width() > self.__width or image.get_height() > self.__height:
            raise Exception("Image is too large for texture array")

        # If it doesn't fit on the current row then advance the row.
        if image.get_width() > self.__width - self.__row_x:
            self.__row_y += self.__row_height
            self.__row_x = 0

        # If it doesnt fit on the page advance the page.
        if image.get_height() > self.__height - self.__row_y:
            self.__current_page += 1
            self.__row_x = 0
            self.__row_y = 0
            self.__row_height = 0

        # Ok, upload the image to the texture array.
        image_bytes = pygame.image.tostring(image, "RGBA", 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, self.__texture)
        GL.glTexSubImage3D(
            GL.GL_TEXTURE_2D_ARRAY,
            0, # Mipmap number
            self.__row_x, # x offset
            self.__row_y, # y offset
            self.__current_page, # z offset
            image.get_width(),
            image.get_height(),
            1, # Depth
            GL.GL_RGBA, # format
            GL.GL_UNSIGNED_BYTE, # data type
            image_bytes # data
        )

        # Remember the location of this texture in the atlas.
        ret = VirtualTexture(self,
                             self.__row_x,
                             self.__row_y,
                             image.get_width(),
                             image.get_height(),
                             self.__current_page)

        # Advance the cursor.
        self.__row_x += image.get_width()
        self.__row_height = max(self.__row_height, image.get_height())

        # Return the texture info.
        return ret

    def lookup_texture(self, filename):
        """ Lookup a texture in the atlas from its filename. """
        if not filename in self.__filename_map:
            return VirtualTexture.create_null_texture()
        return self.__filename_map[filename]

    def begin(self):
        """ Begin rendering with the texture array. """
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, self.__texture)

    def end(self):
        """ Stop rendering with the texture array. """
        pass


class CommandBufferArray(object):
    """ Command buffer array - stores a set of command buffers and knows what
    buffer should be filled from a given job. """

    def __init__(self, shader_program, texture_array):
        """ Initialise the command buffer array. """
        self.__shader_program = shader_program
        self.__texture_array = texture_array
        self.__buffers = {}

    def get_buffer(self, coordinate_system, level, primitive_type):
        """ Get the buffer to add vertices to. """
        key = (level, coordinate_system, primitive_type)
        if key not in self.__buffers:
            self.__buffers[key] = CommandBuffer(
                coordinate_system,
                self.__shader_program,
                self.__texture_array,
                primitive_type
            )
        return self.__buffers[key]

    def reset(self, view):
        """ Reset the buffers so they can be re-used. """
        for key in self.__buffers:
            self.__buffers[key].reset(view)

    def dispatch(self):
        """ Dispatch commands to the GPU. """
        for key in sorted(self.__buffers.keys()):
            self.__buffers[key].dispatch()


class VertexData(object):
    """ A blob of vertex data. Each vertex can have a number of attributes. """

    def __init__(self, shader_program, attribute_formats, default_size=32):
        """ Initialise a vertex data block. """
        self.__shader_program = shader_program
        self.__arrays = {}
        self.__vbos = {}
        self.__sizes = {}
        self.__numpy_types = {}
        self.__n = 0
        self.__max = default_size
        for (name, size, data_type) in attribute_formats:
            self.__sizes[name] = size
            self.__arrays[name] = numpy.zeros(default_size * size, data_type)
            self.__vbos[name] = OpenGL.arrays.vbo.VBO(self.__arrays[name])
            self.__numpy_types[name] = data_type

    def reset(self):
        """ Reset the vertex data so it can be re-used. """
        self.__n = 0

    def add_vertex(self, **kwargs):
        """ Add a vertex. """

        # NOTE: Since this function is going to be called once per vertex
        # I should imagine it is going to be performance critical. The current
        # implementation not very efficient, looking up lots of string in
        # hash tables etc. Will probably need to optimise or do this in a
        # different way (e.g. specify more than one vertex at a time, have
        # calling code specify vertex components directly...)

        # TODO: Use DrawElements not DrawArrays so we can emit fewer vertices
        # and use TRIANGLE_STRIP and TRIANGLE_FAN primitives. Would need to
        # use primitive restart to render different triangle strips in a single
        # call.  Not sure if supported on this hardware.
        #
        # I *think* the restart is done in hardware, not a loop in the driver,
        # but even if it is I should think that's faster than a loop in python.
        #
        # This function would then return the vertex index and the caller would
        # then call e.g. add_primitive(indices) which would take care of the
        # primitive restart.

        # Expand the buffer if necessary.
        if self.__n == self.__max:
            self.__max *= 2
            for name in self.__arrays:
                # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
                # NOTE: not doing refcheck here since it fails. I'm not sure
                # why, something in the vbo code must be creating a view onto
                # the array. This shuts up the exception, but it could mean
                # that the code is going to go horribly wrong. Dont try this
                # at home kids.
                #
                # Need to work out what the right thing to do here is.
                # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
                self.__arrays[name].resize(self.__max * self.__sizes[name], refcheck=False)

        # Add the vertex attributes. If the attribute has not been specified
        # then we default it to zero, otherwise we'll end up rendering garbage.
        for key in self.__vbos:
            array = self.__arrays[key]
            size = self.__sizes[key]
            data = None
            if key in kwargs:
                data = kwargs[key]
            else:
                data = numpy.zeros(size)
            try:
                # Try to interpret the data as a vector.
                for (i, component) in enumerate(data):
                    array[self.__n*size+i] = component
            except TypeError:
                # Ok, it's a scalar.
                array[self.__n*size] = data

        # we've added a vertex.
        self.__n += 1

    def bind_attributes(self):
        """ Setup the vertex attributes for rendering. """

        # We store each attribute in its own buffer.
        for name in self.__vbos:

            # Get the attribute vbo.
            vbo = self.__vbos[name]

            # Update the array data, since it will change per-frame.
            vbo.set_array(self.__arrays[name])

            # Bind the vbo (this does also does some data wrangling I believe.)
            vbo.bind()

            # Switch on the attribute and describe the data format to OpenGL.
            GL.glEnableVertexAttribArray(self.__shader_program.get_attribute_location(name))
            gl_type = {'f': GL.GL_FLOAT}[self.__numpy_types[name]]
            GL.glVertexAttribPointer(self.__shader_program.get_attribute_location(name),
                                     self.__sizes[name], gl_type, GL.GL_FALSE, 0, None)

    def __len__(self):
        """ Return the number of vertices. """
        return self.__n


class CommandBuffer(object):
    """ A single draw call. """

    def __init__(self, coordinate_system, shader_program, texture_array, primitive_type):
        """ Constructor. """

        # Uniform state.
        self.__coordinate_system = coordinate_system
        self.__shader_program = shader_program
        self.__primitive_type = primitive_type
        self.__texture_array = texture_array
        self.__view_position = (0, 0)
        self.__view_size = (0, 0)
        self.__view_zoom = 1

        # Per-vertex data.
        self.__vertex_data = self.__shader_program.create_vertex_buffers()

    def reset(self, view):
        """ Reset the command buffer so we can re-use it. """
        self.__vertex_data.reset()
        self.__view_position = view.position
        self.__view_size = view.size
        self.__view_zoom = view.zoom

    def add_quad(self, position, size, **kwargs):
        """ Emit a quad. Note that we say quad, but we actually emit
        a pair of triangles since this type of geometry can be more
        easily batched. """

        # Dummy texref in case one hasn't been specified.
        texref=VirtualTexture.create_null_texture()
        if "texref" in kwargs:
            texref = kwargs["texref"]

        # (0, 0) -------------------- (1, 0)
        #    |                          |
        #    |                          |
        #    |                          |
        # (0, 1) -------------------- (1, 1)

        # The four corners of a quad.
        w = size[0]
        h = size[1]
        tl = (-w/2, -h/2)
        tr = (w/2, -h/2)
        br = (w/2, h/2)
        bl = (-w/2, h/2)
        positions = (tl, tr, br, bl)

        # Emit the top left triangle.
        for i in (0, 1, 3):
            self.__vertex_data.add_vertex(origin=position,
                                          position=positions[i],
                                          texcoord=texref.get_texcoord(i),
                                          **kwargs)

        # Emit the bottom right triangle.
        for i in (3, 1, 2):
            self.__vertex_data.add_vertex(origin=position,
                                          position=positions[i],
                                          texcoord=texref.get_texcoord(i),
                                          **kwargs)

    def add_polygon(self, points, **kwargs):
        """ Emit a polygon. """

        # Emit the polygon vertices. We assume the polygon is convex, and draw
        # a triangle between the first vertex and each subsequent pair of
        # vertices.
        i = 1
        while i+1 < len(points):
            self.__vertex_data.add_vertex(origin=points[0],
                                          texcoord=(0, 0, -1),
                                          **kwargs)
            self.__vertex_data.add_vertex(origin=points[i],
                                          texcoord=(0, 0, -1),
                                          **kwargs)
            self.__vertex_data.add_vertex(origin=points[i+1],
                                          texcoord=(0, 0, -1),
                                          **kwargs)
            i += 1

    def __get_circle_points(self, position, radius):
        """ Get points for a polygonised circle. """
        points = []
        circumference = 2*math.pi*radius
        npoi = max(int(math.sqrt(circumference)), 6)
        for i in range(0, npoi):
            angle = i/float(npoi) * math.pi * 2
            point = position + radius * Vec2d(math.cos(angle), math.sin(angle))
            points.append(point)
        return points

    def add_circle(self, position, radius, **kwargs):
        """ Emit a circular polygon. """
        self.add_polygon(self.__get_circle_points(position, radius), **kwargs)

    def add_circle_lines(self, position, radius, **kwargs):
        """ Emit a loop of line segments. """
        points = self.__get_circle_points(position, radius)
        points.append(points[0])
        self.add_lines(points, **kwargs)

    def add_lines(self, points, **kwargs):
        """ Emit a line. """

        # Add a line segment for each pair of vertices.
        i = 0
        while i+1 < len(points):
            self.__vertex_data.add_vertex(origin=points[i],
                                          texcoord=(0, 0, -1),
                                          **kwargs)
            self.__vertex_data.add_vertex(origin=points[i+1],
                                          texcoord=(0, 0, -1),
                                          **kwargs)
            i += 1

    def dispatch(self):
        """ Dispatch the command to the GPU. """

        # If there's nothing to do then avoid doing any work.
        if len(self.__vertex_data) == 0:
            return

        # Use the shader program.
        self.__shader_program.begin()

        # Use texture unit 0.
        GL.glActiveTexture(GL.GL_TEXTURE0)

        # Use the texture array.
        self.__texture_array.begin()

        # Setup uniform data.
        GL.glUniform1i(self.__shader_program.get_uniform_location("coordinate_system"), self.__coordinate_system)
        GL.glUniform2f(self.__shader_program.get_uniform_location("view_position"), *self.__view_position)
        GL.glUniform2f(self.__shader_program.get_uniform_location("view_size"), *self.__view_size)
        GL.glUniform1f(self.__shader_program.get_uniform_location("view_zoom"), self.__view_zoom)
        GL.glUniform1i(self.__shader_program.get_uniform_location("texture_array"), 0)

        # Specify vertex attributes.
        self.__vertex_data.bind_attributes()

        # Draw the quads.
        GL.glDrawArrays(self.__primitive_type, 0, len(self.__vertex_data))

        # Stop using the texture array.
        self.__texture_array.end()

        # Stop using the shader program.
        self.__shader_program.end()


class PygameOpenGLRenderer(Renderer):
    """ A pygame software renderer. """

    def __init__(self):
        """ Constructor. """
        Renderer.__init__(self)
        self.__surface = None
        self.__data_path = None
        self.__anim_shader = None
        self.__texture_array = None
        self.__command_buffers = None

    def initialise(self, screen_size, data_path):
        """ Initialise the pygame display. """

        # We want an OpenGL display.
        self.__surface = pygame.display.set_mode(screen_size, pygame.DOUBLEBUF|pygame.OPENGL)

        # This is needed to load shaders.
        self.__data_path = data_path

        # Enable alpha blending.
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # Output opengl version info.
        print ("OpenGL version: %s" % GL.glGetString(GL.GL_VERSION))
        print ("OpenGL vendor: %s" % GL.glGetString(GL.GL_VENDOR))
        print ("OpenGL max texture size: %s" % GL.glGetInteger(GL.GL_MAX_TEXTURE_SIZE))
        print ("OpenGL max array texture layers: %s" % GL.glGetInteger(GL.GL_MAX_ARRAY_TEXTURE_LAYERS))

        # Load the shader program.
        self.__anim_shader = self.load_shader_program("anim")

        # Create the texture array.
        self.__texture_array = TextureArray()

        # Initialise command buffers.  Jobs will be sorted by layer and coordinate system and added
        # to an appropriate command buffer for later dispatch.
        self.__command_buffers = CommandBufferArray(self.__anim_shader, self.__texture_array)

    def render_jobs(self, view):
        """ Perform rendering. """

        # Reset command buffers
        self.__command_buffers.reset(view)

        # Clear the screen
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        # Visit each job to fill command buffers
        Renderer.render_jobs(self)

        # Dispatch commands to the GPU.
        self.__command_buffers.dispatch()

    def flip_buffers(self):
        """ Update the pygame display. """
        pygame.display.flip()

    def load_compatible_image(self, filename):
        """ Load a pygame image. """
        return self.__texture_array.load_file(filename)

    def load_compatible_anim_frames(self, filename_list):
        """ Load the frames of an animation into a format compatible
        with the renderer.  The implementation can return its own
        image representation; the client should treat it as an opaque
        object. """
        return AnimFrames([self.__texture_array.load_file(f) for f in filename_list])

    def load_compatible_font(self, filename, size):
        """ Load a pygame font. """
        return pygame.font.Font(filename, size)

    def compatible_image_from_text(self, text, font, colour):
        """ Create an image by rendering a text string. """
        return self.__texture_array.load_image(font.render(text, True, colour))

    def screen_size(self):
        """ Get the display size. """
        return self.__surface.get_size()

    def screen_rect(self):
        """ Get the display size. """
        return self.__surface.get_rect()

    def render_RenderJobBackground(self, job):
        """ Render scrolling background. """
        buffer = self.__command_buffers.get_buffer(Renderer.COORDS_SCREEN,
                                                   Renderer.LEVEL_BACK_FAR,
                                                   GL.GL_TRIANGLES)
        width, height = self.screen_size()
        buffer.add_quad((width/2, height/2),
                        (width, height),
                        texref=job.background_image,
                        colour=(0.5, 0.5, 0.5))

    def render_RenderJobRect(self, job):
        """ Render rectangle. """
        buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_TRIANGLES)
        buffer.add_quad(job.rect.center, job.rect.size, colour=job.colour)

    def render_RenderJobLine(self, job):
        """ Render a line. """
        buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_LINES)
        buffer.add_lines((job.p0, job.p1), width=job.width, colour=job.colour)

    def render_RenderJobLines(self, job):
        """ Render a polyline. """
        buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_LINES)
        buffer.add_lines(job.points, width=job.width, colour=job.colour)

    def render_RenderJobPolygon(self, job):
        """ Render a polygon. """
        buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_TRIANGLES)
        buffer.add_polygon(job.points, colour=job.colour)

    def render_RenderJobCircle(self, job):
        """ Render a circle. """
        if job.width == 0:
            buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_TRIANGLES)
            buffer.add_circle(job.position, job.radius, colour=job.colour)
        else:
            buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_LINES)
            buffer.add_circle_lines(job.position, job.radius, colour=job.colour, width=job.width)

    def render_RenderJobText(self, job):
        """ Render some text. """
        pass

    def render_RenderJobAnimation(self, job):
        """ Render an animation. """

        # Get command buffer to which to dispatch.
        buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_TRIANGLES)

        # Get texture information about current animation frame.
        texref = job.anim.frames.get_frame(job.anim.timer)

        # Dispatch a quad to the command buffer.
        buffer.add_quad(job.position,
                        texref.get_size(),
                        texref=texref,
                        orientation=job.orientation,
                        colour=(1.0, 1.0, 1.0))

    def render_RenderJobImage(self, job):
        """ Render an image. """
        buffer = self.__command_buffers.get_buffer(job.coords, job.level, GL.GL_TRIANGLES)
        rect = pygame.Rect((0, 0), job.image.get_size())
        rect.topleft = job.position
        buffer.add_quad(rect.center,
                        job.image.get_size(),
                        texref=job.image,
                        colour=(1.0, 1.0, 1.0))

    def load_shader_program(self, name):
        """ Load a shader program. """
        return ShaderProgram(os.path.join(self.__data_path, os.path.join("shaders", name)))
