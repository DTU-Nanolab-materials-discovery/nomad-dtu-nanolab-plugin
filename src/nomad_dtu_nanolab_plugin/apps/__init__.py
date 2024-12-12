from nomad.config.models.plugins import AppEntryPoint
from nomad.config.models.ui import (
    App,
    Column,
    Columns,
    Filters,
    Format,
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
        columns=[
            Column(
                search_quantity=f'data.lab_id#{schema}',
                selected=True,
                label='Sputtering ID',
            ),
            Column(
                search_quantity=f'data.datetime#{schema}',
                selected=True,
                label='Date and time',
            ),
            Column(
                search_quantity=f'data.deposition_parameters.deposition_temp#{schema}',
                selected=True,
                label='Deposition temperature',
                unit='degC',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.deposition_parameters.deposition_time#{schema}',
                selected=True,
                label='Deposition time',
                unit='minute',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.deposition_parameters.sputter_pressure#{schema}',
                selected=True,
                label='Sputter pressure',
                unit='mtorr',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.deposition_parameters.material_space#{schema}',
                selected=True,
                label='Material space',
            ),
            Column(
                search_quantity=f'data.deposition_parameters.ar_flow#{schema}',
                selected=True,
                label='Ar flow',
                unit='cm^3/minute',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.deposition_parameters.h2s_in_ar_flow#{schema}',
                selected=True,
                label='H2S in Ar flow',
                unit='cm^3/minute',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.deposition_parameters.ph3_in_ar_flow#{schema}',
                selected=True,
                label='PH3 in Ar flow',
                unit='cm^3/minute',
                format=Format(decimals=1),
            ),
        ],
        menu=Menu(
            title='Material',
            size=MenuSizeEnum.XL,
            items=[
                MenuItemPeriodicTable(
                    quantity='results.material.elements',
                ),
                MenuItemHistogram(
                    x=f'data.deposition_parameters.deposition_temp#{schema}',
                    # unit='degC',
                    # title='Deposition temperature (°C)',
                ),
                MenuItemHistogram(
                    x=f'data.deposition_parameters.deposition_time#{schema}',
                    # unit='minute',
                    # title='Deposition time (min)',
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
        columns=[
            Column(
                search_quantity=f'data.lab_id#{target_schema}',
                selected=True,
                label='Target ID',
            ),
            Column(
                search_quantity=f'data.purity#{target_schema}',
                selected=True,
                label='Purity (%)',
                format=Format(decimals=5),
            ),
            Column(
                search_quantity=f'data.main_material#{target_schema}',
                selected=True,
                label='Material',
            ),
            Column(
                search_quantity=f'data.supplier_id#{target_schema}',
                selected=True,
                label='Supplier',
            ),
            Column(
                search_quantity=f'data.refill_or_mounting_date#{target_schema}',
                selected=True,
                label='Refill or mounting date',
            ),
            Column(
                search_quantity=f'data.thickness#{target_schema}',
                selected=True,
                label='Thickness',
                unit='mm',
                format=Format(decimals=1),
            ),
        ],
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
