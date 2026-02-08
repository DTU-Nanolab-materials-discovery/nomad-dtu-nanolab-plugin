# Characterization Techniques

Materials characterization provides the experimental data needed to understand composition, structure, and properties. This page explains what each technique tells you about your materials, helping you choose the right measurements for your research questions.

## Overview of Available Techniques

The nomad-dtu-nanolab-plugin supports documentation for several characterization techniques, organized by the type of information they provide:

| Technique | Information Type | Key Properties Measured |
|-----------|-----------------|------------------------|
| **[XRD](../reference/xrd.md)** | Structural | Crystal structure, phases, lattice parameters |
| **[XPS](../reference/xps.md)** | Compositional (Surface) | Surface elemental composition, oxidation states |
| **[EDX](../reference/edx.md)** | Compositional (Bulk) | Bulk elemental composition, spatial distribution |
| **[PL](../reference/pl.md)** | Optical | Emission properties, recombination |
| **[Ellipsometry](../reference/ellipsometry.md)** | Optical | Film thickness, refractive index, optical constants |
| **[Raman](../reference/raman.md)** | Structural/Chemical | Vibrational modes, bonding, stress, phase identification |

All measurements extend the common [BaseMeasurement](../reference/basesections.md) infrastructure, ensuring consistent documentation and workflow integration and they are typically adapted to mapping setups.

For complete materials characterization:

- **Structure**: [XRD](../reference/xrd.md) + [Raman](../reference/raman.md) (crystalline + amorphous)
- **Composition**: [EDX](../reference/edx.md) (bulk) + [XPS](../reference/xps.md) (surface)
- **Optical**: [PL](../reference/pl.md) (emission) + [Ellipsometry](../reference/ellipsometry.md) (absorption)
- **Electrical**: [RT measurements](../reference/rt.md) (conductivity, carriers)

This multi-technique approach reveals relationships between composition, structure, and properties.

## Practical Considerations

### Sample Position Measurements

All measurements in the plugin are typically performed mapping [sample positions](combinatorial-libraries.md) on combinatorial libraries:

- Each measurement point tracks a specific coordinate on the library
- Position-based measurements work whether library is intact or [cleaved](../reference/cleaving.md)

## Characterization Data Processing Workflow

The characterization workflow automatically processes measurement data from various instruments and creates a unified, interconnected dataset. This applies to all characterization techniques in the plugin.

### Flexible Data Format Support

The measurement data from thin-film characterization techniques is stored in instrument-dependent formats, either in a single file or separate files depending on the tool software. To enable processing of the variety of characterization data, every data schema was adapted to process:

- Native file formats from each instrument
- Analysis result files when initial analysis is commonly done in the tool's software
- Single-point measurements (treated as 1×1 maps)
- Full mapping measurements

### Workflow Steps

1. **Data Upload and Parsing**: The user creates an entry in NOMAD for the relevant measurement and uploads the measurement file(s) of one measurement map. The files are opened and the information contained is parsed into the chosen data schema automatically. The parsers do not distinguish between a single measurement or mapping measurements—they group the information uploaded by the coordinates attached to each measurement and save the common metadata like tool settings.

2. **Coordinate Transformation**: For mapping measurements, the measurement coordinates are typically recorded with respect to the position on the tool stage. To enable correlation of properties measured with different tools, a coordinate transformation stage was added to the data processing:
   - All coordinates are shifted to a coordinate system with the origin in the center of the library
   - Calibration points (like the corners of the sample) are recorded in tool coordinates if available or added manually by the user
   - From these calibration points and the geometry attributes of the combinatorial library, a mathematical translation and rotation unifies all different measurement coordinates to library-centered coordinates

3. **Automatic Visualization**: After the coordinate transformation, simple standard visualization plots are automatically generated to provide immediate benefit:
   - Gaining an overview of the data at a glance
   - Quick overview when returning to the entry in the future
   - Heatmaps of scalar values (e.g., element content in percent from composition measurements)
   - Stacked plots of spectra or patterns

4. **Library Linking**: The characterization entry is linked automatically to the combinatorial library it was measured on, derived from the file name. This creates an interconnected experimental dataset for each library, enabling:
   - Tracking resulting properties from synthesis parameters
   - Looking up which synthesis parameters resulted in desired material properties previously characterized

5. **Combinatorial Sample Generation**: Combinatorial samples for every measurement point are generated by combining data from all methods found at the coordinates of that specific library. This increases the findability of desired data, as no knowledge of naming conventions or processes is required—a search for individual point characterization results is enabled directly.

### Benefits

**Short-term benefits:**
- Automatic generation of raw data plots and heatmaps over the whole combinatorial library
- Immediate visual feedback on measurement quality and trends

**Long-term benefits:**
- Structured data provision for further processing during analysis
- Automatic coordinate transformation enabling effortless correlation of results from different techniques
- Identifying gradients and changes over multiple samples and processes
- Interconnected dataset facilitating materials discovery and publication

## Learn More

- **[Materials Discovery Workflow](workflow.md)**: See how measurements fit in the complete workflow
- **[Combinatorial Libraries](combinatorial-libraries.md)**: Understand position-based measurements
- **[Reference Documentation](../reference/index.md)**: Technical details for each measurement schema
- **[Tutorial](../tutorial/tutorial.md)**: Hands-on practice with measurements
