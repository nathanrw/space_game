#version 130

varying vec3 v_colour;
varying vec3 v_texcoord;

uniform sampler2DArray texture_array;

void main() {

  // Apply the vertex colour.
  gl_FragData[0] = vec4(v_colour, 1.0);

  // A negative level means don't use a texture.
  if (v_texcoord.z >= 0) {
    vec4 tex_col = texture(texture_array, v_texcoord);
    gl_FragData[0] *= tex_col;
  }
}
