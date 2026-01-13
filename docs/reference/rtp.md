# Rapid Thermal Processing (RTP)

Rapid Thermal Processing provides fast heating and cooling for annealing, oxidation, nitridation, and other thermal treatments. RTP is essential for activating dopants, improving crystallinity, and modifying material properties without extended high-temperature exposure.

## Overview

This schema package defines:

- **DtuRTP** - A rapid thermal processing step with temperature profiles, atmosphere control, and timing

The RTP process extends NOMAD's `Process` and `Activity` base classes, providing:

- Links to input samples/libraries and output (modified) samples
- Temperature profiles (ramp rates, hold times, cooling rates)
- Atmosphere control (gas composition, pressure)
- Multi-step thermal cycles
- Automated workflow integration

## Typical Usage

1. **Select samples**: Reference [samples or libraries](samples.md) to be processed
2. **Define thermal profile**: Set ramp-up rate, peak temperature, hold time, cooling rate
3. **Set atmosphere**: Choose [gas environment](gas.md) (Ar, O₂, N₂, forming gas, vacuum)
4. **Document equipment**: Reference the [RTP instrument](instruments.md) used
5. **Link output**: Updated sample properties (crystallinity, oxidation state, etc.)

## Key Parameters

- **Temperature profile**: Ramp rate, peak temperature, hold time, cooling rate
- **Atmosphere**: Gas type, flow rate, pressure
- **Sample positioning**: Multiple samples, temperature uniformity considerations
- **Cycle steps**: Multi-step profiles for complex treatments

## Common RTP Applications

- **Crystallization**: Improving as-deposited amorphous or poorly crystalline films
- **Annealing**: Stress relief, grain growth, defect reduction
- **Oxidation/Nitridation**: Forming oxide or nitride layers
- **Dopant activation**: Activating implanted or incorporated dopants
- **Interface engineering**: Promoting reactions at interfaces

## Why Document RTP Details?

Thermal history critically affects material properties:

- **Temperature affects**: Phase transitions, grain size, crystallinity
- **Ramp/cooling rates affect**: Stress, defect density, phase stability
- **Atmosphere affects**: Oxidation state, composition, surface chemistry
- **Time affects**: Diffusion, grain growth, decomposition

Detailed records enable:

- Optimizing thermal treatments
- Understanding structure-property relationships
- Reproducing successful conditions
- Avoiding destructive over-processing

## Related Schemas

- **Input entities**: [Samples and Libraries](samples.md)
- **Atmosphere**: [Gas Supplies](gas.md)
- **Instrument**: [DTUInstrument](instruments.md) (RTP furnace)
- **Preceded by**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Followed by**: [Characterization measurements](xrd.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.rtp') }}
