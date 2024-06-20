def test_importing_app():
    # this will raise an exception if pydantic model validation fails for th app
    from nomad_dtu_nanolab_plugin.apps import myapp  # noqa: F401
