
from nomad.config.models.ui import (
    App,
    Column,
    Columns,
    FilterMenu,
    FilterMenus,
    Filters,
)

sputtering_targets_app = App(
    label='Sputtering Targets',
    path='sputtering-targets',
    category='PlasmaNano',
    description="""
    Explore the sputtering targets.
    """,
    # filters=Filters(
    #     include=[
    #         '*#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
    #     ],
    # ),
    # columns=Columns(
    #     selected=[
    #         'data.lab_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
    #         'data.supplier_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget',
    #     ],
    #     options={
    #         'data.lab_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget': Column( # noqa: E501
    #             label='Target ID',
    #         ),
    #         'data.supplier_id#nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget': Column( # noqa: E501
    #             label='Supplier',
    #         ),
    #     },
    # ),
    filter_menus=FilterMenus(
        options={
            'material': FilterMenu(label='Material'),
        }
    ),
),