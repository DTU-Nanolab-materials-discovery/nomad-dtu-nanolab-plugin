# X-ray Diffraction (XRD)

X-ray Diffraction is a non-destructive technique for identifying crystal structures, phases, lattice parameters, crystallite sizes, and strain in materials. XRD is essential for understanding the structural properties of thin films and bulk materials.

## Overview

This schema package defines:

- **DTUXRDMeasurement** - XRD measurements with parameters, scan configurations, and diffraction data

XRD measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- Scan configuration (θ-2θ, rocking curve, pole figure, etc.)
- X-ray source parameters (wavelength, power, slit sizes)
- Detector settings and scan ranges
- Diffraction patterns and peak data

## Typical Usage

1. **Select samples**: Reference [samples or libraries](samples.md) to measure
2. **Configure scan**: Set scan type, 2θ range, step size, dwell time
3. **Set instrument**: Document [XRD instrument](instruments.md) and configuration
4. **Record conditions**: X-ray source (Cu Kα, etc.), power, slits, atmosphere
5. **Store data**: Diffraction pattern, identified phases, lattice parameters
6. **Link analysis**: Reference [Jupyter analysis](analysis.md) for peak fitting, phase ID, etc.

!!! note "Measuring Sample Positions"
    Measurements reference [sample positions](samples.md) defined by specific coordinates on [combinatorial libraries](samples.md). Multiple positions can be measured on a single library (intact or cleaved) to map structural properties across composition space.

## Common XRD Scan Types

- **θ-2θ scan**: Phase identification, out-of-plane lattice parameter
- **Rocking curve (ω-scan)**: Crystalline quality, mosaicity
- **φ-scan**: Texture, epitaxial relationships
- **Reciprocal space map**: Strain, relaxation, composition
- **Grazing incidence (GIXRD)**: Thin films, surface sensitivity

## What XRD Tells You

- **Phase identification**: Which crystal structures are present
- **Lattice parameters**: Unit cell dimensions, composition estimation
- **Crystallite size**: Grain size from peak broadening (Scherrer equation)
- **Strain/stress**: Lattice distortion from peak positions
- **Texture/orientation**: Preferred crystallographic directions
- **Crystallinity**: Relative amounts of crystalline vs. amorphous material

## Key Parameters

- **X-ray source**: Wavelength (Cu Kα1 = 1.5406 Å, etc.), power
- **Scan geometry**: θ-2θ, grazing incidence, pole figure
- **Angular range**: Start/stop angles, step size
- **Detector**: Type, slit configuration, count time
- **Sample environment**: Temperature, atmosphere, in-situ conditions

## Related Schemas

- **Measured samples**: [Samples](samples.md) created by [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md), [RTP](rtp.md)
- **Instrument**: [DTUInstrument](instruments.md) (XRD system)
- **Complementary**: [XPS](xps.md) for composition, [Raman](raman.md) for bonding
- **Analysis**: [Jupyter Analysis](analysis.md) for peak fitting, phase identification

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.xrd') }}
