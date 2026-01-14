# Jupyter Analysis

Python-based analysis workflows using Jupyter notebooks, integrated directly into NOMAD with full provenance tracking.

## Overview

Two complementary approaches for notebook-based analysis:

- **DtuJupyterAnalysis** - Auto-generated notebooks that fetch data from selected NOMAD entries
- **DtuJupyterAnalysisTemplate** - Reusable templates with complex analysis code that can be applied to different datasets

Both provide provenance tracking from samples through measurements to results.

---

## Basic Jupyter Analysis

Create analysis entries through an ELN form:

- Select libraries/measurements using the `libraries` field
- Check `generate_notebook` to auto-create a pre-filled Jupyter notebook
- Generated notebook includes API query to fetch selected entries' data

### ELN Form Interface

![ELN Form](../assets/images/jupyter-analysis-eln-form.png)

### Generated API Query Cell

![API Query Cell](../assets/images/jupyter-analysis-api-query-cell.png)

```python
from nomad.client import ArchiveQuery
from nomad.config import client

analysis_id = "THE_ANALYSIS_ID"
a_query = ArchiveQuery(
    query={'entry_id:any': [analysis_id]},
    required='*',
    url=client.url,
)
entry_list = a_query.download()
analysis = entry_list[0].data
```

The `analysis_id` is automatically replaced with the actual entry ID when the notebook is generated.

### Workflow

```mermaid
graph TD
    A[Create Analysis Entry] --> B[Select Libraries]
    B --> C[Enable generate_notebook]
    C --> D[Notebook Generated with API Query]
    D --> E[Add Analysis Code]
    E --> F[Execute & Save Results]
    
    style D fill:#e1f5e1
    style F fill:#e1f5e1
```

---

## Templated Jupyter Analysis

Reusable templates for complex analysis code (visualizations, ML models, statistical analysis).

### Key Concept

Templates enable **reusing sophisticated analysis code with different data sources**:

1. **Template Creation**: Convert existing analysis → Replace `analysis_id` with `"THE_ANALYSIS_ID"` placeholder → Store template
2. **Template Instantiation**: Reference template → Select new libraries → Only API query cell is updated → All analysis code preserved

### Template Workflow

```mermaid
graph TB
    subgraph "Create Template"
        A1[Analysis with Code] --> A2[Convert to Template]
        A2 --> A3[ID → THE_ANALYSIS_ID]
    end
    
    subgraph "Use Template"
        B1[New Analysis] --> B2[Reference Template]
        B2 --> B3[Select Libraries]
        B3 --> B4[Query Cell Updated]
        B4 --> B5[Analysis Code Preserved]
    end
    
    A3 --> B2
    
    style A3 fill:#ffe1cc
    style B5 fill:#e1f5e1
```

### What Gets Templated

| Component | Template | Instance |
|-----------|----------|----------|
| **API Query Cell** | `"THE_ANALYSIS_ID"` placeholder | Actual entry ID |
| **Analysis Code** | Preserved | Preserved |
| **Visualizations** | Preserved | Runs on new data |
| **ML Models** | Preserved | Runs on new data |

**Key**: Only the data source changes; all analysis logic is reused.

### Use Cases

- Complex visualizations (ternary plots, heatmaps) with consistent styling
- ML inference with pre-trained models on new data
- Standardized statistical analysis across sample sets
- Publication-ready figures with uniform formatting

---

## Benefits

- **Reproducible**: Code and data together in NOMAD
- **Provenance**: Full traceability from raw data to results
- **Reusable**: Templates standardize analysis across datasets
- **Searchable**: Notebooks are searchable NOMAD entries
- **Bidirectional linking**: Analysis ↔ source data connections

---

## Related Schemas

- **Input data**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), [PL](pl.md), [Ellipsometry](ellipsometry.md), [Raman](raman.md), [RT](rt.md)
- **Analyzed samples**: [Samples](samples.md)
- **Synthesis context**: [Sputtering](sputtering.md), [RTP](rtp.md), [Thermal Evaporation](thermal.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.analysis') }}
