shader_type canvas_item;
// Base wall layer (drawn under Kael). Each pixel carries its object id (depth texture B channel); objects Kael is
// standing behind fade as a whole (CrossCode style): fade_tex.r[id] = 0 (solid) .. 1 (fully see-through).
uniform sampler2D depth_tex : filter_nearest;
uniform sampler2D fade_tex : filter_nearest;
uniform float see_alpha = 0.35;

void fragment() {
	vec4 c = texture(TEXTURE, UV);
	float id = floor(texture(depth_tex, UV).b * 255.0 + 0.5);
	float f = texture(fade_tex, vec2((id + 0.5) / 256.0, 0.5)).r;
	COLOR = vec4(c.rgb, c.a * mix(1.0, see_alpha, f));
}
