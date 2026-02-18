"""NOMAD Schema for Raman Spectroscopy Mapping Measurements.

This module defines the NOMAD schema for storing and processing Raman spectroscopy
mapping data within the DTU Nanolab infrastructure. It integrates with the NOMAD
metainfo system to provide standardized metadata capture, data processing, and
visualization for Raman measurements.

Key Features:
    - Read Renishaw WDF mapping files
    - Extract and store optical microscopy images
    - Automatic sample reference linking
    - Interactive Plotly visualizations (overlaid and stacked spectra, intensity maps)
    - Integration with NOMAD ELN (Electronic Lab Notebook)
    - Standardized metadata using NOMAD datamodel

Schema Structure:
    - RamanResult: Individual spectrum at a specific position
    - RamanMeasurement: Collection of spectra from a mapping measurement
    - DTUSampleAlignment: Sample positioning information

Typical Workflow:
    1. User uploads WDF file via NOMAD ELN
    2. Schema parser extracts spectra and optical images
    3. Results are normalized and linked to sample metadata
    4. Interactive plots are automatically generated
    5. Data is searchable and FAIR-compliant

Author: DTU Nanolab
Version: 1.0
License: See LICENSE file
"""

import os
from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
)
from nomad_measurements.utils import merge_sections
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.raman_map_parser import (
    MappingRamanMeas,
)
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DTUBaseSampleAlignment,
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU Raman measurement schema')


