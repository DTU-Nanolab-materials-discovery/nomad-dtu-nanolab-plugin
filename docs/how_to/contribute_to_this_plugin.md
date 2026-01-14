# Contribute to This Plugin

We welcome contributions to the DTU Nanolab plugin! Whether you're fixing bugs, adding features, or improving documentation, your help is appreciated.

## Ways to Contribute

### Report Issues

Found a bug or have a feature request?

1. Check [existing issues](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin/issues) first
2. Create a new issue with:
    - Clear description of the problem or feature
    - Steps to reproduce (for bugs)
    - Expected vs. actual behavior
    - Your environment (NOMAD version, Python version)

### Add New Schemas

Want to add support for a new instrument or measurement technique?

1. Review existing schemas in `src/nomad_dtu_nanolab_plugin/schema_packages/`
2. Extend base measurement classes from `basesections.py`
3. Add parser support if needed
4. Document the new schema in `docs/reference/`
5. Add tests in `tests/`

### Improve Parsers

Help parse data files from lab instruments:

1. Add parser to `src/nomad_dtu_nanolab_plugin/parsers/`
2. Support common file formats from your instrument
3. Map data to appropriate schema sections
4. Add test data files to `tests/data/`

### Enhance Documentation

Improve guides and examples:

1. Add how-to guides for common workflows
2. Improve schema documentation with examples
3. Add tutorial notebooks showing real use cases
4. Fix typos and clarify confusing sections

## Development Setup

### Using nomad-distro-dev (Recommended)

The recommended way to develop NOMAD plugins is using [nomad-distro-dev](https://github.com/FAIRmat-NFDI/nomad-distro-dev), which provides a complete development environment with all NOMAD dependencies.

```bash
# Clone nomad-distro-dev if you haven't already
git clone https://github.com/FAIRmat-NFDI/nomad-distro-dev.git
cd nomad-distro-dev

# Clone this plugin into the packages directory
cd packages
git clone https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin.git
# Or fork it first and clone your fork

cd ..

# Add the plugin to pyproject.toml [project.optional-dependencies] plugins section
# Using local path for development:
"nomad-dtu-nanolab-plugin @ file:packages/nomad-dtu-nanolab-plugin"

# Install with uv (recommended) or pip
uv sync --all-extras
# or: pip install -e '.[dev]'

# Activate the environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Create a Feature Branch

```bash
cd packages/nomad-dtu-nanolab-plugin

# Create feature branch
git checkout -b feature/my-new-feature
```

## Making Changes

### Code Style

We use `ruff` for linting and formatting:

```bash
# Check code style
ruff check .

# Auto-format code
ruff format .
```

Key conventions:

- Use single quotes for strings
- Follow PEP 8 naming (snake_case for functions/variables)
- Add docstrings to classes and functions
- Keep line length ≤ 88 characters

### Write Tests

Add tests for new functionality:

```bash
# Run all tests
pytest -svx tests

# Run specific test file
pytest tests/test_my_feature.py

# Run with coverage
pytest --cov=nomad_dtu_nanolab_plugin tests/
```

Test structure:

- Unit tests in `tests/`
- Test data files in `tests/data/`
- Use pytest fixtures for common setup

### Update Documentation

If adding schemas or features:

1. Add reference documentation in `docs/reference/`
2. Update `docs/reference/index.md` if needed
3. Add how-to guide if applicable
4. Build docs locally to verify:

```bash
pip install -r requirements_docs.txt
mkdocs serve
# View at http://localhost:8000
```

## Submit Your Changes

### 1. Commit Your Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "Add support for XRF measurements

- Implement DTUXRFMeasurement schema
- Add XRF data parser for Bruker format
- Include test data and documentation"
```

Commit message guidelines:

- First line: concise summary (<50 chars)
- Blank line
- Detailed description if needed
- Reference issues: "Fixes #123" or "Related to #456"

### 2. Push and Create PR

```bash
# Push to your fork
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub:

1. Go to your fork on GitHub
2. Click "Pull Request"
3. Provide clear title and description:
    - What does this PR do?
    - Why is this change needed?
    - How has it been tested?
    - Related issues/PRs?

### 3. Review Process

- Maintainers will review your PR
- Address feedback by pushing new commits
- CI checks must pass (tests, linting)
- Once approved, we'll merge your contribution!

## Code Review Guidelines

When reviewing or being reviewed:

- Be constructive and respectful
- Explain your suggestions clearly
- Focus on code quality and maintainability
- Consider backwards compatibility
- Ensure tests cover new functionality

## Schema Design Principles

When adding new schemas:

### Extend Base Classes

```python
from nomad.datamodel.metainfo.basesections import Measurement
from nomad_dtu_nanolab_plugin.schema_packages.basesections import DtuNanolabMeasurement

class MyNewMeasurement(DtuNanolabMeasurement):
    """Document what this measurement does."""
    pass
```

### Follow Naming Conventions

- Class names: `DTU` prefix + descriptive name (e.g., `DTUXRDMeasurement`)
- Quantities: snake_case (e.g., `peak_intensity`)
- Use NOMAD categories consistently

### Document Everything

```python
class MyMeasurement(DtuNanolabMeasurement):
    """Brief description of the measurement.

    Longer description explaining:
    - What does this measurement do?
    - What parameters are important?
    - How is data typically collected?
    """

    laser_wavelength = Quantity(
        type=np.float64,
        unit='nm',
        description='Excitation laser wavelength used for the measurement.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
    )
```

### Link to Related Entities

```python
samples = SubSection(
    section_def=DTUCombinatorialSample,
    repeats=True,
    description='Sample positions measured in this experiment.',
)
```

## Adapting This Plugin for Your Lab

This plugin serves as a reference implementation for combinatorial materials discovery workflows. If you want to adapt it for your own lab:

### What to Consider

1. **Lab-specific naming**: Replace "DTU" prefixes with your lab abbreviation
2. **Instrument schemas**: Adapt or add schemas for your specific instruments
3. **File formats**: Implement parsers for your lab's data file formats
4. **Workflow differences**: Modify schemas to match your lab's processes
5. **Metadata requirements**: Adjust fields to capture your lab's metadata needs

### Recommended Approach

```bash
# Fork this repository as a starting point
# Rename the package and update references
# Modify schemas in src/nomad_dtu_nanolab_plugin/schema_packages/
# Update parsers in src/nomad_dtu_nanolab_plugin/parsers/
# Adapt documentation in docs/
```

### Key Files to Modify

- `pyproject.toml` - Update package name and metadata
- `src/nomad_dtu_nanolab_plugin/` - Rename directory and update imports
- `src/nomad_dtu_nanolab_plugin/nomad_plugin.yaml` - Update plugin ID
- Schema files - Adapt to your lab's needs
- Parsers - Implement for your file formats
- Documentation - Update with your lab context

### Getting Help

For questions about adapting this plugin:

- Review the [NOMAD plugin development guide](https://nomad-lab.eu/prod/v1/develop/docs/howto/plugins/plugins.html)
- Check the [schema writing guide](https://nomad-lab.eu/prod/v1/develop/docs/howto/plugins/schema_packages.html)
- Ask in the [NOMAD Discord](https://discord.gg/Gyzx3ukUw8)
- Reference this plugin's implementation as an example

## Questions?

- Open an issue for technical questions
- Join the [NOMAD Discord](https://discord.gg/Gyzx3ukUw8) for discussions
- Contact DTU Nanolab team for lab-specific questions

Thank you for contributing to making materials data FAIR!

