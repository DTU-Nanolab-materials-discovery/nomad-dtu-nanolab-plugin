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

## Learn More

- **[Materials Discovery Workflow](workflow.md)**: See how measurements fit in the complete workflow
- **[Combinatorial Libraries](combinatorial-libraries.md)**: Understand position-based measurements
- **[Reference Documentation](../reference/index.md)**: Technical details for each measurement schema
- **[Tutorial](../tutorial/tutorial.md)**: Hands-on practice with measurements
