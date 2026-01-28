# Substrates

Substrates are the base materials on which you deposit thin films or grow materials. Proper substrate tracking ensures you can trace your samples back to their starting materials and identify batch-specific effects.

## Overview

This schema package defines:

- **DTUSubstrate** - An individual substrate wafer or piece with specific properties (size, thickness, surface orientation, supplier information)

- **DTUSubstrateBatch** - A collection of substrates from the same supplier batch, sharing common properties. This enables efficient documentation when you purchase and use multiple identical substrates.

Both extend NOMAD's `CompositeSystem` entity, providing lab ID tracking and referenceable objects that can be linked from synthesis processes.

## Typical Usage

1. **Document substrate batch**: When substrates arrive, create a `DTUSubstrateBatch` entry with supplier info, batch number, and common properties
2. **Reference in synthesis**: When performing [sputtering](sputtering.md) or [thermal evaporation](thermal.md), reference the substrate or substrate batch used
3. **Track consumption**: Monitor which substrates have been used for which experiments
4. **Batch analysis**: Identify if results correlate with specific substrate batches

## Related Schemas

- **Used in**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Creates**: [Samples and Libraries](samples.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.substrate') }}
