# Energy-Dispersive X-ray Spectroscopy (EDX)

Energy-Dispersive X-ray Spectroscopy is an elemental analysis technique typically coupled with electron microscopy (SEM/TEM). EDX identifies elements and their spatial distribution through characteristic X-ray emission.

## Overview

This schema package defines:

- **EDXMeasurement** - EDX measurements with elemental composition, spatial mapping, and quantification

EDX measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- Electron beam parameters (voltage, current, spot size)
- Detector configuration and acquisition settings
- Elemental composition (atomic and weight percentages)
- Spatial mapping data (element distribution)

## Typical Usage

1. **Select samples**: Reference [samples or libraries](samples.md) to analyze
2. **Set beam conditions**: Accelerating voltage (typically 10-20 kV), current, spot size
3. **Acquire spectrum**: Collect X-ray counts vs. energy
4. **Identify elements**: Peak identification and deconvolution
5. **Quantification**: Calculate composition from peak intensities
6. **Mapping** (optional): Scan beam to create elemental distribution maps

## What EDX Tells You

- **Elemental composition**: What elements are present and their concentrations
- **Spatial distribution**: Element maps showing composition variations
- **Composition gradients**: In combinatorial libraries, map composition space
- **Layer thickness**: From cross-section analysis
- **Contamination**: Identify unexpected elements
- **Stoichiometry**: Compare to target compositions

## EDX in Combinatorial Screening

For [combinatorial libraries](samples.md) created by multi-target [sputtering](sputtering.md):

1. **Map intact library**: Before [cleaving](cleaving.md), measure composition at multiple points
2. **Create gradient map**: Interpolate composition across library
3. **Guide cleaving**: Choose where to divide library for optimal sampling
4. **Verify samples**: After cleaving, confirm compositions match predictions

## Key Parameters

- **Accelerating voltage**: Determines X-ray generation depth (higher V = deeper)
- **Beam current**: Signal intensity vs. beam damage trade-off
- **Spot size**: Spatial resolution vs. signal
- **Acquisition time**: Counting statistics vs. measurement time
- **Working distance**: Affects collection efficiency

## EDX Limitations

- **Light elements**: Poor sensitivity for Z < 11 (B, C, N, O challenging)
- **Spatial resolution**: Typically 1-2 μm (limited by electron interaction volume)
- **Depth information**: Averages over interaction depth (~1 μm)
- **Quantification accuracy**: ±1-2 at% typical, depends on standards

## EDX vs. XPS

- **EDX**: Bulk analysis (~1 μm deep), better for heavy elements, spatial mapping
- **[XPS](xps.md)**: Surface analysis (~10 nm), better for light elements, chemical states

## Related Schemas

- **Measured samples**: [Samples and Libraries](samples.md) from [Sputtering](sputtering.md)
- **Instrument**: [DTUInstrument](instruments.md) (SEM with EDX detector)
- **Complementary**: [XPS](xps.md) for surface composition, [XRD](xrd.md) for phases
- **Analysis**: [Jupyter Analysis](analysis.md) for composition mapping, gradient fitting

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.edx') }}
