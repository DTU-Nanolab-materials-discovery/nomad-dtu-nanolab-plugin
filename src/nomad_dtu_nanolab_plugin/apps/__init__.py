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


xrd_schema = 'nomad_dtu_nanolab_plugin.schema_packages.xrd.DTUXRDMeasurement'

sputtering_targets = AppEntryPoint(
    name='XRD app',
    description='App for searching the XRD measurements.',
    app=App(
        label='XRD Measurements',
        path='xrd-measurements',
        category='Activities',
        description="""
        Explore the different measurements.
        """,
        filters=Filters(
            include=[
                f'*#{xrd_schema}',
            ],
        ),
        columns=Columns(
            selected=[
                f'data.lab_id#{xrd_schema}',
                f'data.xrd_settings.source.xray_tube_voltage#{xrd_schema}',
                f'data.xrd_settings.source.xray_tube_current#{xrd_schema}',
                f'metadata.main_author#{xrd_schema}',

            ],
            options={
                f'data.lab_id#{xrd_schema}': Column(
                    label='Measurement ID',
                ),
                f'data.xrd_settings.source.xray_tube_voltage#{xrd_schema}': Column(
                    label='X-ray tube voltage',
                    unit='kV',
                ),
                f'data.xrd_settings.source.xray_tube_current#{xrd_schema}': Column(
                    label='X-ray tube current',
                    unit='mA',
                ),
                f'metadata.main_author#{xrd_schema}': Column(
                    label='Main author',
                )
            },
        ),
        menu=Menu(
        ),
        filters_locked={
            'entry_type': 'DTUXRDMeasurement',
        },
    ),
)


edx_schema = 'nomad_dtu_nanolab_plugin.schema_packages.edx.EDXMeasurement'

sputtering_targets = AppEntryPoint(
    name='EDX app',
    description='App for searching the EDX measurements.',
    app=App(
        label='EDX Measurements',
        path='edx-measurements',
        category='Activities',
        description="""
        Explore the different measurements.
        """,
        filters=Filters(
            include=[
                f'*#{edx_schema}',
            ],
        ),
        columns=Columns(
            selected=[
                f'data.lab_id#{edx_schema}',
                f'data.samples.0.lab_id#{edx_schema}',
                f'data.avg_layer_thickness#{edx_schema}',
                f'metadata.main_author#{edx_schema}',

            ],
            options={
                f'data.lab_id#{edx_schema}': Column(
                    label='Measurement ID',
                ),
                f'data.samples.0.lab_id#{edx_schema}': Column(
                    label='Sample ID',
                ),
                f'data.avg_layer_thickness#{edx_schema}': Column(
                    label='Average layer thickness',
                    unit='nm',
                ),
                f'metadata.main_author#{edx_schema}': Column(
                    label='Main author',
                )
            },
        ),
        menu=Menu(
        ),
        filters_locked={
            'entry_type': 'EDXMeasurement',
        },
    ),
)


analysis_schema = 'nomad_dtu_nanolab_plugin.schema_packages.analysis.DtuJupiterAnalysis'

sputtering_targets = AppEntryPoint(
    name='Analysis app',
    description='App for searching the performed analysis.',
    app=App(
        label='Analysis',
        path='analysis',
        category='Activities',
        description="""
        Explore the different Jupyter Notebooks and analysis results.
        """,
        filters=Filters(
            include=[
                f'*#{analysis_schema}',
            ],
        ),
        columns=Columns(
            selected=[
                f'data.name#{analysis_schema}',
                f'data.notebook#{analysis_schema}',
                f'data.datetime#{analysis_schema}',
                f'metadata.main_author#{analysis_schema}',

            ],
            options={
                f'data.name#{analysis_schema}': Column(
                    label='Measurement ID',
                ),
                f'data.notebook#{analysis_schema}': Column(
                    label='Notebook',
                ),
                f'data.datetime#{analysis_schema}': Column(
                    label='Date and time',
                ),
                f'metadata.main_author#{analysis_schema}': Column(
                    label='Main author',
                )
            },
        ),
        menu=Menu(
        ),
        filters_locked={
            'entry_type': 'EDXMeasurement',
        },
    ),
)