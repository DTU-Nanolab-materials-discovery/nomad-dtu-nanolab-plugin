# Base Measurement Infrastructure

This schema package defines the common infrastructure shared by all DTU Nanolab measurement types.

!!! tip "Understanding the Architecture"
    For an explanation of why the plugin uses a common base class and how it ensures consistency, see the [Data Model Philosophy](../explanation/data-model.md).

## Overview

This schema package defines:

- **BaseMeasurement** - Base class providing common functionality for all DTU measurements (XRD, XPS, EDX, PL, etc.)

The base measurement class extends NOMAD's `Measurement` and `Activity` base classes, providing:

- Links to measured samples and instruments
- Standardized datetime and location tracking
- Common measurement metadata (operator, lab notebook references)
- Automated ELN integration
- Result normalization

## Common Measurement Features

All DTU measurements inherit these capabilities:

### Sample Linking
- Reference to [samples](samples.md) measured
- Support for measuring multiple samples in one session
- Automatic sample-measurement relationship tracking

### Instrument Documentation
- Reference to [instrument](instruments.md) used
- Configuration and settings documentation
- Calibration state tracking

### Metadata Management
- Measurement datetime (auto-populated if not specified)
- Operator/researcher information
- Lab notebook page references
- Environmental conditions (if relevant)

### Workflow Integration
- Automatic creation of NOMAD workflow entries
- Links to synthesis processes that created the samples
- Integration with analysis workflows

## Related Schemas

- **Measured samples**: [Samples and Libraries](samples.md)
- **Used instruments**: [Instruments](instruments.md)
- **Specific techniques**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), [PL](pl.md), [Ellipsometry](ellipsometry.md), [Raman](raman.md), [RT](rt.md)
- **Analysis**: [Jupyter Analysis](analysis.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.basesections') }}
