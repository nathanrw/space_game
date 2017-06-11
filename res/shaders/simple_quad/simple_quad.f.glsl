#version 130

uniform sampler2D rendered_scene;
uniform sampler2D bright_regions;

varying vec2 v_texcoord;

void main() {
  vec2 view_size = textureSize(rendered_scene, 0);
  float offset_x = 1.0/(view_size.x/2);
  float offset_y = 1.0/(view_size.y/2);

  // Offsets for doing kernel operations.
  vec2 offsets_3x3[9] = vec2[](
                               vec2(-offset_x, -offset_y), vec2(0, -offset_y), vec2(offset_x, -offset_y),
                               vec2(-offset_x, 0        ), vec2(0,         0), vec2(offset_x, 0        ),
                               vec2(-offset_x, offset_y ), vec2(0, offset_y ), vec2(offset_x, offset_y )
                               );

  // A 3x3 blur kernel.
  float blur_3x3[9] = float[](
                              1/16.0, 2/16.0, 1/16.0,
                              2/16.0, 4/16.0, 2/16.0,
                              1/16.0, 2/16.0, 1/16.0
                              );

  // Don't do anything fancy, just add the bright colour on.
  vec3 bright_colour = texture(bright_regions, v_texcoord).rgb;
  vec3 combined_colour = texture(rendered_scene, v_texcoord).rgb + bright_colour;

  // Tone mapping / gamma correction taken from learnopengl.com.
  float gamma = 2.2;
  float exposure = 1.0;
  vec3 result = pow(vec3(1.0) - exp(-combined_colour * exposure), vec3(1.0/gamma));

  gl_FragColor = vec4(result, 1);
}
