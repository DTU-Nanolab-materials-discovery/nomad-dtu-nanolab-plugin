from typing import TYPE_CHECKING

import numpy as np
from nomad.config import config
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    SectionProperties,
)
from nomad.metainfo.metainfo import MProxy, Package, Quantity, Section, SubSection
from nomad_material_processing.vapor_deposition.pvd.thermal import ThermalEvaporation

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
)
from nomad_dtu_nanolab_plugin.schema_packages.sputtering import DTUSputtering
from nomad_dtu_nanolab_plugin.schema_packages.substrate import (
    DTUSubstrate,
    DTUSubstrateBatch,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_dtu_nanolab_plugin.schema_packages import ThermalEntryPoint


configuration: 'ThermalEntryPoint' = config.get_plugin_entry_point(
    'nomad_dtu_nanolab_plugin.schema_packages:thermal'
)

m_package = Package(name='DTU Thermal Evaporation Schema')


#################### DEFINE MOUNTING (SUBSECTION) ######################
class DtuThermalEvaporationMounting(ArchiveSection):
    """
    Section containing information about the mounting of the substrates or combinatorial
    libraries(input samples) on the platform inside the bell jar evaporator.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'input_sample_substrate',
                    'substrate',
                    'relative_position',
                    'position_x',
                    'position_y',
                ],
            )
        ),
    )
    name = Quantity(
        type=str,
        description='The name of the input sample/substrate that is used.'
        ' This is generated automatically.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    input_sample_substrate = Quantity(
        type=(DTUCombinatorialLibrary, DTUSubstrateBatch),
        description='The substrate batch or input sample (combinatorial library) '
        'or that is used as starting point for the evaporation process.'
        'This is user input.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    substrate = Quantity(
        type=DTUSubstrate,
        description='The substrate used from the selected substrate batch. '
        'This is generated automatically.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    relative_position = Quantity(
        type=str,
        description='The relative position of the input sample or substrates '
        'on the evaporation platform.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(
                suggestions=[
                    'T',  # top - front of the glovebox when deposition starts
                    'B',  # bottom - back of the glovebox when deposition
                    'M',  # middle - center of the platform when deposition starts
                    'L',  # left - left of the platform when deposition starts
                    'R',  # right - right of the platform when deposition starts
                ]
            ),
        ),
    )
    position_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the input sample or substrate '
        'on the evaporation platform. This can be user input or '
        'automatically generated from relative position.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    position_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the input sample or substrate on the '
        'evaporation platform. This can be user input or automatically '
        'generated from relative position.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuTherMounting` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if isinstance(self.substrate_batch, MProxy):
            self.substrate_batch.m_proxy_resolve()
        if self.substrate is None and isinstance(
            self.substrate_batch, DTUSubstrateBatch
        ):
            substrate = self.substrate_batch.next_not_used_in(
                [DTUSputtering, DtuThermalEvaporation]
            )
            self.substrate = substrate
        if self.position_x is None or self.position_y is None:
            positions = {
                'T': (0.075, 0.085),
                'B': (0.075, 0.065),
                'M': (0.075, 0.075),
                'L': (0.065, 0.075),
                'R': (0.085, 0.075),
            }
            if self.relative_position in positions:
                self.position_x, self.position_y = positions[self.relative_position]
        if self.relative_position is not None:
            self.name = self.relative_position
        elif self.position_x is not None and self.position_y is not None:
            self.name = (
                f'x{self.position_x.to("cm").magnitude:.1f}'
                f'y{self.position_y.to("cm").magnitude:.1f}'
            ).replace('.', 'p')


#################### THERMAL EVAPORATION PROCESS OVERVIEW (SUBSECTION) ################
class ThermalEvaporationOverview(ArchiveSection):
    """
    Section containing a human readable overview of the Thermal Evaporation process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'material_space',  # TODO add the other quantities here
                ],
            )
        ),
    )
    material_space = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Material space',
        ),
        description='The material space explored by the Thermal Evaporation process.',
    )

    # TODO add more quantities here for the overview. Is there any calculation
    #  necessary?

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTPOverview` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)


class DtuThermalEvaporation(ThermalEvaporation, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Bell Jar Evaporator',
    )

    ################################### SUBSECTIONS ################################
    input_substrates_samples = SubSection(
        section_def=DtuThermalEvaporationMounting,
        repeats=True,
    )
    overview = SubSection(
        section_def=ThermalEvaporationOverview,
    )


m_package.__init_metainfo__()
