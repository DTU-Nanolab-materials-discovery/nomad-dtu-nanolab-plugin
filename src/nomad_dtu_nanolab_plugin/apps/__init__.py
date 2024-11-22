from nomad.config.models.plugins import AppEntryPoint

from nomad_dtu_nanolab_plugin.apps.targets import sputtering_targets_app

sputtering_targets= AppEntryPoint(
    name='Sputtering targets app',
    description='App for searching sputtering targets.',
    app=sputtering_targets_app,
)
