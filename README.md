# NACA 0012 Wingtip Vortex — OpenFOAM Case

Numerical simulation of the near-field wingtip vortex flow over a half-span **NACA 0012** wing using OpenFOAM (`pimpleFoam`), validated against the NASA Ames experimental dataset of Chow, Zilliac & Bradshaw (1997).

> **Reference experiment:**
> [NASA Turbulence Modeling Resource — Exp: Flow Behind a NACA 0012 Wingtip](https://tmbwg.github.io/turbmodels/Other_exp_Data/wingtip0012_exp.html)

---

## Table of Contents

- [Case Overview](#case-overview)
- [Geometry](#geometry)
- [Flow Conditions](#flow-conditions)
- [Turbulence Model & Initial Conditions](#turbulence-model--initial-conditions)
- [Experimental Data Files](#experimental-data-files)
- [Repository Structure](#repository-structure)
- [References](#references)

---

## Case Overview

The experiment was conducted at NASA Ames Research Center and focused on characterising the complete mean flowfield and Reynolds stress tensor in the near field of a wingtip vortex. The wing is a half-span NACA 0012 model mounted on the wind tunnel wall, with a rounded wingtip formed by rotating the NACA 0012 profile about its symmetry axis.

Key tunnel and model dimensions:

| Parameter | Value |
|---|---|
| Wind tunnel test section | 48 in × 32 in |
| Wing chord | 48 in (4 ft) |
| Wing semispan (constant-chord region) | 33.12 in |
| Overall span to tip (quarter-chord) | 36 in |
| Trailing edge thickness | 0.100 in |
| Transition | Tripped near leading edge |

---

## Geometry

The 3-D wing surface geometry is generated programmatically via:

```
geometry/generate_wing.py
```

The script builds the NACA 0012 cross-section, extrudes the constant-chord semispan, and applies the rounded wingtip (NACA 0012 profile rotated about its symmetry axis). Output is suitable for direct import into the OpenFOAM meshing pipeline.

The coordinate system used in the simulation follows the **wing-fixed, right-handed** convention:

| Axis | Direction |
|---|---|
| X | Chordwise, origin at leading edge / root |
| Y | Upward (normal to chord plane) |
| Z | Spanwise, positive toward tip |

> Note: the experimental data files use a **left-handed, traverse-based** coordinate system. Transformation equations to convert to the right-handed wing system are provided in `README2.DAT` and summarised below:
>
> ```
> xnew = x + xtrans        xtrans =  0.75 * chord * cos(AOA) + 0.25
> ynew = y + ytrans        ytrans = -0.75 * chord * sin(AOA) - 5.3588
> znew = ztrans - z        ztrans =  39.7714
> ```
> where `chord = 48.0 in` and `AOA = 10.0 * π / 360.0 rad`.

---

## Flow Conditions

| Parameter | Value |
|---|---|
| Freestream velocity, U∞ | 170 ft/s (≈ 51.82 m/s) |
| Reynolds number (based on chord) | 4.6 × 10⁶ |
| Angle of attack | 10 deg |
| Max freestream turbulence intensity | 0.15 % |
| Working fluid | Air (incompressible) |

---

## Turbulence Model & Initial Conditions

The case uses the **k-ω SST** turbulence model (`kOmegaSST` in OpenFOAM).

Initial / boundary conditions derived from freestream turbulence intensity `I = 0.0015` and freestream velocity `U`:

### Turbulent kinetic energy — `k`

```
k = 1.5 * (U * I)²
```

| Symbol | Value |
|---|---|
| k (freestream) | 0.00906153 m²/s² |

### Specific dissipation rate — `ω`

```
ω = k^0.5 / (Cμ^0.25 * l)
```

where `Cμ = 0.09` and `l` is the turbulent length scale (taken as chord length).

| Symbol | Value |
|---|---|
| ω (freestream) | 0.078077484 1/s |

### Turbulent dissipation rate — `ε`

```
ε = Cμ * k^1.5 / l
```

| Symbol | Value |
|---|---|
| ε (freestream) | 0.000636751 m²/s³ |

> **Reference formulas:**
> [CFD Online - Turbulence free-stream boundary conditions](https://www.cfd-online.com/Wiki/Turbulence_free-stream_boundary_conditions)

### OpenFOAM `turbulenceProperties`

```cpp
simulationType      RAS;

RAS
{
    RASModel        kOmegaSST;
    turbulence      on;
    printCoeffs     on;
}
```
