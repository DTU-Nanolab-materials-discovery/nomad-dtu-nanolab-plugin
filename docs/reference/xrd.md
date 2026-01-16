# X-ray Diffraction (XRD)

X-ray Diffraction is a non-destructive technique for identifying crystal structures, phases, lattice parameters, crystallite sizes, and strain in materials.

!!! tip "Understanding XRD"
    For an overview of what XRD tells you and how it compares to other characterization techniques, see the [Characterization Techniques](../explanation/characterization.md) explanation.

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
