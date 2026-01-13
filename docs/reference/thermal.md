# Thermal Evaporation

Thermal evaporation is a physical vapor deposition technique where source materials are heated in vacuum until they evaporate and condense onto substrates. It's particularly useful for depositing metals and some semiconductors.

## Overview

This schema package defines thermal evaporation processes with detailed control of:

- Source material heating (resistive, electron beam)
- Deposition rates and film thickness
- Substrate temperature
- Chamber vacuum conditions

The thermal evaporation process extends NOMAD's `Process` and `Activity` base classes, providing:

- Links to input entities (substrates, source materials) and output entities (samples/libraries)
- Evaporation parameters (heating method, power, rate, thickness)
- Vacuum conditions and deposition control
- Automated workflow integration

## Typical Usage

1. **Set up deposition**: Reference [substrates](substrates.md) to use and source materials
2. **Configure evaporation**: Set heating method, power, target rate, final thickness
3. **Control conditions**: Chamber pressure, substrate temperature
4. **Document deposition**: Record actual rates, thickness uniformity
5. **Link output**: Reference the [samples or libraries](samples.md) created

## Key Parameters

- **Source material**: Composition, purity, loading
- **Heating method**: Resistive heating (boat/crucible), electron beam
- **Deposition control**: Rate, thickness, shutter timing
- **Vacuum**: Base pressure, working pressure
- **Substrate handling**: Temperature, rotation, shutter control

## Common Applications

- **Metal contacts**: Electrode deposition for electrical measurements
- **Seed layers**: Nucleation layers for subsequent growth
- **Simple compounds**: Materials that evaporate congruently
- **Multi-layer structures**: Sequential deposition of different materials

## Thermal Evaporation vs. Sputtering

**Use thermal evaporation when:**

- You need very gentle deposition (less energetic than sputtering)
- Working with materials that evaporate cleanly
- Depositing thick metal layers quickly

**Use [sputtering](sputtering.md) when:**

- You need better stoichiometry control (especially for alloys/compounds)
- Creating composition gradients (combinatorial libraries)
- Working with refractory materials
- Depositing oxides or nitrides

## Related Schemas

- **Input entities**: [Substrates](substrates.md), source materials
- **Instrument**: [DTUInstrument](instruments.md) (evaporator)
- **Output entities**: [Samples and Libraries](samples.md)
- **Follow-up processes**: [RTP](rtp.md) for annealing
- **Characterization**: [XRD](xrd.md), [XPS](xps.md), [Ellipsometry](ellipsometry.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.thermal') }}
