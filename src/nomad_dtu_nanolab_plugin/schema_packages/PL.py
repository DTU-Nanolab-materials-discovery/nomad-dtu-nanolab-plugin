from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import CompositeSystemReference
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)
from nomad_dtu_nanolab_plugin.ywf_reader import read_ywa_metadata, read_ywf

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive

m_package = Package(name='DTU PL measurement schema')


class PLMappingResult(MappingResult, PlotSection):
    m_def = Section()

    trace_id = Quantity(
        type=str,
        description='The trace identifier assigned by the YWafer software.',
    )
    wavelength = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='m',
        description='The wavelength axis of the PL spectrum.',
    )
    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='The detector intensity in the units recorded by YWafer.',
    )
    peak_lambda = Quantity(
        type=np.float64,
        unit='m',
        description='Wavelength at maximum measured intensity.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Peak wavelength',
        ),
    )
    peak_intensity = Quantity(
        type=np.float64,
        description='Maximum measured detector intensity.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Peak intensity',
        ),
    )
    signal_intensity = Quantity(
        type=np.float64,
        description='Integrated detector intensity over wavelength.',
    )
    peak_fwhm = Quantity(
        type=np.float64,
        unit='m',
        description='Full width at half maximum of the measured peak.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Peak FWHM',
        ),
    )

    def plot_spectrum(self) -> None:
        if self.wavelength is None or self.intensity is None:
            return

        figure = go.Figure(
            go.Scatter(
                x=self.wavelength.to('nm').magnitude,
                y=self.intensity,
                mode='lines',
                name=self.trace_id or self.name,
            )
        )
        figure.update_layout(
            title=self.trace_id or self.name or 'PL spectrum',
            xaxis_title='Wavelength (nm)',
            yaxis_title='Intensity',
            template='plotly_white',
            hovermode='closest',
        )
        plot_json = figure.to_plotly_json()
        plot_json['config'] = {'scrollZoom': False}
        self.figures = [
            PlotlyFigure(label=self.trace_id or 'PL spectrum', figure=plot_json)
        ]

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        self.plot_spectrum()


class PLMetadata(ArchiveSection):
    m_def = Section(
        label='PL acquisition metadata',
        description=(
            'Measurement and instrument settings extracted from the YWafer file.'
        ),
    )

    software_version = Quantity(
        type=str,
        description='YWafer version recorded in the native measurement file.',
    )
    measurement_setup = Quantity(
        type=str,
        description='Acquisition setup string recorded by YWafer.',
    )
    excitation_source = Quantity(
        type=str,
        description='Excitation source identifier from the measurement setup.',
    )
    excitation_wavelength = Quantity(
        type=np.float64,
        unit='m',
        description='Excitation wavelength parsed from the source identifier.',
    )
    laser_power = Quantity(
        type=np.float64,
        unit='W',
        description='Excitation power recorded by YWafer.',
    )
    laser_power_percentage = Quantity(
        type=np.float64,
        unit='%',
        description='Laser output as a percentage of maximum power.',
    )
    integration_time = Quantity(
        type=np.float64,
        unit='s',
        description='Integration time per accumulation.',
    )
    accumulations = Quantity(
        type=int,
        description='Number of accumulations for each saved trace.',
    )
    wavelength_range = Quantity(
        type=np.float64,
        shape=[2],
        unit='m',
        description='Configured detector wavelength range.',
    )
    lot_id = Quantity(
        type=str,
        description='Lot identifier recorded in the YWafer overview file.',
    )
    wafer_number = Quantity(
        type=str,
        description='Wafer number recorded in the YWafer overview file.',
    )
    chamber = Quantity(
        type=str,
        description='Measurement chamber recorded in the YWafer overview file.',
    )
    scan_pitch = Quantity(
        type=np.float64,
        shape=[2],
        unit='m',
        description='X and Y scan pitch recorded in the YWafer overview file.',
    )
    scan_center = Quantity(
        type=np.float64,
        shape=[2],
        unit='m',
        description='X and Y scan center recorded in the YWafer overview file.',
    )
    wafer_radius = Quantity(
        type=np.float64,
        unit='m',
        description='Wafer radius recorded in the YWafer overview file.',
    )
    edge_exclusion = Quantity(
        type=np.float64,
        unit='m',
        description='Wafer edge exclusion recorded in the YWafer overview file.',
    )
    wafer_flat_angle = Quantity(
        type=np.float64,
        unit='deg',
        description='Wafer flat angle recorded in the YWafer overview file.',
    )
    data_type = Quantity(
        type=str,
        description='YWafer map data type recorded in the overview file.',
    )
    detector = Quantity(
        type=str,
        description='Detector identifier recorded in the native file.',
    )
    emission_filter = Quantity(
        type=str,
        description='Emission filter identifier recorded in the native file.',
    )


class DTUPLMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        links=['http://purl.obolibrary.org/obo/CHMO_0000773'],
        label='PL Measurement',
    )
    pl_data_file = Quantity(
        type=str,
        description=(
            'Native YSystems YWafer .ywf measurement file. Spectra, stage positions, '
            'and acquisition metadata are extracted automatically.'
        ),
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
            label='YWafer measurement file (.ywf)',
        ),
    )
    pl_overview_file = Quantity(
        type=str,
        description=(
            'Optional YWafer .ywa overview file with wafer geometry and scan settings.'
        ),
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
            label='YWafer overview file (.ywa)',
        ),
    )
    metadata = SubSection(
        section_def=PLMetadata,
        description='Acquisition metadata extracted from the native YWafer file.',
    )
    results = SubSection(
        section_def=PLMappingResult,
        description='Saved PL spectra and their measurement positions.',
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=RectangularSampleAlignment,
        description='Automatically determined alignment from the sample geometry.',
    )

    def add_pl_sample_references(
        self,
        filename: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        from nomad.datamodel.context import ServerContext

        filename = filename.replace('\\', '/').rsplit('/', 1)[-1]
        sample_prefix = filename.split('--', 1)[0].rsplit('.', 1)[0]
        sample_prefix = '_'.join(sample_prefix.split('_')[:3])
        if not sample_prefix:
            logger.warning('Could not determine PL sample prefix from: %s', filename)
            return

        if not isinstance(archive.m_context, ServerContext):
            self.samples = [CompositeSystemReference(lab_id=sample_prefix)]
            return

        from nomad.search import MetadataPagination, Q, search

        query = Q(
            'bool',
            should=[
                Q('term', **{'results.eln.lab_ids': sample_prefix}),
                Q('prefix', **{'results.eln.lab_ids': f'{sample_prefix}_'}),
            ],
            minimum_should_match=1,
        )
        page_size = 100
        user_id = getattr(
            getattr(archive.metadata, 'main_author', None), 'user_id', None
        )
        first_page = search(
            owner='all',
            query=query,
            pagination=MetadataPagination(page_size=page_size, page=1),
            user_id=user_id,
        )
        total = first_page.pagination.total
        entries = list(first_page.data)
        page_count = (total + page_size - 1) // page_size
        for page in range(2, page_count + 1):
            result = search(
                owner='all',
                query=query,
                pagination=MetadataPagination(page_size=page_size, page=page),
                user_id=user_id,
            )
            entries.extend(result.data)

        references = []
        seen_entry_ids = set()
        for entry in entries:
            entry_id = entry.get('entry_id')
            upload_id = entry.get('upload_id')
            lab_ids = entry.get('results', {}).get('eln', {}).get('lab_ids', [])
            if isinstance(lab_ids, str):
                lab_ids = [lab_ids]
            matching_lab_id = next(
                (
                    lab_id
                    for lab_id in lab_ids
                    if lab_id == sample_prefix or lab_id.startswith(f'{sample_prefix}_')
                ),
                None,
            )
            if (
                not entry_id
                or not upload_id
                or matching_lab_id is None
                or entry_id in seen_entry_ids
            ):
                continue
            seen_entry_ids.add(entry_id)
            references.append(
                CompositeSystemReference(
                    name=matching_lab_id,
                    lab_id=matching_lab_id,
                    reference=f'../uploads/{upload_id}/archive/{entry_id}#data',
                )
            )

        self.samples = references
        if not references:
            logger.warning(
                'No samples found with the first three name parts %s.',
                sample_prefix,
            )

    def write_pl_data(
        self,
        parsed_data: dict[str, Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        metadata = parsed_data['metadata']
        wavelength_range = metadata.get('wavelength_range_nm')
        pl_metadata = PLMetadata(
            software_version=metadata.get('software_version'),
            measurement_setup=metadata.get('measurement_setup'),
            excitation_source=metadata.get('excitation_source'),
            excitation_wavelength=(
                ureg.Quantity(metadata['excitation_wavelength_nm'], 'nm')
                if 'excitation_wavelength_nm' in metadata
                else None
            ),
            laser_power=(
                ureg.Quantity(metadata['laser_power_mw'], 'mW')
                if 'laser_power_mw' in metadata
                else None
            ),
            laser_power_percentage=metadata.get('laser_power_percentage'),
            integration_time=(
                ureg.Quantity(metadata['integration_time_ms'] / 1000, 's')
                if 'integration_time_ms' in metadata
                else None
            ),
            accumulations=metadata.get('accumulations'),
            wavelength_range=(
                ureg.Quantity(wavelength_range, 'nm')
                if wavelength_range is not None
                else None
            ),
            detector=metadata.get('detector'),
            emission_filter=metadata.get('emission_filter'),
            lot_id=metadata.get('lot_id'),
            wafer_number=metadata.get('wafer_number'),
            chamber=metadata.get('chamber'),
            scan_pitch=(
                ureg.Quantity(metadata['scan_pitch_mm'], 'mm')
                if 'scan_pitch_mm' in metadata
                else None
            ),
            scan_center=(
                ureg.Quantity(metadata['scan_center_mm'], 'mm')
                if 'scan_center_mm' in metadata
                else None
            ),
            wafer_radius=(
                ureg.Quantity(metadata['wafer_radius_mm'], 'mm')
                if 'wafer_radius_mm' in metadata
                else None
            ),
            edge_exclusion=(
                ureg.Quantity(metadata['edge_exclusion_mm'], 'mm')
                if 'edge_exclusion_mm' in metadata
                else None
            ),
            wafer_flat_angle=(
                ureg.Quantity(metadata['wafer_flat_angle_deg'], 'deg')
                if 'wafer_flat_angle_deg' in metadata
                else None
            ),
            data_type=metadata.get('data_type'),
        )
        pl_metadata.normalize(archive, logger)
        self.metadata = pl_metadata

        results = []
        for trace in parsed_data['traces']:
            wavelength_nm = trace['wavelength_nm']
            intensity = trace['intensity']
            result = PLMappingResult(
                trace_id=trace['name'],
                x_absolute=ureg.Quantity(trace['x'], 'mm'),
                y_absolute=ureg.Quantity(trace['y'], 'mm'),
            )
            if wavelength_nm is not None and intensity is not None:
                wavelength_nm = np.asarray(wavelength_nm, dtype=np.float64)
                intensity = np.asarray(intensity, dtype=np.float64)
                result.wavelength = ureg.Quantity(wavelength_nm, 'nm')
                result.intensity = intensity

                peak_index = int(np.argmax(intensity))
                result.peak_lambda = ureg.Quantity(wavelength_nm[peak_index], 'nm')
                result.peak_intensity = float(intensity[peak_index])
                result.signal_intensity = float(
                    np.sum(
                        (intensity[:-1] + intensity[1:]) * np.diff(wavelength_nm) / 2
                    )
                )
                half_maximum = intensity[peak_index] / 2
                above_half_maximum = np.flatnonzero(intensity >= half_maximum)
                if len(above_half_maximum) > 1:
                    result.peak_fwhm = ureg.Quantity(
                        wavelength_nm[above_half_maximum[-1]]
                        - wavelength_nm[above_half_maximum[0]],
                        'nm',
                    )
            result.normalize(archive, logger)
            results.append(result)
        self.results = results

    def plot(self) -> None:
        spectra = [
            result
            for result in self.results or []
            if result.wavelength is not None and result.intensity is not None
        ]
        if spectra:
            figure = go.Figure()
            for result in spectra:
                figure.add_trace(
                    go.Scatter(
                        x=result.wavelength.to('nm').magnitude,
                        y=result.intensity,
                        mode='lines',
                        name=result.name or result.trace_id,
                    )
                )
            figure.update_layout(
                title='Photoluminescence spectra',
                xaxis_title='Wavelength (nm)',
                yaxis_title='Intensity',
                template='plotly_white',
                hovermode='closest',
            )
            plot_json = figure.to_plotly_json()
            plot_json['config'] = {'scrollZoom': False}
            self.figures.append(PlotlyFigure(label='PL spectra', figure=plot_json))

        positioned = [
            result
            for result in spectra
            if result.x_absolute is not None
            and result.y_absolute is not None
            and result.peak_lambda is not None
        ]
        if positioned:
            has_relative_positions = all(
                result.x_relative is not None and result.y_relative is not None
                for result in positioned
            )
            position_label = (
                'Sample position' if has_relative_positions else 'Stage position'
            )
            if has_relative_positions:
                x_positions = [
                    result.x_relative.to('mm').magnitude for result in positioned
                ]
                y_positions = [
                    result.y_relative.to('mm').magnitude for result in positioned
                ]
            else:
                x_positions = [
                    result.x_absolute.to('mm').magnitude for result in positioned
                ]
                y_positions = [
                    result.y_absolute.to('mm').magnitude for result in positioned
                ]
            figure = go.Figure(
                go.Scatter(
                    x=x_positions,
                    y=y_positions,
                    mode='markers',
                    marker={
                        'size': 14,
                        'color': [
                            result.peak_lambda.to('nm').magnitude
                            for result in positioned
                        ],
                        'colorscale': 'Viridis',
                        'showscale': True,
                        'colorbar': {'title': 'Peak wavelength (nm)'},
                    },
                    text=[result.trace_id for result in positioned],
                    hovertemplate=(
                        '%{text}<br>X: %{x:.3f} mm<br>Y: %{y:.3f} mm'
                        '<br>Peak wavelength: %{marker.color:.2f} nm<extra></extra>'
                    ),
                )
            )
            figure.update_layout(
                title='PL peak wavelength map',
                xaxis_title=f'X {position_label.lower()} (mm)',
                yaxis_title=f'Y {position_label.lower()} (mm)',
                template='plotly_white',
                hovermode='closest',
            )
            plot_json = figure.to_plotly_json()
            plot_json['config'] = {'scrollZoom': False}
            self.figures.append(PlotlyFigure(label='PL peak map', figure=plot_json))

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        if self.location is None:
            self.location = 'DTU Nanolab PL measurement'

        if self.pl_data_file:
            self.add_pl_sample_references(self.pl_data_file, archive, logger)
            with archive.m_context.raw_file(self.pl_data_file, 'rb') as file:
                parsed_data = read_ywf(file.read())
            if self.pl_overview_file:
                with archive.m_context.raw_file(self.pl_overview_file, 'rb') as file:
                    parsed_data['metadata'].update(read_ywa_metadata(file.read()))
            self.write_pl_data(parsed_data, archive, logger)

            if self.sample_alignment is None:
                self.around_barycenter = True
        else:
            logger.warning('Upload a native YWafer .ywf file to extract PL data.')

        super().normalize(archive, logger)
        self.figures = []
        self.plot()


m_package.__init_metainfo__()
