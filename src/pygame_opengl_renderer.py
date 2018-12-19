"""
A modern OpenGL renderer aiming to render textured quads and simple 2D geometry
efficiently and with the potential to add fancy post processing effects.

The current stategy is to try and do as little work in python as possible
(since it is very slow) and get the GPU to do the heavy lifting - but this
involves compromise in terms of uploading redundant data, shader program
efficiency etc. The optimal approach has not yet been found.

Features:

  * All textures stored in a single large texture array so no need change
    the bound texture.

  * Attributes & uniforms automatically parsed from shader source, and
    vertex data arrays allocated automatically based on this.

  * Geometry batched into very few draw calls by adding quads to 'command
    buffers' keyed on attributes that change.

Testing on an old laptop with intel integrated graphics reveals that (a) the
OpenGL renderer is currently slower than the software implementation at least
for few sprites and (b) a lot of time gets spent in add_vertex() which does a
lot of work parsing arguments and fiddling with arrays.  This may be different
on a beefier machine.
"""

import pygame
import OpenGL

# Switch on more debugging facilities
#OpenGL.FULL_LOGGING = True

import OpenGL.GL as GL
import math
import os
import os.path
import numpy
import pynk
import pynk.nkpygame
import re
import unicodedata

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
        program_uniforms = []
        self.__program_attributes = []
        self.__attribute_types = {}

        # Compile all of the source files and attach the resulting
        # shader objects to our shader program.
        for (filename, shader_type) in self.__list_shader_files(shader_dir):
            (file_uniforms, file_attributes, attribute_types) = \
                self.__parse_uniforms_and_attributes(filename)
            program_uniforms += file_uniforms
            self.__program_attributes += file_attributes
            self.__attribute_types.update(attribute_types)
            shader = GL.glCreateShader(shader_type)
            GL.glShaderSource(shader, open(filename, 'r').read())
            GL.glCompileShader(shader)
            if GL.glGetShaderiv(shader, GL.GL_COMPILE_STATUS) != GL.GL_TRUE:
                raise Exception(GL.glGetShaderInfoLog(shader))
            GL.glAttachShader(self.__shader_program, shader)

        # Assign locations to vertex attributes. We'll bind them in the program later...
        self.__attrib_locations = dict((k, v) for (v, k) in enumerate(self.__program_attributes))

        # Uniform locations will be determined by OpenGL, we'll get them later.
        self.__uniform_locations = {}

        # Now we can bind all of the vertex attributes to their
        # assigned locations.
        for attrib in self.__program_attributes:
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
        for name in self.__program_attributes:
            size, data_type = self.__attribute_types[name]
            buffer_formats.append((name, size, data_type))
        return VertexData(self, buffer_formats)

    def __parse_uniforms_and_attributes(self, filename):
        """ Given a shader source file, return the names of attribute and
        uniform inputs. """
        uniforms = []
        attributes = []
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
                    assert not variable_name in attributes
                    attributes.append(variable_name)
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
                    elif data_type == "vec4":
                        data_dims = 4
                        data_array_type = "f"
                    else:
                        raise Exception("Unknown attribute data type: %s" % data_type)
                    attribute_types[variable_name] = (data_dims, data_array_type)
                elif storage_type == "uniform":
                    assert not variable_name in uniforms
                    uniforms.append(variable_name)
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


