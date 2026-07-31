# Photoluminescence (PL)

Photoluminescence spectroscopy measures light emission from materials upon optical excitation. PL is essential for characterizing optical and electronic properties of semiconductors, quantum dots, and luminescent materials.

## Overview

This schema package defines:

- **DTUPLMeasurement** - PL measurements with excitation conditions, emission spectra, and optical properties

PL measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- Excitation source parameters (wavelength, power, spot size)
- Detection configuration (spectrometer, detector, filters)
- Emission spectra and peak analysis
- Temperature-dependent measurements

## Typical Usage

1. **Select samples**: Reference [samples](samples.md) to characterize
2. **Set excitation**: Laser wavelength, power, spot size, beam profile
3. **Configure detection**: Spectrometer grating, detector, integration time
4. **Measure spectrum**: Collect emission intensity vs. wavelength
5. **Analysis**: Identify peaks, calculate bandgap, extract quantum efficiency
6. **Temperature dependence** (optional): PL at multiple temperatures

!!! note "Position-Based Mapping"
    PL measurements are inherently position-aware, mapping optical properties to specific coordinates. Each measured position corresponds to a [sample position](samples.md) entry on [combinatorial libraries](samples.md), enabling composition-property correlations across gradient libraries. Multiple positions can be measured and their data aggregated to create property maps.

## What PL Tells You

- **Bandgap energy**: Emission peak position relates to bandgap
- **Optical quality**: Intensity indicates radiative efficiency
- **Defect states**: Sub-bandgap peaks show trap states
- **Strain**: Peak shifts indicate strain state
- **Composition**: For alloys, bandgap tracks composition
- **Quantum efficiency**: Relative emission intensity

## Common PL Features

- **Band edge emission**: Main peak near bandgap energy
- **Exciton peaks**: Sharp features at low temperature
- **Defect emission**: Broad, lower-energy peaks
- **Donor-acceptor pairs**: Characteristic peak shapes and shifts
- **Temperature dependence**: Peak shifts and intensity changes

## Key Parameters

- **Excitation wavelength**: Must be above bandgap (shorter wavelength than emission)
- **Excitation power**: Linear regime vs. high-injection effects
- **Spot size**: Spatial resolution vs. signal
- **Temperature**: Room temp, cryogenic for high-resolution
- **Time resolution**: Steady-state vs. time-resolved PL

## PL for Materials Screening

For [combinatorial libraries](samples.md):

1. **Spatially-resolved PL**: Map emission across composition gradient
2. **Quick screening**: Fast, non-destructive, identifies promising compositions
3. **Composition-bandgap trends**: Guide further investigation
4. **Compare to targets**: Verify expected optical properties

## Related Schemas

- **Measured samples**: [Samples](samples.md) from [Sputtering](sputtering.md), [RTP](rtp.md)
- **Instrument**: [DTUInstrument](instruments.md) (PL system with laser and spectrometer)
- **Complementary**: [XRD](xrd.md) for structure, [Ellipsometry](ellipsometry.md) for optical constants
- **Analysis**: [Jupyter Analysis](analysis.md) for peak fitting, bandgap extraction

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.PL') }}
