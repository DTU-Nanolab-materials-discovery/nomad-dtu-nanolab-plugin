
import pkg_resources
import yaml
from nomad.config.models.plugins import AppEntryPoint
from nomad.config.models.ui import (
    App,
    Column,
    Columns,
    Dashboard,
    FilterMenu,
    FilterMenus,
    Filters,
)

yaml_file_path = pkg_resources.resource_filename(__name__, 'target_dashboard.yaml')

with open(yaml_file_path) as file:
    target_dashboard = yaml.safe_load(file)

sputtering_targets= AppEntryPoint(
    name='Sputtering targets app',
    description='App for searching sputtering targets.',
    app=App(
        label='Targets',
        path='sputtering-targets',
        category='Sputtering',
        description="""
        Explore the sputtering targets.
        """,
        filters=Filters(
            include=[
                '*#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
            ],
        ),
        columns=Columns(
            selected=[
                'data.lab_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
                'data.main_material#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
                'data.supplier_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
                'data.refill_or_mounting_date#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
            ],
            options={
                'data.lab_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget': Column( # noqa: E501
                    label='Target ID',
                ),
                'data.main_material#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget': Column( # noqa: E501
                    label='Material',
                ),
                'data.supplier_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget': Column( # noqa: E501
                    label='Supplier',
                ),
                'data.refill_or_mounting_date#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget': Column( # noqa: E501
                    label='Refill or mounting date',
                ),
            },
        ),
        filter_menus=FilterMenus(
            options={
                'material': FilterMenu(label='Material'),
            }
        ),
        filters_locked={
            'entry_type': 'DTUTarget',
        },
        dashboard=Dashboard.parse_obj(target_dashboard)
    ),
)