class Framebuffer(object):
    """ Wrap an OpenGL framebuffer object. """

    def __init__(self, width, height, attachments, pixel_format=GL.GL_RGBA16F):
        """ Initialise an FBO given a width and height. """

        # Create and initialise an FBO with colour attachments of
        # the appropriate size.
        self.__fbo = GL.glGenFramebuffers(1)
        self.__textures = {}
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.__fbo)
        for attachment in attachments:
            texture = Texture.blank(width, height, pixel_format)
            GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER,
                                      attachment,
                                      GL.GL_TEXTURE_2D,
                                      texture.get_texture(),
                                      0)
            self.__textures[attachment] = texture
        assert GL.glCheckFramebufferStatus(GL.GL_FRAMEBUFFER) == GL.GL_FRAMEBUFFER_COMPLETE

    def get_texture(self, attachment):
        """ Get the framebuffer texture. """
        return self.__textures[attachment]

    def begin(self):
        """ Bind the framebuffer. """
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.__fbo)
        GL.glDrawBuffers(self.__textures.keys())

    def end(self):
        """ Bind the default framebuffer. """
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, 0)


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

    @classmethod
    def blank(klass, width, height, internal_format=GL.GL_RGBA):
        """ Create a blank texture of a particular size. """
        return Texture((width, height), internal_format)

    def __init__(self, surface, internal_format=GL.GL_RGBA):
        """ Constructor. """
        data = None
        try:
            (self.__width, self.__height) = surface
        except:
            data = pygame.image.tostring(surface, "RGBA", 1)
            self.__width = surface.get_width()
            self.__height = surface.get_height()
        self.__texture = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, self.__texture)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, internal_format, self.get_width(), self.get_height(),
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

    def get_texture(self):
        """ Get the texture ID. """
        return self.__texture

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

    class Cursor(object):
        """ A cursor into the texture array. """
        def __init__(self):
            self.current_page = 0
            self.row_x = 0
            self.row_y = 0
            self.row_height = 0
            self.end = 0

    def __init__(self):
        """ Initialise the texture array, this creates storage for the
        array but does not load any textures. """

        # Dimensions of the texture array.
        self.__width = 1024
        self.__height = 1024
        self.__depth = 30
        self.__scratch_depth = 2

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
            self.__depth + self.__scratch_depth,
            0, #border
            GL.GL_RGBA, # format
            GL.GL_UNSIGNED_BYTE, # data type
            None # The data.
        )

        # We insert images one at a time, and keep track of the current
        # insertion point.  When we reach the end of the row, the next
        # row starts at a y coordinate flush with the bottom of the tallest
        # item in the current row. Note that this will end up with lots of
        # wasted space, we don't do any work to optimise the packing!
        self.__cursor = TextureArray.Cursor()
        self.__cursor.end = self.__depth

        # Initialise the scratch cursor.
        self.__scratch_cursor = TextureArray.Cursor()
        self.__scratch_cursor.index = self.__depth
        self.__scratch_cursor.end = self.__depth + self.__scratch_depth

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
        return self.__load_image(image, self.__cursor)

    def load_image_dynamic(self, image):
        """ Load a texture that persists for the duration of this frame. """
        return self.__load_image(image, self.__scratch_cursor)

    def __load_image(self, image, cursor):
        """ Load an image into the array at position 'cursor'. """

        # If the image is too big then tough luck...
        if image.get_width() > self.__width or image.get_height() > self.__height:
            raise Exception("Image is too large for texture array")

        # If it doesn't fit on the current row then advance the row.
        if image.get_width() > self.__width - cursor.row_x:
            cursor.row_y += cursor.row_height
            cursor.row_x = 0

        # If it doesnt fit on the page advance the page.
        if image.get_height() > self.__height - cursor.row_y:
            cursor.current_page += 1
            cursor.row_x = 0
            cursor.row_y = 0
            cursor.row_height = 0

        # We're out of memory - return a dummy texture.
        if cursor.current_page >= cursor.end:
            return VirtualTexture.create_null_texture()

        # Ok, upload the image to the texture array.
        image_bytes = pygame.image.tostring(image, "RGBA", 1)
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, self.__texture)
        GL.glTexSubImage3D(
            GL.GL_TEXTURE_2D_ARRAY,
            0, # Mipmap number
            cursor.row_x, # x offset
            cursor.row_y, # y offset
            cursor.current_page, # z offset
            image.get_width(),
            image.get_height(),
            1, # Depth
            GL.GL_RGBA, # format
            GL.GL_UNSIGNED_BYTE, # data type
            image_bytes # data
        )

        # Remember the location of this texture in the atlas.
        ret = VirtualTexture(self,
                             cursor.row_x,
                             cursor.row_y,
                             image.get_width(),
                             image.get_height(),
                             cursor.current_page)

        # Advance the cursor.
        cursor.row_x += image.get_width()
        cursor.row_height = max(cursor.row_height, image.get_height())

        # Return the texture info.
        return ret

    def lookup_texture(self, filename):
        """ Lookup a texture in the atlas from its filename. """
        if not filename in self.__filename_map:
            return VirtualTexture.create_null_texture()
        return self.__filename_map[filename]

    def reset_scratch(self):
        """ Reset the scratch cursor. All virtual textures into the scratch
        area now point to garbage. """
        self.__scratch_cursor.current_page = 0
        self.__scratch_cursor.row_x = 0
        self.__scratch_cursor.row_y = 0
        self.__scratch_cursor.row_height = 0

    def begin(self):
        """ Begin rendering with the texture array. """
        GL.glBindTexture(GL.GL_TEXTURE_2D_ARRAY, self.__texture)

    def end(self):
        """ Stop rendering with the texture array. """
        pass


class CommandBufferArray(object):
    """ Command buffer array - stores a set of command buffers and knows what
    buffer should be filled from a given job. """

    def __init__(self, shader_program):
        """ Initialise the command buffer array. """
        self.__shader_program = shader_program
        self.__buffers = {}

    def get_buffer(self, coordinate_system, level, primitive_type):
        """ Get the buffer to add vertices to. """
        key = (level, coordinate_system, primitive_type)
        if key not in self.__buffers:
            self.__buffers[key] = CommandBuffer(
                self.__shader_program,
                primitive_type,
                coordinate_system
            )
        return self.__buffers[key]

    def reset(self):
        """ Reset the buffers so they can be re-used. """
        for key in self.__buffers:
            self.__buffers[key].reset()

    def dispatch(self):
        """ Dispatch commands to the GPU. """
        for key in sorted(self.__buffers.keys()):
            self.__buffers[key].dispatch()


