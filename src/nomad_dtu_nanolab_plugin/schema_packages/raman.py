from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
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
    optical_image = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
        a_browser=BrowserAnnotation(adaptor=BrowserAdaptors.RawFileAdaptor),
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
        img_list: list[str],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Write method for populating the `RamanMeasurement` section from Raman data.

        Args:
            raman_meas_list (list): A list of RamanMeas objects from MappingRamanMeas.
            img_list (list): A list of image file names corresponding to the optical images.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        results = []

        for meas, img_file in zip(raman_meas_list, img_list):
            x_absolute = meas.x_pos * ureg('um')
            y_absolute = meas.y_pos * ureg('um')
            result = RamanResult(
                intensity=meas.data['intensity'].to_list(),
                raman_shift=meas.data['wavenumber'].to_numpy() * ureg('1/cm'),
                laser_wavelength=meas.laser_wavelength,
                optical_image=img_file,
                x_absolute=x_absolute,
                y_absolute=y_absolute,
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

            # Handle file path - use file object's name attribute
            file_path = file.name if hasattr(file, 'name') else self.raman_data_file
            folder = os.path.dirname(file_path)
            filename = os.path.basename(file_path)

            # If folder is empty, use current directory
            if not folder:
                folder = '.'

            mapping.read_wdf_mapping(folder, [filename])
            # meas_name = filename.split(".")[0]
            # grid_path = os.path.join(folder, f"{meas_name}_optical_grid.png")
            # mapping.save_optical_images(folder, meas_name)
            # mapping.create_image_grid(save_path=grid_path)

            _, img_list = mapping.save_optical_images(folder, filename.split(".")[0])
            # Write the data to results
            self.write_raman_data(
                mapping.raman_meas_list, 
                img_list,
                archive, logger)

    def plot(self) -> None:
        fig = go.Figure()
        result: RamanResult
        for result in self.results:
            # Fixed: raman_shift is stored as a list, not a Quantity
            # If it's a Quantity, convert it; otherwise use it directly
            if hasattr(result.raman_shift, 'magnitude'):
                x_data = result.raman_shift.to('1/cm').magnitude
            else:
                x_data = result.raman_shift

            fig.add_trace(
                go.Scatter(
                    x=x_data,
                    y=np.log(result.intensity),
                    mode='lines',
                    name=result.name,
                    hoverlabel=dict(namelength=-1),
                )
            )

        # Update layout
        fig.update_layout(
            title='Raman Spectra',
            xaxis_title='Raman Shift (1/cm)',
            yaxis_title='Log Intensity',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
                type='linear',
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
