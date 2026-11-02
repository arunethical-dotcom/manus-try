shader_type canvas_item;
// Full-screen colour grade: vibrance, saturation, contrast, warm highlights / cool shadows, slight vignette.
uniform sampler2D screen_tex : hint_screen_texture, filter_nearest;
uniform float vibrance = 0.40;
uniform float saturation = 1.12;
uniform float contrast = 1.10;
uniform float brightness = 0.02;
uniform vec3 shadow_tint = vec3(0.97, 1.0, 1.05);
uniform vec3 highlight_tint = vec3(1.03, 1.015, 0.975);
uniform float vignette = 0.18;

void fragment() {
	vec3 c = texture(screen_tex, SCREEN_UV).rgb;
	float l = dot(c, vec3(0.299, 0.587, 0.114));
	c = mix(vec3(l), c, saturation);
	float mx = max(c.r, max(c.g, c.b));
	float mn = min(c.r, min(c.g, c.b));
	float sat = mx - mn;
	c = mix(vec3(l), c, 1.0 + vibrance * (1.0 - sat));          // boosts the dull colours most
	c = (c - 0.5) * contrast + 0.5 + brightness;
	l = clamp(dot(c, vec3(0.299, 0.587, 0.114)), 0.0, 1.0);
	c *= mix(shadow_tint, highlight_tint, smoothstep(0.2, 0.8, l));
	vec2 d = SCREEN_UV - 0.5;
	c *= 1.0 - vignette * dot(d, d) * 2.0;
	COLOR = vec4(clamp(c, 0.0, 1.0), 1.0);
}
