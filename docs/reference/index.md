# Schema Reference Overview

This section provides complete technical documentation for all data models in the nomad-dtu-nanolab-plugin. These schemas capture the materials discovery workflow at DTU Nanolab, from managing lab inventory to synthesizing samples to performing characterization measurements.

!!! tip "Understanding the Concepts"
    If you're new to the plugin, start with the [Explanation](../explanation/index.md) section to understand the data model philosophy, workflow concepts, and characterization techniques. This reference section focuses on technical schema details.

## Navigation Guide

### By Lab Activity

Looking for schemas related to specific activities?

**Managing inventory?** → [Lab Inventory & Items](#lab-inventory-items)

**Synthesizing samples?** → [Synthesis & Processing](#synthesis-processing)

**Characterizing materials?** → [Characterization](#characterization)

**Analyzing data?** → [Data Analysis](#data-analysis)

### By Schema Type

All schemas are listed in the navigation menu organized by their role in the materials discovery workflow. Each page provides:

- Practical context for when and how to use the schema
- Complete auto-generated technical documentation
- Links to related schemas

---

## Lab Inventory & Items

Physical items managed in the lab:

- **[Samples and Libraries](samples.md)** - Combinatorial libraries and individual samples created from synthesis or cleaving
- **[Substrates](substrates.md)** - Base materials for deposition, tracked in batches
- **[Targets](targets.md)** - Sputter deposition source materials with composition and power tracking
- **[Gas Supplies](gas.md)** - Gas cylinders with cylinder numbers and supply management
- **[Instruments](instruments.md)** - Laboratory equipment with capabilities and configurations

## Synthesis & Processing

Fabrication and sample preparation processes:

- **[Sputtering Deposition](sputtering.md)** - Multi-target sputter deposition with power, pressure, and gas control
- **[Rapid Thermal Processing (RTP)](rtp.md)** - Thermal annealing and treatment processes
- **[Thermal Evaporation](thermal.md)** - Vacuum deposition via thermal evaporation
- **[Library Cleaving](cleaving.md)** - Splitting combinatorial libraries into individual samples

## Characterization

Measurement techniques for materials characterization:

- **[Base Measurement Infrastructure](basesections.md)** - Common functionality shared by all DTU measurements
- **[X-ray Diffraction (XRD)](xrd.md)** - Crystal structure and phase identification
- **[X-ray Photoelectron Spectroscopy (XPS)](xps.md)** - Surface composition and chemical states
- **[Energy-Dispersive X-ray Spectroscopy (EDX)](edx.md)** - Elemental composition mapping
- **[Photoluminescence (PL)](pl.md)** - Optical emission and bandgap characterization
- **[Ellipsometry](ellipsometry.md)** - Optical constants and film thickness
- **[Raman Spectroscopy](raman.md)** - Vibrational modes and material fingerprinting
- **[RT Measurements](rt.md)** - Room temperature electrical and optical measurements

## Data Analysis

Computational analysis and data processing:

- **[Jupyter Analysis](analysis.md)** - Python-based data analysis workflows with notebook integration

---

## Additional Resources

- [NOMAD Documentation](https://nomad-lab.eu/prod/v1/docs/){:target="_blank" rel="noopener"} - Main NOMAD platform documentation
- [Explanation Section](../explanation/index.md) - Conceptual understanding of the data model and workflows
- [Tutorial](../tutorial/tutorial.md) - Step-by-step guides for getting started
- [How-to Guides](../how_to/use_this_plugin.md) - Practical usage instructions

## Adapting for Your Lab

These schemas are designed for DTU Nanolab's Materials Discovery group but can serve as a template for similar labs. See the [Adapt for Your Lab](../how_to/adapt-for-your-lab.md) guide for customization guidance.
