# NOMAD DTU Nanolab Plugin

[![Documentation](https://img.shields.io/badge/docs-online-blue)](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A [NOMAD](https://nomad-lab.eu) plugin providing comprehensive data management infrastructure for high-throughput combinatorial materials discovery workflows.

## Overview

The NOMAD DTU Nanolab Plugin implements FAIR data principles (Findable, Accessible, Interoperable, Reusable) for the entire experimental lifecycle from synthesis to characterization. Developed for the Materials Discovery group at [DTU Nanolab](https://www.dtu.dk/english/about/organization/institutter/energy/research/labs/nanolab), this plugin specializes schemas from the [nomad-material-processing](https://github.com/FAIRmat-NFDI/nomad-material-processing) and [nomad-measurements](https://github.com/FAIRmat-NFDI/nomad-measurements) plugins.

### Key Features

- **17 specialized schema packages** organized into entities (samples, substrates, targets, instruments, gases) and activities (synthesis, measurements, analyses)
- **Synthesis processes**: Multi-target sputtering deposition, rapid thermal processing, thermal evaporation
- **Characterization techniques**: XRD, XPS, EDX, photoluminescence, ellipsometry, Raman spectroscopy, resistivity-temperature measurements
- **Combinatorial library support** with composition gradients and position-based sampling
- **Automatic provenance tracking** and seamless workflow integration based on Basic Formal Ontology principles

### Research Applications

The plugin enables accelerated exploration of novel semiconductor materials for sustainable energy applications:

- **Photovoltaics**: Next-generation solar cell materials (phosphosulfides, thiophosphates, selenium-based absorbers)
- **Transparent Conductors**: p-type and n-type transparent conducting materials
- **Sustainable Materials**: Earth-abundant, non-toxic alternatives to conventional semiconductors

## Installation

To use this plugin in your NOMAD Oasis, add it to the plugins table in the `pyproject.toml` file of your [NOMAD distribution repository](https://github.com/FAIRmat-NFDI/nomad-distro-template):

```toml
[project.optional-dependencies]
plugins = [
  "nomad-dtu-nanolab-plugin @ git+https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin.git@main"
]
```

For production use, specify a version tag or commit hash instead of `@main`. See the [installation guide](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/how_to/install_this_plugin/) for details.

## Documentation

**📚 Complete documentation:** [https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/)

- **[Tutorial](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/tutorial/tutorial/)**: Step-by-step guide through a complete combinatorial project
- **[How-to Guides](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/how_to/install_this_plugin/)**: Practical instructions for data upload and visualization
- **[Explanation](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/explanation/)**: Conceptual understanding of data model and workflow
- **[Reference](https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/reference/)**: Complete technical schema documentation

## Development

### Setup

Create a virtual environment with Python 3.9 or higher:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'
```

### Testing

Run automated tests:

```sh
pytest -svx tests
```

### Code Quality

Run linting and formatting:

```sh
ruff check .
ruff format .
```

## Citation

If you use this plugin in your research, please cite it using the metadata in [CITATION.cff](CITATION.cff).

## Funding

This work was supported in part by a research grant (42140) from VILLUM FONDEN and co-funded by the European Union (ERC, IDOL, 101040153). This work was also supported by the NFDI consortium FAIRmat - Deutsche Forschungsgemeinschaft (DFG) - Project 460197019.

## License

Distributed under the terms of the [MIT](LICENSE) license, the NOMAD DTU Nanolab Plugin is free and open source software.

