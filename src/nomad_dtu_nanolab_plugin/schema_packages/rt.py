import os
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Experiment,
    ExperimentStep,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from nomad_measurements.utils import create_archive

from nomad_dtu_nanolab_plugin import autosampler_reader
from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU RT measurement schema')


def _resolve_library_target(
    archive: 'EntryArchive', logger: 'BoundLogger', library_lab_id: str
) -> tuple[str | None, str, str]:
    """Resolve upload and writable raw folder for the library lab_id.

    Returns a tuple of:
    1) target upload id (or None if unresolved),
    2) writable raw folder path relative to the target upload,
    3) archive-style folder reference for logging/debugging.
    """
    default_folder = str(PurePosixPath(archive.metadata.mainfile).parent)
    current_upload_id = getattr(archive.metadata, 'upload_id', None)

    try:
        from nomad.search import MetadataPagination, search

        user_id = None
        main_author = getattr(archive.metadata, 'main_author', None)
        if main_author is not None:
            user_id = getattr(main_author, 'user_id', None)

        search_result = search(
            owner='all',
            query={'results.eln.lab_ids': library_lab_id},
            pagination=MetadataPagination(page_size=1),
            user_id=user_id,
        )
        if search_result.pagination.total <= 0:
            logger.warning(
                'Could not resolve library reference for %s via direct lab_id search; '
                'writing RTMeasurement in current entry folder.',
                library_lab_id,
            )
            return None, default_folder, default_folder

        entry = search_result.data[0]
        upload_id = entry.get('upload_id')
        entry_id = entry.get('entry_id')
        if not upload_id or not entry_id:
            logger.warning(
                'Library %s matched search result but missing upload_id or entry_id; '
                'writing RTMeasurement in the current entry folder.',
                library_lab_id,
            )
            return None, default_folder, default_folder

        # Try to locate the folder where the referenced library archive mainfile lives.
        # This folder is writable within the *target* upload context.
        target_folder = ''
        library_mainfile = entry.get('mainfile')
        if library_mainfile:
            target_folder = str(PurePosixPath(library_mainfile).parent)
        else:
            try:
                installation_url = getattr(archive.m_context, 'installation_url', None)
                target_archive = archive.m_context.load_archive(
                    entry_id, upload_id, installation_url
                )
                target_mainfile = getattr(target_archive.metadata, 'mainfile', None)
                if target_mainfile:
                    target_folder = str(PurePosixPath(target_mainfile).parent)
            except Exception:
                # Fall back to root-level write in
                # target upload if mainfile lookup fails.
                target_folder = ''

        archive_reference_folder = str(
            PurePosixPath('..') / 'uploads' / upload_id / 'archive'
        )
        if current_upload_id and upload_id != current_upload_id:
            logger.info(
                'Library %s resolved in another upload. Writing RTMeasurement using '
                'ServerContext(upload=%s) into folder=%s.',
                library_lab_id,
                upload_id,
                target_folder or '.',
            )
        return upload_id, target_folder, archive_reference_folder
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning(
            'Failed to resolve library %s via explicit lab_id search; writing '
            'RTMeasurement in current entry folder. Details: %s',
            library_lab_id,
            exc,
            exc_info=True,
        )
        return None, default_folder, default_folder


def resolve_library_folder(
    archive: 'EntryArchive', logger: 'BoundLogger', library_lab_id: str
) -> str:
    """Resolve the folder for a library using the same explicit lab-id query as the
    notebook analysis.

    This avoids relying on a lazily populated ``CompositeSystemReference.reference``
    that may not yet be normalized in the active processing context.
    """
    _, _, archive_reference_folder = _resolve_library_target(
        archive, logger, library_lab_id
    )
    return archive_reference_folder


def _create_archive_in_upload(
    measurement: 'RTMeasurement',
    archive: 'EntryArchive',
    measurement_mainfile: str,
    target_upload_id: str,
) -> str:
    """Create an archive file in the given upload context."""
    current_upload_id = getattr(archive.metadata, 'upload_id', None)
    if target_upload_id == current_upload_id:
        return create_archive(measurement, archive, measurement_mainfile)

    from nomad.datamodel.context import ServerContext
    from nomad.processing import Upload
    from nomad.utils import hash

    target_upload = Upload.get(target_upload_id)
    if target_upload is None:
        raise ValueError(f'Could not get target upload: {target_upload_id}')

    target_context = ServerContext(upload=target_upload)
    with target_context.update_entry(
        measurement_mainfile, write=True, process=True
    ) as entry:
        entry['data'] = measurement.m_to_dict(with_root_def=True)

    target_entry_id = hash(target_upload_id, measurement_mainfile)
    return f'../uploads/{target_upload_id}/archive/{target_entry_id}#data'


class RTSpectrum(ArchiveSection):
    """
    A single reflection or transmission spectrum measured at a specific configuration.
    """

    m_def = Section(
        description='Single R or T spectrum with measurement geometry information.',
    )

    spectrum_type = Quantity(
        type=MEnum('Reflection', 'Transmission'),
        description='Type of spectrum: Reflection (R) or Transmission (T).',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
        ),
    )

    wavelength = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='nm',
        description='Wavelength array in nanometers.',
    )

    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Intensity values (R or T as fraction 0-1).',
    )

    detector_angle = Quantity(
        type=np.float64,
        unit='degree',
        description="""
        Detector angle in degrees, the angle between the beam and the detector.
        180° means is in the direction of the transmitted beam (typically for
        transmission measurements), while small angles means it is in the
        direction of the reflected beam (typically for reflection measurements).
        Angles constrained between 12 and 180° (if the beam is detector is on
        the left side of the optical path) and -12 and -179° (if the detector
        is on the right side of the optical path) based on typical Agilent Cary
        7000 UMS configurations.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    sample_angle = Quantity(
        type=np.float64,
        unit='degree',
        description="""
        Sample angle in degrees, the angle between the beam and the sample
        surface. 0° means the beam is normal to the sample surface, while
        larger angles mean the beam is more grazing. Angles are typically
        between 0 and 85° based on typical Agilent Cary 7000 UMS
        configurations.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    polarization = Quantity(
        type=MEnum('s', 'p', 'unpolarized(p-biased)'),
        description="""
        Polarisation of the light if the polarizer element was used during
        the measurement. 's (angle 0°)' means the electric field is
        perpendicular to the plane of incidence, 'p (angle 90°)' means the
        electric field is parallel to the plane of incidence, and
        'unpolarized (p-biased)' means the polarizer was set to unpolarized
        mode to increase measurement throughput, which typically results in a
        p-polarized bias in the transmitted beam.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTSpectrum` class.
        """
        super().normalize(archive, logger)


class RTResult(MappingResult):
    """
    Results from a single spatial position containing multiple R/T spectra.
    """

    # repeating subsection for multiple
    # spectra measured at the same position with different configurations
    # (ex: one reflection and one transmission spectrum, or multiple
    # spectra with different detector/sample angles or polarization)
    spectra = SubSection(
        section_def=RTSpectrum,
        repeats=True,
        description="""
        List of Reflection and/or Transmission spectra measured at this position.
        """,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizes the results data for the RT measurement.
        """
        super().normalize(archive, logger)


class DtuAutosamplerMeasurement(Experiment, PlotSection, Schema):
    """
    Base Experiment class for Agilent Cary autosampler measurements.

    This class handles the parsing of data and config files from the Agilent Cary
    7000 UMS autosampler and creates individual measurement archives for each
    sample/library found in the data.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Autosampler Measurement',
        description='Experiment container for autosampler R/T measurements',
    )

    # .csv file exported from the Agilent Cary .bsw or .dsw file
    data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Data file (CSV with R/T spectra)',
        },
        description=(
            'CSV file containing all R and T spectra recorded by the Agilent '
            'Cary 7000 UMS autosampler. This file contains the raw spectral '
            'data along with metadata and needs to be parsed together with '
            'the config file to extract individual spectra and associate them '
            'with the correct sample/library and position.'
        ),
    )

    # config file output by our homemade code (template called
    # Autosampler_GridGenerator_Analysis_Template_V2 on our)
    # generating mapping file that connect
    # autosampler state positions to each position on each sample. This
    # way, the data file with all the spectra in series can be parsed
    # each spectrum can be associated with the correct position on the sample, and
    # the correct sample/library.
    config_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Config/Grid file (CSV)',
        },
        description="""
        CSV file containing the grid/position metadata mapping. This file
        maps each position on each library to the corresponding recorded
        spectra in the data file, (Ex: the first recorded spectrum of the
        data_file has been recorded at position X=5mm, Y=10mm on library
        "eugbe_0025_Zr_FL")
        """,
    )

    # raw batch .bsw file from the instrument
    raw_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Raw instrument batch file (.bsw)',
        },
        description="""
            Raw binary file from the Agilent Cary 7000 UMS instrument
            (for bookkeeping and data provenance). File extension is typically .bsw.
        """,
    )

    # the three following slits are the optical slits that need to be manually
    # placed and removed. The default values for high throughput autosampler
    # measurements are 1 degree for the two vertical slits and 3 degrees
    # for the horizontal slit.
    vertical_back_slit = Quantity(
        type=np.float64,
        unit='degree',
        default=1.0,
        description='Vertical back slit setting in degrees.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='deg',
            label='Vertical back slit',
        ),
    )

    vertical_front_slit = Quantity(
        type=np.float64,
        unit='degree',
        default=1.0,
        description='Vertical front slit setting in degrees.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='deg',
            label='Vertical front slit',
        ),
    )

    horizontal_slit = Quantity(
        type=np.float64,
        unit='degree',
        default=3.0,
        description='Horizontal slit setting in degrees.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='deg',
            label='Horizontal slit',
        ),
    )

    detector_slit = Quantity(
        type=MEnum('None (open)', '1°', '2°'),
        default='None (open)',
        description='Detector slit used during the measurement.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Detector slit',
        ),
    )

    def plot_grid(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Create an interactive Plotly visualization of the autosampler measurement grid.

        This plot shows:
        1. The autosampler boundary as a circle (107 mm radius)
        2. All measurement positions grouped by sample (colored by sample)
        3. Sample labels and measurement point locations
        """
        try:
            grid_df = self._read_grid_dataframe(archive, logger)
            if grid_df is None:
                return
            self._append_grid_figure(grid_df)
        except Exception as e:
            logger.debug(
                f'Could not generate autosampler grid plot: {e}', exc_info=True
            )

    def _read_grid_dataframe(self, archive, logger):
        import pandas as pd

        if not self.config_file:
            return None
        with archive.m_context.raw_file(self.config_file) as config_f:
            grid_df = pd.read_csv(config_f.name, skiprows=0, header=0, decimal=',')
        if 'X' not in grid_df.columns or 'Y' not in grid_df.columns:
            x_col = next((c for c in grid_df.columns if 'x' in c.lower()), None)
            y_col = next((c for c in grid_df.columns if 'y' in c.lower()), None)
            if not (x_col and y_col):
                logger.debug('Could not find X/Y position columns in config file')
                return None
            grid_df.rename(columns={x_col: 'X', y_col: 'Y'}, inplace=True)
        if 'Sample Name' not in grid_df.columns:
            if 'Sample Number' not in grid_df.columns:
                logger.debug('Config file missing Sample Name or Sample Number column')
                return None
            grid_df['Sample Name'] = 'Sample_' + grid_df['Sample Number'].astype(str)
        return grid_df

    def _append_grid_figure(self, grid_df):
        import plotly.graph_objs as go

        fig = go.Figure()
        angles = np.linspace(0, 2 * np.pi, 100)
        fig.add_trace(
            go.Scatter(
                x=107 * np.cos(angles),
                y=107 * np.sin(angles),
                mode='lines',
                name='Autosampler Boundary',
                line=dict(color='red', width=2, dash='dash'),
                hovertemplate='<b>Boundary</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm',
            )
        )
        self._add_baseline_trace(fig, grid_df, go)
        self._add_sample_traces(fig, grid_df, go)
        fig.update_layout(
            title='Autosampler Measurement Grid',
            xaxis_title='X Position (mm)',
            yaxis_title='Y Position (mm)',
            template='plotly_white',
            hovermode='closest',
            xaxis=dict(scaleanchor='y', scaleratio=1),
            yaxis=dict(scaleanchor='x', scaleratio=1),
            width=800,
            height=800,
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(label='Measurement Grid Layout', figure=plot_json)
        )

    @staticmethod
    def _add_baseline_trace(fig, grid_df, go):
        if 'Baseline' not in grid_df['Sample Name'].values:
            return
        baseline_rows = grid_df[grid_df['Sample Name'] == 'Baseline']
        if len(baseline_rows) == 0:
            return
        fig.add_trace(
            go.Scatter(
                x=baseline_rows['X'].values,
                y=baseline_rows['Y'].values,
                mode='markers',
                name='Baseline Center',
                marker=dict(size=10, color='black', symbol='star'),
                hovertemplate='<b>Baseline</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm',
            )
        )

    @staticmethod
    def _add_sample_traces(fig, grid_df, go):
        color_palette = [
            '#1f77b4',
            '#ff7f0e',
            '#2ca02c',
            '#d62728',
            '#9467bd',
            '#8c564b',
            '#e377c2',
            '#7f7f7f',
            '#bcbd22',
            '#17becf',
        ]
        for idx, sample_name in enumerate(grid_df['Sample Name'].unique()):
            if sample_name == 'Baseline':
                continue
            sample_data = grid_df[grid_df['Sample Name'] == sample_name]
            has_sample_coords = (
                'Xsample' in sample_data.columns and 'Ysample' in sample_data.columns
            )
            customdata = (
                list(zip(sample_data['Xsample'].values, sample_data['Ysample'].values))
                if has_sample_coords
                else None
            )
            hover_template = (
                f'<b>{sample_name}</b><br><b>Autosampler Coords:</b><br>'
                'X: %{x:.2f} mm<br>Y: %{y:.2f} mm<br><b>Sample Coords:</b><br>'
                'X_sample: %{customdata[0]:.2f} mm<br>'
                'Y_sample: %{customdata[1]:.2f} mm<extra></extra>'
                if has_sample_coords
                else f'<b>{sample_name}</b><br>X: %{{x:.2f}} mm<br>'
                'Y: %{y:.2f} mm<extra></extra>'
            )
            fig.add_trace(
                go.Scatter(
                    x=sample_data['X'].values,
                    y=sample_data['Y'].values,
                    mode='markers',
                    name=sample_name,
                    marker=dict(size=8, color=color_palette[idx % len(color_palette)]),
                    text=sample_name,
                    customdata=customdata,
                    hovertemplate=hover_template,
                )
            )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuAutosamplerMeasurement` class.

        This method:
        1. Parses the data and config files using autosampler_reader
        2. Groups data by sample/library
        3. Creates separate RTMeasurement archives for each library
        4. Adds them as steps to this experiment
        """
        super().normalize(archive, logger)

        if not self.data_file or not self.config_file:
            logger.warning(
                'Both data_file and config_file are required for '
                'autosampler measurements.'
            )
            return

        try:
            library_data = self._parse_autosampler_data(archive)
            measurements = [
                step
                for library_id, position_data in library_data.items()
                if library_id != 'Baseline'
                for step in [
                    self._create_library_step(
                        library_id, position_data, archive, logger
                    )
                ]
            ]

            self.steps = measurements

            # Generate visualization of the measurement grid
            self.figures = []
            self.plot_grid(archive, logger)

            logger.info(
                f'Created {len(measurements)} RT measurement archives '
                f'from autosampler data.'
            )

        except Exception as e:
            logger.error(f'Error parsing autosampler data: {e}', exc_info=True)

    def _parse_autosampler_data(self, archive):
        with archive.m_context.raw_file(self.data_file) as data_f:
            with archive.m_context.raw_file(self.config_file) as config_f:
                collects = autosampler_reader.parse_file(data_f.name, config_f.name)
        samples = autosampler_reader.group_samples(collects)
        return autosampler_reader.group_measurements_position(samples)

    @staticmethod
    def _collection_datetime_label(position_data):
        first_multi_measurement = next(iter(position_data.values()))
        if not first_multi_measurement.measurements:
            return 'unknown'
        collection_time = first_multi_measurement.measurements[0].metadata.get(
            'Collection Time'
        )
        if collection_time is None:
            return 'unknown'
        if hasattr(collection_time, 'strftime'):
            return collection_time.strftime('%Y%m%d_%H%M%S')
        return str(collection_time).replace(' ', '_').replace(':', '')

    def _create_library_step(self, library_id, position_data, archive, logger):
        datetime_label = self._collection_datetime_label(position_data)
        measurement = RTMeasurement(
            name=f'{library_id}_RT_{datetime_label}',
            vertical_back_slit=self.vertical_back_slit,
            vertical_front_slit=self.vertical_front_slit,
            horizontal_slit=self.horizontal_slit,
        )
        measurement.results = [
            self._create_position_result(key, data, logger)
            for key, data in position_data.items()
        ]
        measurement.accessory = 'UMA'
        measurement.samples = [CompositeSystemReference(lab_id=library_id)]
        measurement_ref = create_archive(
            measurement,
            archive,
            f'{library_id}_rt_measurement_{datetime_label}.archive.json',
        )
        return ExperimentStep(
            name=f'{library_id}_rt_measurement_{datetime_label}',
            activity=measurement_ref,
        )

    def _create_position_result(self, position_key, multi_measurement, logger):
        result = RTResult(name=f'Position {position_key}')
        if multi_measurement.position_x is not None:
            result.x_absolute = multi_measurement.position_x * ureg('mm')
            result.x_relative = multi_measurement.position_x * ureg('mm')
        if multi_measurement.position_y is not None:
            result.y_absolute = multi_measurement.position_y * ureg('mm')
            result.y_relative = multi_measurement.position_y * ureg('mm')
        result.spectra = [
            spectrum
            for single_meas in multi_measurement.measurements
            if (spectrum := self._create_autosampler_spectrum(single_meas, logger))
            is not None
        ]
        return result

    @staticmethod
    def _create_autosampler_spectrum(single_meas, logger):
        meas_type = single_meas.metadata.get('MeasurementType', 'Unknown')
        spectrum_types = {'T': 'Transmission', 'R': 'Reflection'}
        spectrum_type = spectrum_types.get(meas_type)
        if spectrum_type is None:
            logger.warning(f'Unknown measurement type: {meas_type}')
            return None
        spectrum = RTSpectrum(
            spectrum_type=spectrum_type,
            wavelength=single_meas.data['Wavelength'].values * ureg('nm'),
            intensity=single_meas.data['Intensity'].values / 100.0,
        )
        metadata = single_meas.metadata
        if 'DetectorAngle' in metadata:
            spectrum.detector_angle = float(metadata['DetectorAngle']) * ureg('degree')
        if 'SampleAngle' in metadata:
            spectrum.sample_angle = float(metadata['SampleAngle']) * ureg('degree')
        if 'Polarization' in metadata:
            logger.debug(metadata['PolarizationAngle'])
            logger.debug(metadata['Polarization'])
            spectrum.polarization = metadata['Polarization']
        return spectrum


class RTMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        links=[
            'http://purl.obolibrary.org/obo/CHMO_0002622',
            'http://purl.obolibrary.org/obo/CHMO_0000939',
        ],
        label='RT Measurement',
    )

    # Wavelength bounds for averaging (in nm). We choose the visible range.
    WAVELENGTH_MIN = 400  # nm
    WAVELENGTH_MAX = 800  # nm

    results = SubSection(
        section_def=RTResult,
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=RectangularSampleAlignment,
        description='The alignment of the sample.',
    )

    accessory = Quantity(
        type=MEnum('UMA', 'DRA', 'None'),
        default='None',
        description=(
            'Instrument accessory used for the measurement.'
            'DRA is the integrating sphere accessory while'
            'UMA is the universal measurement accessory'
            '(variable incidence, detector and polarization).'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Accessory',
        ),
    )

    # see slit description in the DtuAutosamplerMeasurement class
    vertical_back_slit = Quantity(
        type=np.float64,
        unit='degree',
        description='Vertical back slit setting in degrees (V_back slot).',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='deg',
            label='Vertical back slit',
        ),
    )

    vertical_front_slit = Quantity(
        type=np.float64,
        unit='degree',
        description='Vertical front slit setting in degrees (V_front slot).',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='deg',
            label='Vertical front slit',
        ),
    )

    horizontal_slit = Quantity(
        type=np.float64,
        unit='degree',
        description='Horizontal slit setting in degrees (H slot).',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='deg',
            label='Horizontal slit',
        ),
    )

    detector_slit = Quantity(
        type=MEnum('None (open)', '1°', '2°'),
        default='None (open)',
        description='Detector slit used during the measurement.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            label='Detector slit',
        ),
    )

    # one csv (for example an UMA sequence with R, T, and R at different angles)
    # or several csv files measured at the name single point (for example two
    # csv files obtained with the DRA integratingsphere, one with R, one with T)
    data_file = Quantity(
        type=str,
        shape=['*'],
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'Data file (.csv)'},
        description=(
            'CSV file(s) for single-point R/T measurement. '
            'Can include R, T, or both spectra in one or multiple files. '
            'Only used when uploading single-point measurements directly; '
            'NOT used for autosampler batch experiments.'
        ),
    )
    # the corresponding raw files
    raw_file = Quantity(
        type=str,
        shape=['*'],
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Raw instrument .bsw or .dsw files',
        },
        description=(
            'Optional raw .bsw batch file for single-point measurements (provenance). '
            'Only used when uploading single-point measurements directly; '
            'NOT used for autosampler batch experiments.'
        ),
    )

    def plot(self) -> None:
        """Create spectra and spatial visualizations for this measurement."""
        import plotly.graph_objs as go
        from scipy.interpolate import griddata

        if not self.results:
            return
        self._append_spectra_plot(go)
        configs = self._get_spectrum_configs()
        positions, config_values = self._collect_config_values(configs)
        if not positions:
            return
        x_values = [point[0] for point in positions]
        y_values = [point[1] for point in positions]
        unique_x, unique_y = len(set(x_values)), len(set(y_values))
        spatial_data = configs, config_values, x_values, y_values
        if unique_x > 1 and unique_y > 1:
            self._append_configuration_heatmaps(spatial_data, go, griddata)
        else:
            self._append_configuration_lines(spatial_data, unique_x, go)

    def _append_spectra_plot(self, go):
        from nomad.datamodel.metainfo.plot import PlotlyFigure

        fig = go.Figure()
        max_traces = 25
        trace_count = 0
        max_traces_reached = False
        for result in self.results:
            if max_traces_reached:
                break
            position_label = result.name or 'Unknown'
            for spectrum in result.spectra:
                if trace_count >= max_traces:
                    max_traces_reached = True
                    break
                if spectrum.wavelength is None or spectrum.intensity is None:
                    continue
                wavelength = (
                    spectrum.wavelength.to('nm').magnitude
                    if hasattr(spectrum.wavelength, 'magnitude')
                    else spectrum.wavelength
                )
                spectrum_type = spectrum.spectrum_type or 'Unknown'
                detector = getattr(spectrum, 'detector_angle', None)
                sample = getattr(spectrum, 'sample_angle', None)
                detector_label = (
                    f'{detector.to("degree").magnitude:g} deg'
                    if detector is not None
                    else 'n/a'
                )
                sample_label = (
                    f'{sample.to("degree").magnitude:g} deg'
                    if sample is not None
                    else 'n/a'
                )
                polarization = spectrum.polarization or 'n/a'
                trace_name = (
                    f'{position_label}_{spectrum_type} '
                    f'({detector_label}, {sample_label}, {polarization})'
                )
                line_style = {}
                if spectrum_type == 'Reflection':
                    line_style['dash'] = 'solid'
                elif spectrum_type == 'Transmission':
                    line_style['dash'] = 'dot'
                fig.add_trace(
                    go.Scatter(
                        x=wavelength,
                        y=spectrum.intensity,
                        mode='lines',
                        name=trace_name,
                        line=line_style,
                        hoverlabel=dict(namelength=-1),
                    )
                )
                trace_count += 1
        title = 'Reflection (solid) and Transmission (dot) Spectra'
        if max_traces_reached:
            title += f' (showing first {max_traces} traces only)'
        fig.update_layout(
            title=title,
            xaxis_title='Wavelength (nm)',
            yaxis_title='R, T (fraction)',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(PlotlyFigure(label='R and T Spectra', figure=plot_json))

    def _get_spectrum_configs(self):
        configs = {}
        for result in self.results:
            for spectrum in result.spectra:
                if not spectrum.spectrum_type:
                    continue
                detector = getattr(spectrum, 'detector_angle', None)
                sample = getattr(spectrum, 'sample_angle', None)
                detector_value = (
                    detector.to('degree').magnitude if detector is not None else None
                )
                sample_value = (
                    sample.to('degree').magnitude if sample is not None else None
                )
                polarization = getattr(spectrum, 'polarization', None) or 'unknown'
                config_key = (
                    spectrum.spectrum_type,
                    detector_value,
                    sample_value,
                    polarization,
                )
                configs.setdefault(config_key, [])
        return configs

    def _compute_avg_for_config(self, result, config_key):
        spectrum_type, detector_angle, sample_angle, polarization = config_key
        for spectrum in result.spectra:
            if spectrum.spectrum_type != spectrum_type:
                continue
            detector = getattr(spectrum, 'detector_angle', None)
            sample = getattr(spectrum, 'sample_angle', None)
            detector_value = (
                detector.to('degree').magnitude if detector is not None else None
            )
            sample_value = sample.to('degree').magnitude if sample is not None else None
            polarization_value = getattr(spectrum, 'polarization', None) or 'unknown'
            if (detector_value, sample_value, polarization_value) != (
                detector_angle,
                sample_angle,
                polarization,
            ):
                continue
            if spectrum.wavelength is None or spectrum.intensity is None:
                continue
            wavelength = (
                spectrum.wavelength.to('nm').magnitude
                if hasattr(spectrum.wavelength, 'magnitude')
                else spectrum.wavelength
            )
            mask = (wavelength >= self.WAVELENGTH_MIN) & (
                wavelength <= self.WAVELENGTH_MAX
            )
            if np.any(mask):
                return float(np.mean(spectrum.intensity[mask]))
        return np.nan

    def _collect_config_values(self, configs):
        positions = []
        for result in self.results:
            pos_x = getattr(result, 'x_absolute', None)
            pos_y = getattr(result, 'y_absolute', None)
            if pos_x is None or pos_y is None:
                continue
            pos_x = pos_x.to('mm').magnitude if hasattr(pos_x, 'magnitude') else pos_x
            pos_y = pos_y.to('mm').magnitude if hasattr(pos_y, 'magnitude') else pos_y
            positions.append((pos_x, pos_y))
            for config_key, values in configs.items():
                values.append(self._compute_avg_for_config(result, config_key))
        return positions, list(configs.values())

    def _configuration_labels(self, config_key):
        spectrum_type, detector_angle, sample_angle, polarization = config_key
        detector_label = (
            f'{detector_angle:.1f}\u00b0' if detector_angle is not None else 'n/a'
        )
        sample_label = (
            f'{sample_angle:.1f}\u00b0' if sample_angle is not None else 'n/a'
        )
        polarization_label = polarization if polarization else 'n/a'
        title = (
            f'Avg. {spectrum_type} {self.WAVELENGTH_MIN}-{self.WAVELENGTH_MAX}nm '
            f'(detector: {detector_label}, sample: {sample_label}, '
            f'{polarization_label})'
        )
        label = (
            f'{spectrum_type[0]} {detector_label}_{sample_label}_{polarization_label}'
        )
        return spectrum_type, title, label

    def _append_configuration_heatmaps(self, spatial_data, go, griddata):
        from nomad.datamodel.metainfo.plot import PlotlyFigure

        configs, config_values, x_values, y_values = spatial_data
        xi, yi = np.meshgrid(
            np.linspace(min(x_values), max(x_values), 100),
            np.linspace(min(y_values), max(y_values), 100),
        )
        for (config_key, _), values in zip(configs.items(), config_values):
            if all(np.isnan(values)):
                continue
            spectrum_type, title, label = self._configuration_labels(config_key)
            zi = griddata((x_values, y_values), values, (xi, yi), method='linear')
            heatmap = go.Heatmap(
                x=xi[0],
                y=yi[:, 0],
                z=zi,
                colorscale='Viridis',
                colorbar=dict(title=spectrum_type),
            )
            scatter = go.Scatter(
                x=x_values,
                y=y_values,
                mode='markers',
                marker=dict(
                    size=15,
                    color=values,
                    colorscale='Viridis',
                    showscale=False,
                    line=dict(width=2, color='DarkSlateGrey'),
                ),
                customdata=values,
                hovertemplate=(
                    '<b>Value:</b> %{customdata:.3f}<br>'
                    '<b>X:</b> %{x:.2f} mm<br><b>Y:</b> %{y:.2f} mm'
                ),
            )
            self._append_spatial_figure(
                go.Figure(data=[heatmap, scatter]),
                (title, label, 'X Position (mm)', 'Y Position (mm)'),
                PlotlyFigure,
            )

    def _append_configuration_lines(self, spatial_data, unique_x, go):
        from nomad.datamodel.metainfo.plot import PlotlyFigure

        configs, config_values, x_values, y_values = spatial_data
        x_axis = x_values if unique_x > 1 else y_values
        x_label = 'X Position (mm)' if unique_x > 1 else 'Y Position (mm)'
        colors = {'Transmission': 'blue', 'Reflection': 'red'}
        for (config_key, _), values in zip(configs.items(), config_values):
            if all(np.isnan(values)):
                continue
            spectrum_type, title, label = self._configuration_labels(config_key)
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=x_axis,
                    y=values,
                    mode='lines+markers',
                    line=dict(color=colors.get(spectrum_type, 'green')),
                    marker=dict(size=8),
                    hovertemplate=(
                        f'{x_label}: %{{x}} mm<br>'
                        f'{spectrum_type}: %{{y:.3f}}<extra></extra>'
                    ),
                )
            )
            self._append_spatial_figure(
                fig, (title, label, x_label, spectrum_type), PlotlyFigure
            )

    def _append_spatial_figure(self, fig, metadata, figure_type):
        title, label, x_label, y_label = metadata
        fig.update_layout(
            title=title,
            xaxis_title=x_label,
            yaxis_title=y_label,
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(figure_type(label=label, figure=plot_json))

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalize measurement metadata, results, and visualizations."""
        if (not self.results or len(self.results) == 0) and self.data_file:
            try:
                self._normalize_single_point_csv(archive, logger)
            except Exception as e:
                logger.error(
                    f'Error parsing csv with autosampler_reader: {e}',
                    exc_info=True,
                )
        if self.location is None:
            self.location = 'DTU Nanolab RT Measurement'
        if self.data_file:
            first_file = (
                self.data_file[0]
                if isinstance(self.data_file, (list, tuple))
                else self.data_file
            )
            self.add_sample_reference(first_file, 'RT', archive, logger)
        super().normalize(archive, logger)
        self.figures = []
        if len(self.results) > 0:
            self.plot()

    def _normalize_single_point_csv(self, archive, logger):
        files = (
            self.data_file
            if isinstance(self.data_file, (list, tuple))
            else [self.data_file]
        )
        spectra = []
        any_angle_meta = False
        for file_name in files:
            with archive.m_context.raw_file(file_name) as raw_file:
                collects = autosampler_reader.parse_file(
                    raw_file.name, parse_sequence=False
                )
            for measurement in collects:
                spectrum, has_geometry = self._single_point_spectrum(
                    measurement, file_name, logger
                )
                if spectrum is not None:
                    spectra.append(spectrum)
                    any_angle_meta = any_angle_meta or has_geometry
        if not spectra:
            return
        first_file = files[0]
        result_name = os.path.splitext(os.path.basename(first_file))[0]
        result = RTResult(name=result_name)
        result.spectra = spectra
        result.x_absolute = 0 * ureg('mm')
        result.y_absolute = 0 * ureg('mm')
        self.results = [result]
        if getattr(self, 'accessory', None) in (None, 'None'):
            self.accessory = 'UMA' if any_angle_meta else 'DRA'

    @staticmethod
    def _single_point_spectrum(single_meas, file_name, logger):
        metadata = single_meas.metadata
        meas_type = metadata.get('MeasurementType', 'Unknown')
        if meas_type in {'T', 'Transmission'}:
            spectrum_type = 'Transmission'
        elif meas_type in {'R', 'Reflection'}:
            spectrum_type = 'Reflection'
        elif 'T' in file_name.upper():
            spectrum_type = 'Transmission'
        else:
            spectrum_type = 'Reflection'
        wavelength = single_meas.data.get('Wavelength')
        intensity = single_meas.data.get('Intensity')
        if wavelength is None or intensity is None:
            return None, False
        spectrum = RTSpectrum(
            spectrum_type=spectrum_type,
            wavelength=(wavelength.values * ureg('nm'))
            if hasattr(wavelength, 'values')
            else (np.asarray(wavelength) * ureg('nm')),
            intensity=intensity / 100.0,
        )
        has_geometry = False
        for metadata_key, attribute in (
            ('DetectorAngle', 'detector_angle'),
            ('SampleAngle', 'sample_angle'),
        ):
            if metadata_key in metadata:
                try:
                    setattr(
                        spectrum,
                        attribute,
                        float(metadata[metadata_key]) * ureg('degree'),
                    )
                    has_geometry = True
                except Exception:
                    pass
        if 'Polarization' in metadata:
            logger.debug(metadata['PolarizationAngle'])
            logger.debug(metadata['Polarization'])
            spectrum.polarization = metadata['Polarization']
            has_geometry = True
        return spectrum, has_geometry


m_package.__init_metainfo__()
