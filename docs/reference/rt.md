# RT Measurements

RT (Room Temperature) measurements encompass various electrical and optical characterization techniques performed at ambient conditions. These provide quick, non-destructive assessment of material properties.

## Overview

This schema package defines:

- **RTMeasurement** - Room temperature electrical and optical measurements with flexible parameter documentation

RT measurements extend [BaseMeasurement](basesections.md), providing:

- Links to measured [samples](samples.md) and [instrument](instruments.md)
- Flexible parameter definitions for various measurement types
- Electrical properties (resistance, conductivity, carrier concentration)
- Optical properties (transmission, reflection, absorption)
- Quick screening data

## Typical Usage

1. **Select samples**: Reference [samples](samples.md) to characterize
2. **Choose measurement type**: Electrical (I-V, Hall, 4-point probe) or optical (transmission, reflection)
3. **Configure setup**: Probe configuration, voltage/current ranges, light sources
4. **Record data**: Measurement results and conditions
5. **Extract properties**: Calculate conductivity, mobility, bandgap, etc.

## Common RT Measurement Types

### Electrical Measurements

- **Four-point probe**: Sheet resistance, conductivity
- **Hall effect**: Carrier concentration, mobility, type (n or p)
- **I-V curves**: Diode characteristics, contact resistance
- **Capacitance-voltage**: Depletion width, doping profiles

### Optical Measurements

- **Transmission**: Optical transparency, absorption edge
- **Reflection**: Surface reflectivity, optical constants
- **Absorption**: Calculated from transmission and reflection
- **Quick PL**: Simple emission screening (detailed PL in [PL measurements](pl.md))

## What RT Measurements Tell You

- **Electrical conductivity**: Is the material conductive?
- **Carrier type**: n-type or p-type semiconductor
- **Carrier concentration**: Doping level or defect density
- **Mobility**: Charge transport quality
- **Optical bandgap**: From absorption edge (Tauc plot)
- **Transparency**: For transparent conductor applications

## RT Screening for Combinatorial Libraries

For [combinatorial samples](samples.md):

1. **Quick assessment**: Fast measurements across composition space
2. **Identify trends**: Composition-property relationships
3. **Guide selection**: Choose promising samples for detailed characterization
4. **Pre-screening**: Before time-consuming measurements like [XRD](xrd.md), [XPS](xps.md)

## Key Parameters

- **Probe configuration**: Two-point, four-point, Hall bar geometry
- **Current/voltage**: Applied bias, current range
- **Magnetic field**: For Hall measurements
- **Light source**: Wavelength, intensity for optical measurements
- **Environment**: Air, vacuum, controlled atmosphere

## Related Schemas

- **Measured samples**: [Samples](samples.md) from [Sputtering](sputtering.md), [RTP](rtp.md)
- **Instrument**: [DTUInstrument](instruments.md) (probe stations, optical setups)
- **Detailed optical**: [PL](pl.md), [Ellipsometry](ellipsometry.md) for advanced characterization
- **Analysis**: [Jupyter Analysis](analysis.md) for property extraction, Tauc plots

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.rt') }}
