#version 130

uniform vec2 window_size;
uniform vec2 view_position;
uniform float scale;

void main() {
  vec2 pos = vec2(gl_Vertex.x, -gl_Vertex.y);
  vec2 view_pos = vec2(view_position.x, -view_position.y);
  gl_Position = vec4((pos - view_pos) * scale / (window_size/2), 0, 1);
}