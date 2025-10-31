import yaml
from nomad.config.models.plugins import AppEntryPoint
from nomad.config.models.ui import (
    App,
    Axis,
    Column,
    Filters,
    Format,
    Menu,
    MenuItemHistogram,
    MenuItemPeriodicTable,
    MenuItemTerms,
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
                search_quantity=(
                    f'data.deposition_parameters.deposition_temperature#{schema}'
                ),
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
            Column(
                search_quantity=f'data.deposition_parameters.n2_flow#{schema}',
                selected=True,
                label='N2 flow',
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
                MenuItemTerms(
                    search_quantity='authors.name',
                    show_input=True,
                ),
            ],
        ),
        filters_locked={
            'entry_type': 'DTUSputtering',
        },
        dashboard={
            'widgets': [
                {
                    'type': 'histogram',
                    'title': 'Deposition temperature',
                    'show_input': False,
                    'autorange': False,
                    'nbins': 30,
                    'y': {
                        'scale': 'linear',
                    },
                    'x': {
                        'search_quantity': (
                            f'data.deposition_parameters.deposition_temperature#{schema}'
                        ),
                        'unit': 'degree_Celsius',
                        'title': 'Deposition temperature',
                    },
                    'layout': {
                        'xxl': {
                            'minH': 3,
                            'minW': 3,
                            'h': 4,
                            'w': 18,
                            'y': 0,
                            'x': 0,
                        },
                        'xl': {
                            'minH': 3,
                            'minW': 3,
                            'h': 3,
                            'w': 15,
                            'y': 0,
                            'x': 0,
                        },
                        'lg': {
                            'minH': 3,
                            'minW': 3,
                            'h': 3,
                            'w': 12,
                            'y': 0,
                            'x': 0,
                        },
                        'md': {
                            'minH': 3,
                            'minW': 6,
                            'h': 3,
                            'w': 9,
                            'y': 0,
                            'x': 0,
                        },
                        'sm': {
                            'minH': 3,
                            'minW': 6,
                            'h': 3,
                            'w': 6,
                            'y': 0,
                            'x': 0,
                        },
                    },
                },
                {
                    'type': 'histogram',
                    'title': 'Deposition time',
                    'show_input': False,
                    'autorange': False,
                    'nbins': 30,
                    'y': {
                        'scale': 'linear',
                    },
                    'x': {
                        'search_quantity': (
                            f'data.deposition_parameters.deposition_time#{schema}'
                        ),
                        'unit': 'minute',
                        'title': 'Deposition time',
                    },
                    'layout': {
                        'xxl': {
                            'minH': 3,
                            'minW': 3,
                            'h': 4,
                            'w': 18,
                            'y': 0,
                            'x': 18,
                        },
                        'xl': {
                            'minH': 3,
                            'minW': 3,
                            'h': 3,
                            'w': 15,
                            'y': 0,
                            'x': 15,
                        },
                        'lg': {
                            'minH': 3,
                            'minW': 3,
                            'h': 3,
                            'w': 12,
                            'y': 0,
                            'x': 12,
                        },
                        'md': {
                            'minH': 3,
                            'minW': 6,
                            'h': 3,
                            'w': 9,
                            'y': 0,
                            'x': 9,
                        },
                        'sm': {
                            'minH': 3,
                            'minW': 6,
                            'h': 3,
                            'w': 6,
                            'y': 0,
                            'x': 6,
                        },
                    },
                },
            ]
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


xrd_schema = 'nomad_dtu_nanolab_plugin.schema_packages.xrd.DTUXRDMeasurement'

xrd = AppEntryPoint(
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
        columns=[
            Column(
                search_quantity=f'data.lab_id#{xrd_schema}',
                selected=True,
                label='XRD ID',
            ),
            Column(
                search_quantity=f'data.xrd_settings.source.xray_tube_voltage#{xrd_schema}',
                selected=True,
                label='X-ray tube voltage',
                unit='kV',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.xrd_settings.source.xray_tube_current#{xrd_schema}',
                selected=True,
                label='X-ray tube current',
                unit='mA',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity='main_author.name',
                selected=True,
                label='Main author',
            ),
        ],
        menu=Menu(
            size=MenuSizeEnum.MD,
            items=[
                MenuItemTerms(
                    title='Sample ID',
                    search_quantity=f'data.samples.lab_id#{xrd_schema}',
                    show_input=True,
                ),
                MenuItemTerms(
                    search_quantity='authors.name',
                    show_input=True,
                ),
            ],
        ),
        filters_locked={
            'entry_type': 'DTUXRDMeasurement',
        },
    ),
)


edx_schema = 'nomad_dtu_nanolab_plugin.schema_packages.edx.EDXMeasurement'

