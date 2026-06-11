import pandas as pd
import numpy as np
from pathlib import Path

from import_exp_data import exp_data
from import_of_data  import of_data

ROOT        = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT / "scripts" / "results"

# ── Load ───────────────────────────────────────────────────────────────────────
exp_b11, exp_p, exp_v = exp_data()
of_b11,  of_p,  of_v  = of_data()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 1 — MERGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Coordinates are rounded to 6 decimal places before merging.
# Necessary because exp dataframes compute x_of/y_of/z_of fresh in Python
# (full float64), while CFD result CSVs were written rounded to 8 decimal
# places and read back — tiny differences prevent exact float matches.

COORD_ROUND = 6
COORD_KEYS  = ["x_of", "y_of", "z_of"]

for df in [exp_b11, of_b11, exp_v, of_v, exp_p, of_p]:
    for col in COORD_KEYS:
        df[col] = df[col].round(COORD_ROUND)

merged_b11 = pd.merge(
    exp_b11, of_b11,
    on       = ["x_of", "y_of", "z_of", "station"],
    suffixes = ("_exp", "_cfd")
)

merged_v = pd.merge(
    exp_v, of_v,
    on       = ["x_of", "y_of", "z_of"],
    suffixes = ("_exp", "_cfd")
)

merged_p = pd.merge(
    exp_p, of_p,
    on       = ["x_of", "y_of", "z_of"],
    suffixes = ("_exp", "_cfd")
)

# Diagnostic — catch empty merges immediately before writing anything
print(f"merged_b11 : {len(merged_b11):>6} rows")
print(f"merged_v   : {len(merged_v):>6} rows")
print(f"merged_p   : {len(merged_p):>6} rows")

assert len(merged_b11) > 0, "merged_b11 empty — try reducing COORD_ROUND"
assert len(merged_v)   > 0, "merged_v   empty — try reducing COORD_ROUND"
assert len(merged_p)   > 0, "merged_p   empty — try reducing COORD_ROUND"

# Derive station label for v and p (no station column — group by x plane)
merged_v["station"] = merged_v["x_of"].round(3).astype(str)
merged_p["station"] = merged_p["x_of"].round(3).astype(str)

# Delta columns  (CFD − experiment)
b11_qty = ["u", "v", "w", "u_rms", "v_rms", "w_rms", "uv", "vw", "uw"]
v_qty   = ["u", "v", "w"]
p_qty   = ["vmag", "cp_stat", "cp_tot"]

for q in b11_qty:
    merged_b11[f"delta_{q}"] = merged_b11[f"{q}_cfd"] - merged_b11[f"{q}_exp"]

for q in v_qty:
    merged_v[f"delta_{q}"] = merged_v[f"{q}_cfd"] - merged_v[f"{q}_exp"]
    
Uinf = 51.816 # vmag openfoam data needs to be normalized for postprocessing

for q in p_qty:
	if q == "vmag":
		merged_p[f"delta_{q}"] = (merged_p[f"{q}_cfd"] / Uinf) - merged_p[f"{q}_exp"]
	else:
		merged_p[f"delta_{q}"] = merged_p[f"{q}_cfd"] - merged_p[f"{q}_exp"]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 2 — PER-PLANE METRICS  (RMSE and MAE per station)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def plane_metrics(merged, quantities):
    rows = []
    for station, group in merged.groupby("station"):
        row = {"station": station}
        for q in quantities:
            delta = group[f"delta_{q}"]
            row[f"rmse_{q}"] = np.sqrt((delta ** 2).mean())
            row[f"mae_{q}"]  = delta.abs().mean()
        rows.append(row)
    return pd.DataFrame(rows)

metrics_b11 = plane_metrics(merged_b11, b11_qty)
metrics_v   = plane_metrics(merged_v,   v_qty)
metrics_p   = plane_metrics(merged_p,   p_qty)

metrics_b11.to_csv(RESULTS_DIR / "metrics_b11.csv", index=False, float_format="%.6f")
metrics_v  .to_csv(RESULTS_DIR / "metrics_v.csv",   index=False, float_format="%.6f")
metrics_p  .to_csv(RESULTS_DIR / "metrics_p.csv",   index=False, float_format="%.6f")

print("\nMetrics b11:")
print(metrics_b11.to_string(index=False))
print("\nMetrics v:")
print(metrics_v.to_string(index=False))
print("\nMetrics p:")
print(metrics_p.to_string(index=False))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 3 — VORTEX CORE TRACKING  (per station, CFD vs experiment)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Core identified as the point of minimum cp_stat per plane (pressure trough).

rows = []
for station, group in merged_p.groupby("station"):

    idx_exp = group["cp_stat_exp"].idxmin()
    idx_cfd = group["cp_stat_cfd"].idxmin()
    exp_row = group.loc[idx_exp]
    cfd_row = group.loc[idx_cfd]

    rows.append({
        "station"     : station,
        "x_of"        : exp_row["x_of"],
        "y_core_exp"  : exp_row["y_of"],
        "z_core_exp"  : exp_row["z_of"],
        "cp_stat_exp" : exp_row["cp_stat_exp"],
        "y_core_cfd"  : cfd_row["y_of"],
        "z_core_cfd"  : cfd_row["z_of"],
        "cp_stat_cfd" : cfd_row["cp_stat_cfd"],
        "dy_core"     : cfd_row["y_of"] - exp_row["y_of"],
        "dz_core"     : cfd_row["z_of"] - exp_row["z_of"],
        "d_cp_stat"   : cfd_row["cp_stat_cfd"] - exp_row["cp_stat_exp"],
    })

