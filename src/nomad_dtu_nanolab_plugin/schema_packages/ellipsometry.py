from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objs as go
from nomad.datamodel.data import ArchiveSection, Schema
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


class EllipsometrySpectra(ArchiveSection):
    m_def = Section()

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


class EllipsometryMappingResult(MappingResult, Schema):
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
        description='The Mean Squared Error (MSE) of the fit',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    e_inf = Quantity(
        type=np.float64,
        description='The high-frequency dielectric constant (E Inf)',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    ir_amp = Quantity(
        type=np.float64,
        description='The infrared amplitude (IR Amp)',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    spectra = SubSection(
        section_def=EllipsometrySpectra,
        repeats=True,
        description='The ellipsometry spectra (n and k)',
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
        The normalizer for the `PLMetadata` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)


class DTUEllipsometryMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Ellipsometry Measurement',
    )
    native_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'native SESNAP file'},
    )
    n_and_k_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'exported n and k text file'},
    )
    thickness_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'exported thickness text file',
        },
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

            logger.debug(f'Read thickness file with shape: {df.shape}')
            logger.debug(f'Thickness file columns: {df.columns.tolist()}')

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
            # Read the header to check if first column is energy or wavelength
            # Files have 2-line header: "Optical Constants" then the actual column names
            with open(file.name) as f:
                f.readline()  # Skip first line ("Optical Constants")
                header_line = f.readline().strip()  # Read second line with column names

            # Read the data, skipping first line (skiprows=1 means
            # use line 2 as header)
            # Important: index_col=False to prevent first column from being
            # used as index
            df = pd.read_csv(file.name, sep='\t', skiprows=1, index_col=False)

            # Check if first column is "Energy (eV)" and convert to wavelength (nm)
            first_col_name = header_line.split('\t')[0]
            if first_col_name == 'Energy (eV)':
                logger.debug(
                    'Detected Energy (eV) column, converting to wavelength (nm)'
                )
                # Convert energy (eV) to wavelength (nm) using
                # λ = 1239.84 / E
                df.iloc[:, 0] = 1239.84 / df.iloc[:, 0]
                # After conversion, wavelength should be in descending order
                # from the ascending energy. We need to reverse the entire
                # dataframe to have wavelength in ascending order
                df = df.iloc[::-1].reset_index(drop=True)
                logger.debug(
                    'Converted energy to wavelength and reversed order '
                    'for ascending wavelength'
                )
            elif first_col_name == 'Wavelength (nm)':
                logger.debug('Detected Wavelength (nm) column, no conversion needed')
            else:
                logger.warning(f'Unknown spectral unit in header: {first_col_name}')

            logger.debug(f'Read n and k file with shape: {df.shape}')
            logger.debug(
                f'Wavelength range: {df.iloc[0, 0]:.2f} - {df.iloc[-1, 0]:.2f} nm'
            )

            return df

    def write_ellipsometry_data(
        self,
        thickness_df: pd.DataFrame,
        nk_df: pd.DataFrame,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
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
        logger.debug('Starting to write ellipsometry data.')

        # Get wavelength column (first column)
        wavelength = nk_df.iloc[:, 0].to_numpy() * ureg('nm')
        logger.debug(f'Extracted {len(wavelength)} wavelength points')

        # Parse the n and k columns to extract position and values
        # Columns are named like 'n: (-1.8,0)', 'k: (-1.8,0)', etc.
        positions = {}
        for col in nk_df.columns[1:]:
            if col.startswith('n: '):
                pos_str = col.split('n: ')[1]
                if pos_str not in positions:
                    positions[pos_str] = {}
                positions[pos_str]['n_col'] = col
            elif col.startswith('k: '):
                pos_str = col.split('k: ')[1]
                if pos_str not in positions:
                    positions[pos_str] = {}
                positions[pos_str]['k_col'] = col

        logger.debug(f'Found {len(positions)} positions in n and k file.')

        # Create a mapping from position to thickness and other parameters
        thickness_map = {}
        if not thickness_df.empty:
            # Expected columns: X (cm), Y (cm), MSE, Absolute MSE,
            # Roughness (nm), Thickness # 1 (nm)
            logger.debug(f'Thickness file has {thickness_df.shape[1]} columns')
            logger.debug(f'Thickness file columns: {thickness_df.columns.tolist()}')

            # Build thickness map with all parameters using explicit column names
            for _, row in thickness_df.iterrows():
                x_pos = float(row['X (cm)'])
                y_pos = float(row['Y (cm)'])
                mse = float(row['MSE'])
                roughness_nm = float(row['Roughness (nm)'])
                thickness_nm = float(row['Thickness # 1 (nm)'])
                e_inf = float(row['E Inf'])
                ir_amp = float(row['IR Amp'])

                thickness_map[(x_pos, y_pos)] = {
                    'thickness': thickness_nm,
                    'roughness': roughness_nm,
                    'mse': mse,
                    'e_inf': e_inf,
                    'ir_amp': ir_amp,
                }

            logger.debug(f'Created thickness map with {len(thickness_map)} entries')

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

            logger.debug(
                f'Position {pos_str}: n range '
                f'[{n_values.min():.3f}, {n_values.max():.3f}], '
                f'k range [{k_values.min():.6f}, {k_values.max():.6f}]'
            )

            # Create spectra
            spectra = EllipsometrySpectra(
                wavelength=wavelength,
                n=n_values,
                k=k_values,
            )

            # Get thickness and other parameters for this position using fuzzy matching
            thickness_data = None
            tolerance = 0.01  # Tolerance for coordinate matching (1 cm = 10 mm)

            # Try exact match first
            if (x_pos, y_pos) in thickness_map:
                thickness_data = thickness_map[(x_pos, y_pos)]
                logger.debug(
                    f'Exact match for {pos_str}: '
                    f'thickness={thickness_data["thickness"]:.2f} nm, '
                    f'roughness={thickness_data["roughness"]:.2f} nm, '
                    f'MSE={thickness_data["mse"]:.4f}'
                )
            else:
                # Try fuzzy match (within tolerance)
                for (x_thick, y_thick), data in thickness_map.items():
                    if (
                        abs(x_thick - x_pos) < tolerance
                        and abs(y_thick - y_pos) < tolerance
                    ):
                        thickness_data = data
                        logger.debug(
                            f'Fuzzy match for {pos_str} with '
                            f'({x_thick}, {y_thick}): '
                            f'thickness={thickness_data["thickness"]:.2f} nm'
                        )
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
            e_inf = thickness_data['e_inf'] if thickness_data is not None else None
            ir_amp = thickness_data['ir_amp'] if thickness_data is not None else None

            # Create result
            result = EllipsometryMappingResult(
                position=pos_str,
                x_absolute=x_pos * ureg('cm'),
                y_absolute=y_pos * ureg('cm'),
                thickness=thickness_nm * ureg('nm'),
                roughness=roughness_nm * ureg('nm'),
                mse=mse,
                e_inf=e_inf,
                ir_amp=ir_amp,
                spectra=[spectra],
            )
            result.normalize(archive, logger)
            results.append(result)

        logger.debug(f'Created {len(results)} ellipsometry results.')

        # Merge results into this measurement
        ellipsometry = DTUEllipsometryMeasurement(
            results=results,
        )
        merge_sections(self, ellipsometry, logger)

    def plot(self) -> None:
        """
        Create plots for the ellipsometry data.
        """
        if not self.results:
            return

        # Plot n and k spectra
        fig = go.Figure()
        for result in self.results:
            if result.spectra:
                spectrum = result.spectra[0]
                wavelength = spectrum.wavelength.to('nm').magnitude
                n = spectrum.n
                k = spectrum.k
                position = result.position

                fig.add_trace(
                    go.Scatter(
                        x=wavelength,
                        y=n,
                        mode='lines',
                        name=f'n @ {position}',
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=wavelength,
                        y=k,
                        mode='lines',
                        name=f'k @ {position}',
                        # line=dict(dash='dash'), #remove dashed line
                    )
                )

        fig.update_layout(
            title='Optical Constants (n and k)',
            xaxis_title='Wavelength (nm)',
            yaxis_title='n, k',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(fixedrange=False),
            yaxis=dict(fixedrange=False),
        )

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Optical Constants',
                figure=plot_json,
            )
        )

        # Plot thickness map if we have thickness data
        # For 1D data: line plot
        # For 2D data: heatmap or contour plot
        thickness_data = []
        for r in self.results:
            if r.thickness is not None:
                thickness_data.append(
                    {
                        'x': r.x_absolute.to('mm').magnitude,
                        'y': r.y_absolute.to('mm').magnitude,
                        'thickness': r.thickness.to('nm').magnitude,
                    }
                )

        if thickness_data:
            # Check if it's 1D or 2D data
            x_vals = [d['x'] for d in thickness_data]
            y_vals = [d['y'] for d in thickness_data]
            thickness_vals = [d['thickness'] for d in thickness_data]

            unique_x = len(set(x_vals))
            unique_y = len(set(y_vals))

            if unique_x == 1 or unique_y == 1:
                # 1D data - line plot
                if unique_x == 1:
                    # Y varies
                    fig2 = go.Figure()
                    fig2.add_trace(
                        go.Scatter(
                            x=y_vals,
                            y=thickness_vals,
                            mode='lines+markers',
                            name='Thickness',
                        )
                    )
                    fig2.update_layout(
                        title='Thickness vs Y Position',
                        xaxis_title='Y Position (mm)',
                        yaxis_title='Thickness (nm)',
                        template='plotly_white',
                        hovermode='closest',
                        dragmode='zoom',
                        xaxis=dict(fixedrange=False),
                        yaxis=dict(fixedrange=False),
                    )
                else:
                    # X varies
                    fig2 = go.Figure()
                    fig2.add_trace(
                        go.Scatter(
                            x=x_vals,
                            y=thickness_vals,
                            mode='lines+markers',
                            name='Thickness',
                        )
                    )
                    fig2.update_layout(
                        title='Thickness vs X Position',
                        xaxis_title='X Position (mm)',
                        yaxis_title='Thickness (nm)',
                        template='plotly_white',
                        hovermode='closest',
                        dragmode='zoom',
                        xaxis=dict(fixedrange=False),
                        yaxis=dict(fixedrange=False),
                    )
            else:
                # 2D data - heatmap with scatter overlay (like EDX)
                # Create a grid for the heatmap
                xi = np.linspace(min(x_vals), max(x_vals), 100)
                yi = np.linspace(min(y_vals), max(y_vals), 100)
                xi, yi = np.meshgrid(xi, yi)
                zi = griddata(
                    (x_vals, y_vals), thickness_vals, (xi, yi), method='linear'
                )

                # Create a heatmap
                heatmap = go.Heatmap(
                    x=xi[0],
                    y=yi[:, 0],
                    z=zi,
                    colorscale='Viridis',
                    colorbar=dict(title='Thickness (nm)'),
                )

                # Create a scatter plot overlay
                scatter = go.Scatter(
                    x=x_vals,
                    y=y_vals,
                    mode='markers',
                    marker=dict(
                        size=15,
                        color=thickness_vals,
                        colorscale='Viridis',
                        showscale=False,
                        line=dict(
                            width=2,
                            color='DarkSlateGrey',
                        ),
                    ),
                    customdata=thickness_vals,
                    hovertemplate='<b>Thickness:</b> %{customdata:.1f} nm',
                )

                # Combine heatmap and scatter plot
                fig2 = go.Figure(data=[heatmap, scatter])

                fig2.update_layout(
                    title='Thickness Colormap',
                    xaxis_title='X Position (mm)',
                    yaxis_title='Y Position (mm)',
                    template='plotly_white',
                    hovermode='closest',
                    dragmode='zoom',
                    xaxis=dict(fixedrange=False),
                    yaxis=dict(fixedrange=False),
                )

            plot_json2 = fig2.to_plotly_json()
            plot_json2['config'] = dict(scrollZoom=False)
            self.figures.append(
                PlotlyFigure(
                    label='Thickness Map',
                    figure=plot_json2,
                )
            )

        # Plot roughness map if we have roughness data
        roughness_data = []
        for r in self.results:
            if r.roughness is not None:
                roughness_data.append(
                    {
                        'x': r.x_absolute.to('mm').magnitude,
                        'y': r.y_absolute.to('mm').magnitude,
                        'roughness': r.roughness.to('nm').magnitude,
                    }
                )

        if roughness_data:
            # Check if it's 1D or 2D data
            x_vals_r = [d['x'] for d in roughness_data]
            y_vals_r = [d['y'] for d in roughness_data]
            roughness_vals = [d['roughness'] for d in roughness_data]

            unique_x_r = len(set(x_vals_r))
            unique_y_r = len(set(y_vals_r))

            if unique_x_r == 1 or unique_y_r == 1:
                # 1D data - line plot
                if unique_x_r == 1:
                    # Y varies
                    fig3 = go.Figure()
                    fig3.add_trace(
                        go.Scatter(
                            x=y_vals_r,
                            y=roughness_vals,
                            mode='lines+markers',
                            name='Roughness',
                        )
                    )
                    fig3.update_layout(
                        title='Roughness vs Y Position',
                        xaxis_title='Y Position (mm)',
                        yaxis_title='Roughness (nm)',
                        template='plotly_white',
                        hovermode='closest',
                        dragmode='zoom',
                        xaxis=dict(fixedrange=False),
                        yaxis=dict(fixedrange=False),
                    )
                else:
                    # X varies
                    fig3 = go.Figure()
                    fig3.add_trace(
                        go.Scatter(
                            x=x_vals_r,
                            y=roughness_vals,
                            mode='lines+markers',
                            name='Roughness',
                        )
                    )
                    fig3.update_layout(
                        title='Roughness vs X Position',
                        xaxis_title='X Position (mm)',
                        yaxis_title='Roughness (nm)',
                        template='plotly_white',
                        hovermode='closest',
                        dragmode='zoom',
                        xaxis=dict(fixedrange=False),
                        yaxis=dict(fixedrange=False),
                    )
            else:
                # 2D data - heatmap with scatter overlay
                # Create a grid for the heatmap
                xi_r = np.linspace(min(x_vals_r), max(x_vals_r), 100)
                yi_r = np.linspace(min(y_vals_r), max(y_vals_r), 100)
                xi_r, yi_r = np.meshgrid(xi_r, yi_r)
                zi_r = griddata(
                    (x_vals_r, y_vals_r), roughness_vals, (xi_r, yi_r), method='linear'
                )

                # Create a heatmap
                heatmap_r = go.Heatmap(
                    x=xi_r[0],
                    y=yi_r[:, 0],
                    z=zi_r,
                    colorscale='Viridis',
                    colorbar=dict(title='Roughness (nm)'),
                )

                # Create a scatter plot overlay
                scatter_r = go.Scatter(
                    x=x_vals_r,
                    y=y_vals_r,
                    mode='markers',
                    marker=dict(
                        size=15,
                        color=roughness_vals,
                        colorscale='Viridis',
                        showscale=False,
                        line=dict(
                            width=2,
                            color='DarkSlateGrey',
                        ),
                    ),
                    customdata=roughness_vals,
                    hovertemplate='<b>Roughness:</b> %{customdata:.1f} nm',
                )

                # Combine heatmap and scatter plot
                fig3 = go.Figure(data=[heatmap_r, scatter_r])

                fig3.update_layout(
                    title='Roughness Colormap',
                    xaxis_title='X Position (mm)',
                    yaxis_title='Y Position (mm)',
                    template='plotly_white',
                    hovermode='closest',
                    dragmode='zoom',
                    xaxis=dict(fixedrange=False),
                    yaxis=dict(fixedrange=False),
                )

            plot_json3 = fig3.to_plotly_json()
            plot_json3['config'] = dict(scrollZoom=False)
            self.figures.append(
                PlotlyFigure(
                    label='Roughness Map',
                    figure=plot_json3,
                )
            )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUEllipsometryMeasurement` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        filename = None
        if self.native_file:
            filename = self.native_file
        elif self.n_and_k_file:
            filename = self.n_and_k_file
        elif self.thickness_file:
            filename = self.thickness_file
        if filename:
            self.add_sample_reference(filename, 'Ellipsometry', archive, logger)

        # Read and write data if files are provided and results are empty
        if (self.n_and_k_file or self.thickness_file) and not self.results:
            thickness_df = self.read_thickness_file(archive, logger)
            nk_df = self.read_n_and_k_file(archive, logger)
            if not nk_df.empty:
                self.write_ellipsometry_data(thickness_df, nk_df, archive, logger)

        super().normalize(archive, logger)

        # Create plots if we have results
        self.figures = []
        if self.results:
            self.plot()


m_package.__init_metainfo__()
