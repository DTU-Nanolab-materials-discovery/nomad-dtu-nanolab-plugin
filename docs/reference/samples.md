# Samples and Combinatorial Libraries

Samples represent specific measurement positions on combinatorial libraries. At DTU Nanolab, the materials discovery workflow uses combinatorial libraries with composition gradients to efficiently explore material composition spaces through position-based sampling.

!!! tip "Understanding the Concepts"
    For a deep dive into the distinction between physical library pieces and logical sample positions, see the [Combinatorial Libraries](../explanation/combinatorial-libraries.md) explanation.

## Overview

This schema package defines two main classes:

- **DTUCombinatorialLibrary** - A physical substrate with multiple material compositions deposited as gradients or patterns (e.g., from multi-target sputtering). The library can optionally be cleaved into smaller physical pieces for parallel processing.

- **DTUCombinatorialSample** - A specific measurement position (coordinates) on a combinatorial library or cleaved piece. Each sample position represents a distinct composition point that can be characterized independently. Multiple sample positions can exist on a single library or cleaved piece.

Both classes extend NOMAD's `CompositeSystem` entity, providing:

- Unique lab IDs for tracking
- References to synthesis processes that created them
- Sample properties (dimensions, mass, composition)
- Links to measurements performed on them

## Typical Usage

1. **Create a library**: A [DTUSputtering](sputtering.md) process deposits materials on a [substrate](substrates.md), creating a `DTUCombinatorialLibrary` with composition gradients
2. **Map sample positions**: Define specific coordinates on the library as `DTUCombinatorialSample` entries, each representing a measurement point at a particular composition
3. **Optional cleaving**: A [DTULibraryCleaving](cleaving.md) process can physically split the library into smaller pieces for parallel processing. Each cleaved piece can contain multiple sample positions
4. **Characterize sample positions**: [Measurements](xrd.md) like XRD, XPS, PL reference specific sample positions by their coordinates. Multiple measurements across different positions enable composition-property mapping
5. **Aggregate data**: When multiple measurements target different positions, data can be aggregated (with interpolation if needed) to create property maps across composition space
6. **Track provenance**: The entire chain from substrate → sputtering → library → sample positions → measurements is linked


## Related Schemas

- **Created by**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md), [RTP](rtp.md)
- **Split by**: [Library Cleaving](cleaving.md)
- **Measured in**: All [characterization techniques](xrd.md)
- **Starts from**: [Substrates](substrates.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.sample') }}
