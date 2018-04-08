Nuklear OpenGL
=================

I've integrated the nuklear GUI library.  Rendering via pygame works fine,
but I need to implement OpenGL rendering.

Several things need to be done:
* Render the vertex buffer output from nk_convert in the OpenGL
  renderer.  This is in the form of an interleaved array of positions,
  texcoords and so on.  The issue at present is that I currently have
  a separate buffer for each vertex attribute.
* Bake a font atlas and upload it so that font rendering works. (This
  will be useful generally because at present text rendering is done
  on the CPU with the resulting texture uploaded to the GPU each time. )
  
Vertex Specification
------------------------

* Make VertexData store all attributes interleaved in the same array.
* Add a way to pass a compatible buffer directly to a VertexData.

     # * * * * * 
     # Renderer.initialise()
     self.__nuklear_shader = self.__load_shader_program("nuklear")
     self.__nuklear_vertices = self.__nuklear_shader.create_vertex_buffers()
     
     # * * * * * * 
     # VertexData
     def get_vertex_specification() # For nk_convert() to give the right format.
     def set_buffer(...) # To pass in the resulting buffer.
     
     # * * * * * 
     # Renderer.post_render()
     GL.glEnable(Gl.GL_SCISSOR)
     commands = get_nuklear_command_queue()
     nk_convert(commands, ...) # Note - get vertex format from VertexData
     self.__nuklear_vertices.set_buffer(...)
     elem_offset = 0
     with Bind(self.__nuklear_shader,
               self.__nuklear_vertices,
               TextureUnitBinding(self.__texture_array, GL.GL_TEXTURE0)):
         for each command:
             GL.glScissor(...)
             self.__nuklear_vertices.draw_elements(..., elem_offset, ...)
             elem_offset += ...
     GL.glDisable(GL.GL_SCISSOR)

Font Atlas
------------

* Bake all fonts under res/ into a nuklear font atlas, and upload the texture 
  to the renderer. Do any necessary work to stitch things together.
* Make all font rendering use the atlas - use nuklear code.

Note that I think the atlas might need a font baked for each size we want to
use it at.
