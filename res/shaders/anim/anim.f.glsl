#version 130

varying vec3 v_colour;
varying vec3 v_texcoord;

uniform sampler2DArray texture_array;

void main() {

  // Apply the vertex colour.
  gl_FragColor = vec4(v_colour, 1.0);

  // A negative level means don't use a texture.
  if (v_texcoord.z >= 0) {
    gl_FragColor *= texture(texture_array, v_texcoord);
  }
}
