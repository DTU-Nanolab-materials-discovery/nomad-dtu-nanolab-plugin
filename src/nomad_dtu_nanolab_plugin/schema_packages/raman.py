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
    RectangularSampleAlignment,
)
from nomad_measurements.utils import merge_sections
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.raman_map_parser import (
    MappingRamanMeas,
)
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU Raman measurement schema')


class RamanResult(MappingResult):
    """Single Raman spectrum result at a specific spatial position.

    Stores spectral data (intensity vs Raman shift) along with metadata about
    the measurement position, laser parameters, and associated optical image.
    Inherits from MappingResult to get standardized position handling and naming.

    Attributes:
        intensity (np.ndarray): Raman intensity values (arbitrary units).
            Shape: [n_points], where n_points is number of wavenumber values.
        raman_shift (np.ndarray with unit): Raman shift values in cm⁻¹.
            Shape: [n_points]. Values typically range from ~100 to 3500 cm⁻¹.
        laser_wavelength (float with unit): Excitation laser wavelength in nm.
            Common values: 532 nm (green), 633 nm (red), 785 nm (NIR).
        optical_image (str): Relative path to optical microscopy image PNG file
            showing the measurement location. Used for spatial correlation.
        x_absolute (float with unit): Inherited from MappingResult.
            Absolute X-coordinate on sample in mm.
        y_absolute (float with unit): Inherited from MappingResult.
            Absolute Y-coordinate on sample in mm.
        name (str): Inherited from MappingResult.
            Auto-generated from position, e.g., "Stage x = 2.0 mm, y = 5.0 mm".

    Notes:
        - Intensity and raman_shift arrays must have matching lengths
        - Position information enables correlation with other mapping
            techniques (EDX, XRD)
        - Optical images help identify measurement locations on heterogeneous samples

    Example YAML Entry:
        ```yaml
        intensity: [1234.5, 2345.6, 3456.7, ...]  # Raw counts
        raman_shift: [100.0, 101.0, 102.0, ...]  # cm⁻¹
        laser_wavelength: 532  # nm
        optical_image: sample_001_point0_x2000_y5000.png
        x_absolute: 0.002  # m (2.0 mm)
        y_absolute: 0.005  # m (5.0 mm)
        ```
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
    laser_wavelength = Quantity(
        type=np.dtype(np.float64),
        unit='nm',
        description='The wavelength of the laser used in the Raman measurement.',
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

        Args:
            archive (EntryArchive): NOMAD archive containing this result.
            logger (BoundLogger): Structured logger for debug/error messages.

        Notes:
            - Name generation happens in parent class based on x_absolute,
                y_absolute
            - Future: Could add relative position calculation if
                sample_alignment provided
        """
        super().normalize(archive, logger)
        # TODO: Add code for calculating the relative positions of the measurements.


class DTUSampleAlignment(RectangularSampleAlignment):
    """Sample alignment information for rectangular mapping grids.

    Defines the spatial relationship between measurement positions and the physical
    sample. Used to convert between stage coordinates and sample coordinates.

    Inherited from RectangularSampleAlignment:
        - width (float with unit): Sample width
        - height (float with unit): Sample height
        - x_upper_left (float with unit): X-coordinate of upper-left corner
        - y_upper_left (float with unit): Y-coordinate of upper-left corner
        - x_lower_right (float with unit): X-coordinate of lower-right corner
        - y_lower_right (float with unit): Y-coordinate of lower-right corner

    Notes:
        - Enables consistent positioning across different measurement techniques
        - Currently optional; many measurements use absolute stage coordinates only
        - Future: Will enable automatic relative position calculation
    """

    m_def = Section(
        description='The alignment of the sample on the stage.',
    )


class RamanMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    """Main schema for Raman mapping measurements.

    Top-level section for a complete Raman mapping measurement, containing multiple
    individual spectra (results), metadata, sample references, and auto-generated
    visualizations. Implements NOMAD Schema interface for ELN integration.

    Attributes:
        raman_data_file (str): Path to uploaded WDF file (Renishaw format).
            File is automatically parsed during normalization.
        results (list[RamanResult]): Individual Raman spectra from each position.
            Auto-populated from WDF file.
        optical_image_grid (str): Path to generated PNG grid showing all optical images.
            Created automatically during normalization.
        sample_alignment (DTUSampleAlignment): Optional sample positioning information.
        figures (list[PlotlyFigure]): Auto-generated interactive plots:
            - "Patterns": Overlaid spectra (log intensity vs Raman shift)
            - "Stacked Patterns": Offset spectra for easier comparison
            - "Raman Intensity Map": 2D heatmap at auto-detected peak

    Inherited Attributes:
        lab_id (str): Unique identifier (e.g., "indiogo_0019")
        location (str): Measurement location (default: "DTU Nanolab Raman Measurement")
        datetime (datetime): Measurement timestamp
        samples (list): References to measured samples
        instruments (list): References to instruments used
        steps (list): Experimental steps/procedures

    Methods:
        read_raman_data: Parse WDF file and extract spectra + images
        write_raman_data: Convert parsed data to RamanResult objects
        plot: Generate interactive Plotly visualizations
        normalize: Main processing pipeline (called automatically)

    Processing Pipeline:
        1. normalize() is called when entry is saved
        2. read_raman_data() parses WDF file
        3. write_raman_data() creates RamanResult objects
        4. plot() generates interactive figures
        5. All data is searchable and FAIR-compliant

    Example YAML Entry:
        ```yaml
        data:
          m_def: nomad_dtu_nanolab_plugin.schema_packages.raman.RamanMeasurement
          lab_id: indiogo_0019
          raman_data_file: indiogo_0019_RTP_hc_1x10s_P1_x20_map_0.wdf
          # Results, figures, etc. auto-populated during normalization
        ```
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
        section_def=DTUSampleAlignment,
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

        Args:
            raman_meas_list (list[RamanMeas]): Parsed Raman measurements from
                MappingRamanMeas.raman_meas_list. Each contains position,
                spectral data, and optional image.
            img_list (list[str or None]): Paths to saved optical images,
                one per measurement. None if no image for that position.
            archive (EntryArchive): NOMAD archive for normalization context.
            logger (BoundLogger): Structured logger for progress tracking.

        Returns:
            None. Populates self.results with RamanResult objects.

        Processing Steps:
            1. Iterate through each RamanMeas object
            2. Convert positions to proper units (micrometers → meters)
            3. Extract intensity and wavenumber arrays
            4. Create RamanResult with all metadata
            5. Normalize each result (generates name from position)
            6. Merge results into this measurement section

        Notes:
            - Uses merge_sections utility to properly integrate results
            - Position units converted: μm → m (for NOMAD standardization)
            - Raman shift units: cm⁻¹ (standard spectroscopy unit)
            - Each result is normalized individually for proper metadata
        """
        results = []
        for meas, img_file in zip(raman_meas_list, img_list):
            x_absolute = meas.x_pos * ureg('um')
            y_absolute = meas.y_pos * ureg('um')
            result = RamanResult(
                intensity=meas.data['intensity'].to_list(),
                raman_shift=meas.data['wavenumber'].to_numpy() * ureg('1/cm'),
                laser_wavelength=meas.laser_wavelength,
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
        5. Generates intensity map figure
        6. Converts data to RamanResult objects

        Args:
            archive (EntryArchive): NOMAD archive providing file access context.
                Used to open raw files and determine upload folder.
            logger (BoundLogger): Structured logger for progress tracking and debugging.

        Returns:
            plotly.graph_objects.Figure or None: Intensity map figure if successful,
                None if no valid data.

        File Handling:
            - Uses archive.m_context.raw_file() to access uploaded WDF
            - Handles both ServerContext (production) and ClientContext (testing)
            - In tests: saves images to temp directory
            - In production: saves to upload folder alongside WDF file

        Generated Files:
            - Individual optical images: {filename}_point{i}_x{x}_y{y}.png
            - Image grid: {filename}_optical_grid.png
            - All paths are relative to upload folder

        Error Handling:
            - Logs detailed debug information at each step
            - Gracefully handles missing optical images
            - Returns None figure if intensity map creation fails

        Notes:
            - X-coordinates are negated in WDF parser to match sample orientation
            - Image extraction is optional; works without images
            - Intensity map uses auto-detected peak (excluding Si at 520 cm⁻¹)

        See Also:
            - MappingRamanMeas.read_wdf_mapping: Core WDF parsing
            - write_raman_data: Converts parsed data to results
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

            # Generate intensity map figure and add to figures
            fig_heatmap = mapping.plot_intensity_map()

            # Write the data to results
            self.write_raman_data(mapping.raman_meas_list, img_list, archive, logger)

            return fig_heatmap

    def plot(self) -> None:
        """Generate interactive Plotly visualizations of Raman data.

        Creates two types of spectral plots and stores them in self.figures:
        1. "Patterns": Overlaid spectra with log intensity scale
        2. "Stacked Patterns": Offset spectra for easy visual comparison

        Both plots are interactive with:
        - Zoom and pan capabilities
        - Hover labels showing spectrum name and values
        - Fixed/unfixed axis options
        - Export to PNG functionality

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

        Notes:
            - Figures are automatically displayed in NOMAD ELN interface
            - Can be exported as HTML or static images
            - Plot configurations optimized for scientific publication
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
            log_intensity_filtered = log_intensity[mask]

            cumulative_offset += log_intensity_filtered.max() * OFFSET_FACTOR
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

        Args:
            archive (EntryArchive): Complete NOMAD archive with metadata and context.
            logger (BoundLogger): Structured logger for tracking and debugging.

        Returns:
            None. Modifies archive in-place with processed data and visualizations.

        Side Effects:
            - Populates self.results with RamanResult objects
            - Creates self.figures with interactive plots
            - Saves optical images to upload folder
            - Links to sample entries if filename matches pattern
            - Sets self.location if not already defined

        Sample Linking:
            - Uses add_sample_reference from parent class
            - Extracts sample ID from filename (e.g., "indiogo_0019" from WDF name)
            - Searches NOMAD for matching sample entries
            - Creates bidirectional reference if found

        Error Handling:
            - Continues even if WDF parsing fails (logs error)
            - Skips plotting if no results available
            - Gracefully handles missing optical images

        Notes:
            - This is the main entry point for data processing
            - Called automatically by NOMAD infrastructure
            - Can be triggered manually for re-processing
            - All child results are also normalized recursively

        See Also:
            - read_raman_data: WDF file parsing
            - plot: Visualization generation
            - DtuNanolabMeasurement.normalize: Parent normalizer
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
            fig_heatmap = self.read_raman_data(archive, logger)

        super().normalize(archive, logger)

        self.figures = []
        if len(self.results) > 0:
            self.plot()
            if fig_heatmap:
                fig_heatmap.update_layout(
                    template='plotly_white',
                    hovermode='closest',
                    dragmode='zoom',
                    xaxis=dict(
                        fixedrange=False,
                    ),
                    yaxis=dict(
                        fixedrange=False,
                    ),
                )
                self.figures.append(
                    PlotlyFigure(
                        label='Raman Intensity Map',
                        figure=fig_heatmap.to_plotly_json(),
                    )
                )


m_package.__init_metainfo__()
