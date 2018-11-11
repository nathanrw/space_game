#version 130

// The texture page.
uniform int texture_page;

// The vertex position relative to the origin.
attribute vec2 position;

// Vertex texture coordinate.
attribute vec2 texcoord;

// Vertex colour.
attribute vec4 colour;

// Outputs to fragment shader.
varying vec3 v_colour;
varying vec3 v_texcoord;

// Compute the vertex position.
void main() {
  gl_Position = vec4(position, 0, 1);
  v_colour = colour.xyz;
  v_texcoord = vec3(texcoord, texture_page);
}
