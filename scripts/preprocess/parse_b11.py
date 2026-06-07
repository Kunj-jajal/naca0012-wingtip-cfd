import pandas as pd
import glob
import os

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
