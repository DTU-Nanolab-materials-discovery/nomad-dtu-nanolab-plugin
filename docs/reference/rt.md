# Reflection/Transmission (RT) Measurements

These schemas support high-throughput optical measurements from the **Agilent Cary 7000 UMS + UMA autosampler** workflow.

## Overview

This schema package defines two complementary entry types:

- **DtuAutosamplerMeasurement**: experiment container that ingests the autosampler data files and creates per-sample measurement archives.
- **RTMeasurement**: measurement archive containing position-resolved reflection and transmission spectra.

The data model is designed for combinatorial mapping and keeps full provenance between raw files, grid mapping, and generated RT results.

## Input Files

The autosampler workflow uses three file types:

- **Data file (`.csv`)**: exported spectra and metadata from Agilent software.
- **Grid/config file (`*_grid.csv`)**: maps autosampler positions to sample names and sample coordinates.
- **Raw batch file (`.bsw`)**: native instrument batch file for traceability and provenance.

## Typical Workflow

1. Generate a measurement map with the grid-generator notebook.
2. Use the generated `*_polar.csv` in the autosampler software to run the measurement.
3. Export measurement data as `.csv` from Agilent software.
4. Upload the `.csv` data file and the matching `*_grid.csv` into `DtuAutosamplerMeasurement`.
5. Let normalization generate one or more `RTMeasurement` entries automatically.

## What RT Captures

- Reflection and transmission spectra per position.
- Measurement geometry (sample angle, detector angle, polarization).
- Spatially resolved maps through `x/y` coordinates from the grid file.
- Derived visualization (stacked spectra and configuration-specific maps).

## Related Schemas

- **Samples and libraries**: [Samples](samples.md)
- **Shared measurement base**: [Base Measurement Infrastructure](basesections.md)
- **Other optical methods**: [PL](pl.md), [Ellipsometry](ellipsometry.md), [Raman](raman.md)
- **Analysis workflows**: [Jupyter Analysis](analysis.md)

## How-To Guide

For a complete upload procedure, see [Add Autosampler Reflection/Transmission Measurements](../how_to/add-autosampler-measurements.md).

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.rt') }}
