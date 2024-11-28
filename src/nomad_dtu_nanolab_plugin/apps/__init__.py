from nomad.config.models.plugins import AppEntryPoint
from nomad.config.models.ui import (
    App,
    Column,
    Columns,
    Filters,
    Menu,
    MenuItemHistogram,
    MenuItemPeriodicTable,
    MenuSizeEnum,
    SearchQuantities,
)

schema = 'nomad_dtu_nanolab_plugin.schema_packages.sputtering.DTUSputtering'

sputtering = AppEntryPoint(
    name='Sputtering app',
    description='App for searching sputtering processes.',
    app=App(
        label='Sputtering',
        path='sputtering',
        category='Activities',
        description="""
        Explore the sputtering processes.
        """,
        search_quantities=SearchQuantities(
            include=[
                f'*#{schema}',
            ],
        ),
        columns=Columns(
            selected=[
                f'data.lab_id#{schema}',
                f'data.datetime#{schema}',
                f'data.deposition_parameters.deposition_temp#{schema}',
                f'data.deposition_parameters.deposition_time#{schema}',
                f'data.deposition_parameters.sputter_pressure#{schema}',
                f'data.deposition_parameters.material_space#{schema}',
                f'data.deposition_parameters.ar_flow#{schema}',
                f'data.deposition_parameters.h2s_in_ar_flow#{schema}',
                f'data.deposition_parameters.ph3_in_ar_flow#{schema}',
            ],
            options={
                f'data.lab_id#{schema}': Column(
                    label='Sputtering ID',
                ),
                f'data.datetime#{schema}': Column(
                    label='Date and time',
                ),
                f'data.deposition_parameters.deposition_temp#{schema}': Column(
                    label='Deposition temperature',
                    unit='degC',
                ),
                f'data.deposition_parameters.deposition_time#{schema}': Column(
                    label='Deposition time',
                    unit='minute',
                ),
                f'data.deposition_parameters.sputter_pressure#{schema}': Column(
                    label='Sputter pressure',
                    unit='mtorr',
                ),
                f'data.deposition_parameters.material_space#{schema}': Column(
                    label='Material space',
                ),
                f'data.deposition_parameters.ar_flow#{schema}': Column(
                    label='Ar flow',
                    unit='cm^3/minute',
                ),
                f'data.deposition_parameters.h2s_in_ar_flow#{schema}': Column(
                    label='H2S in Ar flow',
                    unit='cm^3/minute',
                ),
                f'data.deposition_parameters.ph3_in_ar_flow#{schema}': Column(
                    label='PH3 in Ar flow',
                    unit='cm^3/minute',
                ),
            },
        ),
        menu=Menu(
            title='Material',
            size=MenuSizeEnum.XL,
            items=[
                MenuItemPeriodicTable(
                    quantity='results.material.elements',
                ),
                MenuItemHistogram(
                    x=f'data.deposition_parameters.deposition_temp#{schema}',
                ),
            ],
        ),
        filters_locked={
            'entry_type': 'DTUSputtering',
        },
    ),
)

target_schema = 'nomad_dtu_nanolab_plugin.schema_packages.target.DTUTarget'

sputtering_targets = AppEntryPoint(
    name='Sputtering targets app',
    description='App for searching sputtering targets.',
    app=App(
        label='Targets',
        path='sputtering-targets',
        category='Inventory',
        description="""
        Explore the sputtering targets.
        """,
        filters=Filters(
            include=[
                f'*#{target_schema}',
            ],
        ),
        columns=Columns(
            selected=[
                f'data.lab_id#{target_schema}',
                f'data.main_material#{target_schema}',
                f'data.purity#{target_schema}',
                f'data.supplier_id#{target_schema}',
                f'data.refill_or_mounting_date#{target_schema}',
                f'data.thickness#{target_schema}',
            ],
            options={
                f'data.lab_id#{target_schema}': Column(
                    label='Target ID',
                ),
                f'data.purity#{target_schema}': Column(
                    label='Purity (%)',
                ),
                f'data.main_material#{target_schema}': Column(
                    label='Material',
                ),
                f'data.supplier_id#{target_schema}': Column(
                    label='Supplier',
                ),
                f'data.refill_or_mounting_date#{target_schema}': Column(
                    label='Refill or mounting date',
                ),
                f'data.thickness#{target_schema}': Column(
                    label='Thickness',
                    unit='mm',
                ),
            },
        ),
        menu=Menu(
            title='Material',
            size=MenuSizeEnum.XXL,
            items=[
                MenuItemPeriodicTable(
                    quantity='results.material.elements',
                ),
                MenuItemHistogram(
                    x=f'data.purity#{target_schema}',
                ),
            ],
        ),
        filters_locked={
            'entry_type': 'DTUTarget',
        },
    ),
)
