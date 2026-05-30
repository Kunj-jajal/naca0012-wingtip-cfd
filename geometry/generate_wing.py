import gmsh
import numpy as np
import matplotlib.pyplot as plt

gmsh.initialize()
gmsh.model.add("naca0012_wing")
geo = gmsh.model.occ   # use OpenCASCADE kernel throughout

# ── STEP 1: Generate 2D profile coordinates ────────────────────────────────
chord = 48.0           # inches
te_half = 0.05         # half of 0.100" blunt TE
n_points = 100         # number of points per surface (upper/lower)

# x/c from 0 to 1, cosine spacing (denser near LE and TE)
# Cosine spacing: t = linspace(0,pi,n), x/c = (1 - cos(t))/2
# This gives better resolution at leading/trailing edges vs uniform spacing
t = np.linspace(0, np.pi, n_points)
xc = (1 - np.cos(t)) / 2

def naca0012_y(xc):
    return 0.594689181 * (
        0.298222773 * np.sqrt(xc)
        - 0.127125232 * xc
        - 0.357907906 * xc**2
        + 0.291984971 * xc**3
        - 0.105174606 * xc**4
    )

yc = naca0012_y(xc)

te_thresh = te_half / chord                          # 0.001042, normalized

max_idx = np.argmax(yc)                              # index of max thickness (~x/c=0.3)
after_peak = yc[max_idx:]                            # profile from peak to TE

# Last index (after peak) where y is still above threshold
last_above = np.where(after_peak > te_thresh)[0][-1]
te_idx = max_idx + last_above

# Truncate both arrays at that index
xc_trunc = xc[:te_idx + 1]
yc_trunc = yc[:te_idx + 1].copy()
yc_trunc[-1] = te_thresh                             # snap last point exactly to threshold

xc_trunc = np.append(xc_trunc, 1.0)       # x/c = 1.0 → x = 48 inches exactly
yc_trunc = np.append(yc_trunc, te_thresh)  # y stays at threshold

# Plot
plt.figure(figsize=(12, 4))
plt.plot(xc_trunc * chord,  yc_trunc * chord, 'b')  # upper surface
plt.plot(xc_trunc * chord, -yc_trunc * chord, 'b')  # lower surface

# Blunt TE closing line
te_x = xc_trunc[-1] * chord
plt.plot([te_x, te_x], [te_half, -te_half], 'r', linewidth=2)  # TE face

plt.axis('equal')    # critical — without this the profile looks distorted
plt.grid(True)
plt.xlabel("x (inches)")
plt.ylabel("y (inches)")
plt.title("NACA 0012 — chord = 48 in, blunt TE = 0.100 in")
plt.show()

print(f"Truncation at x/c = {xc_trunc[-1]:.4f}, x = {xc_trunc[-1]*chord:.4f} inches")
print(f"TE half-thickness = {yc_trunc[-1]*chord:.4f} inches")
