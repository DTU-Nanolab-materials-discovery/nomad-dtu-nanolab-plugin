from typing import TYPE_CHECKING

from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    MappingMeasurement,
    MappingResult,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package()  # fill out later


class EllipsometryMappingResult(MappingResult, Schema):
    m_def = Section()

    position = Quantity(
        type=str,
        description='The position of the PL spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Position',
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `PLMappingResult` class.

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


class DTUEllipsometryMeasurement(MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='XRD Measurement',
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
        description='The PL results.',
        repeats=True,
        # add the spectra from n and k as well as the thickness value here
    )

    # def write_PL_by_position(
    #     self,
    #     data_dict: dict[str, Any],
    #     archive: 'EntryArchive',
    #     logger: 'BoundLogger',
    # ) -> None:

    #         #add the information accoring to the key to the respective subsections

    # def plot_overview(self, data_df: pd.DataFrame ) -> None:
    #     # Sort the DataFrame by 'X' and 'Y' columns
    #     plot_json = fig.to_plotly_json()
    #     plot_json['config'] = dict(
    #         scrollZoom=False,
    #     )
    #     self.figures.append(
    #         PlotlyFigure(
    #             label=column,
    #             figure=plot_json,
    #         )
    #     )

    # def plot_spectra(self) -> None:
    #     #add the plotting stuff here
    #     data_lines = []
    #     #problem : how toplot these in their subsections

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUXRDMeasurement` section.

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

        super().normalize(archive, logger)


m_package.__init_metainfo__()
