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
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from nomad_measurements.utils import create_archive

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
        Angles contrainted between 12 and 180° (if the beam is detector is on
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

    m_def = Section(
        description='RT measurement results at a specific position on the sample.',
    )

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


class DTUSampleAlignment(RectangularSampleAlignment):
    m_def = Section(
        description='The alignment of the sample on the stage.',
    )


class DtuAutosamplerMeasurement(Experiment, Schema):
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

    config_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Config/Grid file (CSV)',
        },
        description="""
        CSV file containing the grid/position metadata mapping. This file
        mapps each position on each library to the corresponding recorded
        spectra in the data file, (Ex: the first recorded spectrum of the
        data_file has been recorded at position X=5mm, Y=10mm on library
        "eugbe_0025_Zr_FL")
        """,
    )

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

        # Import here to avoid circular dependencies
        from nomad_dtu_nanolab_plugin import autosampler_reader

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
                    data_file=f'{library_id}_RT_{datetime_label}',
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
                            spectrum.polarization = single_meas.metadata['Polarization']

                        spectra.append(spectrum)

                    result.spectra = spectra

                    # Verify positions were set correctly before adding to results
                    results.append(result)

                measurement.results = results

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
                        name=f'{library_id} measurement',
                        activity=measurement_ref,
                    )
                )

            self.steps = measurements

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

    data_file = Quantity(
        type=str,
        description='Reference to the source data file for sample identification.',
    )

    results = SubSection(
        section_def=RTResult,
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=DTUSampleAlignment,
        description='The alignment of the sample.',
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

        for result in self.results:
            position_label = result.name or 'Unknown'

            for spectrum in result.spectra:
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

        fig_spectra.update_layout(
            title='Reflection (solid) and Transmission (dot) Spectra',
            xaxis_title='Wavelength (nm)',
            yaxis_title='Intensity (%)',
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

        if self.location is None:
            self.location = 'DTU Nanolab RT Measurement'

        if self.data_file:
            self.add_sample_reference(self.data_file, 'RT', archive, logger)

        super().normalize(archive, logger)

        self.figures = []
        if len(self.results) > 0:
            self.plot()


m_package.__init_metainfo__()
