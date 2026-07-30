from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section
from plotly.subplots import make_subplots

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU generalised point measurement schema package')


class PointMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Point measurements',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'technique',
                    'measuremet_area',
                    'measured_property',
                    'extracted_value',
                    'raw_file',
                    'plotting_file',
                ],
                visible=Filter(
                    exclude=['steps', 'methode', 'around_barycenter'],
                ),
            ),
        ),
    )
    technique = Quantity(
        type=str,
        description='The technique used for the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    measured_property = Quantity(
        type=str,
        description='The property that was measured.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    extracted_value = Quantity(
        type=np.float64,
        description='The extracted value from the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    measuremet_area = Quantity(
        type=np.float64,
        description='The area or footprint of the measurement in square millimeters.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm**2',
        ),
        unit='m**2',
    )
    raw_file = Quantity(
        type=str,
        shape=['*'],
        description="""The raw data file of the measurement.
          Please add position of measurement manually in the subsection.""",
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
    )
    plotting_file = Quantity(
        type=str,
        description="""please use one excel file.
        The first column will be the x-axis and 
        the following columns will be the y-axis.
        The first row will be the header.""",
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
    )
    plot_type = Quantity(
        type=MEnum(
            'none',
            'scatter',
            'line',
            'map',
        ),
        description='The type of plot to be generated from the plotting file.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RadioEnumEditQuantity),
        default='none',
    )

    def plot(self, archive: 'EntryArchive') -> None:
        """
        Generates a plot from the plotting file and adds it to the section.
        """
        if self.plotting_file is None:
            return

        # Load the header and data from the Excel plotting file
        with archive.m_context.raw_file(self.plotting_file, 'rb') as f:
            df = pd.read_excel(f)
        header = df.columns.tolist()

        x = df.iloc[:, 0].to_numpy()
        x_title = header[0] if len(header) > 0 else 'X-axis'

        # Create the plot based on the specified plot type
        if self.plot_type in ('scatter', 'line'):
            y = df.iloc[:, 1:].to_numpy()
            y_titles = (
                header[1:]
                if len(header) > 1
                else [f'Column {i + 1}' for i in range(y.shape[1])]
            )
            mode = 'markers' if self.plot_type == 'scatter' else 'lines'

            fig = go.Figure()
            for i in range(y.shape[1]):
                trace_name = y_titles[i] if i < len(y_titles) else f'Column {i + 1}'
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y[:, i],
                        mode=mode,
                        name=trace_name,
                    )
                )
            fig.update_layout(
                title='Scatter Plot' if self.plot_type == 'scatter' else 'Line Plot',
                xaxis_title=x_title,
                yaxis_title='Y-axis',
            )

        elif self.plot_type == 'map':
            y_col = df.iloc[:, 1].to_numpy()
            y_title = header[1] if len(header) > 1 else 'Y-axis'

            z_columns = df.iloc[:, 2:]
            z_titles = (
                header[2:]
                if len(header) > 1
                else [f'Column {i + 2}' for i in range(z_columns.shape[1])]
            )
            n_maps = z_columns.shape[1]

            fig = make_subplots(
                rows=1,
                cols=n_maps,
                subplot_titles=z_titles,
            )

            for i in range(n_maps):
                color_col = z_columns.iloc[:, i].to_numpy()
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=y_col,
                        mode='markers',
                        marker=dict(
                            color=color_col,
                            colorscale='Viridis',
                            showscale=True,
                            colorbar=dict(
                                title=z_titles[i],
                                x=1.0 / n_maps * (i + 1) - 0.02,
                                len=1.0,
                            ),
                        ),
                        name=z_titles[i],
                    ),
                    row=1,
                    col=i + 1,
                )
                fig.update_xaxes(title_text=x_title, row=1, col=i + 1)
                if i == 0:
                    fig.update_yaxes(title_text=y_title, row=1, col=i + 1)

            fig.update_layout(title='Heatmap')

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        self.figures.append(
            PlotlyFigure(
                label='Plot',
                figure=plot_json,
            )
        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUInstrument` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        if self.location is None:
            self.location = 'DTU Nanolab'

        if self.raw_file is not None:
            self.add_sample_reference(self.raw_file[0], 'Raw Data', archive, logger)

        self.figures = []

        if self.plot_type != 'none' and self.plotting_file is not None:
            self.plot(archive)


m_package.__init_metainfo__()