class VertexData(object):
    """ A blob of vertex data. Each vertex can have a number of attributes. """

    def __init__(self, shader_program, attribute_formats, default_size=32):
        """ Initialise a vertex data block. """
        self.__shader_program = shader_program
        self.__offsets = {}
        self.__sizes = {}
        self.__n = 0
        self.__max = default_size
        self.__vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self.__vao)
        self.__size = 0
        for (name, size, data_type) in attribute_formats:
            if data_type != 'f':
                raise Exception("Only float data supported at present.")
            self.__sizes[name] = size
            self.__offsets[name] = self.__size
            self.__size += size
        self.__array = numpy.zeros(default_size * self.__size, 'f')
        self.__vbo = OpenGL.arrays.vbo.VBO(self.__array)
        self.__vbo.bind()
        self.__element_array = numpy.zeros(0, 'u2')
        self.__elements_buffer = OpenGL.arrays.vbo.VBO(self.__element_array, target=GL.GL_ELEMENT_ARRAY_BUFFER)
        self.__elements_buffer.bind()
        for (name, size, data_type) in attribute_formats:
            GL.glEnableVertexAttribArray(self.__shader_program.get_attribute_location(name))
            GL.glVertexAttribPointer(self.__shader_program.get_attribute_location(name),
                                     self.__sizes[name], GL.GL_FLOAT, False, self.__size*4, self.__vbo+self.__offsets[name]*4)
        GL.glBindVertexArray(0)

        # Note: these need to persist between frames so we allocate them as
        # members. Note that this only makes sense when drawing the gui! need
        # to refactor.
        # See https://github.com/vurtun/nuklear/commit/1caba3a5c9850b29416bd87ef33c79b0382cf065
        self.cmds = pynk.ffi.new("struct nk_buffer*")
        self.vbuf = pynk.ffi.new("struct nk_buffer*")
        self.ebuf = pynk.ffi.new("struct nk_buffer*")
        pynk.lib.nk_buffer_init_default(self.cmds)
        pynk.lib.nk_buffer_init_default(self.vbuf)
        pynk.lib.nk_buffer_init_default(self.ebuf)

    def draw(self, primitive_type):
        """ Draw the vertices. """
        GL.glDrawArrays(primitive_type, 0, len(self))

    def draw_elements(self, primitive_type, num_elements, offset):
        """ Draw elements. """
        GL.glDrawElements(primitive_type, num_elements, GL.GL_UNSIGNED_SHORT, self.__elements_buffer+offset*2)

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
            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
            # NOTE: not doing refcheck here since it fails. I'm not sure
            # why, something in the vbo code must be creating a view onto
            # the array. This shuts up the exception, but it could mean
            # that the code is going to go horribly wrong. Dont try this
            # at home kids.
            #
            # Need to work out what the right thing to do here is.
            # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
            self.__array.resize(self.__max * self.__size, refcheck=False)

        # Add the vertex attributes. If the attribute has not been specified
        # then we default it to zero, otherwise we'll end up rendering garbage.
        for key in self.__offsets:
            offset = self.__offsets[key]
            data = None
            if key in kwargs:
                data = kwargs[key]
            else:
                data = numpy.zeros(self.__sizes[key])
            try:
                # Try to interpret the data as a vector.
                for (i, component) in enumerate(data):
                    self.__array[self.__n*self.__size+offset+i] = component
            except TypeError:
                # Ok, it's a scalar.
                self.__array[self.__n*self.__size+offset] = data

        # we've added a vertex.
        self.__n += 1

    def add_nuklear(self, nuklear):
        """ Convert nuklear vertex data. """

        # Specify vertex format.
        config = pynk.ffi.new("struct nk_convert_config*")
        vertex_layout = pynk.ffi.new("struct nk_draw_vertex_layout_element[]", [
            [pynk.lib.NK_VERTEX_POSITION, pynk.lib.NK_FORMAT_FLOAT, self.__offsets["position"]*4],
            [pynk.lib.NK_VERTEX_TEXCOORD, pynk.lib.NK_FORMAT_FLOAT, self.__offsets["texcoord"]*4],
            [pynk.lib.NK_VERTEX_COLOR, pynk.lib.NK_FORMAT_R32G32B32A32_FLOAT, self.__offsets["colour"]*4],
            [pynk.lib.NK_VERTEX_ATTRIBUTE_COUNT, pynk.lib.NK_FORMAT_COUNT, 0] # NK_VERTEX_LAYOUT_END
        ])
        # Note: cffi zero initialises by default
        #NK_MEMSET(&config, 0, sizeof(config));
        config.vertex_layout = vertex_layout;
        config.vertex_size = self.__size*4
        config.vertex_alignment = 1
        #config.null = dev->null;
        config.circle_segment_count = 22
        config.curve_segment_count = 22
        config.arc_segment_count = 22
        config.global_alpha = 1.0
        config.shape_AA = pynk.lib.NK_ANTI_ALIASING_ON;
        config.line_AA = pynk.lib.NK_ANTI_ALIASING_ON;

        # Get the buffer data.
        result = pynk.lib.nk_convert(nuklear.ctx, self.cmds, self.vbuf, self.ebuf, config)
        assert result == pynk.lib.NK_CONVERT_SUCCESS

        # Reference the data in numpy format.
        array = numpy.frombuffer(pynk.ffi.buffer(pynk.lib.nk_buffer_memory(self.vbuf), self.vbuf.needed), "f", self.vbuf.needed/4)
        elements = numpy.frombuffer(pynk.ffi.buffer(pynk.lib.nk_buffer_memory(self.ebuf), self.ebuf.needed), 'u2', self.ebuf.needed/2)

        if len(array) > len(self.__array):
            self.__array.resize(len(array), refcheck=False) # NOTE: See comment above on refcheck.
        self.__array[:len(array)] = array[:]
        if len(elements) > len(self.__element_array):
            self.__element_array.resize(len(elements), refcheck=False) # NOTE: See comment above on refcheck.
        self.__element_array[:len(elements)] = elements
        self.__n = len(array)/self.__size
        self.__max = self.__n

    def begin(self):
        """ Setup the vertex attributes for rendering. """

        # Update the data array.  I'm not entirely sure whether we need
        # to do this or not, and 'set_array()' might be sufficient on its
        # own (doing 'bind()' as well)
        self.__vbo.set_array(self.__array)
        self.__vbo.bind()
        self.__elements_buffer.set_array(self.__element_array)
        self.__elements_buffer.bind()

        if OpenGL.FULL_LOGGING:
            self.print_out()

        # Bind the attributes.
        GL.glBindVertexArray(self.__vao)

    def end(self):
        """ Unbind the VAO. """
        GL.glBindVertexArray(0)

    def print_out(self):
        """ Print out the structure of the buffer.  This is useful for debugging. """
        space = 25
        for name in self.__offsets:
            print (name + " " * (space - len(name))),
        print ("")
        for i in range(0, self.__n):
            for name in self.__offsets:
                offset = self.__offsets[name]
                components = ""
                for j in xrange(self.__sizes[name]):
                    index = i * self.__size+offset+j
                    components += str(round(self.__array[index], 2)) + ", "
                components = components[:-2]
                components = components + " " * (space-len(components))
                print (components),
            print ("")
        print ("")
        print "index"
        for i in range (0, len(self.__element_array)/3):
            for j in xrange(3):
                print self.__element_array[i*3+j],
            print ""

    def __len__(self):
        """ Return the number of vertices. """
        return self.__n


