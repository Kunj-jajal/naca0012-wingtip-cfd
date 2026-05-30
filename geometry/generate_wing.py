import gmsh
import numpy as np

gmsh.initialize()
gmsh.model.add("naca0012_wing")
geo = gmsh.model.occ

# ── STEP 1: Profile parameters ─────────────────────────────────────────────
chord    = 48.0   # inches
te_half  = 0.05   # half of 0.100" blunt trailing edge (inches)
n_points = 100    # points per surface (cosine-spaced)

# Cosine spacing: denser near LE and TE, coarser in the middle
t  = np.linspace(0, np.pi, n_points)
xc = (1 - np.cos(t)) / 2   # normalized x/c from 0 to 1

def naca0012_y(xc):
    """NACA 0012 half-thickness distribution (normalized, y/c)."""
    return 0.594689181 * (
          0.298222773 * np.sqrt(xc)
        - 0.127125232 * xc
        - 0.357907906 * xc**2
        + 0.291984971 * xc**3
        - 0.105174606 * xc**4
    )

yc = naca0012_y(xc)

# ── STEP 2: Truncate for blunt trailing edge ───────────────────────────────
# The equation gives y=0 at x/c=1 (sharp TE).
# Physical model has 0.100" TE thickness, so we cut the profile
# where y/c drops to te_half/chord and anchor the TE face at x=48".

te_thresh = te_half / chord                           # 0.001042 (normalized)
max_idx   = np.argmax(yc)                             # index of peak thickness (~x/c=0.3)
after_peak = yc[max_idx:]
last_above = np.where(after_peak > te_thresh)[0][-1]  # last point above threshold on TE side
te_idx     = max_idx + last_above

xc_trunc = xc[:te_idx + 1]
yc_trunc = yc[:te_idx + 1].copy()
yc_trunc[-1] = te_thresh          # snap last profile point exactly to threshold

# Append TE corner at exactly x/c=1.0 (x=48") to preserve full chord length
xc_trunc = np.append(xc_trunc, 1.0)
yc_trunc = np.append(yc_trunc, te_thresh)
