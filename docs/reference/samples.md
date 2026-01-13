# Samples and Combinatorial Libraries

Samples are the core materials you create and study in your research. At DTU Nanolab, the materials discovery workflow uses combinatorial libraries to efficiently explore material composition spaces.

## Overview

This schema package defines two main classes:

- **DTUCombinatorialLibrary** - A single substrate with multiple material compositions deposited as gradients or patterns (e.g., from multi-target sputtering). The library can be cleaved into individual samples for parallel characterization.

- **DTUCombinatorialSample** - Individual pieces created by cleaving a combinatorial library. Each sample represents a specific composition point and can be characterized independently.

Both classes extend NOMAD's `CompositeSystem` entity, providing:

- Unique lab IDs for tracking
- References to synthesis processes that created them
- Sample properties (dimensions, mass, composition)
- Links to measurements performed on them

## Typical Usage

1. **Create a library**: A [DTUSputtering](sputtering.md) process deposits materials on a [substrate](substrates.md), creating a `DTUCombinatorialLibrary`
2. **Cleave the library**: A [DTULibraryCleaving](cleaving.md) process splits the library, creating multiple `DTUCombinatorialSample` entries
3. **Characterize samples**: Each sample is referenced in [measurements](xrd.md) like XRD, XPS, PL, etc.
4. **Track provenance**: The entire chain from substrate → sputtering → library → cleaving → sample → measurements is linked

## Related Schemas

- **Created by**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md), [RTP](rtp.md)
- **Split by**: [Library Cleaving](cleaving.md)
- **Measured in**: All [characterization techniques](xrd.md)
- **Starts from**: [Substrates](substrates.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.sample') }}
