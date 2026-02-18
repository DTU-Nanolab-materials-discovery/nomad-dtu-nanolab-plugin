"""Raman Mapping Data Parser.

This module provides classes and utilities for reading, processing, and visualizing
Raman spectroscopy mapping data from Renishaw WDF files. It extracts both spectral
data and optical microscopy images embedded in WDF files.

The main workflow:
    1. Read WDF mapping files containing multiple Raman spectra at different positions
    2. Extract optical microscopy images from the WDF file
    3. Process and normalize spectral data
    4. Create visualizations (spectra plots, intensity maps, image grids)

Typical usage:
    >>> mapping = MappingRamanMeas()
    >>> mapping.read_wdf_mapping(folder, ['sample.wdf'])
    >>> mapping.save_optical_images(folder, 'sample_name')
    >>> fig = mapping.plot_spectra(method='normalize')
    >>> intensity_map = mapping.plot_intensity_map(target_wavenumber=380)

Author: DTU Nanolab
License: See LICENSE file
"""

import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from renishawWiRE import WDFReader

NBR_SPECTRA = 2  # Number of spectra to print detailed info for


class RamanMeas:
    """Container for a single Raman measurement point.

    This class stores data for one Raman spectrum acquired at a specific position
    in a mapping measurement. It includes the spectral data (wavenumber vs intensity),
    the spatial position, and optionally an optical microscopy image of that location.

    Attributes:
        x_pos (float): X-coordinate of the measurement position in micrometers (μm).
            Note: For Renishaw data, x-coordinates are negated to match
            sample orientation.
        y_pos (float): Y-coordinate of the measurement position in micrometers (μm).
        data (pd.DataFrame): Spectral data with columns:
            - 'wavenumber': Raman shift values in cm⁻¹
            - 'intensity': Raman intensity (arbitrary units)
            - 'norm_intensity': Normalized intensity (0-1), added by
                normalize_intensity()
        image (PIL.Image or None): Optical microscopy image at this
            measurement position, extracted from the WDF file if available.
        laser_wavelength (float or None): Wavelength of the laser used for excitation,
            in nanometers (nm).

    Example:
        >>> meas = RamanMeas()
        >>> meas.x_pos = 100.0  # 100 μm
        >>> meas.y_pos = 50.0   # 50 μm
        >>> meas.data = pd.DataFrame(
        ...     {'wavenumber': [100, 200], 'intensity': [1000, 2000]}
        ... )
    """

    def __init__(self):
        self.x_pos = 0
        self.y_pos = 0
        self.data = pd.DataFrame(columns=['wavenumber', 'intensity'])
        self.image = None  # Store the optical image for this measurement point
        self.laser_wavelength = None