class CommandBuffer(object):
    """ A single draw call. """

    def __init__(self, shader_program, primitive_type, coordinate_system):
        """ Constructor. """

        # Uniform state.
        self.__coordinate_system = coordinate_system
        self.__shader_program = shader_program
        self.__primitive_type = primitive_type

        # Per-vertex data.
        self.__vertex_data = self.__shader_program.create_vertex_buffers()

    def reset(self):
        """ Reset the command buffer so we can re-use it. """
        self.__vertex_data.reset()

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

    def __get_circle_points(self, position, radius, **kwargs):
        """ Get points for a polygonised circle. """
        if radius == 0:
            return []
        points = []
        circumference = 2*math.pi*radius
        scale_factor = min(1.0, kwargs.get("scale_factor", 1.0))
        npoi = min(max(int(math.sqrt(circumference * scale_factor)), 6), 64)
        for i in range(0, npoi):
            angle = i/float(npoi) * math.pi * 2
            point = position + radius * Vec2d(math.cos(angle), math.sin(angle))
            points.append(point)
        return points

    def add_circle(self, position, radius, **kwargs):
        """ Emit a circular polygon. """
        self.add_polygon(self.__get_circle_points(position, radius, **kwargs), **kwargs)

    def add_circle_lines(self, position, radius, **kwargs):
        """ Emit a loop of line segments. """
        points = self.__get_circle_points(position, radius, **kwargs)
        points.append(points[0])
        self.add_lines(points, **kwargs)

    def add_lines(self, points, **kwargs):
        """ Emit a line. """

        # Determine the width of the line.
        width = 1
        if "width" in kwargs:
            width = kwargs["width"]

        # Add a line segment for each pair of vertices.
        i = 0
        while i+1 < len(points):

            # Get the segment.
            p0 = Vec2d(points[i])
            p1 = Vec2d(points[i+1])

            # Skip 0-length segment.
            if (p0 - p1).length == 0:
                continue

            # Determine the corners of a quad for the line segment.
            normal = (p0 - p1).perpendicular_normal() * width / 2.0
            tl = p1 - normal
            tr = p1 + normal
            br = p0 + normal
            bl = p0 - normal
            positions = (tl, tr, br, bl)

            # Emit the top left triangle.
            for j in (0, 1, 3):
                self.__vertex_data.add_vertex(origin=positions[j],
                                              texcoord=(0, 0, -1),
                                              **kwargs)

            # Emit the bottom right triangle.
            for j in (3, 1, 2):
                self.__vertex_data.add_vertex(origin=positions[j],
                                              texcoord=(0, 0, -1),
                                              **kwargs)

            # Move on to the next segment.
            i += 1

    def dispatch(self):
        """ Dispatch the command to the GPU. """

        # If there's nothing to do then avoid doing any work.
        if len(self.__vertex_data) == 0:
            return

        # Setup uniform data.
        GL.glUniform1i(self.__shader_program.get_uniform_location("coordinate_system"), self.__coordinate_system)

        # Draw the vertices.
        with Bind(self.__vertex_data):
            self.__vertex_data.draw(self.__primitive_type)


