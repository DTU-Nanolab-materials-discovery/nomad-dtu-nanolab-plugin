import os
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
            pd.DataFrame: DataFrame with columns 'X (cm)' and 'Thickness # 1'
        """
        if not self.thickness_file:
            logger.warning('No thickness file provided.')
            return pd.DataFrame()

        with archive.m_context.raw_file(self.thickness_file) as file:
            df = pd.read_csv(file.name, sep='\t', skiprows=1)
            logger.debug(f'Read thickness file with shape: {df.shape}')
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
            with open(file.name, 'r') as f:
                f.readline()  # Skip first line ("Optical Constants")
                header_line = f.readline().strip()  # Read second line with column names

            df = pd.read_csv(file.name, sep='\t', skiprows=1)

            # Check if first column is "Energy (eV)" and convert to wavelength (nm)
            first_col_name = header_line.split('\t')[0]
            if first_col_name == 'Energy (eV)':
                logger.debug('Detected Energy (eV) column, converting to wavelength (nm)')
                # Convert energy (eV) to wavelength (nm) using λ = 1239.84 / E
                df.iloc[:, 0] = 1239.84 / df.iloc[:, 0]
                logger.debug('Converted energy to wavelength')
            elif first_col_name == 'Wavelength (nm)':
                logger.debug('Detected Wavelength (nm) column, no conversion needed')
            else:
                logger.warning(f'Unknown spectral unit in header: {first_col_name}')

            logger.debug(f'Read n and k file with shape: {df.shape}')
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

        # Parse the n and k columns to extract position and values
        # Columns are named like 'n: (-1.8,0)', 'k: (-1.8,0)', etc.
        positions = {}
        for col in nk_df.columns[1:]:
            if col.startswith('n: '):
                # Extract position from column name
                pos_str = col.split('n: ')[1]
                if pos_str not in positions:
                    positions[pos_str] = {'n_col': col}
            elif col.startswith('k: '):
                pos_str = col.split('k: ')[1]
                if pos_str in positions:
                    positions[pos_str]['k_col'] = col

        logger.debug(f'Found {len(positions)} positions in n and k file.')

        # Create a mapping from position to thickness
        # Handle three cases: (X, Thickness), (Y, Thickness), or (X, Y, Thickness)
        thickness_map = {}
        if not thickness_df.empty:
            num_cols = thickness_df.shape[1]
            if num_cols == 2:
                # Single coordinate case - determine if it's X or Y
                # Check first position from n_k data to determine which coordinate varies
                first_pos_str = list(positions.keys())[0]
                first_pos_tuple = eval(first_pos_str)
                x_varies = any(eval(p)[0] != first_pos_tuple[0] for p in positions.keys())
                y_varies = any(eval(p)[1] != first_pos_tuple[1] for p in positions.keys())

                if x_varies and not y_varies:
                    # X coordinate in file, Y is constant (assume 0)
                    for _, row in thickness_df.iterrows():
                        x_pos = row.iloc[0]
                        thickness_val = row.iloc[1]
                        thickness_map[(x_pos, 0.0)] = thickness_val
                    logger.debug('Detected 1D thickness map with X coordinate')
                elif y_varies and not x_varies:
                    # Y coordinate in file, X is constant (assume 0)
                    for _, row in thickness_df.iterrows():
                        y_pos = row.iloc[0]
                        thickness_val = row.iloc[1]
                        thickness_map[(0.0, y_pos)] = thickness_val
                    logger.debug('Detected 1D thickness map with Y coordinate')
                else:
                    # Both vary or neither varies - assume X coordinate
                    for _, row in thickness_df.iterrows():
                        x_pos = row.iloc[0]
                        thickness_val = row.iloc[1]
                        thickness_map[(x_pos, 0.0)] = thickness_val
                    logger.debug('Detected 1D thickness map, assuming X coordinate')
            elif num_cols >= 3:
                # 2D case: X, Y, and Z (thickness) columns
                for _, row in thickness_df.iterrows():
                    x_pos = row.iloc[0]
                    y_pos = row.iloc[1]
                    thickness_val = row.iloc[2]
                    thickness_map[(x_pos, y_pos)] = thickness_val
                logger.debug('Detected 2D thickness map (X, Y, Thickness)')

        # Create a result for each position
        for pos_str, cols in positions.items():
            # Parse position (e.g., '(-1.8,0)' -> x=-1.8, y=0)
            try:
                pos_tuple = eval(pos_str)  # Safe here as we control the format
                x_pos = pos_tuple[0]
                y_pos = pos_tuple[1]
            except Exception as e:
                logger.warning(f'Could not parse position {pos_str}: {e}')
                continue

            # Get n and k values
            n_values = nk_df[cols['n_col']].to_numpy()
            k_values = nk_df[cols['k_col']].to_numpy()

            # Create spectra
            spectra = EllipsometrySpectra(
                wavelength=wavelength,
                n=n_values,
                k=k_values,
            )

            # Get thickness for this position using (x, y) tuple lookup
            thickness_nm = thickness_map.get((x_pos, y_pos), None)
            thickness_m = thickness_nm * ureg('nm') if thickness_nm is not None else None

            # Create result
            result = EllipsometryMappingResult(
                position=pos_str,
                x_absolute=x_pos * ureg('cm'),
                y_absolute=y_pos * ureg('cm'),
                thickness=thickness_m,
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

                fig.add_trace(go.Scatter(
                    x=wavelength,
                    y=n,
                    mode='lines',
                    name=f'n @ {position}',
                ))
                fig.add_trace(go.Scatter(
                    x=wavelength,
                    y=k,
                    mode='lines',
                    name=f'k @ {position}',
                    line=dict(dash='dash'),
                ))

        fig.update_layout(
            title='Optical Constants (n and k)',
            xaxis_title='Wavelength (nm)',
            yaxis_title='Value',
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
        thickness_data = [(r.x_absolute.to('cm').magnitude, r.thickness.to('nm').magnitude)
                          for r in self.results if r.thickness is not None]
        if thickness_data:
            x_vals, thickness_vals = zip(*thickness_data)
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=x_vals,
                y=thickness_vals,
                mode='lines+markers',
                name='Thickness',
            ))
            fig2.update_layout(
                title='Thickness vs Position',
                xaxis_title='X Position (cm)',
                yaxis_title='Thickness (nm)',
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
                    label='Thickness',
                    figure=plot_json2,
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
