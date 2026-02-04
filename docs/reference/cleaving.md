# Library Cleaving

Library cleaving is the process of physically splitting a combinatorial library into smaller pieces for parallel processing and characterization. Each cleaved piece (child library) can contain multiple sample positions representing different composition points.

!!! tip "Understanding Physical Pieces vs. Sample Positions"
    For a detailed explanation of how cleaving creates physical pieces while sample positions remain coordinate-based, see the [Combinatorial Libraries](../explanation/combinatorial-libraries.md) explanation.

## Overview

This schema package defines:

- **DTULibraryCleaving** - A sample preparation process that physically divides a [DTUCombinatorialLibrary](samples.md) into multiple smaller pieces (child libraries), each potentially containing several [sample positions](samples.md) for measurement

The cleaving process extends NOMAD's `Process` and `Activity` base classes, providing:

- Link to input entity (the combinatorial library)
- Links to output entities (individual samples created)
- Cleaving method and pattern documentation
- Position/composition mapping for each sample
- Automated workflow integration


## Cleaving and Annealing Workflow Integration

Here, we showcase in the cleaving in relation to a Cleaving plus Anealing workflow

### Hierarchical Sample Structure

To make the hierarchical sample structure operational, the annealing workflow was designed to capture and organize process data in line with the parent-child relationships created by virtual cleaving. This requirement guided the implementation of the RTP schema, which ensures that each annealing event is linked to the correct sample fragment while storing all relevant details from prior processing.

### Complete Processing History

The database keeps a complete record of thermal treatments, enabling experimentalists to:

- **Link annealing conditions**: Directly connect temperature profiles and pressure to the resulting properties of each individual piece
- **Trace origins**: Track where each piece originated within the parent library
- **Review prior processing**: Access deposition details and other prior process steps
- **Track property evolution**: Follow how properties evolved from the initial state to the annealed condition

This comprehensive tracking enables deeper insights into material behavior and facilitates understanding of structure-property relationships.

### Workflow Benefits

The cleaving/annealing workflow extends the database's capabilities by:

- **Linking thermal treatment data** to the hierarchical structure of combinatorial libraries
- **Preserving processing history**: Each child fragment retains its full processing history through parent library references
- **Enabling comparison**: Easy tracking, comparison, and analysis of property evolution across multiple processes
- **Handling complexity**: Flexible design handles the wide range of situations that come up in real lab work
- **Knowledge transfer**: Solutions established for one technique (sputtering) benefit implementation of new synthesis methods to track even more complex workflows

## Typical Usage

1. **Select library**: Reference the [DTUCombinatorialLibrary](samples.md) to be divided
2. **Document pattern**: Describe cleaving pattern (grid, linear array, custom)
3. **Create samples**: Generate [DTUCombinatorialSample](samples.md) entries for each piece
4. **Map positions**: Document where each sample came from on the original library
5. **Link compositions**: If composition varies across library, assign compositions to samples

## Related Schemas

- **Input entity**: [DTUCombinatorialLibrary](samples.md) (parent library)
- **Output entities**: Multiple child [DTUCombinatorialLibrary](samples.md) entries (cleaved pieces)
- **Sample positions**: [DTUCombinatorialSample](samples.md) entries reference coordinates on libraries or pieces
- **Created from**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Followed by**: [Characterization measurements](xrd.md) at specific sample positions

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.sample') }}

