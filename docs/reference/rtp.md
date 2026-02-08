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


## Parsing Workflow

The RTP parser automatically processes thermal treatment log files and extracts relevant process information through a multi-step workflow:

### Data Logging

The logging of RTP-related signals includes thermal properties, process gases, and pressure data collection. This is achieved by combining the native software of the RTP tool (CX-Thermo) and the sputtering tool (Lesker Eklipse). Relevant logged quantities include:

- Gas flow rates
- Chamber pressure
- Chamber temperature
- Power applied to the lamps

### Process Step Identification

The data is uploaded to the RTP entry in the form of two distinct log files and automatically processed using the developed parser. Similar to the sputtering data parser, the logic consists of unambiguously identifying the different steps of the annealing process.

The steps belong to one of three categories:

- **Heating**: Initial setpoint temperature is lower than final setpoint temperature
- **Annealing plateau**: Initial and final setpoint temperatures are identical
- **Cooling**: Initial setpoint temperature is higher than final setpoint temperature

These setpoints are timestamped, along with all other signals from both log files, making correlation possible. The timestamped setpoint temperature serves as the basis for the parser logic.

This approach remains valid even when experimentalists use multiple steps of one type (e.g., two heating steps with different ramps, or two heating steps separated by an intermediate annealing plateau), showcasing the high degree of adaptability to real laboratory workflows.

### Parameter Extraction

From an experimental perspective, useful information not obtained directly from the log files is automatically extracted, including:

- Partial pressure of each gas present in the RTP chamber during annealing
- Heating and cooling rates
- Other derived parameters calculated from identified process events

### Schema Population

Derived parameters are mapped to their corresponding fields in the RTP schema, similar to the sputtering workflow. This enables users to access process details organized:

- By individual step
- As an overview of the entire process

### Visualization

Similar to the sputtering workflow, the annealing process benefits from automatic plot generation, enabling quick visualization of key aspects:

- Temperature profiles and setpoints as a function of time
- Atmosphere composition during annealing
- Pressure stability during annealing

This organized access to critical parameters makes it easier to identify trends or anomalies that might otherwise go unnoticed, reinforcing the FAIR-by-design principle.

### Input Sample Handling

A key difference between sputtering and RTP processes:

- **Sputtering**: Uses bare substrates as input
- **RTP**: Uses previously deposited combinatorial libraries as input

Input samples can be:

- Whole combinatorial libraries from the sputtering process
- Child libraries created by cleaving a parent library

The user provides information about which input samples were introduced in the RTP chamber. By processing this information, output combinatorial libraries are automatically created and named according to established conventions.

**Example**: If four child combinatorial libraries are mounted horizontally on the sample holder, four independent output combinatorial libraries are created following the naming convention (by user, by iteration number, and position on holder) and referencing:

- The RTP process that generated them
- The corresponding parent combinatorial libraries each was cleaved from

## Related Schemas

- **Input entities**: [Samples and Libraries](samples.md)
- **Atmosphere**: [Gas Supplies](gas.md)
- **Instrument**: [DTUInstrument](instruments.md) (RTP furnace)
- **Preceded by**: [Sputtering](sputtering.md), [Thermal Evaporation](thermal.md)
- **Followed by**: [Characterization measurements](xrd.md)

---

## Schema Documentation

{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.rtp') }}
