# Explanation

This section provides conceptual understanding of how the nomad-dtu-nanolab-plugin organizes materials discovery data. While the [Reference](../reference/index.md) section describes *what* each schema contains, this section explains *why* the plugin is designed this way and *how* the different pieces fit together.

## What You'll Find Here

### [Data Model Philosophy](data-model.md)
Understand the fundamental organization: what makes something an "Entity" vs. an "Activity," and how the Basic Formal Ontology (BFO) provides a foundation for consistent data modeling. This conceptual framework helps you understand why samples, substrates, and instruments are organized differently from measurements and synthesis processes.

### [Materials Discovery Workflow](workflow.md)
See how a complete materials discovery project flows through the system, from lab inventory setup through synthesis, characterization, and analysis. The workflow diagrams and explanations show how different schemas connect in practice.

### [Combinatorial Libraries Concept](combinatorial-libraries.md)
Grasp the distinction between physical library pieces and logical sample positions—a key concept for understanding how the plugin handles composition gradients and parallel measurements. This clarifies why cleaving creates physical pieces but doesn't redefine sample positions.

### [Characterization Techniques](characterization.md)
Learn what each characterization technique tells you about your materials. This overview helps you understand which measurements provide which types of information, enabling informed experimental design.

## How This Relates to Other Sections

- **[Tutorial](../tutorial/tutorial.md)**: Step-by-step learning exercises that walk you through using the plugin
- **[How-to Guides](../how_to/use_this_plugin.md)**: Task-oriented instructions for specific actions
- **[Reference](../reference/index.md)**: Complete technical documentation of all schemas and their fields

## Design Philosophy

The nomad-dtu-nanolab-plugin is built on three core principles:

1. **Traceability**: Every sample links back to its synthesis process, which links to the materials and instruments used. This complete provenance enables reproducibility and troubleshooting.

2. **Flexibility**: The plugin handles both simple workflows (single samples) and complex ones (combinatorial libraries with position-based mapping). You can document as much or as little as needed.

3. **Standardization**: Common base classes ensure all measurements work the same way, all entities have lab IDs, and all activities link to their inputs and outputs. This consistency makes data queryable and reusable.

## Additional Resources

- [NOMAD Documentation](https://nomad-lab.eu/prod/v1/docs/){:target="_blank" rel="noopener"} - Main platform documentation
- [Basic Formal Ontology](https://basic-formal-ontology.org/){:target="_blank" rel="noopener"} - Ontological foundation (advanced reading)
- [Diataxis Framework](https://diataxis.fr/){:target="_blank" rel="noopener"} - Documentation structure philosophy we follow