class Bind(object):
    """ Lets us pass a number of objects with begin/end to 'with'. """
    def __init__(self, *args):
        self.__objects = args
    def __enter__(self):
        for arg in self.__objects:
            arg.begin()
    def __exit__(self, type, value, traceback):
        for arg in reversed(self.__objects):
            arg.end()

class TextureUnitBinding(object):
    """ Bind a texture to a texture unit. """
    def __init__(self, texture, unit):
        self.__texture = texture
        self.__unit = unit
    def begin(self):
        GL.glActiveTexture(self.__unit)
        self.__texture.begin()
    def end(self):
        GL.glActiveTexture(self.__unit)
        self.__texture.end()
        GL.glActiveTexture(GL.GL_TEXTURE0)

class FontAtlas(object):
    """ Loads glyphs for a font into a texture array. """
    class Glyph(object):
        def __init__(self, ustring, font, texture_array):
            assert len(ustring) == 1
            self.glyph = ustring
            self.texture = texture_array.load_image(font.render(ustring, True, (255, 255, 255)));
            self.minx, self.maxx, self.miny, self.maxy, self.advance = font.metrics(ustring)[0]
    def __init__(self, texture_array, pygame_font):
        self.__first_page = -1
        self.__atlas = {}
        for codepoint in range(32, 0x01FF):
            ustring = unichr(codepoint)
            try:
                name = unicodedata.name(ustring)
            except ValueError:
                continue
            glyph = FontAtlas.Glyph(ustring, pygame_font, texture_array)
            if self.__first_page < 0:
                self.__first_page = glyph.texture.get_level()
            self.__atlas[ustring] = glyph
    def lookup_uchar(self, ustring):
        assert len(ustring) == 1
        return self.__atlas[ustring]
    def lookup_codepoint(self, codepoint):
        return self.lookup_uchar(unichr(codepoint))
    def first_page_index(self):
        return self.__first_page

class NkAtlasFont(pynk.nkpygame.NkPygameFont):
    """ Font interface through which nuklear can query our font atlas for
    texture coordinates. """

    def __init__(self, font, atlas):
        pynk.nkpygame.NkPygameFont.__init__(self, font)
        self.__atlas = atlas

    def query_glyph(self, height, glyph, codepoint, next_codepoint):
        """ Obtain texture coordinates for a glyph.  This is not necessary for
        pygame software rendering - it will only be called if nk_convert() VBO
        output is being used. """

        # struct nk_user_font_glyph {
        #     struct nk_vec2 uv[2];
        #     /* texture coordinates */
        #     struct nk_vec2 offset;
        #     /* offset between top left and glyph */
        #     float width, height;
        #     /* size of the glyph  */
        #     float xadvance;
        #     /* offset to the next glyph */
        # };

        try:
            atlas_glyph = self.__atlas.lookup_codepoint(codepoint)
        except KeyError:
            glyph.uv[0].x = 0
            glyph.uv[0].y = 0
            glyph.uv[1].x = 0
            glyph.uv[1].y = 0
            glyph.offset.x = 0
            glyph.offset.y = 0
            glyph.width = 0
            glyph.height = 0
            glyph.xadvance = 0;
            return

        a = atlas_glyph.texture.get_texcoord(0)
        b = atlas_glyph.texture.get_texcoord(2)
        glyph.uv[0].x = a[0]
        glyph.uv[0].y = a[1]
        glyph.uv[1].x = b[0]
        glyph.uv[1].y = b[1]
        glyph.offset.x = 0
        glyph.offset.y = 0
        glyph.width = atlas_glyph.texture.get_width()
        glyph.height = atlas_glyph.texture.get_height()
        glyph.xadvance = atlas_glyph.advance

    def get_texture_id(self):
        """ Obtain a texture id for font rendering.  If VBO output via
        nk_convert() is not being used, then this is not necessary. """
        return self.__atlas.first_page_index() + 1 # Note: see post_render().

