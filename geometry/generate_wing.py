import gmsh
import numpy as np
import math

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

# ── STEP 3: Add 2D profile points to gmsh ─────────────────────────────────
lc_body = 1.0	# generate surface mesh size (inches) - tune during meshing 
lc_le = 0.1 # finer at leading edge (high curvature)
lc_te = 0.05 # finest at trailing edge (blunt face, thin boundary layer)

# leading edge - single shared point (upper and lower surface meet here)
le_tag = geo.addPoint(0.0, 0.0, 0.0, lc_le)

# upper surface - from LE+1 to TE (skip index 0, that's the LE point)
upper_tags = [le_tag]
for i in range(1, len(xc_trunc)):
	tag = geo.addPoint(xc_trunc[i] * chord, yc_trunc[i] * chord, 0.0, lc_body)
	upper_tags.append(tag)
	
# lower surface - mirror of upper
# TE point already exists as upper_tags[-1] hence from LE to TE
lower_tags = [le_tag]
for i in range(1, len(xc_trunc)):
	tag = geo.addPoint(xc_trunc[i] * chord, -yc_trunc[i] * chord, 0.0, lc_body)
	lower_tags.append(tag)
	
# TE face connects upper TE corner to lower TE corner
te_upper_tag = upper_tags[-1]
te_lower_tag = lower_tags[-1]

# ── STEP 4: Create splines through the points ──────────────────────────────
upper_spline = geo.addSpline(upper_tags)  
lower_spline = geo.addSpline(lower_tags)  

# Short vertical line closing the blunt TE face
te_line = geo.addLine(te_upper_tag, te_lower_tag)

# ── STEP 5: Close into a curve loop then a surface ─────────────────────────
# Sign convention: positive = use curve in its defined direction
#                  negative = use curve in reverse direction

profile_loop = geo.addCurveLoop([upper_spline, te_line, -lower_spline])
profile_surface = geo.addPlaneSurface([profile_loop])

# ── STEP 6: Extrude profile along Z to form the straight wing section ───────
# The constant-chord section runs from z=0 (root/symmetry plane) to z=33.12"
# Refer to notes.md

z_straight = 33.12 # inches

extrusion = geo.extrude(
	[(2, profile_surface)],
	0, 0, z_straight
)

wing_volume = extrusion[1] #geo.extrude returns volume for [1]
tip_face = extrusion[0] #geo.extrude returns the face swept along the side for [0]

#tip_face is the profile which is at z = 33.12" to be used for revolution next

# ── STEP 7: Revolve the tip face to form the rounded wingtip ────────────────
# The tip face (at z=33.12) gets revolved 180° around the chord line
# Chord line at z=33.12: runs along x-axis, at y=0

geo.revolve(
	[tip_face], # surface to revolve
	0, 0, z_straight, # origin of surface to revolve
	1, 0, 0, # along X axis (also the chord)
	math.pi
)

# ── STEP 8: Synchronize and export ──────────────────────────
geo.synchronize()

gmsh.write("geometry/wing.stl")
gmsh.finalize()


