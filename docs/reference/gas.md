# Gas Supplies

Gas supplies track the process gases used in deposition and annealing. Proper gas documentation ensures reproducibility and helps troubleshoot contamination issues.

## Overview

This schema package defines:

- **DTUGasSupply** - A gas cylinder or supply with gas type, purity, cylinder number, and supplier information

Gas supplies extend NOMAD's `CompositeSystem` entity, providing:

- Unique lab IDs for inventory management
- Gas composition (Ar, O₂, N₂, etc.)
- Purity specifications (99.999%, etc.)
- Cylinder identification numbers
- Supplier and batch tracking

## Typical Usage

1. **Register gas cylinders**: When cylinders arrive, create `DTUGasSupply` entries with purity and cylinder numbers
2. **Reference in processes**: [Sputtering](sputtering.md) and [RTP](rtp.md) processes reference the gas supplies used
3. **Track consumption**: Monitor cylinder usage and replacement schedules
4. **Quality control**: Link film properties to specific gas batches for contamination troubleshooting

## Why Track Gas Supplies?

Gas quality is critical for many processes:

- **Purity matters**: Even trace impurities can affect film properties (especially for electronic materials)
- **Contamination troubleshooting**: If unexpected impurities appear, gas supply records help identify the source
- **Reproducibility**: Different gas suppliers or batches can produce different results
- **Cost management**: High-purity gases are expensive; tracking helps optimize usage

## Common Gases at DTU Nanolab

- **Argon (Ar)** - Sputter gas (typically 99.999% purity)
- **Oxygen (O₂)** - Reactive sputtering, oxidation treatments
- **Nitrogen (N₂)** - Nitride formation, inert atmosphere
- **Forming gas (H₂/N₂)** - Reduction and annealing

## Related Schemas

- **Used in**: [Sputtering Deposition](sputtering.md), [RTP](rtp.md)
- **Creates**: [Samples and Libraries](samples.md) (via synthesis processes)
- **Co-used with**: [Targets](targets.md), [Instruments](instruments.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.gas') }}
