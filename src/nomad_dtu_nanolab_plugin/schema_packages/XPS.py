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


class XPSMappingResult(MappingResult, Schema):
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


class XPSMetadata(Schema):
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


class DTUXPSMeasurement(MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='XRD Measurement',
    )
    native_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'native file'},
    )
    spectra_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'exported spectra text file'},
    )
    analysis_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'exported analysis text file',
        },
    )
    metadata = SubSection(
        section_def=XPSMetadata,
        description='The metadata of the ellipsometry measurement',
        # need the native file and a way to open it to extract the metadata
    )
    results = SubSection(
        section_def=XPSMappingResult,
        description='The PL results.',
        repeats=True,
        # add the spectra here
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUXRDMeasurement` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        # if self.pl_data_file:

        super().normalize(archive, logger)


m_package.__init_metainfo__()
