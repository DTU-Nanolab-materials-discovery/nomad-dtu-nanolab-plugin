import re
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ase.data import chemical_symbols
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from nomad_measurements.utils import merge_sections
from scipy.interpolate import griddata

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU EDX measurement schema')


class EDXQuantification(ArchiveSection):
    m_def = Section(
        label_quantity='element',
    )
    element = Quantity(
        type=MEnum(chemical_symbols[1:]),
        description="""
        The symbol of the element, e.g. 'Pb'.
        """,
        a_eln=ELNAnnotation(component=ELNComponentEnum.AutocompleteEditQuantity),
    )
    atomic_fraction = Quantity(
        type=np.float64,
        description="""
        The atomic fraction of the element.
        """,
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )


class EDXResult(MappingResult):
    m_def = Section()
    layer_thickness = Quantity(
        type=np.float64,
        description="""
        The layer thickness from the EDX measurement.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
        unit='m',
    )
    assumed_material_density = Quantity(
        type=np.float64,
        description="""
        The assumed material density for the thickness determination.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='g/(cm**3)',
        ),
        unit='kg/(m**3)',
    )
    quantifications = SubSection(
        section_def=EDXQuantification,
        repeats=True,
    )
    electron_image = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
        a_browser=BrowserAnnotation(adaptor=BrowserAdaptors.RawFileAdaptor),
    )  # TODO: Add electron image handling in normalizer

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `EDXResult` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        # TODO: Add code for calculating the relative positions of the measurements.


