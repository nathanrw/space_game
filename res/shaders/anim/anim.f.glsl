#version 130

varying vec3 v_colour;
varying vec3 v_texcoord;

uniform sampler2DArray texture_array;

void main() {

  // Apply the vertex colour.
  gl_FragData[0] = vec4(v_colour, 1.0);

  // A negative level means don't use a texture.
  if (v_texcoord.z >= 0) {
    gl_FragData[0] *= texture(texture_array, v_texcoord);
  }

  // Write bright regions to the second render target.
  // Note: vector constant taken from the excellent learnopengl.com
  // Note: If we were doing HDR, the brightness comparison could be against
  // 1.0 not 0.8.
  float brightness  = dot(gl_FragData[0].xyz, vec3(0.2126, 0.7152, 0.0722));
  gl_FragData[1] = vec4(0, 0, 0, 1);
  if (brightness > 0.9) {
    gl_FragData[1] = gl_FragData[0];
  }
}
