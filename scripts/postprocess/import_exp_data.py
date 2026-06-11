import pandas as pd
import glob
import os
from pathlib import Path

import math

# Functions to load the files

def load_all_b11(data_dir):

    # Reads all *.b11 files and returns a single dataframe

    files = sorted(glob.glob(os.path.join(data_dir, "TAK3W*C.B11")))

    frames = []
    for fp in files:
        df = _read_single_b11(fp)
        df["station"] = os.path.basename(fp)
        frames.append(df)

    return pd.concat(frames, ignore_index=True)
	
def _read_single_b11(filepath):
	
	df = pd.read_csv(filepath, sep='\s+', header = None, names = ["pt", "x_raw", "y_raw", "z_raw", "u", "v", "w", "u_rms", "v_rms", "w_rms", "uv", "vw", "uw", "flag"])
	df["w"] = -df["w"]
	
	return df
	
def load_takall_and_retakall(data_dir):

	file1 = sorted(glob.glob(os.path.join(data_dir, "TAKALL.DAT")))
	file2 = sorted(glob.glob(os.path.join(data_dir, "RETAKALL.DAT")))
	
	df1 = pd.read_csv(file1[0], sep='\s+', header = None, names = ["x_raw", "y_raw", "z_raw", "u", "v", "w", "flag1", "flag2", "flag3", "flag4"])
	df1["w"] = -df1["w"]
	
	df2 = pd.read_csv(file2[0], sep='\s+', header = None, names = ["x_raw", "y_raw", "z_raw", "vmag", "cp_stat", "cp_tot", "flag1", "flag2", "flag3", "flag4"])
	
	return df1, df2
	
# Functions to transform the coordinates
	
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
	
# Add openfoam coordinates to dataframe

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "Wingtip_expdata"

def exp_data():
    
    extracted_data = load_all_b11(DATA_DIR)
    exp_b11 = add_openfoam_coords(extracted_data)
    
    v_extracted,p_extracted = load_takall_and_retakall(DATA_DIR)
    exp_p = add_openfoam_coords(p_extracted)
    exp_v = add_openfoam_coords(v_extracted)
    
    return exp_b11, exp_p, exp_v
