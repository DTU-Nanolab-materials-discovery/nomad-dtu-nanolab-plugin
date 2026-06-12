import os
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

    def plot_grid(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Create an interactive Plotly visualization of the autosampler measurement grid.

        This plot shows:
        1. The autosampler boundary as a circle (107 mm radius)
        2. All measurement positions grouped by sample (colored by sample)
        3. Sample labels and measurement point locations
        """
        import pandas as pd
        import plotly.graph_objs as go

        # Try to parse the grid from config_file if available
        try:
            if not self.config_file:
                return

            # Use archive context to read config file
            with archive.m_context.raw_file(self.config_file) as config_f:
                grid_df = pd.read_csv(config_f.name, skiprows=0, header=0, decimal=',')

            # Ensure we have X and Y columns
            if 'X' not in grid_df.columns or 'Y' not in grid_df.columns:
                # Try alternative column names
                x_col = next((c for c in grid_df.columns if 'x' in c.lower()), None)
                y_col = next((c for c in grid_df.columns if 'y' in c.lower()), None)
                if x_col and y_col:
                    grid_df.rename(columns={x_col: 'X', y_col: 'Y'}, inplace=True)
                else:
                    logger.debug('Could not find X/Y position columns in config file')
                    return  # Cannot find position columns

            # Extract unique samples
            if (
                'Sample Name' not in grid_df.columns
                and 'Sample Number' in grid_df.columns
            ):
                grid_df['Sample Name'] = 'Sample_' + grid_df['Sample Number'].astype(
                    str
                )
            elif 'Sample Name' not in grid_df.columns:
                logger.debug('Config file missing Sample Name or Sample Number column')
                return

            fig = go.Figure()

            # Add autosampler boundary circle (107 mm radius)
            AUTOSAMPLER_RADIUS = 107  # mm
            circle_angles = np.linspace(0, 2 * np.pi, 100)
            circle_x = AUTOSAMPLER_RADIUS * np.cos(circle_angles)
            circle_y = AUTOSAMPLER_RADIUS * np.sin(circle_angles)

            fig.add_trace(
                go.Scatter(
                    x=circle_x,
                    y=circle_y,
                    mode='lines',
                    name='Autosampler Boundary',
                    line=dict(color='red', width=2, dash='dash'),
                    hovertemplate='<b>Boundary</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm',
                )
            )

            # Add baseline center if it exists
            if 'Baseline' in grid_df['Sample Name'].values:
                baseline_rows = grid_df[grid_df['Sample Name'] == 'Baseline']
                if len(baseline_rows) > 0:
                    fig.add_trace(
                        go.Scatter(
                            x=baseline_rows['X'].values,
                            y=baseline_rows['Y'].values,
                            mode='markers',
                            name='Baseline Center',
                            marker=dict(size=10, color='black', symbol='star'),
                            hovertemplate=(
                                '<b>Baseline</b><br>X: %{x:.2f} mm<br>Y: %{y:.2f} mm'
                            ),
                        )
                    )

            # Color palette for samples
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

            # Add scatter plots for each sample
            unique_samples = grid_df['Sample Name'].unique()
            for idx, sample_name in enumerate(unique_samples):
                if sample_name == 'Baseline':
                    continue  # Already plotted above

                sample_data = grid_df[grid_df['Sample Name'] == sample_name]
                color = color_palette[idx % len(color_palette)]

                # Prepare custom data for hover (sample coordinates if available)
                has_sample_coords = (
                    'Xsample' in sample_data.columns
                    and 'Ysample' in sample_data.columns
                )

                if has_sample_coords:
                    customdata = list(
                        zip(
                            sample_data['Xsample'].values, sample_data['Ysample'].values
                        )
                    )
                    hover_template = (
                        f'<b>{sample_name}</b><br>'
                        '<b>Autosampler Coords:</b><br>'
                        'X: %{x:.2f} mm<br>'
                        'Y: %{y:.2f} mm<br>'
                        '<b>Sample Coords:</b><br>'
                        'X_sample: %{customdata[0]:.2f} mm<br>'
                        'Y_sample: %{customdata[1]:.2f} mm<extra></extra>'
                    )
                else:
                    customdata = None
                    hover_template = (
                        f'<b>{sample_name}</b><br>'
                        'X: %{x:.2f} mm<br>'
                        'Y: %{y:.2f} mm<extra></extra>'
                    )

                fig.add_trace(
                    go.Scatter(
                        x=sample_data['X'].values,
                        y=sample_data['Y'].values,
                        mode='markers',
                        name=sample_name,
                        marker=dict(size=8, color=color),
                        text=sample_name,
                        customdata=customdata,
                        hovertemplate=hover_template,
                    )
                )

            # Update layout
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
                PlotlyFigure(
                    label='Measurement Grid Layout',
                    figure=plot_json,
                )
            )

        except Exception as e:
            logger.debug(
                f'Could not generate autosampler grid plot: {e}', exc_info=True
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
            # Parse files using autosampler_reader
            with archive.m_context.raw_file(self.data_file) as data_f:
                with archive.m_context.raw_file(self.config_file) as config_f:
                    collects = autosampler_reader.parse_file(data_f.name, config_f.name)

            # Group measurements by sample
            samples = autosampler_reader.group_samples(collects)

            # Group measurements by position for each sample
            library_data = autosampler_reader.group_measurements_position(samples)

            measurements: list[ExperimentStep] = []

            # Create a measurement archive for each library
            for library_id, position_data in library_data.items():
                # Skip baseline samples (we might not to skip it in the future)
                if library_id == 'Baseline':
                    continue

                # Extract datetime from first measurement for uniqueness
                first_multi_measurement = next(iter(position_data.values()))
                collection_time = None
                if first_multi_measurement.measurements:
                    first_measurement = first_multi_measurement.measurements[0]
                    collection_time = first_measurement.metadata.get('Collection Time')

                # Format datetime for name uniqueness
                if collection_time is not None:
                    if hasattr(collection_time, 'strftime'):
                        datetime_label = collection_time.strftime('%Y%m%d_%H%M%S')
                    else:
                        datetime_label = (
                            str(collection_time).replace(' ', '_').replace(':', '')
                        )
                else:
                    datetime_label = 'unknown'

                measurement = RTMeasurement(
                    name=f'{library_id}_RT_{datetime_label}',
                    vertical_back_slit=self.vertical_back_slit,
                    vertical_front_slit=self.vertical_front_slit,
                    horizontal_slit=self.horizontal_slit,
                )

                # Create results for each position
                results = []
                for position_key, multi_measurement in position_data.items():
                    result = RTResult(
                        name=f'Position {position_key}',
                    )
                    # Set positions after creation (inherited from MappingResult)
                    if multi_measurement.position_x is not None:
                        result.x_absolute = multi_measurement.position_x * ureg('mm')
                        result.x_relative = multi_measurement.position_x * ureg('mm')
                    if multi_measurement.position_y is not None:
                        result.y_absolute = multi_measurement.position_y * ureg('mm')
                        result.y_relative = multi_measurement.position_y * ureg('mm')

                    # Create spectra from measurements
                    spectra = []
                    for single_meas in multi_measurement.measurements:
                        # Determine spectrum type from metadata
                        meas_type = single_meas.metadata.get(
                            'MeasurementType', 'Unknown'
                        )
                        if meas_type == 'T':
                            spectrum_type = 'Transmission'
                        elif meas_type == 'R':
                            spectrum_type = 'Reflection'
                        else:
                            logger.warning(f'Unknown measurement type: {meas_type}')
                            continue

                        # Create spectrum object
                        spectrum = RTSpectrum(
                            spectrum_type=spectrum_type,
                            wavelength=(
                                single_meas.data['Wavelength'].values * ureg('nm')
                            ),
                            intensity=single_meas.data['Intensity'].values / 100.0,
                        )

                        # Extract measurement geometry from metadata
                        if 'DetectorAngle' in single_meas.metadata:
                            spectrum.detector_angle = float(
                                single_meas.metadata['DetectorAngle']
                            ) * ureg('degree')
                        if 'SampleAngle' in single_meas.metadata:
                            spectrum.sample_angle = float(
                                single_meas.metadata['SampleAngle']
                            ) * ureg('degree')
                        if 'Polarization' in single_meas.metadata:
                            logger.debug(single_meas.metadata['PolarizationAngle'])
                            logger.debug(single_meas.metadata['Polarization'])
                            spectrum.polarization = single_meas.metadata['Polarization']

                        spectra.append(spectrum)

                    result.spectra = spectra

                    # Verify positions were set correctly before adding to results
                    results.append(result)

                measurement.results = results
                measurement.accessory = 'UMA'

                # Log positions from results after assignment
                # Results are stored in the archive via create_archive

                # Link to sample using lab_id (optional - can be set manually later)
                measurement.samples = [CompositeSystemReference(lab_id=library_id)]

                # Create archive file for this measurement with datetime identifier
                measurement_ref = create_archive(
                    measurement,
                    archive,
                    f'{library_id}_rt_measurement_{datetime_label}.archive.json',
                )

                measurements.append(
                    ExperimentStep(
                        name=f'{library_id}_rt_measurement_{datetime_label}',
                        activity=measurement_ref,
                    )
                )

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


class RTMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
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
            'Instrument accessory used for the measurement.',
            'DRA is the integration sphere accessory while',
            'UMA is the universal measurement accessory',
            '(variable incidence, detector and polarization).',
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
        """
        Create interactive Plotly visualizations of RT measurement data.

        Creates two types of plots:
        1. "R and T Spectra": All spectra overlaid
        2. "Individual Configuration Heatmaps": One spatial heatmap per
           unique measurement configuration (spectrum type, detector angle,
           sample angle, polarization) showing average intensity over the
           wavelength range defined by WAVELENGTH_MIN-WAVELENGTH_MAX class
           constants.

        Each unique configuration gets its own heatmap with measurement
        details in the title.
        """
        import plotly.graph_objs as go
        from nomad.datamodel.metainfo.plot import PlotlyFigure
        from scipy.interpolate import griddata

        if not self.results:
            return

        # ===== Plot 1: All R and T Spectra =====
        fig_spectra = go.Figure()

        MAX_TRACES = 25  # Limit traces for performance
        trace_count = 0
        max_traces_reached = False

        for result in self.results:
            if max_traces_reached:
                break

            position_label = result.name or 'Unknown'

            for spectrum in result.spectra:
                if trace_count >= MAX_TRACES:
                    max_traces_reached = True
                    break

                if spectrum.wavelength is None or spectrum.intensity is None:
                    continue

                # Convert wavelength to nm if it's a Quantity
                if hasattr(spectrum.wavelength, 'magnitude'):
                    wavelength = spectrum.wavelength.to('nm').magnitude
                else:
                    wavelength = spectrum.wavelength

                intensity = spectrum.intensity
                spectrum_type = spectrum.spectrum_type or 'Unknown'

                detector_label = (
                    f'{spectrum.detector_angle.to("degree").magnitude:g} deg'
                    if getattr(spectrum, 'detector_angle', None) is not None
                    else 'n/a'
                )
                sample_label = (
                    f'{spectrum.sample_angle.to("degree").magnitude:g} deg'
                    if getattr(spectrum, 'sample_angle', None) is not None
                    else 'n/a'
                )
                polarization_label = spectrum.polarization or 'n/a'

                # Create trace label with position and type
                trace_name = (
                    f'{position_label}_{spectrum_type} '
                    f'({detector_label}, {sample_label}, {polarization_label})'
                )

                # Use different colors/styles for R vs T
                line_style = dict()
                if spectrum_type == 'Reflection':
                    line_style['dash'] = 'solid'
                elif spectrum_type == 'Transmission':
                    line_style['dash'] = 'dot'

                fig_spectra.add_trace(
                    go.Scatter(
                        x=wavelength,
                        y=intensity,
                        mode='lines',
                        name=trace_name,
                        line=line_style,
                        hoverlabel=dict(namelength=-1),
                    )
                )
                trace_count += 1

        # Update title to indicate if traces were limited
        title = 'Reflection (solid) and Transmission (dot) Spectra'
        if max_traces_reached:
            title += f' (showing first {MAX_TRACES} traces only)'

        fig_spectra.update_layout(
            title=title,
            xaxis_title='Wavelength (nm)',
            yaxis_title='R, T (fraction)',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
        )

        plot_json_spectra = fig_spectra.to_plotly_json()
        plot_json_spectra['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='R and T Spectra',
                figure=plot_json_spectra,
            )
        )

        # ===== Plot 2: Individual Configuration Heatmaps =====
        # Collect all unique spectrum configurations present in the data
        # Each unique combination of (type, detector_angle, sample_angle,
        # polarization) gets its own heatmap

        spectrum_configs = {}

        for result in self.results:
            for spectrum in result.spectra:
                if spectrum.spectrum_type:
                    # Create a unique key for this spectrum configuration
                    detector_angle = getattr(spectrum, 'detector_angle', None)
                    sample_angle = getattr(spectrum, 'sample_angle', None)
                    polarization = getattr(spectrum, 'polarization', None)

                    det_val = (
                        detector_angle.to('degree').magnitude
                        if detector_angle is not None
                        else None
                    )
                    samp_val = (
                        sample_angle.to('degree').magnitude
                        if sample_angle is not None
                        else None
                    )
                    pol_val = polarization if polarization else 'unknown'

                    config_key = (spectrum.spectrum_type, det_val, samp_val, pol_val)

                    if config_key not in spectrum_configs:
                        spectrum_configs[config_key] = []

        # Collect position and average data for each spectrum configuration
        def compute_avg_for_config(result: RTResult, config_key: tuple) -> float:
            """Compute average intensity for a specific spectrum configuration."""
            wv_start = self.WAVELENGTH_MIN
            wv_end = self.WAVELENGTH_MAX
            spectrum_type, det_angle, samp_angle, pol = config_key

            for spectrum in result.spectra:
                if spectrum.spectrum_type != spectrum_type:
                    continue

                # Match all configuration parameters
                det_val = getattr(spectrum, 'detector_angle', None)
                det_val = (
                    det_val.to('degree').magnitude if det_val is not None else None
                )
                samp_val = getattr(spectrum, 'sample_angle', None)
                samp_val = (
                    samp_val.to('degree').magnitude if samp_val is not None else None
                )
                pol_val = getattr(spectrum, 'polarization', None) or 'unknown'

                if det_val == det_angle and samp_val == samp_angle and pol_val == pol:
                    if spectrum.wavelength is None or spectrum.intensity is None:
                        continue

                    if hasattr(spectrum.wavelength, 'magnitude'):
                        wavelength = spectrum.wavelength.to('nm').magnitude
                    else:
                        wavelength = spectrum.wavelength

                    mask = (wavelength >= wv_start) & (wavelength <= wv_end)
                    if np.any(mask):
                        return float(np.mean(spectrum.intensity[mask]))

            return np.nan

        # Populate data for each configuration
        positions = []
        for result in self.results:
            pos_x_attr = getattr(result, 'x_absolute', None)
            pos_y_attr = getattr(result, 'y_absolute', None)

            if pos_x_attr is not None and pos_y_attr is not None:
                if hasattr(pos_x_attr, 'magnitude'):
                    pos_x = pos_x_attr.to('mm').magnitude
                else:
                    pos_x = pos_x_attr

                if hasattr(pos_y_attr, 'magnitude'):
                    pos_y = pos_y_attr.to('mm').magnitude
                else:
                    pos_y = pos_y_attr

                positions.append((pos_x, pos_y))

                # Compute average for each spectrum configuration
                for config_key, config_values in spectrum_configs.items():
                    avg_val = compute_avg_for_config(result, config_key)
                    config_values.append(avg_val)

        if positions:
            # Create heatmap for each unique spectrum configuration
            pos_x_vals = [p[0] for p in positions]
            pos_y_vals = [p[1] for p in positions]

            # Check if we have a 2D grid or just a line
            unique_x = len(set(pos_x_vals))
            unique_y = len(set(pos_y_vals))

            if unique_x > 1 and unique_y > 1:
                # 2D heatmap for each spectrum configuration
                for config_key, values in spectrum_configs.items():
                    if not all(np.isnan(values)):
                        spectrum_type, det_angle, samp_angle, polarization = config_key

                        # Build title with all measurement details
                        det_str = (
                            f'{det_angle:.1f}°' if det_angle is not None else 'n/a'
                        )
                        samp_str = (
                            f'{samp_angle:.1f}°' if samp_angle is not None else 'n/a'
                        )
                        pol_str = polarization if polarization else 'n/a'

                        title = (
                            f'Avg. {spectrum_type} '
                            f'{self.WAVELENGTH_MIN}-{self.WAVELENGTH_MAX}nm '
                            f'(detector: {det_str}, sample: {samp_str}, '
                            f'{pol_str})'
                        )
                        short_label = (
                            f'{spectrum_type[0]} {det_str}_{samp_str}_{pol_str}'
                        )

                        # Create interpolation grid for smooth heatmap
                        xi = np.linspace(min(pos_x_vals), max(pos_x_vals), 100)
                        yi = np.linspace(min(pos_y_vals), max(pos_y_vals), 100)
                        xi, yi = np.meshgrid(xi, yi)
                        zi = griddata(
                            (pos_x_vals, pos_y_vals),
                            values,
                            (xi, yi),
                            method='linear',
                        )

                        # Create heatmap trace
                        heatmap = go.Heatmap(
                            x=xi[0],
                            y=yi[:, 0],
                            z=zi,
                            colorscale='Viridis',
                            colorbar=dict(title=spectrum_type),
                        )

                        # Create scatter overlay for actual measurement points
                        scatter = go.Scatter(
                            x=pos_x_vals,
                            y=pos_y_vals,
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
                                '<b>X:</b> %{x:.2f} mm<br>'
                                '<b>Y:</b> %{y:.2f} mm'
                            ),
                        )

                        # Combine heatmap and scatter
                        fig_map = go.Figure(data=[heatmap, scatter])

                        fig_map.update_layout(
                            title=title,
                            xaxis_title='X Position (mm)',
                            yaxis_title='Y Position (mm)',
                            template='plotly_white',
                            hovermode='closest',
                            dragmode='zoom',
                            xaxis=dict(fixedrange=False),
                            yaxis=dict(fixedrange=False),
                        )

                        plot_json_map = fig_map.to_plotly_json()
                        plot_json_map['config'] = dict(scrollZoom=False)
                        self.figures.append(
                            PlotlyFigure(
                                label=short_label,
                                figure=plot_json_map,
                            )
                        )
            else:
                # 1D line plot - create separate plot for each spectrum configuration
                x_axis = pos_x_vals if unique_x > 1 else pos_y_vals
                x_label = 'X Position (mm)' if unique_x > 1 else 'Y Position (mm)'

                color_map = {'Transmission': 'blue', 'Reflection': 'red'}

                for config_key, values in spectrum_configs.items():
                    if not all(np.isnan(values)):
                        spectrum_type, det_angle, samp_angle, polarization = config_key

                        # Build title with all measurement details
                        det_str = (
                            f'{det_angle:.1f}°' if det_angle is not None else 'n/a'
                        )
                        samp_str = (
                            f'{samp_angle:.1f}°' if samp_angle is not None else 'n/a'
                        )
                        pol_str = polarization if polarization else 'n/a'

                        title = (
                            f'Avg. {spectrum_type} '
                            f'{self.WAVELENGTH_MIN}-{self.WAVELENGTH_MAX}nm '
                            f'(detector: {det_str}, sample: {samp_str}, '
                            f'{pol_str})'
                        )
                        short_label = (
                            f'{spectrum_type[0]} {det_str}_{samp_str}_{pol_str}'
                        )

                        # Get color based on spectrum type
                        color = color_map.get(spectrum_type, 'green')

                        fig_line = go.Figure()
                        fig_line.add_trace(
                            go.Scatter(
                                x=x_axis,
                                y=values,
                                mode='lines+markers',
                                line=dict(color=color),
                                marker=dict(size=8),
                                hovertemplate=(
                                    f'{x_label}: %{{x}} mm<br>'
                                    f'{spectrum_type}: %{{y:.3f}}<extra></extra>'
                                ),
                            )
                        )

                        fig_line.update_layout(
                            title=title,
                            xaxis_title=x_label,
                            yaxis_title=spectrum_type,
                            template='plotly_white',
                            hovermode='closest',
                            showlegend=False,
                        )

                        plot_json_line = fig_line.to_plotly_json()
                        plot_json_line['config'] = dict(scrollZoom=False)
                        self.figures.append(
                            PlotlyFigure(
                                label=short_label,
                                figure=plot_json_line,
                            )
                        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTMeasurement` class.
        """

        # If no spatial results exist but CSV files were uploaded for a
        # single-point measurement, use the autosampler_reader to parse
        # and create a single result at position (0,0).
        if (not self.results or len(self.results) == 0) and self.data_file:
            try:
                files = (
                    self.data_file
                    if isinstance(self.data_file, (list, tuple))
                    else [self.data_file]
                )

                spectra_all = []
                any_angle_meta = False

                for f in files:
                    with archive.m_context.raw_file(f) as rf:
                        # try to parse with sequence parsing first,
                        # if it fails, fallback to non-sequence parsing

                        collects = autosampler_reader.parse_file(
                            rf.name, parse_sequence=False
                        )

                    for single_meas in collects:
                        meas_type = single_meas.metadata.get(
                            'MeasurementType', 'Unknown'
                        )
                        if meas_type in {'T', 'Transmission'}:
                            spectrum_type = 'Transmission'
                        elif meas_type in {'R', 'Reflection'}:
                            spectrum_type = 'Reflection'
                        # fallback: try to infer from filename
                        elif 'T' in f.upper():
                            spectrum_type = 'Transmission'
                        else:
                            spectrum_type = 'Reflection'

                        wavelength = single_meas.data.get('Wavelength')
                        intensity = single_meas.data.get('Intensity')
                        if wavelength is None or intensity is None:
                            continue

                        # convert to fraction (intensity is in percent)
                        intensity_arr = intensity / 100.0

                        spectrum = RTSpectrum(
                            spectrum_type=spectrum_type,
                            wavelength=(wavelength.values * ureg('nm'))
                            if hasattr(wavelength, 'values')
                            else (np.asarray(wavelength) * ureg('nm')),
                            intensity=intensity_arr,
                        )

                        # attach geometry metadata when present
                        if 'DetectorAngle' in single_meas.metadata:
                            try:
                                spectrum.detector_angle = float(
                                    single_meas.metadata['DetectorAngle']
                                ) * ureg('degree')
                                any_angle_meta = True
                            except Exception:
                                pass
                        if 'SampleAngle' in single_meas.metadata:
                            try:
                                spectrum.sample_angle = float(
                                    single_meas.metadata['SampleAngle']
                                ) * ureg('degree')
                                any_angle_meta = True
                            except Exception:
                                pass
                        if 'Polarization' in single_meas.metadata:
                            logger.debug(single_meas.metadata['PolarizationAngle'])
                            logger.debug(single_meas.metadata['Polarization'])
                            spectrum.polarization = single_meas.metadata['Polarization']
                            any_angle_meta = True

                        spectra_all.append(spectrum)

                if spectra_all:
                    # Generate name from CSV filename (strip extension)
                    result_name = 'Single point'
                    if self.data_file:
                        first_file = (
                            self.data_file[0]
                            if isinstance(self.data_file, (list, tuple))
                            else self.data_file
                        )
                        result_name = os.path.splitext(os.path.basename(first_file))[0]
                    result = RTResult(name=result_name)
                    result.spectra = spectra_all
                    # single-point stage position
                    result.x_absolute = 0 * ureg('mm')
                    result.y_absolute = 0 * ureg('mm')

                    self.results = [result]

                    # If accessory not set, infer from presence of angles
                    if getattr(self, 'accessory', None) in (None, 'None'):
                        self.accessory = 'UMA' if any_angle_meta else 'DRA'
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


m_package.__init_metainfo__()