edx = AppEntryPoint(
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
        columns=[
            Column(
                search_quantity=f'data.lab_id#{edx_schema}',
                selected=True,
                label='EDX ID',
            ),
            Column(
                search_quantity=f'data.avg_layer_thickness#{edx_schema}',
                selected=True,
                label='Average layer thickness',
                unit='nm',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity='main_author.name',
                selected=True,
                label='Main author',
            ),
        ],
        menu=Menu(
            size=MenuSizeEnum.XXL,
            items=[
                MenuItemPeriodicTable(
                    quantity=f'data.results.quantifications.element#{edx_schema}',
                ),
                MenuItemTerms(
                    title='Sample ID',
                    search_quantity=f'data.samples.lab_id#{edx_schema}',
                    show_input=True,
                ),
                MenuItemHistogram(
                    title='Average layer thickness',
                    x=Axis(
                        search_quantity=f'data.avg_layer_thickness#{edx_schema}',
                        scale='linear',
                        unit='nm',
                    ),
                ),
                MenuItemTerms(
                    search_quantity='authors.name',
                    show_input=True,
                ),
            ],
        ),
        filters_locked={
            'entry_type': 'EDXMeasurement',
        },
    ),
)


analysis_schema = 'nomad_dtu_nanolab_plugin.schema_packages.analysis.DtuJupyterAnalysis'

analysis = AppEntryPoint(
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
        columns=[
            Column(
                search_quantity=f'data.lab_id#{analysis_schema}',
                selected=True,
                label='Analysis ID',
            ),
            Column(
                search_quantity=f'data.notebook#{analysis_schema}',
                selected=True,
                label='Notebook',
            ),
            Column(
                search_quantity=f'data.datetime#{analysis_schema}',
                selected=True,
                label='Date and time',
            ),
            Column(
                search_quantity='main_author.name',
                selected=True,
                label='Main author',
            ),
        ],
        filters_locked={
            'entry_type': 'DtuJupyterAnalysis',
        },
    ),
)

combi_samples_schema = (
    'nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample'
)

