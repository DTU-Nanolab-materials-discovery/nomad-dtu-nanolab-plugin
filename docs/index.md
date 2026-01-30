# <img src="assets/dtu_nomad.svg" alt="DTU Nanolab NOMAD Plugin logo" width="300" />

This plugin powers the data management infrastructure for the **Materials Discovery group** at the [DTU Nanolab](https://www.dtu.dk/english/about/organization/institutter/energy/research/labs/nanolab), led by [Andrea Crovetto](https://orbit.dtu.dk/en/persons/andrea-crovetto). The group specializes in high-throughput combinatorial synthesis and characterization of thin-film materials for sustainable energy applications.

<div markdown="block" class="action-buttons">
  <a href="#" class="md-button md-button--primary action-button">📄 Paper</a>
  <a href="#" class="md-button md-button--primary action-button">🔍 Explore in NOMAD</a>
  <a href="https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin" class="md-button action-button"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" width="14" height="14"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg> Plugin Repository</a>
</div>

## Getting Started

<div markdown="block" class="framework-grid">

<div markdown="block">

### 📚 Tutorial
**Learning-oriented guides**

Follow our comprehensive step-by-step guide through a complete combinatorial materials discovery project: from sputtering deposition to data visualization.

[Start the tutorial →](tutorial/tutorial.md){.md-button}

</div>

<div markdown="block">

### 📖 How-to Guides
**Task-oriented instructions**

Practical guides for using the NOMAD Oasis deployment:

**Data Upload:**
- [Upload Sputtering Data](how_to/upload-sputtering-data.md)
- [Add EDX Measurements](how_to/add-edx-measurements.md)
- [Add Raman Measurements](how_to/add-raman-measurements.md)
- [Add XRD Measurements](how_to/add-xrd-measurements.md)
- [Add RTP Data](how_to/add-rtp-data.md)
- [Cleave Libraries](how_to/cleave-libraries.md)

**Visualization & Analysis:**
- [Plot Combinatorial EDX Data](how_to/plot-combinatorial-edx.md)
- [Export High-Quality Figures](how_to/export-high-quality-figures.md)

[View all guides →](how_to/install_this_plugin.md){.md-button}

</div>

<div markdown="block">

### 💡 Explanation
**Understanding-oriented context**

Conceptual understanding of the plugin:

- [Data Model Philosophy](explanation/data-model.md)
- [Materials Discovery Workflow](explanation/workflow.md)
- [Combinatorial Libraries](explanation/combinatorial-libraries.md)
- [Characterization Techniques](explanation/characterization.md)

[Learn more →](explanation/index.md){.md-button}

</div>

<div markdown="block">

### 📋 Reference
**Information-oriented documentation**

Complete technical documentation:

- Schema organization
- Entity schemas (samples, substrates, targets, instruments, gases)
- Activity schemas (sputtering, RTP, cleaving, XRD, XPS, EDX, PL, ellipsometry, Raman, RT)

[Explore the schema reference →](reference/index.md){.md-button}

</div>

</div>

### Research Focus

The Materials Discovery group develops novel semiconductor materials for:

- **Photovoltaics**: Next-generation solar cell materials including phosphosulfides, thiophosphates, and selenium-based absorbers
- **Transparent Conductors**: p-type and n-type transparent conducting materials for optoelectronic devices
- **Sustainable Materials**: Earth-abundant, non-toxic alternatives to conventional semiconductors

### Combinatorial Approach

The group employs a **combinatorial materials discovery workflow** that accelerates materials exploration:

1. **Multi-target sputtering** creates composition gradient libraries on single substrates
2. **Position-based sampling** maps specific measurement points across composition space
3. **High-throughput characterization** measures multiple sample positions in parallel
4. **Data-driven analysis** identifies promising compositions for further development

This plugin enables **FAIR** (Findable, Accessible, Interoperable, Reusable) data management for the entire workflow, from synthesis to characterization, ensuring reproducibility and facilitating collaboration.