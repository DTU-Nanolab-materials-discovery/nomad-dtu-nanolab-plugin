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
2. **Attach notebook**: Upload Jupyter notebook (.ipynb) with analysis code
3. **Document parameters**: Any analysis settings, fitting parameters, thresholds
4. **Store results**: Fitted parameters, figures, derived properties
5. **Link back**: Reference analysis from measurement entries for bidirectional traceability

## What Jupyter Analysis Enables

- **Reproducible analysis**: Code and data together in NOMAD
- **Provenance tracking**: From raw data through analysis to results
- **Sharing**: Collaborators can see exactly how results were obtained
- **Reanalysis**: Easy to rerun with different parameters
- **Publication**: Analysis code available as supplementary material

## Common Analysis Workflows

### XRD Analysis
- Peak identification and indexing
- Lattice parameter refinement
- Crystallite size (Scherrer analysis)
- Strain calculation
- Rietveld refinement

### XPS Analysis
- Background subtraction
- Peak fitting and deconvolution
- Chemical state identification
- Quantitative composition
- Depth profiling analysis

### Optical Analysis
- PL peak fitting (Gaussian, Lorentzian)
- Bandgap extraction from absorption
- Ellipsometry model fitting
- Tauc plot analysis

### Composition Analysis
- EDX quantification and mapping
- Composition gradient fitting
- Ternary/quaternary composition plots

### Multi-technique Integration
- Correlating structure (XRD) with properties (PL, electrical)
- Composition-structure-property relationships
- Machine learning for materials screening

## Key Features

- **Data import**: Load measurement data from NOMAD entries
- **Flexible processing**: Any Python libraries (numpy, scipy, matplotlib, etc.)
- **Interactive development**: Develop in Jupyter, then upload to NOMAD
- **Version control**: Track analysis evolution over time
- **Reusable code**: Template notebooks for common analyses

## Best Practices

- **Document clearly**: Markdown cells explaining each step
- **Modular code**: Functions for reusable operations
- **Save figures**: Export plots as high-resolution images
- **Store parameters**: Make fitting results easily accessible
- **Link thoroughly**: Reference all input measurements

## Example Analysis Flow

```python
# 1. Load XRD data from NOMAD measurement entry
xrd_data = load_from_nomad(measurement_id)

# 2. Process data
peaks = identify_peaks(xrd_data)
lattice_param = refine_lattice(peaks)

# 3. Visualize
plot_pattern_with_peaks(xrd_data, peaks)

# 4. Store results
results = {
    'lattice_a': lattice_param,
    'crystallite_size': scherrer_size,
    'identified_phases': phases
}
```

## Related Schemas

- **Input data**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), [PL](pl.md), [Ellipsometry](ellipsometry.md), [Raman](raman.md), [RT](rt.md)
- **Analyzed samples**: [Samples](samples.md)
- **Synthesis context**: [Sputtering](sputtering.md), [RTP](rtp.md), [Thermal Evaporation](thermal.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.analysis') }}
