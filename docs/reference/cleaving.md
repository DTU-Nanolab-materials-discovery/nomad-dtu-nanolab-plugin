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
