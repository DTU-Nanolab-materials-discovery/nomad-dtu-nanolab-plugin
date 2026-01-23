from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotSection, PlotlyFigure
from nomad.metainfo import Package, Quantity, Section, SubSection
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The results section for the Raman measurement.
        """
        super().normalize(archive, logger)
        # TODO: Add code for calculating the relative positions of the measurements.


class DTUSampleAlignment(RectangularSampleAlignment):
    m_def = Section(
        description='The alignment of the sample on the stage.',
    )


class RamanMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Raman Measurement',
    )
    raman_data_file = Quantity(
        type=str,
        description='Data file containing the Raman spectra',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )

    results = SubSection(
        section_def=RamanResult,
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=DTUSampleAlignment,
        description='The alignment of the sample.',
    )

    def write_raman_data(
        self,
        raman_meas_list: list[Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Write method for populating the `RamanMeasurement` section from Raman data.

        Args:
            raman_meas_list (list): A list of RamanMeas objects from MappingRamanMeas.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        results = []

        for meas in raman_meas_list:
            result = RamanResult(
                intensity=meas.data['intensity'].to_list(),
                raman_shift=meas.data['wavenumber'].to_list(),
                laser_wavelength=meas.laser_wavelength,
                x_absolute=meas.x_pos,
                y_absolute=meas.y_pos,
                name=f'Raman at ({meas.x_pos:.2f} um, {meas.y_pos:.2f} um)',
            )
            result.normalize(archive, logger)
            results.append(result)

        raman = RamanMeasurement(
            results=results,
        )
        merge_sections(self, raman, logger)

    def read_raman_data(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Read the Raman data from the provided file.
        """
        with archive.m_context.raw_file(self.raman_data_file) as file:
            # Initialize the mapping reader
            mapping = MappingRamanMeas()
            # Read the data - get folder and filename from the file path
            import os
            folder = os.path.dirname(file.name)
            filename = os.path.basename(file.name)
            mapping.read_wdf_mapping(folder, [filename])
            # Write the data to results
            self.write_raman_data(mapping.raman_meas_list, archive, logger)


    def plot(self) -> None:
        fig = go.Figure()
        result: RamanResult
        for result in self.results:
            fig.add_trace(
                go.Scatter(
                    x=result.raman_shift.to('1/cm').magnitude,
                    y=result.intensity,
                    mode='lines',
                    name=result.name,
                    hoverlabel=dict(namelength=-1),
                )
            )

        # Update layout
        fig.update_layout(
            title='Raman Spectra',
            xaxis_title='Raman Shift / 1/cm',
            yaxis_title='Intensity',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
                type='log',
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RamanMeasurement` class.
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
            self.read_raman_data(archive, logger)

        super().normalize(archive, logger)

        self.figures = []
        if len(self.results) > 0:
            self.plot()


m_package.__init_metainfo__()
