## Wing Geometry Parameters
- Profile: NACA 0012 (symmetric, standard 4-digit equation)
- Chord: 48 inches
- Semispan: 36 inches (wall to tip quarter-chord)
- Planform: Rectangular (no sweep, no taper)
- Trailing edge: Blunt, 0.100 inch thickness
- Wingtip: Surface of revolution of NACA 0012 about chord axis

## Tool
gmsh Python API → STL export → snappyHexMesh

## Approach
Creating profile from 0 to 1 in 2D and multiplying coordinates by 48 (inches) to get the full profile. (refer to generate_wing.py)
Extrusion in Z direction up to (36 - (maximum_length/2)) followed by a revolve extrusion about the chord length to get a rounded tip.