class MappingRamanMeas:
    """Handler for Raman mapping measurements from WDF files.

    This class manages collections of Raman spectra acquired in a mapping configuration,
    where spectra are collected at multiple spatial positions across a sample surface.
    It handles reading Renishaw WDF format files, extracting embedded optical images,
    and providing various visualization and analysis capabilities.

    The class supports:
        - Reading 1D, 2D, and 3D spectral arrays from WDF files
        - Extracting JPEG-encoded optical microscopy images from WXDB blocks
        - Creating intensity maps at specific Raman shifts
        - Plotting spectra with various normalization options
        - Generating image grids showing optical views of all measurement points

    Attributes:
        raman_meas_list (list[RamanMeas]): List of individual Raman measurements,
            one for each position in the mapping grid.

    Example:
        >>> mapping = MappingRamanMeas()
        >>> mapping.read_wdf_mapping('data_folder', ['sample_map.wdf'], verbose=True)
        >>> print(f"Loaded {len(mapping.raman_meas_list)} spectra")
        >>> mapping.normalize_intensity(x_range=(100, 1000))
        >>> fig = mapping.plot_spectra(color_by='x_pos')
        >>> intensity_map = mapping.plot_intensity_map(target_wavenumber=520)

    Notes:
        - X-coordinates from Renishaw files are negated to match standard orientation
        - Supports both single spectra and full mapping grids
        - Optical images are optional and extracted when available in the WDF file
    """

    def __init__(self):
        self.raman_meas_list = []
        self.wdf_reader = None  # Store WDFReader for metadata access

    def read_wdf_mapping(self, folder, filename_list, verbose=False):
        """Read WDF file(s) and extract Raman spectra and optical images.

        Reads Renishaw WDF format files containing Raman mapping data. Automatically
        detects whether the file contains a single spectrum or a full mapping grid,
        and extracts both spectral data and embedded optical microscopy images.

        Args:
            folder (str): Directory path containing the WDF files.
            filename_list (list[str]): List of WDF filenames to process.
            verbose (bool, optional): If True, prints detailed progress information
                including shapes, positions, and image extraction status.
                Defaults to False.

        Returns:
            None. Populates self.raman_meas_list with RamanMeas objects.

        Raises:
            FileNotFoundError: If WDF files cannot be found in the specified folder.
            Exception: If WDF file format is unsupported or corrupted.

        Notes:
            - Handles 1D (single spectrum), 2D (line scan), and 3D (area map)
                data arrays
            - X-coordinates are negated to match standard sample orientation
            - Optical images are extracted from WXDB blocks when available
            - Each measurement point gets a RamanMeas object with position,
                spectrum, and image

        Example:
            >>> mapping = MappingRamanMeas()
            >>> mapping.read_wdf_mapping(
            ...     '/path/to/data', ['sample_001.wdf'], verbose=True
            ... )
            === WDF File: sample_001.wdf ===
            Spectra shape: (5, 5, 1015)
            Extracted 25 optical images
            Total spectra loaded: 25
        """
        for filename in filename_list:
            file_path = os.path.join(folder, filename)
            reader = WDFReader(file_path)

            # Store the reader for metadata access
            self.wdf_reader = reader

            # Debug information
            if verbose:
                print(f'\n=== WDF File: {filename} ===')
                print(f'Spectra shape: {reader.spectra.shape}')
                print(f'Xdata shape: {reader.xdata.shape}')
                if hasattr(reader, 'xpos') and hasattr(reader, 'ypos'):
                    print(f'Number of positions: {len(reader.xpos)}')
                    print(f'X positions: {reader.xpos[:5]}...')
                    print(f'Y positions: {reader.ypos[:5]}...')

            # Get wavenumber data (should be 1D)
            wv_num = reader.xdata

            # Extract optical images first
            optical_images = self._extract_optical_images_from_reader(
                reader, verbose=verbose
            )
            if verbose:
                print(f'Extracted {len(optical_images)} optical images')

            # Check if we have position data
            if (
                hasattr(reader, 'xpos')
                and hasattr(reader, 'ypos')
                and len(reader.xpos) > 1
            ):
                # We have mapping data with positions
                if verbose:
                    print('Processing mapping data with positions...')

                # Handle 3D spectra array (e.g., 5x5x1015 grid)
                spectra_array = reader.spectra
                if len(spectra_array.shape) == 3:  # noqa: PLR2004
                    # 3D array: reshape to 2D [position, wavenumber]
                    if verbose:
                        print(
                            f'Reshaping spectra from {spectra_array.shape} to 2D array'
                        )
                    # original_shape = spectra_array.shape
                    spectra_array = spectra_array.reshape(-1, spectra_array.shape[-1])
                    if verbose:
                        print(f'Reshaped to: {spectra_array.shape}')

                for i in range(len(reader.xpos)):
                    raman_meas = RamanMeas()
                    """
                    here the X direction needs to be swapped to match
                    the stage coordinates of the renishaw raman system
                    """
                    raman_meas.x_pos = -reader.xpos[i]  # swap x
                    raman_meas.y_pos = reader.ypos[i]
                    raman_meas.laser_wavelength = reader.laser_length

                    # Assign optical image if available
                    if i < len(optical_images):
                        raman_meas.image = optical_images[i]

                    # Get intensity data for this position
                    if len(spectra_array.shape) == 2:  # noqa: PLR2004
                        # 2D array: [position, wavenumber]
                        intensity = spectra_array[i]
                        if verbose and i < NBR_SPECTRA:  # Debug first few spectra
                            print(
                                f'Spectrum {i}: '
                                f'pos=({raman_meas.x_pos:.2f}, '
                                f'{raman_meas.y_pos:.2f}), '
                                f'intensity range {intensity.min():.2f} - '
                                f'{intensity.max():.2f}, '
                                f'has_image={raman_meas.image is not None}'
                            )
                    else:
                        # 1D array: single spectrum
                        if verbose:
                            print(
                                'Warning: Only single spectrum found,',
                                'but multiple positions exist',
                            )
                        intensity = spectra_array

                    # Ensure both arrays are 1D
                    wv_num_flat = np.array(wv_num).flatten()
                    intensity_flat = np.array(intensity).flatten()

                    # Make sure arrays have same length
                    min_length = min(len(wv_num_flat), len(intensity_flat))
                    wv_num_flat = wv_num_flat[:min_length]
                    intensity_flat = intensity_flat[:min_length]

                    raman_meas.data = pd.DataFrame(
                        {'wavenumber': wv_num_flat, 'intensity': intensity_flat}
                    )
                    self.raman_meas_list.append(raman_meas)
            else:
                # Single spectrum without position data
                if verbose:
                    print('Processing single spectrum...')
                raman_meas = RamanMeas()
                raman_meas.x_pos = 0
                raman_meas.y_pos = 0

                # Assign optical image if available
                if len(optical_images) > 0:
                    raman_meas.image = optical_images[0]
                    if verbose:
                        print('Assigned optical image to single spectrum')

                # Ensure both arrays are 1D
                wv_num_flat = np.array(wv_num).flatten()
                intensity_flat = np.array(reader.spectra).flatten()

                # Make sure arrays have same length
                min_length = min(len(wv_num_flat), len(intensity_flat))
                wv_num_flat = wv_num_flat[:min_length]
                intensity_flat = intensity_flat[:min_length]

                raman_meas.data = pd.DataFrame(
                    {'wavenumber': wv_num_flat, 'intensity': intensity_flat}
                )
                self.raman_meas_list.append(raman_meas)

            if verbose:
                print(f'Total spectra loaded: {len(self.raman_meas_list)}')

    def _extract_optical_images_from_reader(self, reader, verbose=False):
        """Extract optical microscopy images from WDF file WXDB block.

        Parses the WXDB (Renishaw extended data block) to extract JPEG-encoded
        optical microscopy images that were captured during the Raman mapping.
        Each image corresponds to a specific measurement position.

        Args:
            reader (WDFReader): Initialized WDFReader object with an open WDF file.
            verbose (bool, optional): If True, prints extraction progress and errors.
                Defaults to False.

        Returns:
            list[PIL.Image or None]: List of PIL Image objects, one per
                measurement point. None entries indicate positions where image
                extraction failed.

        Notes:
            - Searches for JPEG markers (0xFFD8FF) in the WXDB binary data
            - Each JPEG is bounded by start (0xFFD8FF) and end (0xFFD9) markers
            - Failed extractions are logged if verbose=True but don't raise exceptions
            - Returns empty list if no WXDB block exists in the file

        Technical Details:
            The WXDB block stores optical images as JPEG data. This method:
            1. Locates the WXDB block using file offset information
            2. Reads the entire block into memory
            3. Searches for JPEG start/end markers
            4. Extracts and decodes each JPEG image
            5. Handles corrupted or incomplete image data gracefully
        """
        import io

        from PIL import Image

        images = []

        # Try to extract from WXDB block
        if hasattr(reader, 'file_obj') and hasattr(reader, 'block_info'):
            if 'WXDB' in reader.block_info:
                if verbose:
                    print('Found WXDB block, extracting optical images...')
                block_type, offset, size = reader.block_info['WXDB']
                reader.file_obj.seek(offset)
                wxdb_data = reader.file_obj.read(size)

                # Find all JPEG start positions
                jpeg_start = b'\xff\xd8\xff'
                jpeg_end = b'\xff\xd9'

                start_positions = []
                pos = 0
                while True:
                    pos = wxdb_data.find(jpeg_start, pos)
                    if pos == -1:
                        break
                    start_positions.append(pos)
                    pos += 1

                # Extract each JPEG
                for i, start_pos in enumerate(start_positions):
                    # Find end of this JPEG
                    end_pos = wxdb_data.find(jpeg_end, start_pos)
                    if end_pos == -1:
                        if i < len(start_positions) - 1:
                            end_pos = start_positions[i + 1]
                        else:
                            end_pos = len(wxdb_data)
                    else:
                        end_pos += 2

                    jpeg_data = wxdb_data[start_pos:end_pos]

                    try:
                        img = Image.open(io.BytesIO(jpeg_data))
                        images.append(img)
                        if verbose:
                            print(
                                f'Successfully extracted image {i + 1}, '
                                f'size: {img.size}'
                            )
                    except Exception as e:
                        if verbose:
                            print(f'Failed to extract image {i + 1}: {e}')
                        images.append(None)

        return images

    def save_optical_images(self, folder, filename_prefix, verbose=False):
        """Save all optical microscopy images to disk as PNG files.

        Exports optical images from all measurement points to individual PNG files
        with filenames encoding the position information.

        Args:
            folder (str): Directory path where images will be saved.
            filename_prefix (str): Prefix for image filenames (typically sample ID).
            verbose (bool, optional): If True, prints save statistics.
                Defaults to False.

        Returns:
            tuple[int, list[str or None]]:
                - int: Count of successfully saved images
                - list: Filenames for each measurement (None if no image available)

        File Naming Convention:
            Images are saved as: {prefix}_point{index}_x{x_pos}_y{y_pos}.png
            Example: sample_001_point0_x2000_y5000.png
            where positions are in micrometers (μm) without decimal points.

        Example:
            >>> count, filenames = mapping.save_optical_images(
            ...     '/output/images',
            ...     'sample_001',
            ...     verbose=True
            ... )
            Saved 25 optical images to /output/images
            >>> print(filenames[0])
            'sample_001_point0_x2000_y5000.png'
        """

        saved_count = 0
        saved_filenames = []
        for i, raman_meas in enumerate(self.raman_meas_list):
            if raman_meas.image is not None:
                filename = (
                    f'{filename_prefix}_point{i}_'
                    f'x{raman_meas.x_pos:.0f}_y{raman_meas.y_pos:.0f}.png'
                )
                img_path = os.path.join(folder, filename)
                raman_meas.image.save(img_path)
                saved_count += 1
                saved_filenames.append(filename)
            else:
                saved_filenames.append(None)

        if verbose:
            print(f'Saved {saved_count} optical images to {folder}')
        return saved_count, saved_filenames

    def normalize_intensity(self, x_range: tuple = None, verbose=False):
        """Normalize Raman intensities for all spectra.

        Normalizes the intensity values by dividing by the maximum intensity,
        either across the full spectrum or within a specified wavenumber range.
        Adds a 'norm_intensity' column to each measurement's data DataFrame.

        Args:
            x_range (tuple[float, float], optional): Wavenumber range (min, max) in cm⁻¹
                to use for finding the normalization maximum. If None, uses the entire
                spectrum. Useful for excluding strong peaks (e.g., Si at 520 cm⁻¹).
            verbose (bool, optional): If True, prints normalization details.
                Defaults to False.

        Returns:
            None. Modifies each RamanMeas.data DataFrame in-place by adding
                'norm_intensity'.
            - Each spectrum is normalized independently to its own maximum
            - Avoids division by zero by checking max_int > 0
            - Normalized values range from 0 to 1
            - Useful for comparing spectral shapes across different intensity scales

        Example:
            >>> # Normalize excluding the Si peak region (510-530 cm⁻¹)
            >>> mapping.normalize_intensity(x_range=(100, 500), verbose=True)
            Normalizing 25 spectra in range (100, 500)
            >>> # Now plot with normalized intensities
            >>> fig = mapping.plot_spectra(method='normalize')
        """
        if verbose:
            range_str = f'in range {x_range}' if x_range else 'using full spectrum'
            print(f'Normalizing {len(self.raman_meas_list)} spectra {range_str}')

        for raman_meas in self.raman_meas_list:
            if x_range is None:
                # Normalize each spectrum by its own max
                max_int = raman_meas.data['intensity'].max()
            else:
                # Filter the data based on the x_range, then get max from filtered data
                mask = (raman_meas.data['wavenumber'] >= x_range[0]) & (
                    raman_meas.data['wavenumber'] <= x_range[1]
                )
                filtered_data = raman_meas.data[mask]
                max_int = (
                    filtered_data['intensity'].max() if len(filtered_data) > 0 else 1
                )

            if max_int > 0:  # Avoid division by zero
                raman_meas.data['norm_intensity'] = (
                    raman_meas.data['intensity'] / max_int
                )
            else:
                raman_meas.data['norm_intensity'] = raman_meas.data['intensity']

    def plot_spectra(
        self,
        color_by='x_pos',
        method='normalize',
        x_range=None,
        max_spectra=None,
        verbose=False,
    ):
        """Create interactive Plotly plot of Raman spectra.

        Generates a Plotly figure showing all (or a subset of) Raman spectra,
        with colors mapped to spatial position or another attribute.

        Args:
            color_by (str, optional): Attribute name to color-code spectra by.
                Options: 'x_pos', 'y_pos'. Defaults to 'x_pos'.
            method (str, optional): Intensity scaling method. Options:
                - 'normalize': Normalize each spectrum to max=1 (recommended)
                - 'default': Use raw intensity values
                Defaults to 'normalize'.
            x_range (tuple[float, float], optional): Wavenumber range (min, max) in cm⁻¹
                to display and use for normalization. None shows full range.
            max_spectra (int, optional): Maximum number of spectra to plot.
                Useful for large datasets. None plots all spectra.
            verbose (bool, optional): If True, prints detailed plotting info for first
                NBR_SPECTRA. Defaults to False.

        Returns:
            plotly.graph_objects.Figure: Interactive plot that can be displayed
                or saved.

        Notes:
            - Colors use Viridis colorscale by default
            - Each spectrum is labeled with its (x, y) position
            - Hovering shows spectrum name and values
            - Plot is interactive (zoom, pan, save as PNG)

        Example:
            >>> # Plot first 10 spectra, colored by y-position
            >>> fig = mapping.plot_spectra(
            ...     color_by='y_pos',
            ...     method='normalize',
            ...     x_range=(100, 1000),
            ...     max_spectra=10,
            ...     verbose=True
            ... )
            >>> fig.show()  # Display in browser
            >>> fig.write_html('spectra.html')  # Save to file
        """
        if method == 'normalize':
            # Always normalize fresh for this plot (remove caching)
            if verbose:
                print('Normalizing spectra...')
            self.normalize_intensity(x_range=x_range, verbose=verbose)
            y_plot = 'norm_intensity'
        elif method == 'default':
            y_plot = 'intensity'

        # Limit number of spectra to plot if specified
        spectra_to_plot = self.raman_meas_list
        if max_spectra is not None:
            spectra_to_plot = self.raman_meas_list[:max_spectra]
            if verbose:
                print(f'Plotting first {len(spectra_to_plot)} spectra...')

        # Get the color values based on the selected attribute
        color_values = [getattr(raman_meas, color_by) for raman_meas in spectra_to_plot]

        # Create a color scale
        color_scale = px.colors.sequential.Viridis

        # Normalize the color values to the range [0, 1]
        if len(set(color_values)) > 1:  # Check if there are different values
            norm_color_values = (np.array(color_values) - np.min(color_values)) / (
                np.max(color_values) - np.min(color_values)
            )
        else:
            norm_color_values = np.zeros(len(color_values))

        # Map the normalized color values to the color scale
        colors = [
            color_scale[int(val * (len(color_scale) - 1))] for val in norm_color_values
        ]

        # Plot spectra with the Plotly library with the position as legend
        fig = go.Figure()
        for i, (raman_meas, color) in enumerate(zip(spectra_to_plot, colors)):
            # Filter data by x_range if specified
            if x_range is not None:
                mask = (raman_meas.data['wavenumber'] >= x_range[0]) & (
                    raman_meas.data['wavenumber'] <= x_range[1]
                )
                plot_data = raman_meas.data[mask]
            else:
                plot_data = raman_meas.data

            # Add some debug info for first few spectra
            if verbose and i < NBR_SPECTRA:
                intensity_range = (
                    f'{plot_data[y_plot].min():.2f}-{plot_data[y_plot].max():.2f}'
                )
                print(
                    f'Spectrum {i}:',
                    f'pos=({raman_meas.x_pos:.2f}, {raman_meas.y_pos:.2f})',
                    f'intensity_range={intensity_range}, n_points={len(plot_data)}',
                )

            fig.add_trace(
                go.Scatter(
                    x=plot_data['wavenumber'],
                    y=plot_data[y_plot],
                    mode='lines',
                    name=f'x={raman_meas.x_pos:.2f}, y={raman_meas.y_pos:.2f}',
                    line=dict(color=color),
                )
            )

        fig.update_layout(
            title=f'Raman Spectra (colored by {color_by})',
            xaxis_title='Wavenumber (cm⁻¹)',
            yaxis_title='Intensity',
        )

        fig.show()
        return fig

    def create_intensity_map(
        self, target_wavenumber, wavenumber_tolerance=5, verbose=False
    ):
        """Create 2D spatial map of Raman intensity at a target wavenumber.

        Extracts the Raman intensity at a specific wavenumber (±tolerance) for each
        measurement position, creating a DataFrame suitable for heatmap visualization.

        Args:
            target_wavenumber (float): Target Raman shift in cm⁻¹ (e.g., 380 for P₄S₃).
            wavenumber_tolerance (float, optional): Tolerance window in cm⁻¹ around
                target_wavenumber. Intensities are averaged within this window.
                Defaults to 5 cm⁻¹.
            verbose (bool, optional): If True, prints map creation details.
                Defaults to False.

        Returns:
            pd.DataFrame: DataFrame with columns:
                - 'x_pos': X-coordinates in μm
                - 'y_pos': Y-coordinates in μm
                - 'intensity': Average Raman intensity at target wavenumber

        Notes:
            - If no data points fall within the tolerance window, intensity is set to 0
            - Useful for identifying spatial distribution of specific compounds/phases
            - Output DataFrame can be used for custom plotting or further analysis

        Example:
            >>> # Map intensity of P₄S₃ peak at 380 cm⁻¹
            >>> map_df = mapping.create_intensity_map(380, wavenumber_tolerance=2)
            >>> print(map_df.head())
               x_pos  y_pos  intensity
            0    2.0    5.0     1245.3
            1    6.5    5.0     2103.7
        """
        if verbose:
            print(
                f'Creating intensity map at {target_wavenumber} ± '
                f'{wavenumber_tolerance} cm⁻¹'
            )

        x_positions = []
        y_positions = []
        intensities = []

        for raman_meas in self.raman_meas_list:
            # Note: x_pos and y_pos are already in micrometers from WDF file
            # These correspond to stage positions (absolute coordinates)
            x_positions.append(raman_meas.x_pos)
            y_positions.append(raman_meas.y_pos)

            # Find intensity at target wavenumber
            mask = (
                raman_meas.data['wavenumber']
                >= target_wavenumber - wavenumber_tolerance
            ) & (
                raman_meas.data['wavenumber']
                <= target_wavenumber + wavenumber_tolerance
            )
            filtered_data = raman_meas.data[mask]

            if len(filtered_data) > 0:
                intensity = filtered_data['intensity'].mean()
            else:
                intensity = 0
            intensities.append(intensity)

        return pd.DataFrame(
            {'x_pos': x_positions, 'y_pos': y_positions, 'intensity': intensities}
        )

    def plot_intensity_map(
        self, target_wavenumber=None, wavenumber_tolerance=5, verbose=False
    ):
        """Create interactive 2D heatmap of Raman intensity distribution.

        Generates a Plotly heatmap showing how Raman intensity at a specific
        wavenumber varies spatially across the sample. If no wavenumber is specified,
        automatically selects the wavenumber with maximum intensity (excluding Si peak).

        Args:
            target_wavenumber (float, optional): Target Raman shift in cm⁻¹.
                If None, automatically finds the wavenumber with highest intensity
                across all spectra, excluding the 510-530 cm⁻¹ range (Si peak).
            wavenumber_tolerance (float, optional): Tolerance window in cm⁻¹.
                Defaults to 5 cm⁻¹.
            verbose (bool, optional): If True, prints selected wavenumber and
                max intensity. Defaults to False.

        Returns:
            plotly.graph_objects.Figure: Interactive heatmap with:
                - X-axis: X position (μm)
                - Y-axis: Y position (μm)
                - Color: Raman intensity at target wavenumber
                - Viridis colorscale

        Auto-Detection Algorithm:
            When target_wavenumber=None:
            1. For each spectrum, exclude 510-530 cm⁻¹ (Si substrate peak)
            2. Find maximum intensity and its wavenumber
            3. Select the wavenumber with highest overall intensity
            4. Use this wavenumber for the entire map

        Notes:
            - Useful for visualizing spatial distribution of specific phases/compounds
            - Interactive: hover for exact values, zoom, pan, save as PNG
            - Auto-detection helps identify dominant Raman features

        Example:
            >>> # Auto-detect most intense peak (excluding Si)
            >>> fig = mapping.plot_intensity_map(verbose=True)
            Selected wavenumber: 380.5 cm⁻¹ (max intensity: 15234.12)
            >>> fig.show()

            >>> # Map specific peak (e.g., P₄S₃ at 380 cm⁻¹)
            >>> fig = mapping.plot_intensity_map(
            ...     target_wavenumber=380, wavenumber_tolerance=2
            ... )
            >>> fig.write_html('intensity_map.html')
        """

        if target_wavenumber is None:
            if verbose:
                print('Auto-detecting target wavenumber (excluding Si peak region)...')
            # Find the wavenumber with the absolute maximum intensity
            # across all spectra (excluding 510-530 cm⁻¹ range
            # corresponding to the Si peak)
            max_intensity = 0
            target_wavenumber = 520  # default fallback (Si)
            range_Si = 10
            for raman_meas in self.raman_meas_list:
                filtered = raman_meas.data[
                    (raman_meas.data['wavenumber'] < target_wavenumber - range_Si)
                    | (raman_meas.data['wavenumber'] > target_wavenumber + range_Si)
                ]
                if len(filtered) > 0:
                    current_max_idx = filtered['intensity'].idxmax()
                    current_max_intensity = filtered.loc[current_max_idx, 'intensity']
                    if current_max_intensity > max_intensity:
                        max_intensity = current_max_intensity
                        target_wavenumber = filtered.loc[current_max_idx, 'wavenumber']

            if verbose:
                print(
                    f'Selected wavenumber: {target_wavenumber:.1f} cm⁻¹ '
                    f'(max intensity: {max_intensity:.2f})'
                )

        map_data = self.create_intensity_map(
            target_wavenumber, wavenumber_tolerance, verbose=verbose
        )

        # Create a pivot table for the heatmap
        x_unique = sorted(map_data['x_pos'].unique())
        y_unique = sorted(map_data['y_pos'].unique())

        # Create intensity matrix
        intensity_matrix = np.zeros((len(y_unique), len(x_unique)))

        for _, row in map_data.iterrows():
            x_idx = x_unique.index(row['x_pos'])
            y_idx = y_unique.index(row['y_pos'])
            intensity_matrix[y_idx, x_idx] = row['intensity']

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
            xaxis_title='X Position (μm)',
            yaxis_title='Y Position (μm)',
        )

        return fig

    def create_image_grid(self, save_path=None, spacing=(-0.4, 0.1), verbose=False):
        """Create matplotlib grid displaying all optical microscopy images.

        Arranges optical images from all measurement points into a grid layout,
        with each image labeled by its point number and spatial coordinates.
        Useful for visual inspection and correlation with Raman data.

        Args:
            save_path (str, optional): File path to save the grid image (PNG format).
                If None, grid is not saved to disk. Defaults to None.
            spacing (tuple[float, float], optional): Vertical and horizontal spacing
                between subplots as (hspace, wspace). Negative values create overlap.
                Defaults to (-0.4, 0.1).
            verbose (bool, optional): If True, prints status messages.
                Defaults to False.

        Returns:
            matplotlib.figure.Figure or None:
                - Figure object if images were found and grid created
                - None if no optical images are available

        Grid Layout:
            - 3 columns by default
            - Rows calculated automatically based on number of images
            - Each subplot shows: optical image + title with point # and (x, y)
            - Axes are hidden for cleaner appearance

        Notes:
            - Only includes measurement points that have optical images
            - Point numbers refer to original indices in raman_meas_list
            - Image quality depends on quality of images in original WDF file
            - Saved with 150 DPI and tight bounding box

        Example:
            >>> # Create and display grid
            >>> fig = mapping.create_image_grid(verbose=True)
            >>> # Save to file
            >>> fig = mapping.create_image_grid(
            ...     save_path='/output/optical_grid.png',
            ...     spacing=(-0.3, 0.15),
            ...     verbose=True
            ... )
            >>> # Returns None if no images available
            >>> if fig is None:
            ...     print("No optical images in this dataset")
        """
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec

        # Filter to only measurements with images
        measurements_with_images = [
            m for m in self.raman_meas_list if m.image is not None
        ]

        if not measurements_with_images:
            if verbose:
                print('No optical images available')
            return None

        n_images = len(measurements_with_images)
        n_cols = 3
        n_rows = (n_images + n_cols - 1) // n_cols

        fig = plt.figure(figsize=(15, 5 * n_rows))
        gs = GridSpec(n_rows, n_cols, figure=fig, hspace=spacing[0], wspace=spacing[1])

        for i, raman_meas in enumerate(measurements_with_images):
            row = i // n_cols
            col = i % n_cols
            ax = fig.add_subplot(gs[row, col])

            ax.imshow(raman_meas.image)
            # Find original index
            orig_idx = self.raman_meas_list.index(raman_meas)
            ax.set_title(
                f'Point {orig_idx}\n'
                f'X={raman_meas.x_pos:.1f} μm, Y={raman_meas.y_pos:.1f} μm',
                fontsize=10,
            )
            ax.axis('off')

        # plt.suptitle('Optical Images at Each Raman Measurement Point',
        #            fontsize=14, fontweight='bold')

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig
