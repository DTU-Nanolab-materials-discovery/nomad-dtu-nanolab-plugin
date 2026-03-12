"""Schema definitions for spectroscopic ellipsometry measurements.

This module provides NOMAD schema classes for storing and visualizing ellipsometry
measurement data from J.A. Woollam CompleteEASE software. It handles:
- Optical constants (n, k) as a function of wavelength
- Film thickness and surface roughness mapping
- Fit quality metrics (MSE)
- Dielectric function parameters (epsilon_inf, ir_pole_amp)

The data is imported from tab-separated text files exported from CompleteEASE,
including n&k optical constants and thickness/fit parameter maps.
"""

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
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
from scipy.interpolate import griddata
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU Ellipsometry measurement schema')


class DTUDeltaPsi(ArchiveSection):
    """Delta and Psi values for a specific angle of incidence.

    This class stores the raw ellipsometric parameters (Psi and Delta) as a function
    of wavelength for a specific angle of incidence. These are the fundamental
    measured quantities in spectroscopic ellipsometry before modeling.
    """

    m_def = Section()

    angle_of_incidence = Quantity(
        type=np.float64,
        unit='degree',
        description='The angle of incidence for this measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    wavelength = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='nm',
        description='The wavelength values in nm',
    )

    psi = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='degree',
        description=(
            'The Psi angle in degrees. Psi is related to the amplitude ratio '
            'of p- and s-polarized light upon reflection.'
        ),
    )

    psi_error = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='degree',
        description='The standard error in Psi measurements',
    )

    delta = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='degree',
        description=(
            'The Delta angle in degrees. Delta is the phase difference '
            'between p- and s-polarized light upon reflection.'
        ),
    )

    delta_error = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='degree',
        description='The standard error in Delta measurements',
    )


class EllipsometryMappingResult(MappingResult):
    """Results from a single ellipsometry measurement position.

    This class stores the optical constants (n, k), film properties (thickness,
    roughness), and fit parameters (MSE, dielectric constants) for one spatial
    position in an ellipsometry mapping measurement.

    """

    m_def = Section()

    position = Quantity(
        type=str,
        description='The position of the ellipsometry measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Position',
        ),
    )

    thickness = Quantity(
        type=np.float64,
        unit='m',
        description='The layer thickness at this position',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
    )

    roughness = Quantity(
        type=np.float64,
        unit='m',
        description='The surface roughness at this position',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
    )

    mse = Quantity(
        type=np.float64,
        description=(
            'The Mean Squared Error (MSE) of the fit, a measure of the '
            'goodness-of-fit between the model and experimental data'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    epsilon_inf = Quantity(
        type=np.float64,
        description=(
            'The high-frequency dielectric constant (epon)), representing the'
            "material's relative permittivity at optical frequencies"
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    ir_pole_amp = Quantity(
        type=np.float64,
        description=(
            'The infrared pole amplitude, representing the strength of the'
            'infrared oscillator in the dielectric function model'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    wavelength = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='nm',
        description='The wavelength values in nm',
    )
    n = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='The refractive index n',
    )
    k = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='The extinction coefficient k',
    )
    delta_psi = SubSection(
        section_def=DTUDeltaPsi,
        repeats=True,
        description=(
            'The delta and psi values for each angle of incidence, stored as '
            'repeated subsections (one per angle).'
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `EllipsometryMappingResult` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)


class EllipsometryMetadata(Schema):
    m_def = Section()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizer for the `EllipsometryMetadata` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)


class DTUEllipsometryMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    """Main schema for spectroscopic ellipsometry measurements.

    This class represents a complete ellipsometry measurement session, which may
    include data from multiple spatial positions. It handles data import from
    J.A. Woollam CompleteEASE export files and creates interactive visualizations
    of optical constants, thickness maps, and roughness maps.

    The measurement data is imported from two types of exported text files:
    1. n_and_k_file: Contains wavelength-dependent optical constants for each position
    2. thickness_file: Contains film thickness, roughness, and fit parameters

    The class automatically:
    - Parses the exported data files
    - Matches data from different files by spatial position
    - Creates interactive Plotly visualizations (1D line plots or 2D heatmaps)
    - Links to the sample being measured
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Ellipsometry Measurement',
    )
    native_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'native .SESNAP snapshot file',
        },
    )
    native_data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'native .SE file'},
    )
    tabulated_data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'tabulated exported .txt file',
        },
    )
    n_and_k_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'exported n and k text file'},
        description=(
            'The exported n and k text file from the CompleteEASE software'
            'from Woolam, containing wavelength, n, and k values for each position'
            '(see https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/'
            'for details on the data export procedure)'
        ),
    )
    thickness_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'exported thickness text file',
        },
        description=(
            'The exported thickness text file from the CompleteEASE software'
            'from Woolam, containing thickness and other parameters for each position'
            '(see https://dtu-nanolab-materials-discovery.github.io/nomad-dtu-nanolab-plugin/'
            'for details on the data export procedure)'
        ),
    )
    metadata = SubSection(
        section_def=EllipsometryMetadata,
        description='The metadata of the ellipsometry measurement',
        # need the native file and a way to open it to extract the metadata
    )
    results = SubSection(
        section_def=EllipsometryMappingResult,
        description='The ellipsometry results.',
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=RectangularSampleAlignment,
        description='The alignment of the sample.',
    )

    def read_thickness_file(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> pd.DataFrame:
        """
        Read the thickness file and return a DataFrame.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.

        Returns:
            pd.DataFrame: DataFrame with thickness data
        """
        if not self.thickness_file:
            logger.warning('No thickness file provided.')
            return pd.DataFrame()

        with archive.m_context.raw_file(self.thickness_file) as file:
            # Read the file, skipping the first header line
            # Important: index_col=False to prevent first column from being
            # used as index
            df = pd.read_csv(file.name, sep='\t', skiprows=0, index_col=False)

            # Remove any empty rows (rows where all values are NaN)
            df = df.dropna(how='all')

            # Remove trailing empty columns (columns that are all NaN)
            df = df.dropna(axis=1, how='all')

            return df

    def read_n_and_k_file(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> pd.DataFrame:
        """
        Read the n and k file and return a DataFrame.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.

        Returns:
            pd.DataFrame: DataFrame with wavelength and n, k values for each position
        """
        if not self.n_and_k_file:
            logger.warning('No n and k file provided.')
            return pd.DataFrame()

        with archive.m_context.raw_file(self.n_and_k_file) as file:
            # CompleteEASE exports n&k files with a 2-line header:
            # Line 1: "Optical Constants"
            # Line 2: Column names (either "Energy (eV)" or "Wavelength (nm)"
            #         + position columns)
            with open(file.name) as f:
                f.readline()  # Skip first line ("Optical Constants")
                header_line = f.readline().strip()  # Read second line with column names

            # Read the data file as tab-separated values
            # skiprows=1: Use line 2 as header (skip "Optical Constants" title)
            # index_col=False: Prevent pandas from using first column as row index
            df = pd.read_csv(file.name, sep='\t', skiprows=1, index_col=False)

            # CompleteEASE can export spectral data as either energy or wavelength
            # Check first column and convert energy to wavelength if needed
            first_col_name = header_line.split('\t')[0]
            if first_col_name == 'Energy (eV)':
                # Convert energy (eV) to wavelength (nm) using
                # lambda = 1239.84 / E
                df.iloc[:, 0] = 1239.84 / df.iloc[:, 0]
                # After conversion, wavelength should be in descending order
                # from the ascending energy. We need to reverse the entire
                # dataframe to have wavelength in ascending order
                df = df.iloc[::-1].reset_index(drop=True)
            elif first_col_name == 'Wavelength (nm)':
                pass
            else:
                logger.warning(f'Unknown spectral unit in header: {first_col_name}')

            return df

    def read_tabulated_data_file(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> pd.DataFrame:
        """
        Read the tabulated raw ellipsometry data file (Psi/Delta vs wavelength).

        This method parses the wide-format tabulated text file exported from
        CompleteEASE containing raw Psi and Delta values at multiple angles
        and positions.

        Args:
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.

        Returns:
            pd.DataFrame: DataFrame with columns:
                - parameter: 'Psi', 'Psi_err', 'Delta', 'Delta_err'
                - angle: angle of incidence in degrees
                - x_cm: X position in cm
                - y_cm: Y position in cm
                - wavelength_nm: wavelength in nm
                - value: the measured value in degrees
        """
        if not self.tabulated_data_file:
            logger.warning('No tabulated data file provided.')
            return pd.DataFrame()

        with archive.m_context.raw_file(self.tabulated_data_file) as file:
            # Read the header row to get wavelength columns
            # Note: CompleteEASE exports with UTF-8 BOM
            with open(file.name, encoding='utf-8-sig') as f:
                # Skip any empty lines at the beginning
                header_line = ''
                line_num = 0
                while not header_line.strip():
                    header_line = f.readline()
                    line_num += 1
                    if not header_line:  # EOF
                        logger.error('Could not find header in tabulated file')
                        return pd.DataFrame()

            # Split header to get wavelength values
            # Format: [empty]\tAOI\tX\tY\t211.012\t212.592\t...
            # The first column is often empty (line starts with tab)
            header_parts = header_line.strip().split('\t')
            # Find where numeric wavelengths start (after AOI, X, Y)
            wavelengths = []
            for part in header_parts:
                if not part.strip():
                    continue
                try:
                    wl = float(part)
                    wavelengths.append(wl)
                except ValueError:
                    # Not a number, skip (AOI, X, Y, or column names)
                    continue

            logger.info(f'Found {len(wavelengths)} wavelengths in header')

            # Read all data rows - use utf-8-sig to handle BOM
            # Skip the header line (which we already parsed)
            df = pd.read_csv(
                file.name,
                sep='\t',
                skiprows=line_num,
                header=None,
                index_col=False,
                encoding='utf-8-sig',
            )

            # Remove empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')

            # Columns are: [Parameter, AOI, X, Y, wavelength1, wavelength2, ...]
            # Set column names
            df.columns = ['parameter', 'angle', 'x_cm', 'y_cm'] + [
                f'wl_{i}' for i in range(len(wavelengths))
            ]

            # Reshape from wide to long format
            # Keep parameter, angle, x_cm, y_cm as identifiers
            id_cols = ['parameter', 'angle', 'x_cm', 'y_cm']
            value_cols = [f'wl_{i}' for i in range(len(wavelengths))]

            # Melt the dataframe
            df_long = df.melt(
                id_vars=id_cols,
                value_vars=value_cols,
                var_name='wl_index',
                value_name='value',
            )

            # Map wavelength index back to actual wavelength values
            wl_mapping = {f'wl_{i}': wavelengths[i] for i in range(len(wavelengths))}
            df_long['wavelength_nm'] = df_long['wl_index'].map(wl_mapping)

            # Drop the wl_index column
            df_long = df_long.drop(columns=['wl_index'])

            # Clean up parameter names (remove extra spaces)
            df_long['parameter'] = df_long['parameter'].str.strip()

            num_positions = len(
                df_long[df_long['parameter'] == 'Psi'].groupby(
                    ['angle', 'x_cm', 'y_cm']
                )
            )
            logger.info(
                f'Read tabulated data: {len(df_long)} records, '
                f'{df_long["angle"].nunique()} angles, '
                f'{num_positions} positions'
            )

            return df_long

    def write_ellipsometry_data(
        self,
        thickness_df: pd.DataFrame,
        nk_df: pd.DataFrame,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        tabulated_df: pd.DataFrame | None = None,
    ) -> None:
        """
        Write method for populating the `DTUEllipsometryMeasurement` section.

        Args:
            thickness_df (pd.DataFrame): DataFrame with thickness data
            nk_df (pd.DataFrame): DataFrame with n and k data
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        results = []

        # Get wavelength column (first column)
        wavelength = nk_df.iloc[:, 0].to_numpy() * ureg('nm')

        # Parse the n and k columns to extract position information
        # CompleteEASE names columns as 'n: (x,y)' and 'k: (x,y)' where (x,y)
        # are the stage coordinates in cm. We extract these to match with
        # thickness data.
        # Example columns: 'n: (-1.8,0)', 'k: (-1.8,0)', 'n: (-1.6,0)', ...
        # Dictionary: position_string -> {'n_col': ..., 'k_col': ...}
        positions = {}
        for col in nk_df.columns[1:]:  # Skip first column (wavelength/energy)
            if col.startswith('n: '):
                pos_str = col.split('n: ')[1]  # Extract '(x,y)' part
                if pos_str not in positions:
                    positions[pos_str] = {}
                positions[pos_str]['n_col'] = col
            elif col.startswith('k: '):
                pos_str = col.split('k: ')[1]  # Extract '(x,y)' part
                if pos_str not in positions:
                    positions[pos_str] = {}
                positions[pos_str]['k_col'] = col

        # Create a mapping from position coordinates to thickness and fit
        # parameters. This allows us to merge data from the two separate
        # export files.
        # Dictionary: (x, y) -> {'thickness': ..., 'roughness': ..., ...}
        thickness_map = {}
        if not thickness_df.empty:
            # Expected columns from CompleteEASE thickness export:
            # 'X (cm)', 'Y (cm)', 'MSE', 'Absolute MSE', 'Roughness (nm)',
            # 'Thickness # 1 (nm)', 'E Inf', 'IR Amp', etc.

            # Build a lookup table indexed by (x, y) coordinates
            # This enables matching thickness data with n&k data by position
            for _, row in thickness_df.iterrows():
                x_pos = float(row['X (cm)'])
                y_pos = float(row['Y (cm)'])
                mse = float(row['MSE'])
                roughness_nm = float(row['Roughness (nm)'])
                thickness_nm = float(row['Thickness # 1 (nm)'])
                epsilon_inf = float(row['E Inf'])
                ir_pole_amp = float(row['IR Amp'])

                thickness_map[(x_pos, y_pos)] = {
                    'thickness': thickness_nm,
                    'roughness': roughness_nm,
                    'mse': mse,
                    'epsilon_inf': epsilon_inf,
                    'ir_pole_amp': ir_pole_amp,
                }

        # Create a result for each position
        for pos_str, cols in positions.items():
            # Parse position (e.g., '(-1.8,0)' -> x=-1.8, y=0)
            try:
                pos_tuple = eval(pos_str)  # Safe here as we control the format
                x_pos = float(pos_tuple[0])
                y_pos = float(pos_tuple[1])
            except Exception as e:
                logger.warning(f'Could not parse position {pos_str}: {e}')
                continue

            # Get n and k values - IMPORTANT: use .to_numpy() to get
            # clean numpy arrays
            n_values = nk_df[cols['n_col']].to_numpy()
            k_values = nk_df[cols['k_col']].to_numpy()

            # Match thickness data to n&k data by position coordinates
            # Use fuzzy matching to handle potential floating-point rounding differences
            # between the two export files
            thickness_data = None
            tolerance = 0.01  # Tolerance in cm (0.1 mm) for coordinate matching

            # Try exact coordinate match first
            if (x_pos, y_pos) in thickness_map:
                thickness_data = thickness_map[(x_pos, y_pos)]
            else:
                # Try fuzzy match (within tolerance)
                for (x_thick, y_thick), data in thickness_map.items():
                    if (
                        abs(x_thick - x_pos) < tolerance
                        and abs(y_thick - y_pos) < tolerance
                    ):
                        thickness_data = data
                        break

            if thickness_data is None:
                logger.warning(
                    f'No thickness data found for position {pos_str} '
                    f'at ({x_pos}, {y_pos})'
                )

            # Convert to appropriate units
            thickness_nm = (
                thickness_data['thickness'] if thickness_data is not None else None
            )
            roughness_nm = (
                thickness_data['roughness'] if thickness_data is not None else None
            )
            mse = thickness_data['mse'] if thickness_data is not None else None
            epsilon_inf = (
                thickness_data['epsilon_inf'] if thickness_data is not None else None
            )
            ir_pole_amp = (
                thickness_data['ir_pole_amp'] if thickness_data is not None else None
            )

            # Create result
            result = EllipsometryMappingResult(
                position=pos_str,
                x_absolute=x_pos * ureg('cm'),
                y_absolute=y_pos * ureg('cm'),
                thickness=thickness_nm * ureg('nm'),
                roughness=roughness_nm * ureg('nm'),
                mse=mse,
                epsilon_inf=epsilon_inf,
                ir_pole_amp=ir_pole_amp,
                wavelength=wavelength,
                n=n_values,
                k=k_values,
            )
            result.normalize(archive, logger)
            results.append(result)

        # Process tabulated raw ellipsometry data (Psi/Delta) if available
        if tabulated_df is not None and not tabulated_df.empty:
            logger.info('Processing raw Psi/Delta data from tabulated file')

            # Group by position and angle to populate delta_psi subsections
            # For each position in results, find matching tabulated data
            for result in results:
                x_pos = result.x_absolute.to('cm').magnitude
                y_pos = result.y_absolute.to('cm').magnitude

                # Find all unique angles for this position
                # Use small tolerance for floating point comparison
                POSITION_TOLERANCE_CM = 0.01
                pos_data = tabulated_df[
                    (abs(tabulated_df['x_cm'] - x_pos) < POSITION_TOLERANCE_CM)
                    & (abs(tabulated_df['y_cm'] - y_pos) < POSITION_TOLERANCE_CM)
                ]

                if pos_data.empty:
                    continue

                unique_angles = pos_data['angle'].unique()

                # Create DTUDeltaPsi for each angle
                delta_psi_list = []
                for angle in unique_angles:
                    # Get data for this angle
                    angle_data = pos_data[pos_data['angle'] == angle]

                    # Extract Psi data
                    psi_data = angle_data[angle_data['parameter'] == 'Psi'].sort_values(
                        'wavelength_nm'
                    )
                    psi_err_data = angle_data[
                        angle_data['parameter'] == 'Psi_err'
                    ].sort_values('wavelength_nm')

                    # Extract Delta data
                    delta_data = angle_data[
                        angle_data['parameter'] == 'Delta'
                    ].sort_values('wavelength_nm')
                    delta_err_data = angle_data[
                        angle_data['parameter'] == 'Delta_err'
                    ].sort_values('wavelength_nm')

                    if psi_data.empty or delta_data.empty:
                        continue

                    # Create DTUDeltaPsi instance
                    delta_psi = DTUDeltaPsi(
                        angle_of_incidence=angle * ureg('degree'),
                        wavelength=psi_data['wavelength_nm'].to_numpy() * ureg('nm'),
                        psi=psi_data['value'].to_numpy() * ureg('degree'),
                        delta=delta_data['value'].to_numpy() * ureg('degree'),
                    )

                    # Add errors if available
                    if not psi_err_data.empty:
                        delta_psi.psi_error = psi_err_data['value'].to_numpy() * ureg(
                            'degree'
                        )
                    if not delta_err_data.empty:
                        delta_psi.delta_error = delta_err_data[
                            'value'
                        ].to_numpy() * ureg('degree')

                    delta_psi_list.append(delta_psi)

                # Assign delta_psi list to result
                if delta_psi_list:
                    result.delta_psi = delta_psi_list
                    logger.debug(
                        f'Added {len(delta_psi_list)} angle measurements '
                        f'for position {result.position}'
                    )

        # Merge results into this measurement
        ellipsometry = DTUEllipsometryMeasurement(
            results=results,
        )
        merge_sections(self, ellipsometry, logger)

    def _create_parameter_map(
        self,
        parameter_name: str,
        parameter_label: str,
        unit: str = 'nm',
    ) -> PlotlyFigure | None:
        """
        Create a spatial map plot for any parameter from the ellipsometry results.

        This helper method creates either a 1D line plot (for line scans) or a 2D
        heatmap with scatter overlay (for area maps) depending on the dimensionality
        of the measurement grid. The plot type is automatically determined by analyzing
        the unique x and y coordinates.

        Args:
            parameter_name: The name of the parameter attribute in results
                (e.g., 'thickness', 'roughness', 'mse')
            parameter_label: The label to display in plot titles and axes
                (e.g., 'Thickness', 'Roughness', 'Mean Squared Error')
            unit: The unit to display in axis labels and hover text (default: 'nm')

        Returns:
            PlotlyFigure: An interactive plot if data exists for the parameter
            None: If no data is available for the parameter
        """
        # Collect parameter values and coordinates from all measurement positions
        param_data = []
        x_title = 'X Position (mm)'
        y_title = 'Y Position (mm)'
        coord_type = 'Position'  # Will be set to 'Sample' or 'Stage'

        for r in self.results:
            param_value = getattr(r, parameter_name, None)
            if param_value is not None:
                # Handle both Quantity objects (with units) and plain numbers
                if isinstance(param_value, ureg.Quantity):
                    value = param_value.to(unit).magnitude
                else:
                    value = float(param_value)

                # Prefer relative positions if available, fallback to absolute
                if isinstance(r.x_relative, ureg.Quantity) and isinstance(
                    r.y_relative, ureg.Quantity
                ):
                    x = r.x_relative.to('mm').magnitude
                    y = r.y_relative.to('mm').magnitude
                    x_title = 'X Sample Position (mm)'
                    y_title = 'Y Sample Position (mm)'
                    coord_type = 'Sample'
                elif isinstance(r.x_absolute, ureg.Quantity) and isinstance(
                    r.y_absolute, ureg.Quantity
                ):
                    x = r.x_absolute.to('mm').magnitude
                    y = r.y_absolute.to('mm').magnitude
                    x_title = 'X Stage Position (mm)'
                    y_title = 'Y Stage Position (mm)'
                    coord_type = 'Stage'
                else:
                    continue

                param_data.append(
                    {
                        'x': x,
                        'y': y,
                        'value': value,
                    }
                )

        if not param_data:
            return None

        # Extract coordinate and value arrays for plotting
        x_vals = [d['x'] for d in param_data]
        y_vals = [d['y'] for d in param_data]
        values = [d['value'] for d in param_data]

        # Format axis labels with or without units
        if unit and unit.strip():
            y_axis_label = f'{parameter_label} ({unit})'
            colorbar_title = f'{parameter_label} ({unit})'
            hover_unit = f' {unit}'
        else:
            y_axis_label = parameter_label
            colorbar_title = parameter_label
            hover_unit = ''

        # Determine dimensionality by counting unique coordinates
        # This tells us if we have a line scan (1D) or area map (2D)
        # Use a tolerance to handle floating-point noise (e.g. ~1e-15 values
        # that should be treated as identical)
        x_range = max(x_vals) - min(x_vals)
        y_range = max(y_vals) - min(y_vals)
        tol = 1e-6  # 1 nm tolerance
        is_1d_x = x_range < tol  # all x approximately the same
        is_1d_y = y_range < tol  # all y approximately the same

        if is_1d_x or is_1d_y:
            # 1D data - create a line plot with markers
            if is_1d_x:
                # Y varies
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=y_vals,
                        y=values,
                        mode='lines+markers',
                        name=parameter_label,
                    )
                )
                fig.update_layout(
                    title=f'{parameter_label} vs Y {coord_type} Position',
                    xaxis_title='Y Position (mm)',
                    yaxis_title=y_axis_label,
                    template='plotly_white',
                    hovermode='closest',
                    dragmode='zoom',
                    xaxis=dict(fixedrange=False),
                    yaxis=dict(fixedrange=False),
                )
            else:
                # X varies
                fig = go.Figure()
                fig.add_trace(
                    go.Scatter(
                        x=x_vals,
                        y=values,
                        mode='lines+markers',
                        name=parameter_label,
                    )
                )
                fig.update_layout(
                    title=f'{parameter_label} vs X {coord_type} Position',
                    xaxis_title='X Position (mm)',
                    yaxis_title=y_axis_label,
                    template='plotly_white',
                    hovermode='closest',
                    dragmode='zoom',
                    xaxis=dict(fixedrange=False),
                    yaxis=dict(fixedrange=False),
                )
        else:
            # 2D data - create a heatmap with scatter overlay
            # Generate a regular interpolation grid for smooth heatmap visualization
            # The actual measurement points are shown as scatter markers on top
            xi = np.linspace(min(x_vals), max(x_vals), 100)  # 100 points in x
            yi = np.linspace(min(y_vals), max(y_vals), 100)  # 100 points in y
            xi, yi = np.meshgrid(xi, yi)  # Create 2D grid
            # Interpolate irregular measurement points onto regular grid
            # using linear interpolation
            zi = griddata((x_vals, y_vals), values, (xi, yi), method='linear')

            # Create a heatmap
            heatmap = go.Heatmap(
                x=xi[0],
                y=yi[:, 0],
                z=zi,
                colorscale='Viridis',
                colorbar=dict(title=colorbar_title),
            )

            # Create a scatter plot overlay
            scatter = go.Scatter(
                x=x_vals,
                y=y_vals,
                mode='markers',
                marker=dict(
                    size=15,
                    color=values,
                    colorscale='Viridis',
                    showscale=False,
                    line=dict(
                        width=2,
                        color='DarkSlateGrey',
                    ),
                ),
                customdata=values,
                hovertemplate=(
                    f'<b>{parameter_label}:</b> %{{customdata:.1f}}{hover_unit}'
                ),
            )

            # Combine heatmap and scatter plot
            fig = go.Figure(data=[heatmap, scatter])

            fig.update_layout(
                title=f'{parameter_label} {coord_type} Colormap',
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
        return PlotlyFigure(
            label=f'{parameter_label} Map',
            figure=plot_json,
        )

    def plot(self) -> None:
        """
        Generate all interactive Plotly visualizations for the ellipsometry data.

        Creates five types of plots:
        1. Optical constants (n and k) vs photon energy for all positions
        2. Absorption coefficient (alpha) vs photon energy for all positions
        3. Thickness spatial map (1D or 2D depending on measurement grid)
        4. Roughness spatial map (1D or 2D depending on measurement grid)
        5. MSE (fit quality) spatial map (1D or 2D depending on measurement grid)

        All plots are interactive with zoom, pan, and hover capabilities.
        """
        if not self.results:
            return

        # ===== Plot 1: Optical Constants (n and k) vs Photon Energy =====
        # Create a multi-trace plot showing n and k for all measurement positions
        fig = go.Figure()
        for result in self.results:
            if (
                result.wavelength is not None
                and result.n is not None
                and result.k is not None
            ):
                wavelength = result.wavelength.to('nm').magnitude
                # Convert wavelength to photon energy: E (eV) = 1240 / lambda(nm)
                photon_energy = 1240.0 / wavelength
                n = result.n
                k = result.k
                position = result.position

                fig.add_trace(
                    go.Scatter(
                        x=photon_energy,
                        y=n,
                        mode='lines',
                        name=f'n @ {position}',
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=photon_energy,
                        y=k,
                        mode='lines',
                        name=f'k @ {position}',
                        # line=dict(dash='dash'), #remove dashed line
                    )
                )

        fig.update_layout(
            title='Optical Constants (n and k)',
            xaxis_title='Photon Energy (eV)',
            yaxis_title='n, k',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
        )

        # Configure and store the optical constants plot
        plot_json = fig.to_plotly_json()
        # Disable scroll zoom for better UX
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Optical Constants',
                figure=plot_json,
            )
        )

        # ===== Plot 2: Absorption Coefficient vs Photon Energy =====
        # Calculate and plot absorption coefficient alpha = 4*pi*k/lambda
        fig_alpha = go.Figure()
        for result in self.results:
            if result.wavelength is not None and result.k is not None:
                wavelength = result.wavelength.to('nm').magnitude
                # Convert wavelength to photon energy: E (eV) = 1240 / lambda(nm)
                photon_energy = 1240.0 / wavelength
                k = result.k
                position = result.position

                # Calculate absorption coefficient: alpha = 4*pi*k/lambda
                # lambda in cm = wavelength_nm * 10^-7
                # alpha in cm^-1 = 4*pi * k / (wavelength_nm * 10^-7)
                alpha = (4 * np.pi * k) / (wavelength * 1e-7)

                fig_alpha.add_trace(
                    go.Scatter(
                        x=photon_energy,
                        y=alpha,
                        mode='lines',
                        name=f'alpha @ {position}',
                    )
                )

        fig_alpha.update_layout(
            title='Absorption Coefficient',
            xaxis_title='Photon Energy (eV)',
            yaxis_title='alpha (1/cm)',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False, exponentformat='power'),
        )

        # Configure and store the absorption coefficient plot
        plot_json_alpha = fig_alpha.to_plotly_json()
        plot_json_alpha['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Absorption Coefficient',
                figure=plot_json_alpha,
            )
        )

        # ===== Plot 3: Thickness Spatial Map =====
        # Use the helper method to create a thickness map (1D or 2D)
        thickness_fig = self._create_parameter_map('thickness', 'Thickness', 'nm')
        if thickness_fig:
            self.figures.append(thickness_fig)

        # ===== Plot 4: Roughness Spatial Map =====
        # Create a roughness map (1D or 2D)
        roughness_fig = self._create_parameter_map('roughness', 'Roughness', 'nm')
        if roughness_fig:
            self.figures.append(roughness_fig)

        # ===== Plot 5: MSE (Fit Quality) Spatial Map =====
        # Create a map showing the quality of the model fit at each position
        # Lower MSE values indicate better fits
        mse_fig = self._create_parameter_map('mse', 'Mean Squared Error', '')
        if mse_fig:
            self.figures.append(mse_fig)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalize and process the ellipsometry measurement data.

        This method is called automatically by NOMAD during data ingestion. It:
        1. Links the measurement to the sample being measured
        2. Reads and parses the exported data files (if not already processed)
        3. Generates interactive visualizations

        Args:
            archive (EntryArchive): The archive containing the section that is being
                normalized.
            logger (BoundLogger): A structlog logger for debugging and info messages.
        """
        # Link to the sample being measured using filename from any available file
        filename = None
        if self.native_file:
            filename = self.native_file
        elif self.tabulated_data_file:
            filename = self.tabulated_data_file
        elif self.n_and_k_file:
            filename = self.n_and_k_file
        elif self.thickness_file:
            filename = self.thickness_file
        if filename:
            self.add_sample_reference(filename, 'Ellipsometry', archive, logger)

        # Import and process data files if they haven't been processed yet
        if (
            self.n_and_k_file or self.thickness_file or self.tabulated_data_file
        ) and not self.results:
            thickness_df = self.read_thickness_file(archive, logger)
            nk_df = self.read_n_and_k_file(archive, logger)
            tabulated_df = self.read_tabulated_data_file(archive, logger)

            # Process data - use tabulated file if available, otherwise use n&k
            if not tabulated_df.empty:
                # Tabulated file can provide both n&k and raw Psi/Delta
                logger.info('Using tabulated data file as primary data source')
                if nk_df.empty:
                    # If we only have tabulated data, still create results structure
                    # The delta_psi will be populated from tabulated_df
                    logger.info('Only tabulated data available, creating results')
                    # We'll need at least one position to create results
                    # Extract unique positions from tabulated data
                    unique_positions = (
                        tabulated_df[['x_cm', 'y_cm']].drop_duplicates().values
                    )
                    # Create minimal nk_df for structure
                    import pandas as pd

                    nk_cols = ['Wavelength (nm)']
                    for x, y in unique_positions:
                        pos_str = f'({x},{y})'
                        nk_cols.extend([f'n: {pos_str}', f'k: {pos_str}'])
                    # Get wavelengths from tabulated data
                    wavelengths = sorted(tabulated_df['wavelength_nm'].unique())
                    nk_data = {'Wavelength (nm)': wavelengths}
                    for col in nk_cols[1:]:
                        nk_data[col] = [np.nan] * len(wavelengths)
                    nk_df = pd.DataFrame(nk_data)

                self.write_ellipsometry_data(
                    thickness_df, nk_df, archive, logger, tabulated_df
                )
            elif not nk_df.empty:
                self.write_ellipsometry_data(thickness_df, nk_df, archive, logger, None)

        super().normalize(archive, logger)

        # Create plots if we have results
        self.figures = []
        if self.results:
            self.plot()


m_package.__init_metainfo__()
