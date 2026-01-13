# X-ray Photoelectron Spectroscopy (XPS)

X-ray Photoelectron Spectroscopy is a surface-sensitive technique for determining elemental composition, chemical states, and electronic structure of materials. XPS probes the top ~10 nm of a surface.

## Overview

This schema package defines:

- **DTUXpsMeasurement** - XPS measurements with survey and high-resolution scans, peak fitting, and composition analysis

XPS measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- X-ray source configuration (Al Kα, Mg Kα, monochromatic)
- Scan parameters (survey, high-resolution regions)
- Peak positions, binding energies, chemical shifts
- Quantitative composition and oxidation states

## Typical Usage

1. **Select samples**: Reference [samples](samples.md) to analyze
2. **Prepare surface**: Document any cleaning (Ar sputtering, etc.)
3. **Survey scan**: Wide binding energy range for elemental identification
4. **High-resolution scans**: Narrow regions for chemical state analysis
5. **Peak fitting**: Identify components, oxidation states, bonding environments
6. **Quantification**: Calculate atomic percentages from peak areas

## What XPS Tells You

- **Elemental composition**: What elements are present (except H, He)
- **Chemical states**: Oxidation states (e.g., Cu⁰, Cu⁺, Cu²⁺)
- **Bonding environment**: Chemical shifts from electronegativity
- **Depth profiling**: With Ar sputtering, composition vs. depth
- **Surface contamination**: Adventitious carbon, oxide layers
- **Electronic structure**: Valence band, work function

## Common XPS Regions

- **Survey scan**: 0-1200 eV, identifies all elements present
- **C 1s**: ~285 eV, carbon bonding, calibration reference
- **O 1s**: ~530 eV, oxygen states, oxides
- **N 1s**: ~400 eV, nitrogen bonding, nitrides
- **Metal peaks**: Core levels specific to each element

## Key Parameters

- **X-ray source**: Al Kα (1486.6 eV), Mg Kα (1253.6 eV), monochromatic
- **Pass energy**: Energy resolution vs. signal (lower = better resolution)
- **Step size**: Binding energy increment (0.1 eV for high-res)
- **Charge neutralization**: Electron flood gun for insulators
- **Sputtering**: For depth profiling or surface cleaning

## XPS Challenges

- **Charging**: Insulators shift binding energies (need calibration)
- **Surface sensitivity**: Only top ~10 nm analyzed
- **Beam damage**: X-rays can modify sensitive materials
- **Quantification accuracy**: Depends on cross-sections, mean free paths

## Related Schemas

- **Measured samples**: [Samples](samples.md) from [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Instrument**: [DTUInstrument](instruments.md) (XPS system)
- **Complementary**: [XRD](xrd.md) for structure, [EDX](edx.md) for bulk composition
- **Analysis**: [Jupyter Analysis](analysis.md) for peak fitting, quantification

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.xps') }}