core_tracking = pd.DataFrame(rows)
core_tracking.to_csv(RESULTS_DIR / "core_tracking.csv", index=False, float_format="%.6f")

print("\nVortex core tracking:")
print(core_tracking.to_string(index=False))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 4 — PLOTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
 
CHORD = 1.2192          # m  (48 in * 0.0254)
PLOTS_DIR = RESULTS_DIR / "plots"
PLOTS_DIR.mkdir(exist_ok=True)
 
STYLE_EXP = dict(color="black",     marker="o", linestyle="-",  linewidth=1.5, markersize=5, label="Experiment")
STYLE_CFD = dict(color="steelblue", marker="s", linestyle="--", linewidth=1.5, markersize=5, label="CFD (k-ω SST)")
 
# ── Prepare core_tracking ──────────────────────────────────────────────────────
ct = core_tracking.copy().sort_values("x_of")
ct["xc"]        = ct["x_of"]       / CHORD
ct["y_exp_c"]   = ct["y_core_exp"] / CHORD
ct["y_cfd_c"]   = ct["y_core_cfd"] / CHORD
ct["z_exp_c"]   = ct["z_core_exp"] / CHORD
ct["z_cfd_c"]   = ct["z_core_cfd"] / CHORD
 
# ── Velocity magnitude at core from merged_v ───────────────────────────────────
# vmag is normalised by Uinf (components are already u/Uinf etc.)
# Max vmag per plane captures the axial velocity excess at the vortex core.
merged_v["vmag_exp"] = np.sqrt(merged_v["u_exp"]**2 + merged_v["v_exp"]**2 + merged_v["w_exp"]**2)
merged_v["vmag_cfd"] = np.sqrt(merged_v["u_cfd"]**2 + merged_v["v_cfd"]**2 + merged_v["w_cfd"]**2)
 
vmag_core = (
    merged_v
    .groupby("station")
    .agg(x_of=("x_of", "first"),
         vmag_exp=("vmag_exp", "max"),
         vmag_cfd=("vmag_cfd", "max"))
    .reset_index()
    .sort_values("x_of")
)
vmag_core["xc"] = vmag_core["x_of"] / CHORD
 
# ── Plot 1 — Cp static at vortex core ─────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(ct["xc"], ct["cp_stat_exp"], **STYLE_EXP)
ax.plot(ct["xc"], ct["cp_stat_cfd"], **STYLE_CFD)
ax.set_xlabel("x/c",       fontsize=12)
ax.set_ylabel("$C_{p,static}$", fontsize=12)
ax.set_title("Static Pressure Coefficient at Vortex Core", fontsize=13)
ax.legend(fontsize=11)
ax.grid(True, linestyle=":", alpha=0.6)
ax.invert_yaxis()       # more negative Cp plots downward (convention)
fig.tight_layout()
fig.savefig(PLOTS_DIR / "cp_static_core.png", dpi=150)
plt.close(fig)
 
# ── Plot 2 — Core centerline y/c ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(ct["xc"], ct["y_exp_c"], **STYLE_EXP)
ax.plot(ct["xc"], ct["y_cfd_c"], **STYLE_CFD)
ax.set_xlabel("x/c",   fontsize=12)
ax.set_ylabel("$y_{core}$ / c", fontsize=12)
ax.set_title("Vortex Core Centerline — y/c", fontsize=13)
ax.legend(fontsize=11)
ax.grid(True, linestyle=":", alpha=0.6)
fig.tight_layout()
fig.savefig(PLOTS_DIR / "core_y_location.png", dpi=150)
plt.close(fig)
 
# ── Plot 3 — Core centerline z/c ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(ct["xc"], ct["z_exp_c"], **STYLE_EXP)
ax.plot(ct["xc"], ct["z_cfd_c"], **STYLE_CFD)
ax.set_xlabel("x/c",   fontsize=12)
ax.set_ylabel("$z_{core}$ / c", fontsize=12)
ax.set_title("Vortex Core Centerline — z/c", fontsize=13)
ax.legend(fontsize=11)
ax.grid(True, linestyle=":", alpha=0.6)
fig.tight_layout()
fig.savefig(PLOTS_DIR / "core_z_location.png", dpi=150)
plt.close(fig)
 
# ── Plot 4 — Velocity magnitude at vortex core ────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(vmag_core["xc"], vmag_core["vmag_exp"], **STYLE_EXP)
ax.plot(vmag_core["xc"], vmag_core["vmag_cfd"], **STYLE_CFD)
ax.set_xlabel("x/c",            fontsize=12)
ax.set_ylabel("$|V|$ / $U_\\infty$", fontsize=12)
ax.set_title("Velocity Magnitude at Vortex Core", fontsize=13)
ax.legend(fontsize=11)
ax.grid(True, linestyle=":", alpha=0.6)
fig.tight_layout()
fig.savefig(PLOTS_DIR / "vmag_core.png", dpi=150)
plt.close(fig)
 
print(f"\n4 plots saved to  {PLOTS_DIR}")

