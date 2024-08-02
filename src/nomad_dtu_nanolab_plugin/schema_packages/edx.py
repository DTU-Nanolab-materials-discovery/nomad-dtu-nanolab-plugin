import re
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import pint
import plotly.graph_objects as go
from ase.data import chemical_symbols
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from scipy.interpolate import griddata

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

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


class EDXResult(MeasurementResult):
    m_def = Section()
    x_position = Quantity(
        type=np.float64,
        description="""
        The x position of the EDX measurement.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_position = Quantity(
        type=np.float64,
        description="""
        The y position of the EDX measurement.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
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
        if isinstance(self.x_position, pint.Quantity) and isinstance(
            self.y_position, pint.Quantity
        ):
            self.name = (
                f'({self.x_position.to("mm").magnitude:.1f}, '
                f'{self.y_position.to("mm").magnitude:.1f})'
            )


class EDXMeasurement(Measurement, PlotSection, Schema):
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

    def plot(self) -> None:
        x, y, thickness = [], [], []
        quantifications = defaultdict(list)
        result: EDXResult
        for result in self.results:
            if (
                not isinstance(result.x_position, pint.Quantity)
                or not isinstance(result.y_position, pint.Quantity)
                or not isinstance(result.layer_thickness, pint.Quantity)
            ):
                continue
            x.append(result.x_position.to('mm').magnitude)
            y.append(result.y_position.to('mm').magnitude)
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
            xaxis_title='X Position (mm)',
            yaxis_title='Y Position (mm)',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
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
                xaxis_title='X Position (mm)',
                yaxis_title='Y Position (mm)',
                template='plotly_white',
                hovermode='closest',
                dragmode='zoom',
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `EDXMeasurement` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.edx_data_file is None:
            return
        with archive.m_context.raw_file(self.edx_data_file, 'rb') as edx:
            df_data = pd.read_excel(edx, header=0)

        self.avg_layer_thickness = ureg.Quantity(
            df_data['Layer 1 Thickness (nm)'].mean(), 'nm'
        )

        pattern = r'Layer 1 [A-Z][a-z]? Atomic %'
        percentage_labels = [
            label for label in df_data.columns if re.match(pattern, label)
        ]

        self.results = []
        for _, row in df_data.iterrows():
            result = EDXResult()
            result.x_position = ureg.Quantity(row['X (mm)'], 'mm')
            result.y_position = ureg.Quantity(row['Y (mm)'], 'mm')
            result.layer_thickness = ureg.Quantity(row['Layer 1 Thickness (nm)'], 'nm')
            result.quantifications = []
            for label in percentage_labels:
                element = label.split(' ')[2]
                atomic_fraction = row[label] * 1e-2
                result.quantifications.append(
                    EDXQuantification(element=element, atomic_fraction=atomic_fraction)
                )
            result.normalize(archive, logger)
            self.results.append(result)
        self.figures = []
        self.plot()


m_package.__init_metainfo__()
