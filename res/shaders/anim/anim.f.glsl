#version 130

varying vec3 v_colour;
varying vec3 v_texcoord;
varying float v_brightness;

uniform sampler2DArray texture_array;

void main() {

  // Apply the vertex colour.
  gl_FragData[0] = vec4(v_colour, 1.0);

  // A negative level means don't use a texture.
  if (v_texcoord.z >= 0) {
    gl_FragData[0] *= texture(texture_array, v_texcoord);
  }

  // If brightness is non-zero then this fragment is glowing.
  gl_FragData[0].xyz *= (1.0 + v_brightness);

  // Weights to use when extractig brightness from a colour.  These add
  // up to 1.0 so that (1.0, 1.0, 1.0) has a brightness of 1.0.  Note
  // that note all weights are equal - I believe this is due to the human
  // eye perceiving the brightness of different colours differently.  These
  // values were taken from the excellent learnopengl.com
  vec3 brightness_weights = vec3(0.2126, 0.7152, 0.0722);

  // Write bright regions to the second render target.
  float brightness  = dot(gl_FragData[0].xyz, brightness_weights);
  gl_FragData[1] = vec4(0, 0, 0, 1);
  if (brightness > 1.0) {
    gl_FragData[1] = gl_FragData[0];
  }
}
