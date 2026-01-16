# Adapt this Plugin for Your Lab

The nomad-dtu-nanolab-plugin is designed for DTU Nanolab's Materials Discovery group, but it can serve as a template for similar labs performing combinatorial materials synthesis and characterization. This guide explains the key principles for adapting the plugin to your specific needs.

## Core Design Principles

When adapting the plugin, maintain these principles to ensure data consistency and reusability:

### 1. Entities (Physical Items) Should Have Unique IDs

Any persistent physical item in your lab should be an [entity](../explanation/data-model.md#entities-physical-items-in-your-lab) with a unique lab identifier:

- **Samples and libraries**: Your materials under study
- **Substrates**: Base materials with batch tracking
- **Consumables**: Targets, gases, chemicals
- **Equipment**: Instruments with configurations

**Why**: Unique IDs enable tracking, referencing, and querying. You can find all measurements on a specific sample or all samples made with a specific target.

**Implementation**: Extend NOMAD's `Entity` base class, add `lab_id` field for your naming convention.

### 2. Activities Should Link to Input and Output Entities

Any process, measurement, or analysis should be an [activity](../explanation/data-model.md#activities-things-you-do-in-the-lab) that explicitly links entities:

- **Synthesis processes**: Inputs (substrates, materials) → Outputs (libraries)
- **Sample preparation**: Input (parent libraries) → Outputs (child libraries)
- **Measurements**: Inputs (samples, instruments) → Results (data)
- **Analysis**: Inputs (measurements, processes, libraries) → Outputs (derived data, figures)

**Why**: Explicit links create provenance chains. NOMAD automatically builds workflow graphs showing how data connects.

**Implementation**: Extend NOMAD's `Process`, `Measurement`, or `Analysis` base classes, use reference fields to link entities.

### 3. Measurements Should Link to Libraries and Instruments

Every measurement should reference:

- **What was measured**: The library or the sample position
- **How it was measured**: The instrument used
- **When it was measured**: Datetime stamps (auto-populated)
- **Results**: Standardized data structures

**Why**: Consistent measurement documentation enables cross-technique comparisons, instrument performance tracking, and automated data aggregation.

**Implementation**: All measurements extend a common [BaseMeasurement](../reference/basesections.md) class with sample and instrument references.

### 4. Analysis Should Link to Input Libraries

Computational analysis and data processing should reference:

- **Input data sources**: Which measurements provide data
- **Analysis method**: Notebook, script, or workflow used
- **Parameters**: Analysis settings and assumptions
- **Results**: Derived quantities, figures, interpretations

**Why**: Links analysis results back to raw data, enables reproducibility, tracks data processing steps.

**Implementation**: Extend NOMAD's `Analysis` base class, reference measurement entries, store analysis artifacts.

## What to Keep from DTU Plugin

### Base Infrastructure

The plugin's foundation is broadly applicable:

- **[BaseMeasurement](../reference/basesections.md)**: Common measurement infrastructure works for any characterization technique
- **[Entity/Activity structure](../explanation/data-model.md)**: BFO-based organization applies to all lab workflows
- **[Workflow integration](../explanation/workflow.md)**: Automatic provenance tracking is universally valuable

### Common Techniques

Many characterization techniques are universal:

- **Structural**: [XRD](../reference/xrd.md), [Raman](../reference/raman.md)
- **Compositional**: [XPS](../reference/xps.md), [EDX](../reference/edx.md)
- **Optical**: [PL](../reference/pl.md), [Ellipsometry](../reference/ellipsometry.md)

These schemas can be used as-is or extended with lab-specific fields.

### Jupyter Analysis

The [Jupyter Analysis](../reference/analysis.md) schema provides flexible analysis documentation that works for any lab.

## What to Customize for Your Lab

### Lab-Specific Synthesis Techniques

Replace or extend the synthesis schemas based on your methods:

- **Keep if you use**: [Sputtering](../reference/sputtering.md), [Thermal Evaporation](../reference/thermal.md), [RTP](../reference/rtp.md)
- **Add if you use**: CVD, MBE, solution processing, spin coating, etc.
- **Extend**: Add lab-specific parameters to existing processes

### Sample Types and Organization

Adapt sample schemas to your workflow:

- **DTU uses**: [Combinatorial libraries](../explanation/combinatorial-libraries.md) with position-based sampling
- **You might use**: Single samples, standard libraries, wafer-scale fabrication
- **Customize**: Sample naming conventions, tracking requirements, batch organization

### Lab-Specific Techniques

Add schemas for your unique characterization capabilities:

- **Keep**: Standard techniques your lab has ([XRD](../reference/xrd.md), [XPS](../reference/xps.md), etc.)
- **Add**: Lab-specific or custom-built instruments
- **Extend**: Add parameters specific to your instrument configurations

### Instrument Definitions

Define your specific equipment:

- **Catalog**: Create [instrument](../reference/instruments.md) entries for your lab's equipment
- **Capabilities**: Document what each instrument can do
- **Configurations**: Track instrument settings and calibrations

## Adaptation Workflow

### 1. Assess Your Needs

**Map your lab workflow**:

- What materials do you synthesize? (Define synthesis process schemas and adapt parsers to your files)
- What measurements do you perform? (Keep/add characterization schemas and adapt parsers to your files)
- How do you organize samples? (Customize sample schemas)
- What are your pain points? (Focus customization there)

### 2. Start Simple

**Phase 1 - Use existing schemas**:

- Deploy the plugin as-is
- Document a few experiments using schemas that fit
- Identify gaps and friction points
- Don't customize yet—understand the system first

**Phase 2 - Extend existing schemas**:

- Add lab-specific fields to existing schemas
- Customize naming conventions (lab_id formats)
- Adjust dropdown options and defaults
- Keep the entity/activity structure intact

**Phase 3 - Add new schemas and parsers**:

- Create schemas for lab-specific processes or measurements
- Follow the same patterns (extend Entity or Activity)
- Maintain provenance chains (link inputs and outputs)
- Adapt the parsers to ingest your lab's files data automatically
- Test with real data early and often

### 3. Common Customizations


#### Add New Process Types

For lab-specific synthesis check-out the [nomad-processing plugin](https://github.com/FAIRmat-NFDI/nomad-material-processing) for base classes and inspiration.

#### Extend Measurements

Add lab-specific parameters to standard techniques or adpat them. We adopted the mapping of our XRD from the [nomad-measurements plugin](https://github.com/FAIRmat-NFDI/nomad-measurements).

```python
from nomad_dtu_nanolab_plugin.schema_packages.xrd import DTUXRDMeasurement

class YourLabXRD(DTUXRDMeasurement):
    """XRD with your lab's specific configuration"""

    # Inherits all standard XRD fields
    # Add lab-specific fields
    custom_scan_mode = Quantity(type=str)
    special_detector_config = Quantity(type=str)
```

### 4. Testing and Iteration

**Test with real data**:

- Document actual experiments, not hypothetical ones
- Have researchers use the schemas hands-on
- Collect feedback on what's confusing or cumbersome
- Iterate rapidly on customizations

**Validate provenance chains**:

- Can you trace: "All XRD measurements on sputtered samples"?
- Can you trace: Sample → synthesis process → materials used?
- Can you find: All measurements with a specific instrument?

If queries work, your entity/activity structure is correct.

## Resources for Plugin Development

- **[NOMAD Plugin Development Guide](https://nomad-lab.eu/prod/v1/docs/howto/plugins/plugins.html)**: Official NOMAD documentation
- **[NOMAD Schema Documentation](https://nomad-lab.eu/prod/v1/docs/reference/data_schemas.html)**: Schema development reference
- **[DTU Plugin Source Code](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin)**: Example implementation
- **[NOMAD Forum](https://matsci.org/c/nomad/)**: Community support for plugin development

## Getting Help

- **NOMAD Discord**: [open Discord](https://discord.gg/Gyzx3ukUw8)

## Contributing Back

If you create useful extensions or improvements:

- Consider contributing back to the DTU plugin (if generally applicable)
- Share your fork/adaptation with the NOMAD community
- Document your customizations for others
- Participate in NOMAD plugin development discussions

---