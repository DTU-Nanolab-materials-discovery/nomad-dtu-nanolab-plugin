# Library Cleaving

Library cleaving is the process of physically splitting a combinatorial library into smaller pieces for parallel processing and characterization. Each cleaved piece (child library) can contain multiple sample positions representing different composition points.

## Physical Pieces vs. Sample Positions

**Important distinction:**

- **Cleaving** creates **physical pieces** (child libraries) by cutting the substrate
- **Sample positions** are **measurement coordinates** that can exist on intact libraries or cleaved pieces
- A single cleaved piece typically contains **multiple sample positions** for characterization

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

## Why Cleave Libraries?

Combinatorial libraries enable efficient exploration of composition space. Cleaving into smaller physical pieces provides:

- **Parallel measurements**: Multiple characterization tools can process different pieces simultaneously
- **Destructive testing**: Some techniques consume or damage the material - cleaving preserves the rest of the library
- **Collaboration**: Physical pieces can be shared with other researchers or labs
- **Storage**: Smaller pieces are easier to store and catalog
- **Flexibility**: Different pieces can undergo different follow-up treatments (e.g., annealing, coating)
- **Sample position preservation**: Each cleaved piece retains its original composition gradient and sample position coordinates

## Cleaving Strategies

- **Regular grid**: Systematic sampling of composition space
- **Linear array**: For 1D composition gradients
- **Custom pattern**: Targeted sampling of interesting regions
- **Position marking**: Clear labeling to maintain position/composition mapping

## Composition Mapping and Sample Positions

For libraries with composition gradients (e.g., from multi-target [sputtering](sputtering.md)):

1. Measure composition at several points on intact library (e.g., [EDX](edx.md))
2. Create composition gradient map
3. Define [sample positions](samples.md) at specific coordinates representing distinct compositions
4. Cleave library into physical pieces if needed - sample positions remain defined by coordinates
5. Verify compositions at selected sample positions after cleaving

**Hierarchy:** Parent Library → Cleaved Pieces (physical/child libraries) → Sample Positions (coordinates) → Measurements

## Related Schemas

- **Input entity**: [DTUCombinatorialLibrary](samples.md) (parent library)
- **Output entities**: Multiple child [DTUCombinatorialLibrary](samples.md) entries (cleaved pieces)
- **Sample positions**: [DTUCombinatorialSample](samples.md) entries reference coordinates on libraries or pieces
- **Created from**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Followed by**: [Characterization measurements](xrd.md) at specific sample positions

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.sample') }}
