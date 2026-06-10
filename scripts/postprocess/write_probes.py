"""
write_probe_dicts.py
====================
Reads the three probe coordinate CSVs and writes the corresponding
OpenFOAM function-object dictionary files into the case system/ folder.

"""

from pathlib import Path
import pandas as pd
 
# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).resolve().parent
CASE_DIR    = (SCRIPT_DIR / "../../OpenFOAM").resolve()
RESULTS_DIR = (SCRIPT_DIR / "../results").resolve()
SYS_DIR     = CASE_DIR / "system"
 
# ── Input coordinate CSVs ──────────────────────────────────────────────────────
COORD_FILES = {
    "v":   RESULTS_DIR / "openfoam_coords_v.csv",    # velocity probes
    "p":   RESULTS_DIR / "openfoam_coords_p.csv",    # pressure probes
    "b11": RESULTS_DIR / "openfoam_coords_b11.csv",  # triple-wire probes
}

# ── Fields to sample per probe set ────────────────────────────────────────────
PROBE_FIELDS = {
    "v":   ["U"],
    "p":   ["U", "CpStatic", "CpTotal"],
    "b11": ["U", "k", "nut", "gradU"],
}

# ── Dict writers ───────────────────────────────────────────────────────────────
 
def write_gradu_compute_dict() -> Path:
    """
    Writes system/gradU_compute.
    postProcess with this dict computes grad(U) and writes it to the
    last time directory as a file named 'grad(U)'.
    You then rename that file to 'gradU' (see instructions below).
    """
    content = """\
/*--------------------------------*- C++ -*----------------------------------*\\
  gradU_compute — computes grad(U) and writes it to the time directory
\\*---------------------------------------------------------------------------*/
gradU_compute
{
    type            grad;
    libs            (fieldFunctionObjects);
 
    field           U;
 
    writeControl    timeStep;
    writeInterval   1;
}
"""
    path = SYS_DIR / "gradU_compute"
    path.write_text(content)
    return path


def write_probes_dict(probe_name: str, coords, fields: list) -> Path:
    """
    Writes a probes function-object dict to system/<probe_name>.
    coords is a (N, 3) array of x, y, z values.
    """
    lines = [
        "/*--------------------------------*- C++ -*----------------------------------*\\",
        f"  {probe_name}",
        "\\*---------------------------------------------------------------------------*/",
        f"{probe_name}",
        "{",
        "    type            probes;",
        "    libs            (sampling);",
        "",
        "    writeControl    timeStep;",
        "    writeInterval   1;",
        "",
        f"    fields          ({' '.join(fields)});",
        "",
        "    probeLocations",
        "    (",
    ]
 
    for row in coords:
        x, y, z = row
        lines.append(f"        ({x:.6f} {y:.6f} {z:.6f})")
 
    lines += [
        "    );",
        "}",
    ]
 
    content = "\n".join(lines) + "\n"
    path = SYS_DIR / probe_name
    path.write_text(content)
    return path


# ── Main ───────────────────────────────────────────────────────────────────────
 
def main():
 
    # 1. gradU_compute dict
    p = write_gradu_compute_dict()
    print(f"\n  Written: {p.name}")
 
    # 2. Probes dicts
    for key in ["v", "p", "b11"]:
        probe_name = f"probes_{key}"
        coords = pd.read_csv(COORD_FILES[key]).values   # shape (N, 3)
        n = len(coords)
        p = write_probes_dict(probe_name, coords, PROBE_FIELDS[key])
        print(f"  Written: {p.name}   ({n:,} probes,  fields: {PROBE_FIELDS[key]})")
 
 
if __name__ == "__main__":
    main()

