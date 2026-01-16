# Materials Discovery Workflow

This page illustrates how the nomad-dtu-nanolab-plugin schemas connect in a complete materials discovery workflow, from lab inventory through synthesis, characterization, and analysis. Understanding this flow helps you see how individual schemas work together to capture the entire research process.

## Schema Package Organization

The plugin contains 17 schema packages organized by function. This organization mirrors the natural workflow progression in the lab:

```mermaid
graph TB
    subgraph "Lab Inventory & Items"
        A[samples<br/>DTUCombinatorialLibrary<br/>DTUCombinatorialSample]
        B[substrates<br/>DTUSubstrate<br/>DTUSubstrateBatch]
        C[targets<br/>DTUTarget]
        D[gas<br/>DTUGasSupply]
        E[instruments<br/>DTUInstrument]
    end

    subgraph "Synthesis & Processing"
        F[sputtering<br/>DTUSputtering]
        G[rtp<br/>DtuRTP]
        H[thermal<br/>Thermal Evaporation]
        I[cleaving<br/>DTULibraryCleaving]
    end

    subgraph "Characterization"
        J[basesections<br/>Base Measurement]
        K[xrd<br/>DTUXRDMeasurement]
        L[xps<br/>DTUXpsMeasurement]
        M[edx<br/>EDXMeasurement]
        N[pl<br/>DTUPLMeasurement]
        O[ellipsometry<br/>DTUEllipsometryMeasurement]
        P[raman<br/>RamanMeasurement]
        Q[rt<br/>RTMeasurement]
    end

    subgraph "Data Analysis"
        R[analysis<br/>DtuJupyterAnalysis]
    end

    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#e1f5ff
    style D fill:#e1f5ff
    style E fill:#e1f5ff
    style F fill:#fff4e1
    style G fill:#fff4e1
    style H fill:#fff4e1
    style I fill:#fff4e1
    style J fill:#ffe1f5
    style K fill:#ffe1f5
    style L fill:#ffe1f5
    style M fill:#ffe1f5
    style N fill:#ffe1f5
    style O fill:#ffe1f5
    style P fill:#ffe1f5
    style Q fill:#ffe1f5
    style R fill:#e1ffe1
```

