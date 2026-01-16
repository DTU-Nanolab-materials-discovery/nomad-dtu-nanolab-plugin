# Welcome to the `nomad-nomad-dtu-nanolab-plugin` documentation

A NOMAD plugin for combinatorial materials discovery at DTU Nanolab.

## Introduction

This plugin powers the data management infrastructure for the **Materials Discovery group** at the [DTU Nanolab](https://www.dtu.dk/english/about/organization/institutter/energy/research/labs/nanolab), led by [Andrea Crovetto](https://orbit.dtu.dk/en/persons/andrea-crovetto). The group specializes in high-throughput combinatorial synthesis and characterization of thin-film materials for sustainable energy applications.

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

<div markdown="block" class="home-grid">
<div markdown="block">

### Tutorial

TODO

- [Tutorial](tutorial/tutorial.md)

</div>
<div markdown="block">

### How-to guides

How-to guides provide step-by-step instructions for a wide range of tasks, with the overarching topics:

- [Install this plugin](how_to/install_this_plugin.md)
- [Use this plugin](how_to/use_this_plugin.md)
- [Adapt for your lab](how_to/adapt-for-your-lab.md)
- [Contribute to this plugin](how_to/contribute_to_this_plugin.md)
- [Contribute to the documentation](how_to/contribute_to_the_documentation.md)

</div>

<div markdown="block">

### Explanation

Conceptual understanding of the plugin:

- [Data Model Philosophy](explanation/data-model.md)
- [Materials Discovery Workflow](explanation/workflow.md)
- [Combinatorial Libraries](explanation/combinatorial-libraries.md)
- [Characterization Techniques](explanation/characterization.md)

[Learn more →](explanation/index.md){.md-button}

</div>
<div markdown="block">

### Reference

Complete technical documentation:

- Schema organization
- Entity schemas (samples, substrates, targets, instruments, gases)
- Activity schemas (sputtering, RTP, cleaving, XRD, XPS, EDX, PL, ellipsometry, Raman, RT)

[Explore the schema reference →](reference/index.md){.md-button}

</div>
</div>
