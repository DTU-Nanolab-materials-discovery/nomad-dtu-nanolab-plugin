# Contribute to the Documentation

Good documentation is crucial for helping users understand and use the plugin effectively. We welcome contributions to improve our documentation!

## Documentation Structure

The documentation follows the [Diátaxis framework](https://diataxis.fr/):

- **Tutorial** (`tutorial/`) - Learning-oriented, step-by-step lessons
- **How-to guides** (`how_to/`) - Problem-oriented, practical steps
- **Reference** (`reference/`) - Information-oriented, technical descriptions
- **Explanation** (`explanation/`) - Understanding-oriented, background and context

## Local Documentation Development

### Setup

```bash
# From within the plugin directory
cd packages/nomad-dtu-nanolab-plugin

# Install documentation dependencies
pip install -r requirements_docs.txt

# Serve documentation locally
mkdocs serve

# View at http://localhost:8000
# Docs auto-reload when you save changes
```

## Documentation Style Guide

### Writing Guidelines

**Be Clear and Concise**

- Use simple, direct language
- Avoid jargon unless necessary
- Define technical terms on first use
- Keep sentences short and focused

**Be Consistent**

- Use consistent terminology (e.g., "sample position" not "sample point" or "measurement position")
- Follow existing formatting patterns
- Use the same voice and tone throughout

**Be Helpful**

- Include practical examples
- Explain "why" not just "how"
- Anticipate common questions
- Link to related sections

### Markdown Formatting

**Headers**

```markdown
# Top Level (page title)
## Main Sections
### Subsections
#### Details
```

**Code Blocks**

````markdown
```python
# Python code with syntax highlighting
from nomad.datamodel import EntryArchive
```

```bash
# Shell commands
mkdocs serve
```
````

**Links**

```markdown
# Internal links (relative paths)
[Sample documentation](../reference/samples.md)
[Specific section](../reference/samples.md#overview)

# External links
[NOMAD documentation](https://nomad-lab.eu/prod/v1/docs/)
```

**Admonitions**

```markdown
!!! note "Optional Title"
    Important information that enhances understanding.

!!! tip
    Helpful suggestions and best practices.

!!! warning
    Cautions about potential issues.

!!! danger
    Critical warnings about data loss or errors.
```

**Images**

```markdown
![Alt text](../assets/image-name.png)

# With caption
<figure markdown>
  ![Alt text](../assets/image-name.png)
  <figcaption>Figure caption explaining the image</figcaption>
</figure>
```

**Tables**

```markdown
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
| Cell 3   | Cell 4   |
```

### Schema Documentation

When documenting schemas in the reference section, include:

1. Brief introduction
2. Overview of main classes
3. Typical usage workflow
4. Related schemas
5. Auto-generated API docs using `{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.package_name') }}`

See existing reference pages for examples.

## Adding New Documentation

### New How-to Guide

1. Create file in `docs/how_to/descriptive-name.md`
2. Use the following structure:

```markdown
# How to [Do Something]

Brief introduction to what this guide covers.

## Prerequisites

- What you need before starting
- Links to installation/setup guides

## Step-by-Step Instructions

### 1. First Step

Detailed instructions...

```bash
# Example commands
```

### 2. Second Step

More details...

## Troubleshooting

Common issues and solutions.

## Next Steps

- Related guides
- Further reading
```

3. Add to `docs/index.md` how-to section
4. Update `mkdocs.yml` navigation

### New Reference Page

1. Create file in `docs/reference/schema-name.md`
2. Follow schema documentation template above
3. Add to `docs/reference/index.md` navigation
4. Update workflow diagrams if needed

### Adding Images

1. Save images in `docs/assets/`
2. Use descriptive filenames: `workflow-sputtering.png`
3. Optimize image size (use PNG for diagrams, JPG for photos)
4. Add alt text for accessibility
5. Reference in markdown: `![Description](../assets/filename.png)`

## Updating API Documentation

The schema API documentation is auto-generated using the `metainfo_package` macro:

```markdown
{{ metainfo_package('nomad_dtu_nanolab_plugin.schema_packages.xrd') }}
```

To update:

1. Ensure docstrings are complete in Python code
2. Add `description` to Quantity definitions
3. Documentation regenerates automatically

## Testing Documentation

### Check Links

```bash
# Test all links (including external)
mkdocs serve
# Click through all internal links
```

### Review Build

```bash
# Build and check for warnings
mkdocs build --strict

# This will fail if there are broken links or missing files
```

### Preview Changes

Before submitting:

1. Build docs locally and review pages
2. Check on different screen sizes
3. Verify all images load correctly
4. Test code examples if possible
5. Check for typos and grammar

## Submitting Documentation Changes

```bash
# Create a feature branch
git checkout -b docs/describe-your-changes

# Make your changes
# ...

# Commit with descriptive message
git commit -m "Brief description of documentation changes"

# Push and create PR
git push origin docs/describe-your-changes
```

## Pre-submission Checklist

- [ ] Builds without errors: `mkdocs build --strict`
- [ ] Tested locally: `mkdocs serve`
- [ ] All links work
- [ ] Images display correctly
- [ ] Code examples are accurate
- [ ] Added to `mkdocs.yml` navigation if new page

## Getting Help

- Check [MkDocs documentation](https://www.mkdocs.org/)
- Review [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) for advanced features
- Ask in the [NOMAD Discord](https://discord.gg/Gyzx3ukUw8)
- Open an issue for documentation-specific questions

Thank you for helping improve the documentation!
