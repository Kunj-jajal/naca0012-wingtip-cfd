import pandas as pd
import glob
import os

def load_takall_and_retakall(data_dir):

	file1 = sorted(glob.glob(os.path.join(data_dir, "TAKALL.DAT")))
	file2 = sorted(glob.glob(os.path.join(data_dir, "RETAKALL.DAT")))
	
	df1 = pd.read_csv(file1[0], sep='\s+', header = None, names = ["x_raw", "y_raw", "z_raw", "u", "v", "w", "flag1", "flag2", "flag3", "flag4"])
	df1["w"] = -df1["w"]
	
	df2 = pd.read_csv(file2[0], sep='\s+', header = None, names = ["x_raw", "y_raw", "z_raw", "vmag", "cp_stat", "cp_tot", "flag1", "flag2", "flag3", "flag4"])
	
	return df1, df2
