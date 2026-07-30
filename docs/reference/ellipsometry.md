# Ellipsometry

Ellipsometry is a non-destructive optical technique for measuring film thickness, refractive index, and optical constants. It's particularly powerful for thin film characterization and in-situ growth monitoring.

## Overview

This schema package defines:

- **DTUEllipsometryMeasurement** - Ellipsometry measurements with angular/spectroscopic data, optical models, and fitted parameters

Ellipsometry measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- Measurement configuration (spectroscopic, angle-resolved, time-resolved)
- Raw ellipsometry data (Ψ, Δ vs. wavelength/angle)
- Optical models (layers, materials, roughness)
- Fitted parameters (thickness, refractive index, extinction coefficient)

## Typical Usage

1. **Select samples**: Reference [samples](samples.md) to measure
2. **Configure measurement**: Wavelength range, angles, polarizer/analyzer settings
3. **Measure Ψ and Δ**: Raw ellipsometry parameters vs. wavelength and/or angle
4. **Build optical model**: Layer stack with materials and approximate thicknesses
5. **Fit model**: Optimize parameters to match measured data
6. **Extract results**: Film thickness, n & k (refractive index and extinction), roughness

## What Ellipsometry Tells You

- **Film thickness**: Accurate to ~0.1 nm for single layers
- **Refractive index (n)**: Real part of optical constant
- **Extinction coefficient (k)**: Imaginary part, related to absorption
- **Optical bandgap**: From absorption onset
- **Surface roughness**: Interface quality
- **Layer structure**: Multi-layer stacks with individual thicknesses

## Ellipsometry Basics

Ellipsometry measures changes in polarization upon reflection:

- **Ψ (psi)**: Amplitude ratio between p and s polarizations
- **Δ (delta)**: Phase difference between p and s polarizations
- These relate to sample optical properties through Fresnel equations
- Modeling required: No direct inversion from Ψ,Δ to thickness/n/k

## Key Parameters

- **Wavelength range**: UV-Vis-NIR (typically 200-1000 nm)
- **Angle of incidence**: Multiple angles improve sensitivity (e.g., 65°, 70°, 75°)
- **Spot size**: Spatial resolution (typically few mm)
- **Optical model**: Layer materials, thicknesses, roughness, grading

## Ellipsometry for Thin Films

Ideal for:

- **Single and multi-layer films**: Thickness determination
- **Transparent films**: Refractive index without absorption
- **Semiconductors**: Bandgap from absorption edge
- **Metals**: Optical constants for plasmonic applications
- **In-situ monitoring**: Real-time growth/etching

## Related Schemas

- **Measured samples**: [Samples](samples.md) from [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Instrument**: [DTUInstrument](instruments.md) (spectroscopic ellipsometer)
- **Complementary**: [PL](pl.md) for bandgap, [XRD](xrd.md) for structure
- **Analysis**: [Jupyter Analysis](analysis.md) for advanced fitting, parameter extraction

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.ellipsometry') }}
