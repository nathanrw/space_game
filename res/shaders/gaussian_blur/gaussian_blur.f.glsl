#version 130

// Image we are blurring.
uniform sampler2D image;

// Are we doing vertical or horizontal pass?
uniform int horizontal;

// Tex coordinate for this fragment.
varying vec2 v_texcoord;

void main() {

  // The contribution of the current fragment.
  vec2 tex_offset = 1.0 / textureSize(image, 0);

  // Gaussian weights, gotten from learnopengl.com
  float weights[5] = float[] (0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

  // Vertical and horizontal offsets.
  vec2 offsets[2] = vec2[](vec2(0, tex_offset.y),
                           vec2(tex_offset.x, 0));

  // Do 1 pass of gaussian blur.
  gl_FragColor = vec4(texture(image, v_texcoord).rgb * weights[0], 1);
  for (int i = 1; i < 5; ++i) {
    gl_FragColor.xyz += texture(image, v_texcoord + offsets[horizontal]*i).rgb * weights[i];
    gl_FragColor.xyz += texture(image, v_texcoord - offsets[horizontal]*i).rgb * weights[i];
  }
}
