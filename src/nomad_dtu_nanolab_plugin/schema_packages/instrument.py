#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import CompositeSystem, Instrument
from nomad.metainfo import Datetime, Package, Quantity, Section, SubSection

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU customised Instrument scheme')


class ExternalInstrument(Instrument, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='external Instrument',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'lab_id',
                    'method',
                    'web_reference',
                    'responsible_person_instrument',
                    'responsible_person_group',
                    'description',
                ],
                visible=Filter(
                    exclude=[
                        'datetime',
                    ]
                ),
            )
        ),
    )
    method = Quantity(
        type=str,
        shape=['*'],
        description='The measurement methode of this Instrument.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(
                suggestions=[
                    'EDX',
                    'XRD',
                    'XPS',
                    'R/T',
                    'Ellipsometry',
                    'Raman',
                    'PL',
                    'Other',
                ]
            ),
        ),
    )
    responsible_person_instrument = Quantity(
        type=str,
        shape=['*'],
        description="""
        The external person responsible for this Instrument.
        Please add Email
        """,
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    responsible_person_group = Quantity(
        type=str,
        shape=['*'],
        description='The group responsible for this Instrument.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    web_reference = Quantity(
        type=str,
        shape=['*'],
        description='Web reference for this Instrument. If possible Labadvisor',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
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


class GasInlet(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'gas_inlet_position',
                    'gas_inlet_direction_vector',
                    'gas_inlet_pipe_diameter',
                    'description',
                ],
            ),
        ),
    )
    gas_inlet_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    gas_inlet_direction_vector = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    gas_inlet_pipe_diameter = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )


class SputterSource(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'source_type',
                    'date_of_installation',
                    'mounted_taret',
                    'height_of_source',
                    'set_angle',
                    'rotation',
                    'pointed_towards',
                    'distance_to_substrate',
                ],
            ),
        ),
    )
    date_of_installation = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    source_type = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(suggestions=['Taurus', 'Magkeeper', 'Other']),
        ),
    )
    position_of_source_mounting_port = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    pointed_towards = Quantity(
        type=np.float64,
        shape=(2,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    height_of_source = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    distance_to_substrate = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    set_angle = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )
    rotation = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )
    mounted_taret = Quantity(
        type=CompositeSystem,
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )


class SCrackerSource(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_installation',
                    'S_cracker_extension_into_chamber',
                    'S_cracker_mounting_hight',
                    'nozzle_position',
                    'pointed_towards',
                    'distance_to_substrate',
                    'description',
                ],
            ),
        ),
    )
    date_of_changes = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    nozzle_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    pointed_towards = Quantity(
        type=np.float64,
        shape=(2,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    distance_to_substrate = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    S_cracker_extension_into_chamber = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    S_cracker_mounting_hight = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )


class ChamberGeometry(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'chamber_size_3D',
                    'chamber_picture',
                    'aluminum_covers',
                    'description',
                    'source_1',
                    'source_2',
                    'source_3',
                    'source_4',
                    'sulfur_cracker',
                    'Inert_gas_inlet',
                    'Reactive_gas_inlet',
                ],
            ),
        ),
    )
    chamber_size_3D = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    chamber_picture = Quantity(
        type=str,
        description='A picture of the chamber geometry.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
    )
    aluminum_covers = Quantity(
        type=bool,
        description='Whether aluminum covers are used in the chamber.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_1 = SubSection(
        section_def=SputterSource,
        repeats=False,
    )
    source_2 = SubSection(
        section_def=SputterSource,
        repeats=False,
    )
    source_3 = SubSection(
        section_def=SputterSource,
        repeats=False,
    )
    source_4 = SubSection(
        section_def=SputterSource,
        repeats=False,
    )
    sulfur_cracker = SubSection(
        section_def=SCrackerSource,
        repeats=False,
    )
    Inert_gas_inlet = SubSection(
        section_def=GasInlet,
        repeats=False,
    )
    Reactive_gas_inlet = SubSection(
        section_def=GasInlet,
        repeats=False,
    )


class StatusChangeSputtersystem(ArchiveSection):
    m_def = Section()
    date_of_change = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    comment_about_change = Quantity(
        type=str,
        a_eln=ELNAnnotation(component=ELNComponentEnum.RichTextEditQuantity),
    )
    chamber_geometry = SubSection(
        section_def=ChamberGeometry,
        repeats=False,
    )


class PurgeAndCleaning(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'sulfur_cracker_refilled',
                    'detector_alarm',
                    'number_of_purge_cycles',
                    'time_per_purge_cycles',
                    'pressure_during_purge',
                    'comment_about_change',
                    'description',
                ],
            ),
        ),
    )
    sulfur_cracker_refilled = Quantity(
        type=bool,
        description='Whether the sulfur cracker was refilled.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    number_of_purge_cycles = Quantity(
        type=np.float64,
        description='Number of purge cycles automatically performed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    time_per_purge_cycles = Quantity(
        type=np.float64,
        description='Time per purge cycle.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='minute'
        ),
        unit='s',
    )
    detector_alarm = Quantity(
        type=bool,
        description='Whether the detector alarm went off during purge.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    pressure_during_purge = Quantity(
        type=np.float64,
        description='Maximum pressure during purge.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mbar',
        ),
        unit='kg/(m*s^2)',
    )


class QuickCleaning(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'vaccumed',
                    'other_cleaning_methods',
                    'comment_about_change',
                ],
            ),
        ),
    )
    vaccumed = Quantity(
        type=bool,
        description='Whether the chamber was vacuumed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    other_cleaning_methods = Quantity(
        type=str,
        description='Other cleaning methods used.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RichTextEditQuantity),
    )


class TargetChange(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'source_1_changed',
                    'source_2_changed',
                    'source_3_changed',
                    'source_4_changed',
                    'comment_about_change',
                ],
            ),
        ),
    )
    source_1_changed = Quantity(
        type=bool,
        description='Whether the target in source 1 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_2_changed = Quantity(
        type=bool,
        description='Whether the target in source 2 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_3_changed = Quantity(
        type=bool,
        description='Whether the target in source 3 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_4_changed = Quantity(
        type=bool,
        description='Whether the target in source 4 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )


class DtuSputterInstrument(Instrument, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Sputter System',
    )
    time_used_chamber = Quantity(
        type=np.float64,
        description="""
        The total time the chamber has been used for sputtering as of today.
          """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
        ),
        unit='s',
    )
    lab_location = Quantity(
        type=str,
        description='The location of the lab where this Instrument is located.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    manufacturer = Quantity(
        type=str,
        description='The manufacturer of this Instrument.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    latest_base_pressure = Quantity(
        type=np.float64,
        shape=(),
        description='The base pressure of the sputtering chamber over time.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mbar',
        ),
        unit='kg/(m*s^2)',
    )
    status_of_system = SubSection(
        section_def=StatusChangeSputtersystem,
        repeats=True,
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


m_package.__init_metainfo__()
