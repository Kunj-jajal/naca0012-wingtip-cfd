#!/usr/bin/env python3
"""
parse_probe_results.py
======================
Reads the postProcessing probe output files produced by OpenFOAM and
writes three clean result CSVs to scripts/results/.

Run this AFTER the postProcess commands from write_probe_dicts.py.

Output CSVs
-----------
openfoam_results_v.csv    x_of, y_of, z_of, u, v, w
openfoam_results_p.csv    x_of, y_of, z_of, vmag, cp_stat, cp_tot
openfoam_results_b11.csv  x_of, y_of, z_of, u, v, w,
                          u_rms, v_rms, w_rms, uv, vw, uw

Normalisation
-------------
Velocity components : divided by Uinf
Reynolds stresses   : divided by Uinf²

RANS notes (k-omega SST)
------------------------
u_rms = v_rms = w_rms = sqrt(2k/3) / Uinf   (isotropic assumption)

Shear stresses via Boussinesq:
  <u'v'> = -nut * (dU/dy + dV/dx)
  <v'w'> = -nut * (dV/dz + dW/dy)
  <u'w'> = -nut * (dU/dz + dW/dx)

OpenFOAM grad(U) tensor layout (row-major, 9 components):
  index:  0       1       2       3       4       5       6       7       8
          dUx/dx  dUx/dy  dUx/dz  dUy/dx  dUy/dy  dUy/dz  dUz/dx  dUz/dy  dUz/dz
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd

# ── Paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
CASE_DIR     = (SCRIPT_DIR / "../../OpenFOAM").resolve()
RESULTS_DIR  = (SCRIPT_DIR / "../results").resolve()
POSTPROC_DIR = CASE_DIR / "postProcessing"

# ── Constants ──────────────────────────────────────────────────────────────────
UINF = 51.816   # m/s

# ── Input coordinate CSVs (needed to attach x,y,z to the results) ─────────────
COORD_FILES = {
    "v":   RESULTS_DIR / "openfoam_coords_v.csv",
    "p":   RESULTS_DIR / "openfoam_coords_p.csv",
    "b11": RESULTS_DIR / "openfoam_coords_b11.csv",
}

# ── Output result CSVs ─────────────────────────────────────────────────────────
RESULT_FILES = {
    "v":   RESULTS_DIR / "openfoam_results_v.csv",
    "p":   RESULTS_DIR / "openfoam_results_p.csv",
    "b11": RESULTS_DIR / "openfoam_results_b11.csv",
}


# ── Directory helper ───────────────────────────────────────────────────────────

def latest_time_subdir(base: Path) -> Path:
    """Return the numerically largest time sub-directory inside base/."""
    candidates = []
    for d in base.iterdir():
        if d.is_dir():
            try:
                float(d.name)
                candidates.append(d)
            except ValueError:
                pass
    if not candidates:
        raise FileNotFoundError(f"No time sub-directories found in {base}")
    return max(candidates, key=lambda d: float(d.name))


# ── OpenFOAM probes file parsers ───────────────────────────────────────────────
#
# OpenFOAM probes output format (one file per field):
#
#   # Probe 0  (x0 y0 z0)
#   # Probe 1  (x1 y1 z1)
#   ...
#   # Time        0           1        ...
#   <time>    val0        val1         ...   <- scalar
#   <time>    (ux uy uz)  (ux uy uz)   ...   <- vector
#   <time>    (t0 .. t8)  (t0 .. t8)   ...   <- tensor
#
# Since we sampled with -latestTime there is exactly ONE data line.

def _last_data_line(filepath: Path) -> str:
    """Return the last non-comment, non-empty line in a probes output file."""
    last = None
    with open(filepath) as fh:
        for line in fh:
            s = line.strip()
            if s and not s.startswith("#"):
                last = s
    if last is None:
        raise ValueError(f"No data found in {filepath}")
    return last


def parse_scalar(filepath: Path, n: int) -> np.ndarray:
    """Scalar probes file → (n,) array.  Column 0 is time, skipped."""
    parts = _last_data_line(filepath).split()
    values = np.array(parts[1:], dtype=float)
    assert len(values) == n, f"{filepath.name}: expected {n} values, got {len(values)}"
    return values


def parse_vector(filepath: Path, n: int) -> np.ndarray:
    """Vector probes file → (n, 3) array."""
    line   = _last_data_line(filepath)
    tuples = re.findall(r'\(([^)]+)\)', line)
    arr    = np.array([list(map(float, t.split())) for t in tuples])
    assert arr.shape == (n, 3), f"{filepath.name}: expected ({n},3), got {arr.shape}"
    return arr


def parse_tensor(filepath: Path, n: int) -> np.ndarray:
    """
    Tensor probes file → (n, 9) array (full tensor, row-major).

    Handles both:
      - Full tensor     (9 components)
      - symmTensor      (6 components: xx xy xz yy yz zz) → expanded to 9
    """
    line   = _last_data_line(filepath)
    tuples = re.findall(r'\(([^)]+)\)', line)
    raw    = [list(map(float, t.split())) for t in tuples]
    assert len(raw) == n, f"{filepath.name}: expected {n} tensors, got {len(raw)}"

    n_comp = len(raw[0])

    if n_comp == 9:
        return np.array(raw)

    elif n_comp == 6:
        # symmTensor: xx xy xz yy yz zz
        s    = np.array(raw)
        full = np.empty((n, 9))
        full[:, 0] = s[:, 0]  # dUx/dx
        full[:, 1] = s[:, 1]  # dUx/dy  (= dUy/dx for symm, but grad is NOT symm)
        full[:, 2] = s[:, 2]  # dUx/dz
        full[:, 3] = s[:, 1]  # dUy/dx
        full[:, 4] = s[:, 3]  # dUy/dy
        full[:, 5] = s[:, 4]  # dUy/dz
        full[:, 6] = s[:, 2]  # dUz/dx
        full[:, 7] = s[:, 4]  # dUz/dy
        full[:, 8] = s[:, 5]  # dUz/dz
        return full

    else:
        raise ValueError(f"{filepath.name}: unexpected component count {n_comp}")


# ── Result builders ────────────────────────────────────────────────────────────

def build_v(coords: np.ndarray, tdir: Path, n: int) -> pd.DataFrame:
    U = parse_vector(tdir / "U", n)
    return pd.DataFrame({
        "x_of": coords[:, 0],
        "y_of": coords[:, 1],
        "z_of": coords[:, 2],
        "u":    U[:, 0] / UINF,
        "v":    U[:, 1] / UINF,
        "w":    U[:, 2] / UINF,
    })


def build_p(coords: np.ndarray, tdir: Path, n: int) -> pd.DataFrame:
    U    = parse_vector(tdir / "U",        n)
    cp_s = parse_scalar(tdir / "CpStatic", n)
    cp_t = parse_scalar(tdir / "CpTotal",  n)
    return pd.DataFrame({
        "x_of":    coords[:, 0],
        "y_of":    coords[:, 1],
        "z_of":    coords[:, 2],
        "vmag":    np.linalg.norm(U, axis=1),
        "cp_stat": cp_s,
        "cp_tot":  cp_t,
    })


def build_b11(coords: np.ndarray, tdir: Path, n: int) -> pd.DataFrame:
    U   = parse_vector(tdir / "U",     n)   # (n, 3)
    k   = parse_scalar(tdir / "k",     n)   # (n,)
    nut = parse_scalar(tdir / "nut",   n)   # (n,)
    gU  = parse_tensor(tdir / "gradU", n)   # (n, 9)

    # RMS from TKE — isotropic RANS assumption
    rms = np.sqrt(np.maximum(2.0 * k / 3.0, 0.0)) / UINF

    # Boussinesq shear stresses, normalised by Uinf²
    #   <u'v'> = -nut * (dU/dy + dV/dx)  →  gU indices [1] + [3]
    #   <v'w'> = -nut * (dV/dz + dW/dy)  →  gU indices [5] + [7]
    #   <u'w'> = -nut * (dU/dz + dW/dx)  →  gU indices [2] + [6]
    uv = -nut * (gU[:, 1] + gU[:, 3]) / UINF**2
    vw = -nut * (gU[:, 5] + gU[:, 7]) / UINF**2
    uw = -nut * (gU[:, 2] + gU[:, 6]) / UINF**2

    return pd.DataFrame({
        "x_of":  coords[:, 0],
        "y_of":  coords[:, 1],
        "z_of":  coords[:, 2],
        "u":     U[:, 0] / UINF,
        "v":     U[:, 1] / UINF,
        "w":     U[:, 2] / UINF,
        "u_rms": rms,
        "v_rms": rms,
        "w_rms": rms,
        "uv":    uv,
        "vw":    vw,
        "uw":    uw,
    })


BUILDERS = {"v": build_v, "p": build_p, "b11": build_b11}


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print()
    print("=" * 60)
    print("  parse_probe_results.py")
    print("=" * 60)
    print(f"  postProcessing : {POSTPROC_DIR}")
    print(f"  Results out    : {RESULTS_DIR}")

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    for key in ["v", "p", "b11"]:
        probe_name = f"probes_{key}"
        print(f"\n  ── {probe_name} ──")

        # Locate latest time directory inside postProcessing/probes_<key>/
        tdir = latest_time_subdir(POSTPROC_DIR / probe_name)
        print(f"     Reading from : {tdir}")

        # Read coordinates (to attach x, y, z columns to results)
        # Drop NaN rows — must match exactly what write_probe_dicts.py wrote
        df_coords = pd.read_csv(COORD_FILES[key]).dropna()
        coords = df_coords.values   # (N, 3)
        n = len(coords)

        df = BUILDERS[key](coords, tdir, n)
        df.to_csv(RESULT_FILES[key], index=False, float_format="%.8f")

        print(f"     Written      : {RESULT_FILES[key].name}"
              f"  ({n:,} rows × {len(df.columns)} cols)")
        print(f"     Columns      : {list(df.columns)}")

    print()
    print("=" * 60)
    print("  Done.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