**Color coding:**
- 🔵 **Blue** = Lab Inventory & Items ([Entities](data-model.md#entities-physical-items-in-your-lab))
- 🟡 **Yellow** = Synthesis & Processing ([Activities](data-model.md#activities-things-you-do-in-the-lab))
- 🔴 **Pink** = Characterization ([Activities](data-model.md#activities-things-you-do-in-the-lab))
- 🟢 **Green** = Data Analysis ([Activities](data-model.md#activities-things-you-do-in-the-lab))

## End-to-End Workflow Example

Here's how these schemas connect in a typical DTU Nanolab workflow, from inventory to analysis:

```mermaid
graph LR
    subgraph "1. Lab Inventory"
        A[DTUSubstrateBatch<br/>Batch of substrates]
        B[DTUTarget<br/>Sputter targets]
        C[DTUGasSupply<br/>Process gases]
        D[DTUInstrument<br/>Sputter tool]
    end

    subgraph "2. Synthesis"
        E[DTUSputtering<br/>Deposition process]
        F[DTUCombinatorialLibrary<br/>Material library with<br/>composition gradient]
    end

    subgraph "3. Sample Position Mapping"
        S[DTUCombinatorialSample<br/>Sample positions at<br/>specific coordinates]
    end

    subgraph "4. Optional Physical Cleaving"
        G[DTULibraryCleaving<br/>Split into pieces]
        H[Child Libraries<br/>Physical pieces containing<br/>multiple sample positions]
    end

    subgraph "5. Characterization"
        I[DTUXRDMeasurement<br/>Crystal structure]
        J[DTUXpsMeasurement<br/>Surface composition]
        K[DTUPLMeasurement<br/>Optical properties]
    end

    subgraph "6. Analysis"
        L[DtuJupyterAnalysis<br/>Data processing]
    end

    A -->|uses substrate from| E
    B -->|uses target| E
    C -->|uses gas| E
    D -->|performed on| E
    E -->|creates| F
    F -->|defines positions on| S
    F -.->|optional: split| G
    G -.->|creates pieces| H
    S -->|references coord on| F
    S -.->|or on cleaved| H
    S -->|measured at position| I
    S -->|measured at position| J
    S -->|measured at position| K
    I -->|data fed to| L
    J -->|data fed to| L
    K -->|data fed to| L

    style A fill:#e1f5ff
    style B fill:#e1f5ff
    style C fill:#e1f5ff
    style D fill:#e1f5ff
    style E fill:#fff4e1
    style F fill:#e1f5ff
    style S fill:#e1f5ff
    style G fill:#fff4e1
    style H fill:#e1f5ff
    style I fill:#ffe1f5
    style J fill:#ffe1f5
    style K fill:#ffe1f5
    style L fill:#e1ffe1
```

!!! note "Key Workflow Concepts"
    - **Sample positions** (DTUCombinatorialSample) are defined by **coordinates** on libraries, not by physical cleaving
    - **Cleaving** (optional) creates **physical pieces** (child libraries) for parallel processing
    - **Measurements** reference libraries and track their coordinates, whether on intact libraries or cleaved pieces
    - A single cleaved piece can contain **multiple sample positions** at different compositions

## Workflow Stages Explained

### 1. Lab Inventory Setup

Before starting experiments, you document your lab's resources:

- **[Substrate batches](../reference/substrates.md)**: Catalog wafers/substrates with batch numbers and properties
- **[Targets](../reference/targets.md)**: Document sputter targets with composition and usage tracking
- **[Gas supplies](../reference/gas.md)**: Register gas cylinders with purity and cylinder numbers
- **[Instruments](../reference/instruments.md)**: Define lab equipment with capabilities and configurations

These are all **[entities](data-model.md#entities-physical-items-in-your-lab)**—persistent physical items with lab IDs.

### 2. Synthesis Process

You perform a **[synthesis activity](data-model.md#synthesis-and-processing)** that consumes inventory items and creates libraries:

- **[Sputtering](../reference/sputtering.md)**, **[Thermal Evaporation](../reference/thermal.md)**, or **[RTP](../reference/rtp.md)** processes
- **Inputs**: References to substrates, targets, gases, and instruments from inventory
- **Outputs**: Creates a **[combinatorial library](../reference/samples.md)** with composition gradients
- **Parameters**: Complete deposition/annealing conditions documented

The process extends NOMAD's `Process` activity class, automatically linking inputs and outputs.


### 3. Optional Physical Cleaving

If needed for parallel processing, you can physically divide the library:

- **[Library cleaving](../reference/cleaving.md)** process (DTULibraryCleaving) splits the substrate
- **Input**: Parent library
- **Outputs**: Multiple child libraries (physical pieces)
- **Sample positions remain unchanged**: They still reference their original coordinates
- Each cleaved piece typically contains multiple sample positions

Learn more about this distinction in [Combinatorial Libraries Concept](combinatorial-libraries.md).

### 4. Characterization Measurements

You perform **[measurement activities](data-model.md#measurements)** on several library coordinates:

- **Structural**: [XRD](../reference/xrd.md) for crystal structure and phases
- **Compositional**: [XPS](../reference/xps.md) and [EDX](../reference/edx.md) for elemental analysis
- **Optical**: [PL](../reference/pl.md), [Ellipsometry](../reference/ellipsometry.md), [Raman](../reference/raman.md)
- **Electrical**: [RT measurements](../reference/rt.md)

Each measurement:

- References the specific library and track coordinates
- Links to the instrument used
- Stores measurement parameters and results
- Extends the common [BaseMeasurement](../reference/basesections.md) infrastructure

See [Characterization Techniques](characterization.md) for what each technique provides.

### 5. Data Analysis

Finally, you process and interpret the data:

- **[Jupyter Analysis](../reference/analysis.md)** (DtuJupyterAnalysis) for computational workflows
- **Inputs**: References to libraries and their provenance
- **Outputs**: Processed results, figures, derived properties
- **Notebook integration**: Links to Jupyter notebooks with analysis code

The analysis activity completes the provenance chain: inventory → synthesis → samples → measurements → analysis.

This workflow structure provides:

1. **Reproducibility**: Exact conditions documented for every sample
2. **Traceability**: Query any sample's complete history
3. **Efficiency**: Reuse inventory items across many experiments
4. **Analysis**: Correlate synthesis parameters with measured properties
5. **Publications**: Auto-generate methods sections from metadata
6. **Collaboration**: Share complete provenance with collaborators

## Learn More

- **[Data Model Philosophy](data-model.md)**: Understand entities vs. activities
- **[Combinatorial Libraries](combinatorial-libraries.md)**: Deep dive into sample positions
- **[Characterization Techniques](characterization.md)**: What each measurement tells you
- **[Tutorial](../tutorial/tutorial.md)**: Hands-on walkthrough of a complete workflow
- **[Reference](../reference/index.md)**: Technical schema documentation