class PygameOpenGLRenderer(Renderer):
    """ A hardware accelerated renderer using pygame to create an OpenGL
    context and load bitmaps etc."""

    def __init__(self, screen_size, options, **kwargs):
        """ Constructor. """
        Renderer.__init__(self, screen_size, options, **kwargs)
        self.__screen_size = screen_size
        self.__options = options
        self.__surface = None
        self.__data_path = kwargs["data_path"]
        self.__anim_shader = None
        self.__fbo_shader = None
        self.__texture_array = None
        self.__command_buffers = None
        self.__view = None
        self.__nuklear = None
        self.__font_atlas_lookup = {} # Font to atlas
        self.__font_atlases = {} # dims to atlas

    def initialise(self):
        """ Initialise the pygame display. """

        # We want an OpenGL display.
        self.__surface = pygame.display.set_mode(self.__screen_size, pygame.DOUBLEBUF|pygame.OPENGL)

        # Enable alpha blending.
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        # Output opengl version info.
        print ("OpenGL version: %s" % GL.glGetString(GL.GL_VERSION))
        print ("OpenGL vendor: %s" % GL.glGetString(GL.GL_VENDOR))
        print ("OpenGL max texture size: %s" % GL.glGetInteger(GL.GL_MAX_TEXTURE_SIZE))
        print ("OpenGL max array texture layers: %s" % GL.glGetInteger(GL.GL_MAX_ARRAY_TEXTURE_LAYERS))

        # Load the shader program.
        self.__anim_shader = self.__load_shader_program("anim")

        # Framebuffer to render into and shader for rendering from it.
        self.__fbo = Framebuffer(self.__screen_size[0],
                                 self.__screen_size[1],
                                 (GL.GL_COLOR_ATTACHMENT0, GL.GL_COLOR_ATTACHMENT1))
        self.__fbo_shader = self.__load_shader_program("simple_quad")

        # A quad in normalised device coordinates for framebuffer effects.
        self.__ndc_quad = self.__fbo_shader.create_vertex_buffers()
        self.__ndc_quad.add_vertex(position=(-1, -1), texcoord=(0, 0))
        self.__ndc_quad.add_vertex(position=(1, -1), texcoord=(1, 0))
        self.__ndc_quad.add_vertex(position=(1, 1), texcoord=(1, 1))
        self.__ndc_quad.add_vertex(position=(-1, 1), texcoord=(0, 1))

        # Framebuffers and shader for gaussian blur.
        self.__gaussian_blur_shader = self.__load_shader_program("gaussian_blur")
        self.__gaussian_blur_fbo0 = Framebuffer(self.__screen_size[0],
                                                self.__screen_size[1],
                                                [GL.GL_COLOR_ATTACHMENT0])
        self.__gaussian_blur_fbo1 = Framebuffer(self.__screen_size[0],
                                                self.__screen_size[1],
                                                [GL.GL_COLOR_ATTACHMENT0])

        # Create the texture array.
        self.__texture_array = TextureArray()

        # Initialise command buffers.  Jobs will be sorted by layer and coordinate system and added
        # to an appropriate command buffer for later dispatch.
        self.__command_buffers = CommandBufferArray(self.__anim_shader)

        # Create a special buffer and shader for rendering nuklear, which
        # creates its vertex buffer.
        self.__nuklear_shader = self.__load_shader_program("nuklear")
        self.__nuklear_buffer = self.__nuklear_shader.create_vertex_buffers()

    def pre_render(self, view):
        """ Prepare to build commands. """

        # Cache the view.
        self.__view = view

        # Delete scratch textures.
        self.__texture_array.reset_scratch()

        # Reset command buffers
        self.__command_buffers.reset()

    def post_render(self):
        """ Dispatch commands to gpu. """

        # Use texture unit 0 - we bind it to a uniform later.
        GL.glActiveTexture(GL.GL_TEXTURE0)

        exposure = 1.0
        gamma = 2.2

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # Render the scene to the FBO
        with Bind(self.__fbo,
                  self.__anim_shader,
                  TextureUnitBinding(self.__texture_array, GL.GL_TEXTURE0)):

            # Clear the buffer.
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)

            # Set uniform state.
            GL.glUniform1i(self.__anim_shader.get_uniform_location("texture_array"), 0)
            GL.glUniform2f(self.__anim_shader.get_uniform_location("view_position"),
                           *self.__view.position)
            GL.glUniform2f(self.__anim_shader.get_uniform_location("view_size"),
                           *self.__view.size)
            GL.glUniform1f(self.__anim_shader.get_uniform_location("view_zoom"),
                           self.__view.zoom)
            GL.glUniform1f(self.__anim_shader.get_uniform_location("gamma"), gamma)

            # Dispatch commands to the GPU.
            self.__command_buffers.dispatch()

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # Ping pong gaussian blur the brightness image.
        passes = 2
        with Bind(self.__gaussian_blur_shader,
                  self.__ndc_quad):
            GL.glUniform1i(self.__gaussian_blur_shader.get_uniform_location("image"), 0)

            # The first pass, using the main fbo colour attachment as input.
            with Bind(self.__gaussian_blur_fbo0,
                      self.__fbo.get_texture(GL.GL_COLOR_ATTACHMENT1)):
                GL.glUniform1i(self.__gaussian_blur_shader.get_uniform_location("horizontal"), 0)
                GL.glClear(GL.GL_COLOR_BUFFER_BIT)
                self.__ndc_quad.draw(GL.GL_QUADS)

            # Subsequent passes, do a 'ping pong'.  The result should end up in the second
            # fbo.
            assert passes > 0
            for i in range(1, passes*2+2):
                fbos = (self.__gaussian_blur_fbo0, self.__gaussian_blur_fbo1)
                from_fbo = fbos[(i+1)%2]
                to_fbo = fbos[i%2]
                with Bind(to_fbo, from_fbo.get_texture(GL.GL_COLOR_ATTACHMENT0)):
                    GL.glUniform1i(self.__gaussian_blur_shader.get_uniform_location("horizontal"), i%2)
                    GL.glClear(GL.GL_COLOR_BUFFER_BIT)
                    self.__ndc_quad.draw(GL.GL_QUADS)

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # Blend the brightness image with the main framebuffer.
        with Bind(self.__fbo_shader,
                  self.__ndc_quad,
                  TextureUnitBinding(self.__fbo.get_texture(GL.GL_COLOR_ATTACHMENT0), GL.GL_TEXTURE0),
                  TextureUnitBinding(self.__gaussian_blur_fbo1.get_texture(GL.GL_COLOR_ATTACHMENT0),
                                     GL.GL_TEXTURE1)):
            GL.glUniform1f(self.__fbo_shader.get_uniform_location("exposure"), exposure)
            GL.glUniform1f(self.__fbo_shader.get_uniform_location("gamma"), gamma)
            GL.glUniform1i(self.__fbo_shader.get_uniform_location("rendered_scene"), 0)
            GL.glUniform1i(self.__fbo_shader.get_uniform_location("bright_regions"), 1)
            self.__ndc_quad.draw(GL.GL_QUADS)

        # * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
        # Render the GUI.
        if self.__nuklear:
            with Bind(self.__nuklear_shader,
                      self.__nuklear_buffer):
                GL.glUniform2f(self.__nuklear_shader.get_uniform_location("view_size"),
                               *self.__view.size)
                offset = 0
                cmd = pynk.lib.nk__draw_begin(self.__nuklear.ctx, self.__nuklear_buffer.cmds)
                while cmd:
                    if cmd.elem_count > 0:
                        # Note: smuggling texture page in as texture ID, which is 0 for unspecified.
                        texture_page = -1 if cmd.texture.id == 0 else cmd.texture.id - 1
                        GL.glUniform1i(self.__nuklear_shader.get_uniform_location("texture_page"), texture_page)
                        GL.glScissor(int(cmd.clip_rect.x),
                                     int(self.__screen_size[1] - (cmd.clip_rect.y + cmd.clip_rect.h)),
                                     int(cmd.clip_rect.w),
                                     int(cmd.clip_rect.h))
                        self.__nuklear_buffer.draw_elements(GL.GL_TRIANGLES, cmd.elem_count, offset)
                        offset += cmd.elem_count
                    cmd = pynk.lib.nk__draw_next(cmd, self.__nuklear_buffer.cmds, self.__nuklear.ctx)
                GL.glBindTexture(GL.GL_TEXTURE_2D, 0)
                GL.glScissor(0, 0, *self.__view.size)

        # We're not rendering any more.
        self.__view = None
        self.__nuklear = None

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
        font = pygame.font.Font(filename, size)
        return font

    def load_compatible_gui_font(self, filename, size):
        """ Load a font that can be rendered on the GUI. """
        font = self.load_compatible_font(filename, size)
        atlas = FontAtlas(self.__texture_array, font)
        nkfont = NkAtlasFont(font, atlas)
        return nkfont

    def compatible_image_from_text(self, text, font, colour):
        """ Create an image by rendering a text string. """
        return self.__texture_array.load_image(font.render(text, True, colour))

    def screen_size(self):
        """ Get the display size. """
        return self.__surface.get_size()

    def screen_rect(self):
        """ Get the display size. """
        return self.__surface.get_rect()

    def render_background(self, background_image, **kwargs):
        """ Render scrolling background. """
        (coords, level) = self.__parse_kwargs(kwargs)
        buffer = self.__command_buffers.get_buffer(Renderer.COORDS_SCREEN,
                                                   Renderer.LEVEL_BACK_FAR,
                                                   GL.GL_TRIANGLES)
        """ Render scrolling background. """
        (image_width, image_height) = background_image.get_size()
        (screen_width, screen_height) = self.screen_size()
        pos = self.__view.position
        x = int(pos.x / 10000.0)
        y = int(pos.y / 10000.0)
        start_i = -(x%image_width)
        start_j = -(y%image_width)
        for i in range(start_i, screen_width, image_width):
            for j in range(start_j, screen_height, image_height):
                buffer.add_quad((i+image_width/2.0, j+image_width/2.0),
                                (image_width, image_height),
                                texref=background_image,
                                **kwargs)

    def render_rect(self, rect, **kwargs):
        """ Render rectangle. """
        width = kwargs.get("width", 0)
        if width > 0:
            kwargs["width"] = 0
            self.render_rect(Rect(rect.left, rect.top, rect.width, width), **kwargs)
            self.render_rect(Rect(rect.left, rect.bottom-width, rect.width, width), **kwargs)
            self.render_rect(Rect(rect.left, rect.top+width, width, rect.height-width*2), **kwargs)
            self.render_rect(Rect(rect.right-width, rect.top+width, width, rect.height-width*2), **kwargs)
            return
        (coords, level) = self.__parse_kwargs(kwargs)
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)
        buffer.add_quad(rect.center, rect.size, **kwargs)

    def render_line(self, p0, p1, **kwargs):
        """ Render a line. """
        (coords, level) = self.__parse_kwargs(kwargs)
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)
        buffer.add_lines((p0, p1), **kwargs)

    def render_lines(self, points, **kwargs):
        """ Render a polyline. """
        (coords, level) = self.__parse_kwargs(kwargs)
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)
        buffer.add_lines(points, **kwargs)

    def render_polygon(self, points, **kwargs):
        """ Render a polygon. """
        (coords, level) = self.__parse_kwargs(kwargs)
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)
        buffer.add_polygon(points, **kwargs)

    def render_circle(self, position, radius, **kwargs):
        """ Render a circle. """
        (coords, level) = self.__parse_kwargs(kwargs)
        width = 0
        if "width" in kwargs:
            width = kwargs["width"]
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)
        scale_factor = 1.0 
        if coords == Renderer.COORDS_WORLD:
            scale_factor = self.__view.zoom
        if width == 0:
            buffer.add_circle(position, radius, scale_factor=scale_factor, **kwargs)
        else:
            buffer.add_circle_lines(position, radius, scale_factor=scale_factor, **kwargs)

    def render_text(self, font, text, position, **kwargs):
        """ Render some text. """
        colour = kwargs.get("colour", (255, 255, 255))
        text = self.__texture_array.load_image_dynamic(
            font.render(text, True, colour)
        )
        del kwargs["colour"]
        self.render_image(position, text, **kwargs)

    def render_animation(self, position, orientation, anim, **kwargs):
        """ Render an animation. """
        (coords, level) = self.__parse_kwargs(kwargs)

        # Get command buffer to which to dispatch.
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)

        # Get texture information about current animation frame.
        texref = anim.frames.get_frame(anim.timer)

        # Dispatch a quad to the command buffer.
        buffer.add_quad(position,
                        texref.get_size(),
                        texref=texref,
                        orientation=orientation,
                        **kwargs)

    def render_image(self, position, image, **kwargs):
        """ Render an image. """
        (coords, level) = self.__parse_kwargs(kwargs)
        buffer = self.__command_buffers.get_buffer(coords, level, GL.GL_TRIANGLES)
        rect = pygame.Rect((0, 0), image.get_size())
        rect.topleft = position
        buffer.add_quad(rect.center,
                        image.get_size(),
                        texref=image,
                        **kwargs)

    def render_nuklear(self, nuklear, **kwargs):
        """ Render the nuklear GUI. """
        (screen_width, screen_height) = self.screen_size()
        self.__nuklear = nuklear
        self.__nuklear_buffer.reset()
        self.__nuklear_buffer.add_nuklear(nuklear)

    def __load_shader_program(self, name):
        """ Load a shader program. """
        return ShaderProgram(os.path.join(self.__data_path, os.path.join("shaders", name)))

    def __colour_int_to_float(self, colour):
        """ Convert colour to float format. """
        return (float(colour[0])/255, float(colour[1])/255, float(colour[2])/255)

    def __parse_kwargs(self, kwargs_dict):
        """ Extract level and coordinate system, map colour. """
        level = Renderer.LEVEL_MID
        if "level" in kwargs_dict:
            level = kwargs_dict["level"]
            del kwargs_dict["level"]
        coords = Renderer.COORDS_WORLD
        if "coords" in kwargs_dict:
            coords = kwargs_dict["coords"]
            del kwargs_dict["coords"]
        if "colour" in kwargs_dict:
            kwargs_dict["colour"] = self.__colour_int_to_float(kwargs_dict["colour"])
        else:
            kwargs_dict["colour"] = (1.0, 1.0, 1.0)
        if not "brightness" in kwargs_dict:
            kwargs_dict["brightness"] = 0.0
        return (coords, level)
