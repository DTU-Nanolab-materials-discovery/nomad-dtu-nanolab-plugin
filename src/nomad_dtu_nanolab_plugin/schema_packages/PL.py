import re
from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from plotly.colors import sample_colorscale
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)
from nomad_dtu_nanolab_plugin.schema_packages.sample import DtuLibraryReference
from nomad_dtu_nanolab_plugin.ywf_reader import read_ywa_metadata, read_ywf

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive

m_package = Package(name='DTU PL measurement schema')
PL_SAMPLE_NAME_PARTS = 4
PL_SAMPLE_QUANTITY_ORDER = [
    'name',
    'reference',
    'lab_id',
    'measurement_x_max',
    'measurement_x_min',
    'measurement_y_max',
    'measurement_y_min',
    'position_top_left_x',
    'position_top_left_y',
    'rotation',
]


class PLMappingResult(MappingResult, PlotSection):
    m_def = Section()

    samples = SubSection(
        section_def=DtuLibraryReference,
        description='Combinatorial libraries assigned to this measurement position.',
        repeats=True,
    )
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


class PLSampleReference(DtuLibraryReference):
    m_def = Section(
        label='PL sample',
        description='A combinatorial library measured by this PL measurement.',
        a_eln=ELNAnnotation(
            properties=SectionProperties(order=PL_SAMPLE_QUANTITY_ORDER)
        ),
    )

    measurement_x_max = Quantity(
        type=np.float64,
        unit='m',
        description='Maximum stage X position detected in the measurement file.',
        a_eln=ELNAnnotation(label='X max', defaultDisplayUnit='cm'),
    )
    measurement_x_min = Quantity(
        type=np.float64,
        unit='m',
        description='Minimum stage X position detected in the measurement file.',
        a_eln=ELNAnnotation(label='X min', defaultDisplayUnit='cm'),
    )
    measurement_y_max = Quantity(
        type=np.float64,
        unit='m',
        description='Maximum stage Y position detected in the measurement file.',
        a_eln=ELNAnnotation(label='Y max', defaultDisplayUnit='cm'),
    )
    measurement_y_min = Quantity(
        type=np.float64,
        unit='m',
        description='Minimum stage Y position detected in the measurement file.',
        a_eln=ELNAnnotation(label='Y min', defaultDisplayUnit='cm'),
    )
    position_top_left_x = Quantity(
        type=np.float64,
        unit='m',
        description='Stage X coordinate of the library top-left corner.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
            label='Top-left X',
        ),
    )
    position_top_left_y = Quantity(
        type=np.float64,
        unit='m',
        description='Stage Y coordinate of the library top-left corner.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
            label='Top-left Y',
        ),
    )
    rotation = Quantity(
        type=np.float64,
        unit='rad',
        description='Counterclockwise rotation of the library in the stage plane.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
            label='Sample rotation',
        ),
    )


class DTUPLMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        links=['http://purl.obolibrary.org/obo/CHMO_0000773'],
        label='PL Measurement',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'pl_data_file',
                    'pl_overview_file',
                    'around_barycenter',
                    'datetime',
                    'lab_id',
                    'location',
                    'description',
                    'samples',
                    'results',
                    'sample_alignment',
                    'metadata',
                    'instruments',
                    'figures',
                ],
                visible=Filter(exclude=['steps']),
            )
        ),
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
    samples = SubSection(
        section_def=PLSampleReference,
        description='Combinatorial libraries measured in this PL measurement.',
        repeats=True,
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
        name_parts = re.split(r'_+|--', filename.rsplit('.', 1)[0])
        library_name = (
            '_'.join(name_parts[:PL_SAMPLE_NAME_PARTS])
            if len(name_parts) >= PL_SAMPLE_NAME_PARTS
            else None
        )
        entry = None
        if isinstance(archive.m_context, ServerContext) and library_name:
            from nomad.search import MetadataPagination, Q, search

            user_id = getattr(
                getattr(archive.metadata, 'main_author', None), 'user_id', None
            )
            result = search(
                owner='all',
                query=Q('term', **{'results.eln.lab_ids': library_name}),
                pagination=MetadataPagination(page_size=1),
                user_id=user_id,
            )
            if result.pagination.total == 1:
                entry = next(iter(result.data), None)

        if entry:
            lab_ids = entry.get('results', {}).get('eln', {}).get('lab_ids') or []
            if isinstance(lab_ids, str):
                lab_ids = [lab_ids]
            if (
                entry.get('entry_id')
                and entry.get('upload_id')
                and library_name in lab_ids
            ):
                sample = next(
                    (
                        item
                        for item in self.samples or []
                        if item.lab_id == library_name
                    ),
                    PLSampleReference(),
                )
                sample.name = library_name
                sample.lab_id = library_name
                sample.reference = (
                    f'../uploads/{entry["upload_id"]}/archive/{entry["entry_id"]}#data'
                )
                self.samples = [sample]
                self._set_sample_measurement_ranges()
                self._assign_result_samples()
                return

        self._set_sample_measurement_ranges()
        self._assign_result_samples()
        if self.samples:
            if self._manual_samples_cover_measurement():
                self.around_barycenter = False
                self._set_sample_alignment_from_library_position(archive, logger)
            else:
                logger.warning(
                    'Assigned sample positions and library geometries do not cover '
                    'every PL measurement point; processing will continue.'
                )
            return

        raise ValueError(
            f'Could not uniquely match a library named "{library_name or "<invalid>"}" '
            f'to {filename}. Add each combinatorial library in Samples and enter '
            'its top-left position and rotation.'
        )

    def _set_sample_measurement_ranges(self) -> None:
        points = [
            (
                result.x_absolute.to('m').magnitude,
                result.y_absolute.to('m').magnitude,
            )
            for result in self.results or []
            if result.x_absolute is not None and result.y_absolute is not None
        ]
        if not points:
            return
        x_values, y_values = zip(*points, strict=True)
        for sample in self.samples or []:
            sample.measurement_x_max = max(x_values)
            sample.measurement_x_min = min(x_values)
            sample.measurement_y_max = max(y_values)
            sample.measurement_y_min = min(y_values)

    def _manual_samples_cover_measurement(self) -> bool:
        samples = self.samples or []
        if not samples or not self.results:
            return False
        if not all(
            result.x_absolute is not None and result.y_absolute is not None
            for result in self.results
        ):
            return False
        return all(
            any(
                self._sample_contains_position(
                    sample,
                    result.x_absolute.to('m').magnitude,
                    result.y_absolute.to('m').magnitude,
                )
                for sample in samples
            )
            for result in self.results
        )

    @staticmethod
    def _sample_geometry_dimensions(
        sample: PLSampleReference,
    ) -> tuple[float, float] | None:
        library = getattr(sample, 'reference', None)
        geometry = getattr(library, 'geometry', None)
        if geometry is None:
            substrate_reference = getattr(library, 'substrate', None)
            substrate = getattr(substrate_reference, 'reference', None)
            geometry = getattr(substrate, 'geometry', None)
        width = getattr(geometry, 'width', None)
        length = getattr(geometry, 'length', None)
        if width is None or length is None:
            return None
        width_m = width.to('m').magnitude if hasattr(width, 'to') else float(width)
        length_m = length.to('m').magnitude if hasattr(length, 'to') else float(length)
        return width_m, length_m

    def _sample_corners(
        self, sample: PLSampleReference
    ) -> list[tuple[float, float]] | None:
        if (
            sample.position_top_left_x is None
            or sample.position_top_left_y is None
            or sample.rotation is None
        ):
            return None
        dimensions = self._sample_geometry_dimensions(sample)
        if dimensions is None:
            return None
        width, length = dimensions
        x = sample.position_top_left_x.to('m').magnitude
        y = sample.position_top_left_y.to('m').magnitude
        angle = sample.rotation.to('rad').magnitude
        cosine, sine = np.cos(angle), np.sin(angle)
        return [
            (x, y),
            (x + width * cosine, y + width * sine),
            (
                x + width * cosine + length * sine,
                y + width * sine - length * cosine,
            ),
            (x + length * sine, y - length * cosine),
        ]

    def _sample_contains_position(
        self, sample: PLSampleReference, x: float, y: float
    ) -> bool:
        corners = self._sample_corners(sample)
        if corners is None:
            return False
        inside = False
        previous_x, previous_y = corners[-1]
        for current_x, current_y in corners:
            cross = (x - previous_x) * (current_y - previous_y) - (y - previous_y) * (
                current_x - previous_x
            )
            if (
                np.isclose(cross, 0, atol=1e-12)
                and min(previous_x, current_x) <= x <= max(previous_x, current_x)
                and min(previous_y, current_y) <= y <= max(previous_y, current_y)
            ):
                return True
            if (current_y > y) != (previous_y > y) and x < (
                (previous_x - current_x) * (y - current_y) / (previous_y - current_y)
                + current_x
            ):
                inside = not inside
            previous_x, previous_y = current_x, current_y
        return inside

    def _assign_result_samples(self) -> None:
        for result in self.results or []:
            if result.x_absolute is None or result.y_absolute is None:
                continue
            matching_samples = [
                sample
                for sample in self.samples or []
                if self._sample_contains_position(
                    sample,
                    result.x_absolute.to('m').magnitude,
                    result.y_absolute.to('m').magnitude,
                )
            ]
            if not matching_samples and len(self.samples or []) == 1:
                matching_samples = self.samples
            result.samples = [
                DtuLibraryReference(
                    name=sample.name,
                    lab_id=sample.lab_id,
                    reference=sample.reference,
                )
                for sample in matching_samples
            ]

    def _set_sample_alignment_from_library_position(
        self, archive: 'EntryArchive', logger: 'BoundLogger'
    ) -> None:
        if len(self.samples or []) == 1 and self.sample_alignment is None:
            sample = self.samples[0]
            dimensions = self._sample_geometry_dimensions(sample)
            corners = self._sample_corners(sample)
            if dimensions is None or corners is None:
                return
            width, length = dimensions
            x0, y0 = corners[0]
            x2, y2 = corners[2]
            alignment = RectangularSampleAlignment(
                width=width,
                height=length,
                x_upper_left=x0,
                y_upper_left=y0,
                x_lower_right=x2,
                y_lower_right=y2,
            )
            alignment.normalize(archive, logger)
            self.sample_alignment = alignment

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

        self.plot_sample_positions()

    def plot_sample_positions(self) -> None:
        positioned = [
            result
            for result in self.results or []
            if result.x_absolute is not None and result.y_absolute is not None
        ]
        if not positioned:
            return

        figure = go.Figure()
        samples = self.samples or []
        colors = sample_colorscale(
            'Turbo',
            [index / max(len(samples) - 1, 1) for index in range(len(samples))],
        )
        for index, sample in enumerate(samples):
            corners = self._sample_corners(sample)
            if corners is None:
                continue
            color = colors[index]
            red, green, blue = color.removeprefix('rgb(').removesuffix(')').split(',')
            fillcolor = f'rgba({red}, {green}, {blue}, 0.12)'
            label = sample.name or sample.lab_id or f'Library {index + 1}'
            x_corners, y_corners = zip(*corners, strict=True)
            figure.add_trace(
                go.Scatter(
                    x=[*x_corners, x_corners[0]],
                    y=[*y_corners, y_corners[0]],
                    mode='lines',
                    fill='toself',
                    fillcolor=fillcolor,
                    line={'color': color},
                    name=label,
                    hoverinfo='name',
                )
            )
            figure.add_trace(
                go.Scatter(
                    x=[sum(x_corners) / len(x_corners)],
                    y=[sum(y_corners) / len(y_corners)],
                    mode='text',
                    text=[label],
                    textposition='middle center',
                    textfont={'color': color, 'size': 12},
                    showlegend=False,
                    hoverinfo='skip',
                )
            )
        figure.add_trace(
            go.Scatter(
                x=[result.x_absolute.to('mm').magnitude for result in positioned],
                y=[result.y_absolute.to('mm').magnitude for result in positioned],
                mode='markers',
                marker={'color': '#111111', 'size': 8},
                text=[result.trace_id for result in positioned],
                name='Measurement points',
                hovertemplate=(
                    '%{text}<br>X: %{x:.3f} mm<br>Y: %{y:.3f} mm<extra></extra>'
                ),
            )
        )
        figure.update_layout(
            title='PL sample regions and measurement points',
            xaxis_title='Stage X (mm)',
            yaxis_title='Stage Y (mm)',
            template='plotly_white',
            hovermode='closest',
        )
        plot_json = figure.to_plotly_json()
        plot_json['config'] = {'scrollZoom': False}
        self.figures.append(PlotlyFigure(label='PL sample positions', figure=plot_json))

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        if self.location is None:
            self.location = 'DTU Nanolab PL measurement'

        if self.pl_data_file:
            with archive.m_context.raw_file(self.pl_data_file, 'rb') as file:
                parsed_data = read_ywf(file.read())
            if self.pl_overview_file:
                with archive.m_context.raw_file(self.pl_overview_file, 'rb') as file:
                    parsed_data['metadata'].update(read_ywa_metadata(file.read()))
            self.write_pl_data(parsed_data, archive, logger)
            self._set_sample_measurement_ranges()
            self.figures = []
            self.plot()
            self.add_pl_sample_references(self.pl_data_file, archive, logger)

            if self.sample_alignment is None and not any(
                self._sample_corners(sample) is not None
                for sample in self.samples or []
            ):
                self.around_barycenter = True
        else:
            logger.warning('Upload a native YWafer .ywf file to extract PL data.')

        super().normalize(archive, logger)
        self.figures = []
        self.plot()


m_package.__init_metainfo__()
