# Laboratory Instruments

Instruments are the equipment used for synthesis, processing, and characterization. Tracking instrument configurations ensures reproducibility and helps correlate results with specific tool conditions.

## Overview

This schema package defines:

- **DTUInstrument** - A laboratory instrument with capabilities, configurations, and usage tracking

Instruments extend NOMAD's `Instrument` entity, providing:

- Unique lab IDs and asset numbers
- Instrument type and model information
- Capabilities and specifications
- Configuration parameters
- Maintenance and calibration history

## Typical Usage

1. **Register instruments**: Create `DTUInstrument` entries for sputter tools, XRD systems, XPS systems, etc.
2. **Reference in activities**: [Synthesis processes](sputtering.md) and [measurements](xrd.md) reference the instrument used
3. **Track configurations**: Document chamber pressure, power supplies, detector settings, etc.
4. **Maintenance logs**: Record calibrations, repairs, and modifications

## Why Track Instruments?

Instrument details affect data quality and reproducibility:

- **Tool-to-tool variation**: Different instruments can produce different results even with "identical" parameters
- **Configuration changes**: Software updates, hardware modifications, and calibrations affect results
- **Troubleshooting**: When results change unexpectedly, instrument logs help identify the cause
- **Publication requirements**: Many journals require detailed instrument information

## Instrument Types at DTU Nanolab

- **Deposition tools**: Sputter systems, thermal evaporators
- **Processing tools**: RTP furnaces, annealing systems
- **Characterization**: XRD, XPS, EDX, Raman, ellipsometry, PL

## Related Schemas

- **Used in synthesis**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md), [RTP](rtp.md)
- **Used in measurements**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), [PL](pl.md), [Ellipsometry](ellipsometry.md), [Raman](raman.md), [RT](rt.md)
- **Co-used with**: [Targets](targets.md), [Gas Supplies](gas.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.instrument') }}
