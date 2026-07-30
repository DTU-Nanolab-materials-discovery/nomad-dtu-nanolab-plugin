# Sputter Targets

Sputter targets are the source materials used in physical vapor deposition. Each target has specific composition, power settings, and usage history that affect your deposited films.

## Overview

This schema package defines:

- **DTUTarget** - A sputter target with composition, dimensions, power ratings, and usage tracking

Targets extend NOMAD's `CompositeSystem` entity, providing:

- Unique lab IDs for inventory management
- Composition tracking (elements and stoichiometry)
- Power and voltage parameters
- Usage history (hours sputtered, replacement tracking)
- Supplier information

## Typical Usage

1. **Register new target**: When a target arrives, create a `DTUTarget` entry with composition, size, and power specifications
2. **Reference in sputtering**: Each [DTUSputtering](sputtering.md) process references the targets used and their operating conditions
3. **Track usage**: Monitor target lifetime and schedule replacements
4. **Correlate with results**: Link film properties to specific targets (useful for identifying contamination or target aging effects)

## Why Track Targets?

Target properties directly affect film quality:

- **Composition variations**: Even small differences in target composition affect film stoichiometry
- **Aging effects**: Target surface changes over time, affecting deposition rate and film quality
- **Power history**: Previous high-power sputtering can modify target surface
- **Cost tracking**: Expensive targets need careful lifetime management

## Related Schemas

- **Used in**: [Sputtering Deposition](sputtering.md)
- **Creates**: [Samples and Libraries](samples.md) (via sputtering)
- **Co-used with**: [Gas Supplies](gas.md), [Instruments](instruments.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.target') }}
