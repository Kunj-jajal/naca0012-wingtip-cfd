from pathlib import Path
from parse_b11 import load_all_b11
from transform_coords import add_openfoam_coords
from parse_pv_info import load_takall_and_retakall

ROOT     = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "Wingtip_expdata"
OUT_DIR  = ROOT / "scripts" / "results"

def main():
    
    extracted_data = load_all_b11(DATA_DIR)
    openfoam_data = add_openfoam_coords(extracted_data)
    
    cols = ["x_of", "y_of", "z_of"]
    openfoam_data[cols].to_csv(OUT_DIR / "openfoam_coords_b11.csv", index = False)
    print(f"Saved {len(openfoam_data)} probe locations → {OUT_DIR / 'openfoam_coords_b11.csv'}")
    
    v_extracted,p_extracted = load_takall_and_retakall(DATA_DIR)
    p_openfoam = add_openfoam_coords(p_extracted)
    v_openfoam = add_openfoam_coords(v_extracted)
    
    p_openfoam[cols].to_csv(OUT_DIR / "openfoam_coords_p.csv", index = False)
    v_openfoam[cols].to_csv(OUT_DIR / "openfoam_coords_v.csv", index = False)
    print(f"Saved {len(p_openfoam)} probe locations → {OUT_DIR / 'openfoam_coords_p.csv'}")
    print(f"Saved {len(v_openfoam)} probe locations → {OUT_DIR / 'openfoam_coords_v.csv'}")
    
if __name__ == "__main__":
    main()