class RamanResult(MappingResult):
    """Single Raman spectrum result at a specific spatial position.

    Stores spectral data (intensity vs Raman shift) along with metadata about
    the measurement position and associated optical image.
    Inherits from MappingResult to get standardized position handling and naming.

    Note: Laser wavelength, accumulation count, and exposure time are stored at
    the RamanMeasurement level as they are common to all measurement points.
    """

    m_def = Section()

    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='The Raman intensity at each wavenumber',
    )

    raman_shift = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='1/cm',
        description='The Raman shift values in 1/cm',
    )
    optical_image = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
        a_browser=BrowserAnnotation(adaptor=BrowserAdaptors.RawFileAdaptor),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalize the Raman result metadata.

        Calls parent MappingResult normalizer to generate the result name from position
        coordinates (e.g., "Stage x = 2.0 mm, y = 5.0 mm").
        """

        super().normalize(archive, logger)


class RamanMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    """Main schema for Raman mapping measurements.

    Top-level section for a complete Raman mapping measurement, containing multiple
    individual spectra (results), metadata, sample references, and auto-generated
    visualizations. Implements NOMAD Schema interface for ELN integration.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Raman Measurement',
    )
    raman_data_file = Quantity(
        type=str,
        description=(
            'Data file containing the Raman spectra. The expected format is '
            'Renishaw WDF mapping file.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )
    accumulation_count = Quantity(
        type=int,
        description=(
            'Number of accumulations for each measurement point. '
            'Common to all spectra in the mapping.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )
    exposure_time_per_point = Quantity(
        type=np.float64,
        unit='s',
        description=(
            'Total exposure time per measurement point, including all accumulations '
            'and overhead. Common to all spectra in the mapping.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='s',
        ),
    )
    laser_wavelength = Quantity(
        type=np.dtype(np.float64),
        unit='nm',
        description=(
            'The wavelength of the laser used in the Raman measurement. '
            'Common to all spectra in the mapping.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
    )
    laser_power_percent = Quantity(
        type=np.float64,
        description=(
            'Laser power as a percentage of maximum power (0-100%). '
            'Common to all spectra in the mapping.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )
    objective_magnification = Quantity(
        type=np.float64,
        description=(
            'Objective lens magnification '
            '(e.g., 20 for 20x, 50 for 50x, 100 for 100x). '
            'Common to all spectra in the mapping.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )
    results = SubSection(
        section_def=RamanResult,
        repeats=True,
    )
    optical_image_grid = Quantity(
        type=str,
        description='Optical image of the measurement grid.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
        a_browser=BrowserAnnotation(adaptor=BrowserAdaptors.RawFileAdaptor),
    )
    sample_alignment = SubSection(
        section_def=DTUBaseSampleAlignment,
        description='The alignment of the sample.',
    )

    def write_raman_data(
        self,
        raman_meas_list: list[Any],
        img_list: list[str],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """Convert parsed Raman data into NOMAD result objects.

        Takes raw data from the WDF parser (MappingRamanMeas) and creates
        standardized RamanResult objects with proper units and metadata.

        Processing Steps:
            1. Iterate through each RamanMeas object
            2. Convert positions to proper units (micrometers → meters)
            3. Extract intensity and wavenumber arrays
            4. Create RamanResult with all metadata
            5. Normalize each result (generates name from position)
            6. Merge results into this measurement section
        """
        results = []
        for meas, img_file in zip(raman_meas_list, img_list):
            x_absolute = meas.x_pos * ureg('um')
            y_absolute = meas.y_pos * ureg('um')
            result = RamanResult(
                intensity=meas.data['intensity'].to_list(),
                raman_shift=meas.data['wavenumber'].to_numpy() * ureg('1/cm'),
                optical_image=img_file,
                x_absolute=x_absolute,
                y_absolute=y_absolute,
            )
            result.normalize(archive, logger)
            results.append(result)

        raman = RamanMeasurement(
            results=results,
        )
        merge_sections(self, raman, logger)

    def read_raman_data(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Read and parse WDF file, extract spectra and optical images.

        Main data extraction method that:
        1. Opens the WDF file from upload context
        2. Parses spectral data and positions using MappingRamanMeas
        3. Extracts and saves optical microscopy images
        4. Creates optical image grid for overview
        5. Converts data to RamanResult objects
        6. Extracts measurement-level metadata (accumulation count, exposure time)
        """
        with archive.m_context.raw_file(self.raman_data_file) as file:
            # Initialize the mapping reader
            mapping = MappingRamanMeas()
            # Read the data - get folder and filename from the file path

            # Handle file path - use file object's name attribute
            file_path = file.name if hasattr(file, 'name') else self.raman_data_file
            folder = os.path.dirname(file_path)
            filename = os.path.basename(file_path)

            # If folder is empty, use current directory
            if not folder:
                folder = '.'

            mapping.read_wdf_mapping(folder, [filename])

            # Extract measurement-level metadata from the WDF file
            # These are common to all measurement points
            if mapping.raman_meas_list and hasattr(mapping, 'wdf_reader'):
                reader = mapping.wdf_reader
                if reader:
                    # Extract laser wavelength
                    if hasattr(reader, 'laser_length'):
                        self.laser_wavelength = reader.laser_length * ureg('nm')

                    # Extract accumulation count
                    if hasattr(reader, 'accumulation_count'):
                        self.accumulation_count = reader.accumulation_count

                    # Calculate exposure time per point from time data
                    # Check for at least 3 headers (typically X, Y, Time)
                    min_headers_for_time = 3
                    if (
                        hasattr(reader, 'origin_list_header')
                        and len(reader.origin_list_header) >= min_headers_for_time
                    ):
                        from renishawWiRE.types import DataType

                        # Find the Time entry in origin_list_header
                        for header in reader.origin_list_header:
                            if header[1] == DataType.Time and len(header[4]) > 1:
                                time_data = header[4]
                                # Calculate average time per point
                                time_diff = time_data[1] - time_data[0]
                                if time_diff > 0:
                                    self.exposure_time_per_point = time_diff * ureg('s')
                                break

            # Save images to the upload directory
            # Handle both ClientContext (tests) and ServerContext (production)
            from nomad.datamodel.context import ClientContext

            if isinstance(archive.m_context, ClientContext):
                # In test/client context, save to temp directory
                import tempfile

                upload_folder = tempfile.gettempdir()
            else:
                upload_folder = archive.m_context.upload_files.os_path

            meas_name = filename.split('.')[0]

            # Get the folder where raman_data_file is located (relative to upload)
            data_file_dir = os.path.dirname(self.raman_data_file)

            # Save images to same folder as data file
            img_save_folder = (
                os.path.join(upload_folder, data_file_dir)
                if data_file_dir
                else upload_folder
            )

            _, img_filenames = mapping.save_optical_images(img_save_folder, meas_name)
            # Create relative paths for the images
            img_list = [
                os.path.join(data_file_dir, img_name)
                if data_file_dir and img_name
                else img_name
                for img_name in img_filenames
            ]

            # Create and save the optical image grid
            grid_path = os.path.join(img_save_folder, f'{meas_name}_optical_grid.png')
            fig = mapping.create_image_grid(save_path=grid_path)
            # Store the relative path to the optical image grid
            if fig:
                self.optical_image_grid = (
                    os.path.join(data_file_dir, f'{meas_name}_optical_grid.png')
                    if data_file_dir
                    else f'{meas_name}_optical_grid.png'
                )

            # Write the data to results
            self.write_raman_data(mapping.raman_meas_list, img_list, archive, logger)

    def plot(self) -> None:
        """Generate interactive Plotly visualizations of Raman data.

        Creates two types of spectral plots and stores them in self.figures:
        1. "Patterns": Overlaid spectra with log intensity scale
        2. "Stacked Patterns": Offset spectra for easy visual comparison

        Plot 1: Overlaid Spectra
            - All spectra plotted on same scale
            - Y-axis: log(intensity) to handle wide dynamic range
            - Each spectrum labeled by position
            - Useful for comparing peak positions

        Plot 2: Stacked Spectra
            - Spectra offset vertically for clarity
            - Offset calculated dynamically based on intensity range
            - Excludes Si peak region (510-530 cm⁻¹) from offset calculation
            - Better for visualizing peak evolution across positions
        Returns:
            None. Appends PlotlyFigure objects to self.figures list.
        """
        fig = go.Figure()
        result: RamanResult
        for result in self.results:
            # Fixed: raman_shift is stored as a list, not a Quantity
            # If it's a Quantity, convert it; otherwise use it directly
            if hasattr(result.raman_shift, 'magnitude'):
                x_data = result.raman_shift.to('1/cm').magnitude
            else:
                x_data = result.raman_shift

            # Add small epsilon to avoid log(0) warnings
            intensity_safe = np.maximum(result.intensity, 1e-10)

            fig.add_trace(
                go.Scatter(
                    x=x_data,
                    y=np.log(intensity_safe),
                    mode='lines',
                    name=result.name,
                    hoverlabel=dict(namelength=-1),
                )
            )

        # Update layout
        fig.update_layout(
            title='Raman Spectra',
            xaxis_title='Raman Shift (1/cm)',
            yaxis_title='Log Intensity',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
                type='linear',
            ),
        )

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        self.figures.append(
            PlotlyFigure(
                label='Patterns',
                figure=plot_json,
            )
        )

        fig2 = go.Figure()

        # Pre-calculate log intensities and cumulative offsets
        log_intensities = []
        offsets = [0]
        cumulative_offset = 0

        OFFSET_FACTOR = 0.3  # Factor to control spacing between patterns
        RAMAN_RANGE_EXCL = (510, 530)  # Exclude this range for offset calculation
        RAMAN_RAYLEIGH_PEAK_FILTER = 80  # Filter to exclude the region around 0 cm-1

        for result in self.results:
            if hasattr(result.raman_shift, 'magnitude'):
                raman_shift_data = result.raman_shift.to('1/cm').magnitude
            else:
                raman_shift_data = result.raman_shift

            log_intensity = np.log10(np.maximum(result.intensity, 1e-10))
            log_intensities.append(log_intensity)

            # Filter to exclude the specified Raman shift range for offset calculation
            mask = (raman_shift_data < RAMAN_RANGE_EXCL[0]) | (
                raman_shift_data > RAMAN_RANGE_EXCL[1]
            )
            # also exclude the Rayleigh peak region
            mask &= raman_shift_data > RAMAN_RAYLEIGH_PEAK_FILTER

            # apply mask
            log_intensity_filtered = log_intensity[mask]

            cumulative_offset += (
                log_intensity_filtered.max() - log_intensity_filtered.min()
            ) * OFFSET_FACTOR
            offsets.append(cumulative_offset)

        # Add traces with dynamically calculated offsets
        for i, result in enumerate(self.results):
            if hasattr(result.raman_shift, 'magnitude'):
                x_data = result.raman_shift.to('1/cm').magnitude
            else:
                x_data = result.raman_shift

            fig2.add_trace(
                go.Scatter(
                    x=x_data,
                    y=log_intensities[i] + offsets[i],
                    mode='lines',
                    name=result.name,
                    hoverlabel=dict(namelength=-1),
                )
            )

        # Update layout
        fig2.update_layout(
            title='Raman Spectra stacked',
            xaxis_title='Raman Shift (1/cm)',
            yaxis_title='Log(Intensity)',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
                type='linear',
            ),
        )

        plot_json2 = fig2.to_plotly_json()
        plot_json2['config'] = dict(
            scrollZoom=False,
        )
        self.figures.append(
            PlotlyFigure(
                label='Stacked Patterns',
                figure=plot_json2,
            )
        )

    def plot_intensity_map_from_results(
        self, wavenumber_tolerance: float = 5
    ) -> PlotlyFigure | None:
        """Generate Raman intensity map from normalized results with position awareness.

        Creates a 2D heatmap showing spatial distribution of Raman intensity at the
        wavenumber with maximum intensity (excluding Si peak). Uses relative positions
        if available, falls back to absolute stage positions otherwise.

        Args:
            wavenumber_tolerance: Tolerance window in cm⁻¹ around detected peak
            wavenumber

        Returns:
            PlotlyFigure or None: Interactive heatmap figure ready for display
        """
        if not self.results:
            return None

        # Determine position type and titles
        use_relative = all(
            isinstance(r.x_relative, ureg.Quantity)
            and isinstance(r.y_relative, ureg.Quantity)
            for r in self.results
        )

        if use_relative:
            position_unit = 'mm'
            x_title = 'X Sample Position (mm)'
            y_title = 'Y Sample Position (mm)'
        else:
            position_unit = 'um'
            x_title = 'X Stage Position (μm)'
            y_title = 'Y Stage Position (μm)'

        # Auto-detect target wavenumber (excluding Si peak region)
        SI_PEAK_RANGE = (510, 530)
        max_intensity = 0
        target_wavenumber = 520  # default fallback

        for result in self.results:
            raman_shift_data = (
                result.raman_shift.to('1/cm').magnitude
                if hasattr(result.raman_shift, 'magnitude')
                else result.raman_shift
            )
            intensity_data = result.intensity

            # Exclude Si peak region
            mask = (raman_shift_data < SI_PEAK_RANGE[0]) | (
                raman_shift_data > SI_PEAK_RANGE[1]
            )
            if mask.any():
                filtered_intensity = intensity_data[mask]
                filtered_wavenumber = raman_shift_data[mask]
                max_idx = np.argmax(filtered_intensity)
                current_max = filtered_intensity[max_idx]
                if current_max > max_intensity:
                    max_intensity = current_max
                    target_wavenumber = filtered_wavenumber[max_idx]

        # Extract intensity at target wavenumber for each position
        x_positions = []
        y_positions = []
        intensities = []

        for result in self.results:
            # Get positions
            if use_relative:
                x_pos = result.x_relative.to(position_unit).magnitude
                y_pos = result.y_relative.to(position_unit).magnitude
            else:
                x_pos = result.x_absolute.to(position_unit).magnitude
                y_pos = result.y_absolute.to(position_unit).magnitude

            x_positions.append(x_pos)
            y_positions.append(y_pos)

            # Get Raman shift and intensity
            raman_shift_data = (
                result.raman_shift.to('1/cm').magnitude
                if hasattr(result.raman_shift, 'magnitude')
                else result.raman_shift
            )
            intensity_data = result.intensity

            # Find intensity at target wavenumber
            mask = (raman_shift_data >= target_wavenumber - wavenumber_tolerance) & (
                raman_shift_data <= target_wavenumber + wavenumber_tolerance
            )

            if mask.any():
                intensity = intensity_data[mask].mean()
            else:
                intensity = 0
            intensities.append(intensity)

        # Create intensity matrix for heatmap
        x_unique = sorted(set(x_positions))
        y_unique = sorted(set(y_positions))

        intensity_matrix = np.zeros((len(y_unique), len(x_unique)))
        for x_pos, y_pos, intensity in zip(x_positions, y_positions, intensities):
            x_idx = x_unique.index(x_pos)
            y_idx = y_unique.index(y_pos)
            intensity_matrix[y_idx, x_idx] = intensity

        # Create heatmap figure
        fig = go.Figure(
            data=go.Heatmap(
                z=intensity_matrix,
                x=x_unique,
                y=y_unique,
                colorscale='Viridis',
                colorbar=dict(title='Intensity'),
            )
        )

        fig.update_layout(
            title=f'Raman Intensity Map at {target_wavenumber:.2f} cm⁻¹',
            xaxis_title=x_title,
            yaxis_title=y_title,
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
        )

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)

        return PlotlyFigure(label='Raman Intensity Map', figure=plot_json)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Main normalization pipeline for Raman measurements.

        Executed automatically when entry is saved in NOMAD. Orchestrates the complete
        data processing workflow from raw WDF file to searchable, visualized results.

        Processing Pipeline:
            1. Set default location if not provided
            2. Link measurement to sample based on filename pattern
            3. Parse WDF file and extract all data (read_raman_data)
            4. Call parent normalizers for standard metadata
            5. Generate interactive plots if results exist (plot)
            6. Add intensity map to figures
        """

        if self.location is None:
            self.location = 'DTU Nanolab Raman Measurement'

        if self.raman_data_file:
            self.add_sample_reference(
                filename=self.raman_data_file,
                measurement_type='Raman',
                archive=archive,
                logger=logger,
            )
            self.read_raman_data(archive, logger)

        super().normalize(archive, logger)

        self.figures = []
        if len(self.results) > 0:
            self.plot()
            # Generate intensity map from normalized results
            # (respects relative positions)
            intensity_map_fig = self.plot_intensity_map_from_results()
            if intensity_map_fig:
                self.figures.append(intensity_map_fig)


m_package.__init_metainfo__()
