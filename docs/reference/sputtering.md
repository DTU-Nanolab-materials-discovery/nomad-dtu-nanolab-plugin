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

## Parsing Workflow

The sputtering parser automatically processes machine log files and extracts relevant process information through a multi-step workflow:

1. **Data Logging**: During depositon, more than 100 machine signals (pressure gauges, powers, flows, etc.) are logged through time using the native software of the sputtering tool (Lesker Eklipse). Relevant logged quantities include:
   - Chamber pressure
   - Flow rates of reactive and non-reactive gases
   - Status of the S cracker
   - Substrate temperature
   - Sputter target information and operating conditions (sputtering mode, power, shutter status, etc.)

2. **Process Step Identification**: The logged information is uploaded to the sputtering entry and rationalized using a custom parser. Important process steps are identified using conditional logic that uniquely describes each processing step. For example:
   - The **deposition step** is defined as timestamps where at least one target is both on with a sustained plasma and in line of sight of the substrate (shutters open)
   - Other identified steps include: Temperature Ramping Up, Deposition, Cooling, etc.

3. **Parameter Extraction**: Once processing steps are identified, derived parameters that give insight into the process are automatically extracted. For instance:
   - Deposition temperature is calculated as the average recorded temperature during the deposition step
   - Similar derived parameters are calculated for each process step

4. **Schema Population**: Derived parameters are routed to their relevant locations in the sputtering data schema, allowing easy access to:
   - General quantities (e.g., deposition temperature)
   - Specific quantities (e.g., reflected RF power as a function of time during target plasma ignition)

5. **Visualization**: Process information is assembled into graphs providing quick process overview:
   - Main deposition events represented as a function of time
   - Visualization of elemental and gaseous source positions during combinatorial deposition
   - Target stability diagnostics (e.g., DC bias as a function of time during deposition for RF sputtering)

6. **Library Generation**: Based on user-provided substrate information, combinatorial libraries are automatically created following laboratory conventions. For example:
   - Four square-shaped Si substrates and one rectangular glass substrate → 5 standalone combinatorial library instances
   - Each library has harmonious naming conventions and references linking to the sputtering process and respective substrate types

![Sputtering workflow visualization](../assets/sputtering-workflow.png)

*Default graphs obtained from parsing a log file through the sputtering entry. (a) Position of the different substrates on the platen during deposition, relative to the sources, namely the reactive toxic gas inlet (H2S + PH3) and the Cu target and other sputtering chamber landmark. (b) Position of the substrate during mounting, defining the orientation of base coordinate system for the combinatorial library. (c) Process timeline graph representing the extend in time of different process-relevant events, such as the moments where reactive gases were flown in the chamber (PH3 On, H2S on) or the moment of the deposition itself. (d) The DC self-bias developed by the Cu target during the deposition.*

### Benefits of Automated Processing

With automatic log file processing, the time a user must spend on uploading data is minimized and the benefits outweigh the extra work by far.

**Short-term benefits:**
- Human-readable plots automatically generated from log file data
- Visualization of important parameters throughout the deposition process
- Immediate diagnostic feedback on process stability

**Long-term benefits:**
- Maintaining an overview of completed experiments
- Easing the integration of collected data during the planning of future experiments
- Facilitating the publication of synthesis data in accordance with FAIR principles

## Key Parameters

- **Target configurations**: Multiple targets with independent power control
- **Chamber conditions**: Base pressure, working pressure, gas composition
- **Deposition control**: Time, rate, substrate rotation/motion for gradients
- **Thermal management**: Substrate temperature, heating/cooling

## Related Schemas

- **Input entities**: [Substrates](substrates.md), [Targets](targets.md), [Gas Supplies](gas.md)
- **Instrument**: [DTUInstrument](instruments.md) (sputter tool)
- **Output entities**: [DTUCombinatorialLibrary](samples.md)
- **Follow-up processes**: [Library Cleaving](cleaving.md), [RTP](rtp.md)
- **Characterization**: [XRD](xrd.md), [XPS](xps.md), [EDX](edx.md), etc.

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.sputtering') }}


