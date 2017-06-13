#version 130

// The size of the view, in pixels.
uniform vec2 view_size;

// The position of the centre of the view, in world space.
uniform vec2 view_position;

// The zoom level of the view.
uniform float view_zoom;

// The coordinate system in which vertex attributes are defined.
uniform int coordinate_system;

// Possible values for coordinate_system.
const int COORDS_WORLD = 0;
const int COORDS_SCREEN = 1;

// The origin of vertices being rendered.
attribute vec2 origin;

// The vertex position relative to the origin.
attribute vec2 position;

// The orientation of the vertex about the origin.
attribute float orientation;

// Vertex texture coordinate.
attribute vec3 texcoord;

// Vertex colour.
attribute vec3 colour;

// Brightness (glow)
attribute float brightness;

// Outputs to fragment shader.
varying vec3 v_colour;
varying vec3 v_texcoord;
varying float v_brightness;

// Pi
const float PI = 3.1415926535897932384626433832795;

// Rotate a 2D vector about the origin.
vec2 rotate(vec2 v, float angle) {
  float s = sin(angle);
  float c = cos(angle);
  return vec2(v.x*c - v.y*s, v.y*c + v.x*s);
}

// Flip the y axis of a vector.
vec2 flip_y(vec2 v) {
  return vec2(v.x, -v.y);
}

// Convert from degrees to radians.
float to_radians(float degrees) {
  return degrees * PI / 180;
}

// Get a point into screen coordinates - it might be already.
vec2 get_screen_coords(vec2 point,
                       vec2 view_position,
                       vec2 view_size,
                       float view_zoom,
                       int coordinate_system) {
  if (coordinate_system == COORDS_SCREEN) {
    return flip_y(point - view_size / 2) / (view_size/2);
  } else {
    return (flip_y(point - view_position) * view_zoom) / (view_size/2);
  }
}

// Compute the vertex position.
void main() {

  // Convert the 'model' coordinates to world.
  vec2 position_world = rotate(position, -to_radians(orientation)) + origin;

  // Convert world coordinates to normalised screen coordinates
  vec2 position_screen=
    get_screen_coords(position_world, view_position, view_size, view_zoom, coordinate_system);

  // Output the vertex.
  gl_Position = vec4(position_screen, 0, 1);
  v_colour = colour;
  v_texcoord = texcoord;
  v_brightness = brightness;
}