class DTUSampleAlignment(RectangularSampleAlignment):
    m_def = Section()
    width = Quantity(
        type=np.float64,
        default=0.04,
        description='The width of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    height = Quantity(
        type=np.float64,
        default=0.04,
        description='The height of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )


class EDXMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='EDX Measurement',
    )

    edx_data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'EDX file'},
        description="""
            The csv file containing the analysis of the EDX measurement using
            the LayerProbe software. Contains quantification results and alignment data.
        """,
    )
    electron_image_files = Quantity(
        type=str,
        shape=['*'],
        description="""
            Data files containing the electron images. Images are automatically mapped
            to their respective spectra by extracting numbers from image filenames and
            matching them with the spectrum numbers from the 'Spectrum Label' column
            in the EDX data file (e.g., 'SE Image 1.png' matches 'Spectrum 1').
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )
    native_file_zip = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'Native data archive'},
        description="""
            A zip archive containing the native data files from the EDX measurement.
        """,
    )
    avg_layer_thickness = Quantity(
        type=np.float64,
        description="""
            The average layer thickness from the EDX measurement
                            """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
        unit='m',
    )
    avg_density = Quantity(
        type=np.float64,
        description="""
            The assumed material density for the thickness determination
                            """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='g/(cm**3)',
        ),
        unit='kg/(m**3)',
    )
    results = SubSection(
        section_def=EDXResult,
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=DTUSampleAlignment,
        description='The alignment of the sample.',
    )

    def plot(self) -> None:
        x, y, thickness = [], [], []
        quantifications = defaultdict(list)
        ratios = defaultdict(list)
        result: EDXResult
        for result in self.results:
            if not isinstance(result.layer_thickness, ureg.Quantity):
                continue
            if isinstance(result.x_relative, ureg.Quantity) and isinstance(
                result.y_relative, ureg.Quantity
            ):
                x.append(result.x_relative.to('mm').magnitude)
                y.append(result.y_relative.to('mm').magnitude)
                x_title = 'X Sample Position (mm)'
                y_title = 'Y Sample Position (mm)'
            elif isinstance(result.x_absolute, ureg.Quantity) and isinstance(
                result.y_absolute, ureg.Quantity
            ):
                x.append(result.x_absolute.to('mm').magnitude)
                y.append(result.y_absolute.to('mm').magnitude)
                x_title = 'X Stage Position (mm)'
                y_title = 'Y Stage Position (mm)'
            else:
                continue
            thickness.append(result.layer_thickness.to('nm').magnitude)
            quantification: EDXQuantification
            for quantification in result.quantifications:
                quantifications[quantification.element].append(
                    quantification.atomic_fraction
                )

            # Calculate and append the fractions of all elements with each other
            # test to see if this works or there is another errror
            quantification_i: EDXQuantification
            # processed_pairs = set()
            for quantification_i in result.quantifications:
                quantification_j: EDXQuantification
                for quantification_j in result.quantifications:
                    if quantification_i.element == quantification_j.element:
                        continue
                    # pair = (quantification_i.element, quantification_j.element)
                    # reverse_pair = (
                    #     quantification_j.element,
                    #     quantification_i.element
                    # )
                    # if pair in processed_pairs or reverse_pair in processed_pairs:
                    #    continue
                    ratio = (
                        quantification_i.atomic_fraction
                        / quantification_j.atomic_fraction
                    )
                    ratios[
                        f'{quantification_i.element}/{quantification_j.element}'
                    ].append(ratio)
                    # processed_pairs.add(pair)

        # Create a grid for the heatmap
        xi = np.linspace(min(x), max(x), 100)
        yi = np.linspace(min(y), max(y), 100)
        xi, yi = np.meshgrid(xi, yi)
        zi = griddata((x, y), thickness, (xi, yi), method='linear')

        # Create a scatter plot
        scatter = go.Scatter(
            x=x,
            y=y,
            mode='markers',
            marker=dict(
                size=15,
                color=thickness,  # Set color to thickness values
                colorscale='Viridis',  # Choose a colorscale
                # colorbar=dict(title='Thickness (nm)'),  # Add a colorbar
                showscale=False,  # Hide the colorbar for the scatter plot
                line=dict(
                    width=2,  # Set the width of the border
                    color='DarkSlateGrey',  # Set the color of the border
                ),
            ),
            customdata=thickness,  # Add thickness data to customdata
            hovertemplate='<b>Thickness:</b> %{customdata} nm',
        )

        # Create a heatmap
        heatmap = go.Heatmap(
            x=xi[0],
            y=yi[:, 0],
            z=zi,
            colorscale='Viridis',
            colorbar=dict(title='Thickness (nm)'),
        )

        # Combine scatter plot and heatmap
        fig = go.Figure(data=[heatmap, scatter])

        # Update layout
        fig.update_layout(
            title='Thickness Colormap',
            xaxis_title=x_title,
            yaxis_title=y_title,
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

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        self.figures.append(
            PlotlyFigure(
                label='Thickness',
                figure=plot_json,
            )
        )

        combined_data = {**quantifications, **ratios}

        for q, data in combined_data.items():
            # Create a grid for the heatmap
            xi = np.linspace(min(x), max(x), 100)
            yi = np.linspace(min(y), max(y), 100)
            xi, yi = np.meshgrid(xi, yi)
            zi = griddata((x, y), data, (xi, yi), method='linear')

            # Create a scatter plot
            scatter = go.Scatter(
                x=x,
                y=y,
                mode='markers',
                marker=dict(
                    size=15,
                    color=data,  # Set color to atomic fraction values
                    colorscale='Viridis',  # Choose a colorscale
                    # colorbar=dict(title=f'{q} Atomic Fraction'),  # Add a colorbar
                    showscale=False,  # Hide the colorbar for the scatter plot
                    line=dict(
                        width=2,  # Set the width of the border
                        color='DarkSlateGrey',  # Set the color of the border
                    ),
                ),
                customdata=data,  # Add atomic fraction data to customdata
                hovertemplate=f'<b>Atomic fraction of {q}:</b> %{{customdata}}',
            )

            # Create a heatmap
            heatmap = go.Heatmap(
                x=xi[0],
                y=yi[:, 0],
                z=zi,
                colorscale='Viridis',
                colorbar=dict(title=f'{q} Atomic Fraction'),
            )

            # Combine scatter plot and heatmap
            fig = go.Figure(data=[heatmap, scatter])

            # Update layout
            fig.update_layout(
                title=f'{q} Atomic Fraction Colormap',
                xaxis_title=x_title,
                yaxis_title=y_title,
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

            plot_json = fig.to_plotly_json()
            plot_json['config'] = dict(
                scrollZoom=False,
            )
            self.figures.append(
                PlotlyFigure(
                    label=f'{q} Atomic Fraction',
                    figure=plot_json,
                )
            )

    def _create_image_mapping(self, logger: 'BoundLogger') -> dict[int, str]:
        """
        Create a mapping from spectrum numbers to image file paths.

        Returns:
            dict[int, str]: A dictionary mapping spectrum numbers to image paths.
        """
        image_mapping = {}

        if not self.electron_image_files:
            return image_mapping

        # Ensure electron_image_files is a list
        image_files = self.electron_image_files
        if isinstance(image_files, str):
            image_files = [image_files]


        for img_file in image_files:
            # Extract spectrum number from filename
            # Pattern: "SE Image - Before/After X" where X is the spectrum number
            match = re.search(r'(?:Before|After)\s*(\d+)', img_file)
            if match:
                spectrum_num = int(match.group(1))
                image_mapping[spectrum_num] = img_file

        return image_mapping

    def write_edx_data(
        self,
        df_data: pd.DataFrame,
        df_alignment: pd.DataFrame,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Write method for populating the `EDXMeasurement` section from a data and
        an alignment pandas DataFrame.

        Args:
            df_data (pd.DataFrame): A pandas DataFrame with the quantification results.
            df_alignment (pd.DataFrame): A pandas DataFrame with the alignment data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        corner_x = ureg.Quantity(df_alignment['corner x'].dropna().values, 'mm')
        corner_y = ureg.Quantity(df_alignment['corner y'].dropna().values, 'mm')
        sample_alignment = DTUSampleAlignment(
            x_upper_left=corner_x[0],
            y_upper_left=corner_y[0],
            x_lower_right=corner_x[1],
            y_lower_right=corner_y[1],
        )

        avg_layer_thickness = ureg.Quantity(
            df_data['Layer 1 Thickness (nm)'].mean(), 'nm'
        )

        if 'Layer 1 Density (g/cm³)' in df_data.columns:
            avg_density = ureg.Quantity(
                df_data['Layer 1 Density (g/cm³)'].mean(), 'g/(cm**3)'
            )
        elif self.avg_density is not None:
            avg_density = self.avg_density
        else:
            avg_density = None

        pattern = r'Layer 1 [A-Z][a-z]? Atomic %'
        percentage_labels = [
            label for label in df_data.columns if re.match(pattern, label)
        ]

        # Create image mapping from spectrum numbers to file paths
        image_mapping = self._create_image_mapping(logger)
        logger.debug(f'Image mapping: {image_mapping}')

        results = []
        for _, row in df_data.iterrows():
            quantifications = []
            for label in percentage_labels:
                element = label.split(' ')[2]
                atomic_fraction = row[label] * 1e-2
                quantifications.append(
                    EDXQuantification(element=element, atomic_fraction=atomic_fraction)
                )
            result = EDXResult(
                x_absolute=ureg.Quantity(row['X (mm)'], 'mm'),
                y_absolute=ureg.Quantity(row['Y (mm)'], 'mm'),
                layer_thickness=ureg.Quantity(row['Layer 1 Thickness (nm)'], 'nm'),
                quantifications=quantifications,
            )

            if 'Layer 1 Density (g/cm³)' in df_data.columns:
                result.assumed_material_density = ureg.Quantity(
                    row['Layer 1 Density (g/cm³)'], 'g/(cm**3)'
                )
            elif self.avg_density is not None:
                result.assumed_material_density = avg_density

            # Associate electron image with result if available
            if 'Spectrum Label' in df_data.columns:
                spectrum_label = row['Spectrum Label']
                match = re.search(r'\d+', str(spectrum_label))
                spectrum_num = int(match.group()) if match else None

                if spectrum_num is not None and spectrum_num in image_mapping:
                    result.electron_image = image_mapping[spectrum_num]

            result.normalize(archive, logger)
            results.append(result)
        edx = EDXMeasurement(
            results=results,
            avg_layer_thickness=avg_layer_thickness,
            avg_density=avg_density,
            sample_alignment=sample_alignment,
        )
        merge_sections(self, edx, logger)
        self.sample_alignment.normalize(archive, logger)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `EDXMeasurement` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        if self.location is None:
            self.location = 'DTU Nanolab EDX Measurement'

        if self.edx_data_file is not None:
            self.add_sample_reference(self.edx_data_file, 'EDX', archive, logger)
            with archive.m_context.raw_file(self.edx_data_file, 'rb') as edx:
                df_data = pd.read_excel(edx, sheet_name='Sheet1', header=0)
                df_alignment = pd.read_excel(edx, sheet_name='Sheet2', header=0)
            self.write_edx_data(df_data, df_alignment, archive, logger)

        super().normalize(archive, logger)

        self.figures = []
        if len(self.results) > 0:
            self.plot()


m_package.__init_metainfo__()
