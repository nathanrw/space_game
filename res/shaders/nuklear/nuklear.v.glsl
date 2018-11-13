#version 130

// The texture page.
uniform int texture_page;

// The size of the screen in pixels.
uniform vec2 view_size;

// The vertex position relative to the origin.
attribute vec2 position;

// Vertex texture coordinate.
attribute vec2 texcoord;

// Vertex colour.
attribute vec4 colour;

// Outputs to fragment shader.
varying vec3 v_colour;
varying vec3 v_texcoord;

// Flip the y axis of a vector.
vec2 flip_y(vec2 v) {
  return vec2(v.x, -v.y);
}

// Compute the vertex position.
void main() {
  vec2 position_normalised = flip_y(position - view_size / 2) / (view_size/2);
  gl_Position = vec4(position_normalised, 0, 1);
  v_colour = colour.xyz;
  v_texcoord = vec3(texcoord, texture_page);
}
