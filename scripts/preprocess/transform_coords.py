import math

# constants

chord_in = 48
aoa_rad = math.radians(10)
in_to_m = 0.0254

# transformation variables

xtrans = 0.75 * chord_in * math.cos(aoa_rad) + 0.25
ytrans = -0.75 * chord_in * math.sin(aoa_rad) - 5.3588
ztrans = 39.7714

def add_openfoam_coords(df):

	df = df.copy()
	
	df["x_of"] = (df["x_raw"] + xtrans) * in_to_m
	df["y_of"] = (df["y_raw"] + ytrans) * in_to_m
	df["z_of"] = (ztrans - df["z_raw"]) * in_to_m
	
	return df	