samples = AppEntryPoint(
    name='Combinatorial sample app',
    description='App for searching the combinatorial samples.',
    app=App(
        label='Combinatorial Samples',
        path='combinatorial-samples',
        category='Samples',
        description="""
        Explore all the combinatorial samples with their aggregated properties.
        """,
        filters=Filters(
            include=[
                f'*#{combi_samples_schema}',
            ],
        ),
        columns=[
            Column(
                search_quantity=f'data.lab_id#{combi_samples_schema}',
                selected=True,
                label='Analysis ID',
            ),
            Column(
                search_quantity=f'data.deposition.material_space#{combi_samples_schema}',
                selected=True,
                label='Material space',
            ),
            Column(
                search_quantity=f'data.band_gap.value#{combi_samples_schema}',
                selected=True,
                label='Band gap',
                unit='eV',
                format=Format(decimals=2),
            ),
            Column(
                search_quantity=f'data.thickness.value#{combi_samples_schema}',
                selected=True,
                label='Thickness',
                unit='nm',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.absorption_coefficient.mean_absorption_above_edge#{combi_samples_schema}',
                selected=True,
                label='Absorption coefficient',
                unit='cm^-1',
                format=Format(decimals=1),
            ),
            Column(
                search_quantity=f'data.datetime#{combi_samples_schema}',
                selected=False,
                label='Date and time',
            ),
            Column(
                search_quantity='main_author.name',
                selected=False,
                label='Main author',
            ),
        ],
        menu=Menu(
            size=MenuSizeEnum.XS,
            items=[
                Menu(
                    title='Deposition',
                    size=MenuSizeEnum.XXL,
                    items=[
                        MenuItemTerms(
                            title='Material space',
                            search_quantity=(
                                f'data.deposition.material_space#{combi_samples_schema}'
                            ),
                            width=6,
                            options=10,
                            show_input=True,
                        ),
                        MenuItemTerms(
                            title='Operator',
                            search_quantity=(
                                f'data.deposition.operator#{combi_samples_schema}'
                            ),
                            width=6,
                            options=10,
                            show_input=True,
                        ),
                        MenuItemTerms(
                            title='Method',
                            search_quantity=(
                                f'data.deposition.method#{combi_samples_schema}'
                            ),
                            show_input=True,
                        ),
                        MenuItemHistogram(
                            title='Pressure',
                            x=Axis(
                                search_quantity=(
                                    f'data.deposition.pressure#{combi_samples_schema}'
                                ),
                                scale='linear',
                                unit='mbar',
                            ),
                        ),
                        MenuItemHistogram(
                            title='Temperature',
                            x=Axis(
                                search_quantity=(
                                    f'data.deposition.temperature#{combi_samples_schema}'
                                ),
                                scale='linear',
                                unit='degC',
                            ),
                        ),
                        MenuItemHistogram(
                            title='Time',
                            x=Axis(
                                search_quantity=(
                                    f'data.deposition.time#{combi_samples_schema}'
                                ),
                                scale='linear',
                                unit='minute',
                            ),
                        ),
                    ],
                ),
                Menu(
                    title='Composition',
                    size=MenuSizeEnum.XXL,
                    items=[
                        MenuItemPeriodicTable(
                            title='Elements',
                            quantity='results.material.elements',
                        ),
                        *[
                            MenuItemHistogram(
                                title=f'{element} atomic fraction',
                                x=Axis(
                                    search_quantity=(
                                        f'data.composition.{element}#'
                                        f'{combi_samples_schema}'
                                    ),
                                    scale='linear',
                                ),
                            )
                            for element in [
                                'O',
                                'S',
                                'P',
                                'Cu',
                                'Sn',
                                'N',
                                'In',
                                'Ba',
                                'Zr',
                                'Sb',
                                'Ag',
                            ]
                        ],
                    ],
                ),
                Menu(
                    title='Properties',
                    size=MenuSizeEnum.XXL,
                    items=[
                        MenuItemHistogram(
                            title='Band gap',
                            x=Axis(
                                search_quantity=(
                                    f'data.band_gap.value#{combi_samples_schema}'
                                ),
                                scale='linear',
                                unit='eV',
                            ),
                            width=9,
                        ),
                        MenuItemTerms(
                            title='Interpolation',
                            search_quantity=(
                                f'data.band_gap.interpolation#{combi_samples_schema}'
                            ),
                            width=3,
                            show_input=True,
                        ),
                        MenuItemHistogram(
                            title='Thickness',
                            x=Axis(
                                search_quantity=(
                                    f'data.thickness.value#{combi_samples_schema}'
                                ),
                                scale='linear',
                                unit='nm',
                            ),
                            width=9,
                        ),
                        MenuItemTerms(
                            title='Interpolation',
                            search_quantity=(
                                f'data.thickness.interpolation#{combi_samples_schema}'
                            ),
                            width=3,
                            show_input=True,
                        ),
                        MenuItemHistogram(
                            title='Absorption coefficient',
                            x=Axis(
                                search_quantity=(
                                    f'data.absorption_coefficient.mean_absorption_above'
                                    f'_edge#{combi_samples_schema}'
                                ),
                                scale='linear',
                                unit='cm^-1',
                            ),
                            width=9,
                        ),
                        MenuItemTerms(
                            title='Interpolation',
                            search_quantity=(
                                f'data.absorption_coefficient.interpolation#{combi_samples_schema}'
                            ),
                            width=3,
                            show_input=True,
                        ),
                    ],
                ),
            ],
        ),
        filters_locked={
            'entry_type': 'DTUCombinatorialSample',
        },
        dashboard={
            'widgets': yaml.safe_load(
                """
- type: scatter_plot
  autorange: true
  size: 10000
  markers:
    color:
      search_quantity: data.deposition.material_space#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
  y:
    search_quantity: data.composition.P#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
  x:
    search_quantity: data.composition.S#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
  title: Phosphosulfide space
  layout:
    xxl:
      minH: 3
      minW: 3
      h: 9
      w: 16
      y: 0
      x: 0
    xl:
      minH: 3
      minW: 3
      h: 9
      w: 13
      y: 0
      x: 0
    lg:
      minH: 3
      minW: 3
      h: 8
      w: 10
      y: 0
      x: 0
    md:
      minH: 3
      minW: 3
      h: 7
      w: 7
      y: 0
      x: 0
    sm:
      minH: 3
      minW: 3
      h: 6
      w: 8
      y: 0
      x: 0
- type: scatter_plot
  autorange: true
  size: 1000
  markers:
    color:
      search_quantity: data.deposition.temperature#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
      unit: degree_Celsius
      title: Deposition temperature
  y:
    search_quantity: data.thickness.value#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
    unit: nm
    title: Thickness
  x:
    search_quantity: data.deposition.time#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
    unit: minute
    title: Deposition time
  layout:
    xxl:
      minH: 3
      minW: 3
      h: 9
      w: 16
      y: 0
      x: 20
    xl:
      minH: 3
      minW: 3
      h: 9
      w: 13
      y: 0
      x: 17
    lg:
      minH: 3
      minW: 3
      h: 8
      w: 10
      y: 0
      x: 14
    md:
      minH: 3
      minW: 3
      h: 7
      w: 7
      y: 0
      x: 11
    sm:
      minH: 3
      minW: 3
      h: 3
      w: 12
      y: 6
      x: 0
- type: terms
  show_input: true
  scale: linear
  search_quantity: data.deposition.material_space#nomad_dtu_nanolab_plugin.schema_packages.sample.DTUCombinatorialSample
  layout:
    xxl:
      minH: 4
      minW: 4
      h: 9
      w: 4
      y: 0
      x: 13
    xl:
      minH: 4
      minW: 4
      h: 9
      w: 4
      y: 0
      x: 13
    lg:
      minH: 4
      minW: 4
      h: 8
      w: 4
      y: 0
      x: 10
    md:
      minH: 4
      minW: 4
      h: 7
      w: 4
      y: 0
      x: 7
    sm:
      minH: 4
      minW: 4
      h: 6
      w: 4
      y: 0
      x: 8
"""  # noqa: E501
            )
        },
    ),
)
