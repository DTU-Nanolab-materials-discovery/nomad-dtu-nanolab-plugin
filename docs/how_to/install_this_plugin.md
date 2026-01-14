# Install This Plugin

If you want to run this plugin locally on your Oasis to use the defined schemas, you need to add the plugin to your Oasis image.

The recommended way of doing this is to add it to the plugins table in the [`pyproject.toml`](https://github.com/FAIRmat-NFDI/nomad-distro-template/blob/main/pyproject.toml) file of your [NOMAD distribution repository](https://github.com/FAIRmat-NFDI/nomad-distro-template?tab=readme-ov-file).

Currently the plugin is not published to PyPI and you will need to specify a git source. For this you also need to specify a version tag, branch, or commit. For example, to use the main branch you should add the following to the `pyproject.toml`:

```toml
[project.optional-dependencies]
plugins = [
  "nomad-dtu-nanolab-plugin @ git+https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin.git@main"
]
```

!!! tip "Using Specific Versions"
    For production use, specify a version tag or commit hash instead of `@main`:
    ```toml
    "nomad-dtu-nanolab-plugin @ git+https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin.git@v1.0.0"
    ```
    or
    ```toml
    "nomad-dtu-nanolab-plugin @ git+https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin.git@a1b2c3d4"
    ```

For more detailed installation instructions, visit our [docs for NOMAD plugins](https://nomad-lab.eu/prod/v1/develop/docs/howto/oasis/plugins_install.html).
