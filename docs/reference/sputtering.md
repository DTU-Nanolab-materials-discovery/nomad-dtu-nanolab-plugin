# Sputter Deposition

Sputter deposition is a physical vapor deposition technique where material is ejected from targets by ion bombardment and deposited onto substrates. At DTU Nanolab, multi-target sputtering creates combinatorial libraries for efficient materials exploration.

## Overview

This schema package defines:

- **DTUSputtering** - A sputter deposition process with detailed parameters for targets, gases, pressures, powers, and substrate handling

The sputtering process extends NOMAD's `Process` and `Activity` base classes, providing:

- Links to input entities (substrates, targets, gases) and output entities (samples/libraries)
- Deposition parameters (pressure, power, time, temperature)
- Multi-target configurations with independent control
- Gas flow and composition settings
- Automated workflow integration

## Typical Usage

1. **Set up deposition**: Reference [substrates](substrates.md) to use, [targets](targets.md) for each source, [gases](gas.md) for atmosphere, and the [instrument](instruments.md)
2. **Configure parameters**: Set target powers, chamber pressure, gas flows, deposition time, substrate temperature
3. **Document gradient/pattern**: For combinatorial libraries, describe the composition gradient or pattern
4. **Link output**: Reference the [DTUCombinatorialLibrary](samples.md) created by this process
5. **Track provenance**: The sputtering entry links the entire chain: substrates + targets + gases → library

## Key Parameters

- **Target configurations**: Multiple targets with independent power control
- **Chamber conditions**: Base pressure, working pressure, gas composition
- **Deposition control**: Time, rate, substrate rotation/motion for gradients
- **Thermal management**: Substrate temperature, heating/cooling

## Why Document Sputtering Details?

Sputtering parameters directly determine film properties:

- **Power affects**: Deposition rate, film stress, stoichiometry
- **Pressure affects**: Mean free path, film density, morphology
- **Gas composition affects**: Oxidation state, doping, crystallinity
- **Substrate motion affects**: Composition gradients in combinatorial libraries

Complete documentation enables:

- Reproducibility of successful depositions
- Understanding parameter-property relationships
- Troubleshooting when results deviate
- Training new lab members

## Related Schemas

- **Input entities**: [Substrates](substrates.md), [Targets](targets.md), [Gas Supplies](gas.md)
- **Instrument**: [DTUInstrument](instruments.md) (sputter tool)
- **Output entities**: [DTUCombinatorialLibrary](samples.md)
- **Follow-up processes**: [Library Cleaving](cleaving.md), [RTP](rtp.md)
- **Characterization**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), etc.

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.sputtering') }}
