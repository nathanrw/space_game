#version 130

uniform sampler2D rendered_scene;
uniform sampler2D bright_regions;
uniform float exposure;
uniform float gamma;

varying vec2 v_texcoord;

void main() {
  vec2 view_size = textureSize(rendered_scene, 0);
  float offset_x = 1.0/(view_size.x/2);
  float offset_y = 1.0/(view_size.y/2);

  // Don't do anything fancy, just add the bright colour on.
  vec3 bright_colour = texture(bright_regions, v_texcoord).rgb;
  vec3 original_colour = texture(rendered_scene, v_texcoord).rgb;
  vec3 combined_colour =  original_colour + bright_colour;

  // Tone mapping / gamma correction taken from learnopengl.com.
  vec3 tone_mapped = vec3(1.0) - exp(-combined_colour * exposure);
  vec3 gamma_corrected = pow(tone_mapped, vec3(1.0/gamma));

  gl_FragColor = vec4(gamma_corrected, 1);
}
