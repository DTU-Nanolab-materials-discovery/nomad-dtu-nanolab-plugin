# Raman Spectroscopy

Raman spectroscopy probes vibrational modes in materials through inelastic light scattering. Raman provides information about crystal structure, bonding, stress, and chemical composition in a non-destructive manner.

## Overview

This schema package defines:

- **RamanMeasurement** - Raman measurements with laser conditions, spectral data, and peak analysis

Raman measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- Laser excitation parameters (wavelength, power, spot size)
- Spectrometer configuration (grating, detector, filters)
- Raman spectra (intensity vs. Raman shift)
- Peak positions, widths, and assignments

## Typical Usage

1. **Select samples**: Reference [samples](samples.md) to analyze
2. **Set laser**: Wavelength (visible or NIR), power, spot size, polarization
3. **Configure spectrometer**: Grating, spectral range, integration time
4. **Measure spectrum**: Raman intensity vs. wavenumber shift (cm⁻¹)
5. **Identify peaks**: Assign vibrational modes to chemical bonds/structures
6. **Analysis**: Peak positions (bonding), widths (disorder), intensities (concentrations)

## What Raman Tells You

- **Crystal structure**: Characteristic mode fingerprints for each phase
- **Phase identification**: Distinguish polymorphs and crystal structures
- **Bonding environment**: Bond types from mode frequencies
- **Stress/strain**: Peak shifts from lattice distortion
- **Crystallinity**: Peak widths indicate disorder
- **Composition**: For alloys/solutions, mode shifts track composition
- **Defects**: Disorder-induced modes

## Common Raman Applications

- **Material identification**: Quick phase ID (complementary to [XRD](xrd.md))
- **Carbon materials**: Graphene layers, disorder (D/G ratio)
- **Semiconductors**: Phonon modes, strain, doping
- **Oxides/ceramics**: Phase purity, oxygen vacancies
- **Stress mapping**: Spatially-resolved strain analysis

## Key Parameters

- **Laser wavelength**: Visible (532, 633 nm) or NIR (785 nm)
  - Shorter wavelength: Better scattering, may cause heating/damage
  - Longer wavelength: Reduced fluorescence background
- **Laser power**: Signal vs. sample heating trade-off
- **Spot size**: Spatial resolution vs. signal
- **Polarization**: Access to specific modes in oriented samples
- **Temperature**: In-situ measurements possible

## Raman vs. Other Techniques

- **Raman vs. [XRD](xrd.md)**: Raman works on amorphous materials, small volumes, gives bonding info
- **Raman vs. [XPS](xps.md)**: Raman is non-destructive, less surface-sensitive, faster
- **Raman vs. FTIR**: Complementary selection rules (Raman: polarizability; FTIR: dipole moment)

## Related Schemas

- **Measured samples**: [Samples](samples.md) from any synthesis method
- **Instrument**: [DTUInstrument](instruments.md) (Raman spectrometer with laser)
- **Complementary**: [XRD](xrd.md) for crystal structure, [XPS](xps.md) for composition
- **Analysis**: [Jupyter Analysis](analysis.md) for peak fitting, deconvolution, stress analysis

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.raman') }}
