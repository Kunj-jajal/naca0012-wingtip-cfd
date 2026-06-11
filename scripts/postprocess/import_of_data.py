import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "scripts" / "results"

# ── Loaders ────────────────────────────────────────────────────────────────────

def load_of_b11(results_dir):
    """
    Reads openfoam_results_b11.csv and returns a single dataframe.

    Assigns a 'station' column matching the B11 filename convention
    (TAK3W1C.B11 ... TAK3W10C.B11) by ranking the 10 unique x_of values
    in ascending order — matching the order the experimental planes were
    concatenated in import_exp_data.py.
    """
    df = pd.read_csv(results_dir / "openfoam_results_b11.csv")

    # Each plane sits at a distinct x_of value. Rank them 1–10 by ascending x.
    unique_x = sorted(df["x_of"].unique())
    x_to_station = {x: f"TAK3W{i}C.B11" for i, x in enumerate(unique_x, start=1)}
    df["station"] = df["x_of"].map(x_to_station)

    return df


def load_of_v(results_dir):
    """Reads openfoam_results_v.csv — mean velocity probes."""
    return pd.read_csv(results_dir / "openfoam_results_v.csv")


def load_of_p(results_dir):
    """Reads openfoam_results_p.csv — pressure probes."""
    return pd.read_csv(results_dir / "openfoam_results_p.csv")


# ── Public entry point ─────────────────────────────────────────────────────────

def of_data():
    of_b11 = load_of_b11(RESULTS_DIR)
    of_v   = load_of_v(RESULTS_DIR)
    of_p   = load_of_p(RESULTS_DIR)

    return of_b11, of_p, of_v
