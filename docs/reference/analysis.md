# Jupyter Analysis

Computational analysis and data processing workflows using Jupyter notebooks. This schema integrates Python-based analysis directly into NOMAD, enabling reproducible data processing with full provenance tracking.

## Overview

This schema package defines:

- **DtuJupyterAnalysis** - Jupyter notebook-based analysis workflows with input data, code, and results

Jupyter analysis extends NOMAD's `Analysis` and `Activity` base classes, providing:

- Links to input [measurements](xrd.md) providing data
- Jupyter notebook attachment or inline code
- Analysis parameters and configuration
- Results and visualizations
- Full provenance from samples → measurements → analysis

## Typical Usage

1. **Reference inputs**: Link to [measurements](xrd.md) providing data to analyze
2. **Attach notebook**: Upload or create a templated Jupyter notebook (.ipynb) with analysis code in NOMAD
3. **Document parameters**: Any analysis settings, fitting parameters, thresholds
4. **Store results**: Fitted parameters, figures, derived properties
5. **Link back**: Reference analysis from measurement entries for bidirectional traceability

## What Jupyter Analysis Enables

- **Reproducible analysis**: Code and data together in NOMAD
- **Provenance tracking**: From raw data through analysis to results
- **Sharing**: Collaborators can see exactly how results were obtained
- **Reanalysis**: Easy to rerun with different parameters
- **Searchability**: Analysis code can be searched in NOMAD


## Related Schemas

- **Input data**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), [PL](pl.md), [Ellipsometry](ellipsometry.md), [Raman](raman.md), [RT](rt.md)
- **Analyzed samples**: [Samples](samples.md)
- **Synthesis context**: [Sputtering](sputtering.md), [RTP](rtp.md), [Thermal Evaporation](thermal.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.analysis') }}
