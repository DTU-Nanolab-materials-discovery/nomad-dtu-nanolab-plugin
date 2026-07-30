from typing import TYPE_CHECKING

import numpy as np
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

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU generalised single point measurement schema package')


class SinglePointMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Single point measurement',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'technique',
                    'extracted_value',
                    'raw_file',
                    'plotting_file'
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
        a_eln=ELNAnnotation(component=ELNComponentEnum.TextEditQuantity),
    )
    extracted_value = Quantity(
        type=np.float64,
        description='The extracted value from the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    raw_file = Quantity(
        type=str,
        shape=['*'],
        description='The raw data file of the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
    )
    plotting_file = Quantity(
        type=str,
        shape=['*'],
        description="""please use an excel file.
        The first column will be the x-axis and the following columns will be the y-axis.
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

    def plot (self) -> None:
        """
        Generates a plot from the plotting file and adds it to the section.
        """
        if self.plotting_file is None:
            return

        # Load the header and data from the plotting file
        header = np.genfromtxt(self.plotting_file, delimiter=',', max_rows=1, dtype=str)
        data = np.genfromtxt(self.plotting_file, delimiter=',', missing_values='', skip_header=1)
        x = data[:, 0]
        y = data[:, 1:]
        x_title = header[0] if header.size > 0 else 'X-axis'
        y_titles = header[1:] if header.size > 1 else [f'Column {i + 1}' for i in range(y.shape[1])]

        # Create the plot based on the specified plot type
        if self.plot_type == 'scatter':
            fig = go.Figure()
            for i in range(y.shape[1]):
                trace_name = y_titles[i] if i < len(y_titles) else f'Column {i + 1}'
                fig.add_trace(go.Scatter(x=x, y=y[:, i], mode='markers', name=trace_name))
            fig.update_layout(title='Scatter Plot', xaxis_title=x_title, yaxis_title='Y-axis')


        elif self.plot_type == 'line':
            fig = go.Figure()
            for i in range(y.shape[1]):
                trace_name = y_titles[i] if i < len(y_titles) else f'Column {i + 1}'
                fig.add_trace(go.Scatter(x=x, y=y[:, i], mode='lines', name=trace_name))
            fig.update_layout(title='Line Plot', xaxis_title=x_title, yaxis_title='Y-axis')


        elif self.plot_type == 'map':
            fig = go.Figure(data=go.Heatmap(z=y, x=x, y=np.arange(y.shape[1])))
            fig.update_layout(title='Heatmap', xaxis_title=x_title, yaxis_title='Columns')


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


    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUInstrument` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        if self.plot_type != 'none' and self.plotting_file is not None:
            self.plot()



m_package.__init_metainfo__()
