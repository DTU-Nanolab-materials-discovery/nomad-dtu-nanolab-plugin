import re
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ase.data import chemical_symbols
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.utils import merge_sections
from scipy.interpolate import griddata

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    MappingMeasurement,
    MappingResult,
    RectangularSampleAlignment,
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
    quantifications = SubSection(
        section_def=EDXQuantification,
        repeats=True,
    )

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


class EDXMeasurement(MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='EDX Measurement',
    )
    edx_data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'EDX file'},
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

        for q in quantifications:
            # Create a grid for the heatmap
            xi = np.linspace(min(x), max(x), 100)
            yi = np.linspace(min(y), max(y), 100)
            xi, yi = np.meshgrid(xi, yi)
            zi = griddata((x, y), quantifications[q], (xi, yi), method='linear')

            # Create a scatter plot
            scatter = go.Scatter(
                x=x,
                y=y,
                mode='markers',
                marker=dict(
                    size=15,
                    color=quantifications[q],  # Set color to atomic fraction values
                    colorscale='Viridis',  # Choose a colorscale
                    # colorbar=dict(title=f'{q} Atomic Fraction'),  # Add a colorbar
                    showscale=False,  # Hide the colorbar for the scatter plot
                    line=dict(
                        width=2,  # Set the width of the border
                        color='DarkSlateGrey',  # Set the color of the border
                    ),
                ),
                customdata=quantifications[q],  # Add atomic fraction data to customdata
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

        pattern = r'Layer 1 [A-Z][a-z]? Atomic %'
        percentage_labels = [
            label for label in df_data.columns if re.match(pattern, label)
        ]

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
            result.normalize(archive, logger)
            results.append(result)
        edx = EDXMeasurement(
            results=results,
            avg_layer_thickness=avg_layer_thickness,
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
        if self.edx_data_file is not None:
            with archive.m_context.raw_file(self.edx_data_file, 'rb') as edx:
                df_data = pd.read_excel(edx, sheet_name='Sheet1', header=0)
                df_alignment = pd.read_excel(edx, sheet_name='Sheet2', header=0)
            self.write_edx_data(df_data, df_alignment, archive, logger)

        super().normalize(archive, logger)

        self.figures = []
        self.plot()


m_package.__init_metainfo__()
