shader_type canvas_item;
// Room reveal for the keep interior. TEXTURE = region map (1 px per tile): R,G,B = up to 3 region ids touching the tile.
// alpha_tex (256 x 1): R = darkness of each region (0 = in view, ~0.8 = visited, 1 = never seen). Soft 16 px edges.
uniform sampler2D alpha_tex : filter_nearest;
uniform sampler2D reg_tex : filter_nearest;
uniform vec2 cells;

float cell_a(ivec2 c) {
	c = clamp(c, ivec2(0), ivec2(cells) - 1);
	vec3 ids = texelFetch(reg_tex, c, 0).rgb * 255.0;
	float a = 1.0;
	if (ids.r > 0.5) { a = min(a, texelFetch(alpha_tex, ivec2(int(ids.r + 0.5), 0), 0).r); }
	if (ids.g > 0.5) { a = min(a, texelFetch(alpha_tex, ivec2(int(ids.g + 0.5), 0), 0).r); }
	if (ids.b > 0.5) { a = min(a, texelFetch(alpha_tex, ivec2(int(ids.b + 0.5), 0), 0).r); }
	return a;
}

void fragment() {
	vec2 p = UV * cells - 0.5;
	ivec2 i = ivec2(floor(p));
	vec2 f = fract(p);
	f = f * f * (3.0 - 2.0 * f);
	float a = mix(mix(cell_a(i), cell_a(i + ivec2(1, 0)), f.x), mix(cell_a(i + ivec2(0, 1)), cell_a(i + ivec2(1, 1)), f.x), f.y);
	COLOR = vec4(0.02, 0.02, 0.04, a);
}
