# Library Cleaving

Library cleaving is the process of splitting a combinatorial library into individual samples for parallel characterization. Each cleaved piece represents a specific composition point in the material parameter space.

## Overview

This schema package defines:

- **DTULibraryCleaving** - A sample preparation process that divides a [DTUCombinatorialLibrary](samples.md) into multiple [DTUCombinatorialSample](samples.md) pieces

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

Combinatorial libraries enable efficient exploration of composition space, but characterization often requires:

- **Parallel measurements**: Multiple characterization tools simultaneously
- **Destructive testing**: Some techniques consume or damage the sample
- **Collaboration**: Sharing pieces with other researchers or labs
- **Storage**: Smaller pieces are easier to store and catalog
- **Flexibility**: Different areas can undergo different follow-up treatments

## Cleaving Strategies

- **Regular grid**: Systematic sampling of composition space
- **Linear array**: For 1D composition gradients
- **Custom pattern**: Targeted sampling of interesting regions
- **Position marking**: Clear labeling to maintain position/composition mapping

## Composition Mapping

For libraries with composition gradients (e.g., from multi-target [sputtering](sputtering.md)):

1. Measure composition at several points on intact library (e.g., [EDX](edx.md))
2. Create composition gradient map
3. Assign estimated composition to each cleaved sample based on position
4. Verify compositions on selected samples after cleaving

## Related Schemas

- **Input entity**: [DTUCombinatorialLibrary](samples.md)
- **Output entities**: Multiple [DTUCombinatorialSample](samples.md) entries
- **Created from**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Followed by**: [Characterization measurements](xrd.md) on individual samples

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.cleaving') }}
