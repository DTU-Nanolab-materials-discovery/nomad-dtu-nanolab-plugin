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
from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    Collection,
    CompositeSystemReference,
    Process,
    PubChemPureSubstanceSection,
    PureSubstanceComponent,
    ReadableIdentifiers,
)
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad_material_processing import (
    CrystallineSubstrate,
    Dopant,
    ElectronicProperties,
    RectangleCuboid,
)
from nomad_material_processing.utils import create_archive
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU customised Substrate scheme')


class DTUSubstrateBatch(Collection, Schema):
    """
    Schema for substrate batches in the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Substrate',
        a_template=dict(
            substrate_identifiers=dict(),
        ),
    )
    material = Quantity(
        type=str,
        default='Si',
        description='The material of the substrate.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    supplier = Quantity(
        type=str,
        default='Siegert Wafer',
        a_eln={'component': 'StringEditQuantity'},
    )
    substrate_polishing = Quantity(
        type=MEnum(['1 sided', '2 sided', 'none']),
        default='1 sided',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    doping_type_of_substrate = Quantity(
        type=MEnum(
            'P-type',
            'N-type',
        ),
        default='N-type',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    doping_of_substrate = Quantity(
        type=np.float64,
        description="""
            The doping of the substrate measured as the electrical resistivity.
        """,
        default=0.2,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'ohm*cm',
        },
        unit='ohm meter',
    )
    doping_elements = Quantity(
        type=str,
        shape=['*'],
        default=['P'],
        a_eln={'component': 'StringEditQuantity'},
    )
    length = Quantity(
        type=np.float64,
        default=0.04,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
    )
    width = Quantity(
        type=np.float64,
        default=0.04,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
    )
    thickness = Quantity(
        type=np.float64,
        default=0.000675,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
    )
    create_substrates = Quantity(
        type=bool,
        description='Whether to (re)create the substrate entities.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    number_of_substrates = Quantity(
        type=int,
        description='The number of substrates in the batch.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    substrate_identifiers = SubSection(
        section_def=ReadableIdentifiers,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrate` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.create_substrates:
            substrate = DTUSubstrate()

            geometry = RectangleCuboid()
            geometry.length = self.length
            geometry.width = self.width
            geometry.height = self.thickness
            substrate.geometry = geometry

            component = PureSubstanceComponent()
            substance_section = PubChemPureSubstanceSection()
            substance_section.molecular_formula = self.material
            substance_section.normalize(archive, logger)

            component.pure_substance = substance_section
            substrate.components = [component]

            substrate.dopants = [
                Dopant(element=element) for element in self.doping_elements
            ]

            electronic_properties = ElectronicProperties()
            electronic_properties.conductivity_type = self.doping_type_of_substrate
            electronic_properties.resistivity = self.doping_of_substrate
            substrate.electronic_properties = electronic_properties

            substrate.supplier = self.supplier
            substrate.substrate_polishing = self.substrate_polishing

            substrate.normalize(archive, logger)

            for i in range(self.number_of_substrates):
                substrate.name = f'{self.name} Substrate {i}'
                substrate.lab_id = f'{self.lab_id}-{i}'
                file_name = f'{substrate.lab_id}.archive.json'
                import json

                print(json.dumps(substrate.m_to_dict(), indent=2))
                substrate_archive = create_archive(substrate, archive, file_name)
                self.entities.append(
                    CompositeSystemReference(
                        reference=substrate_archive,
                        name=substrate.name,
                        lab_id=substrate.lab_id,
                    )
                )
            self.create_substrates = False


class DTUSubstrate(CrystallineSubstrate, Schema):
    """
    Schema for substrates in the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Substrate',
    )
    substrate_polishing = Quantity(  # TODO: Add to base CrystallineSubstrate
        type=MEnum(['1 sided', '2 sided', 'none']),
        default='1 sided',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )


class DTUSubstrateCleaning(Process, Schema):
    """
    Schema for substrate cleaning at the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Substrate Cleaning',
    )
    substrate_batch = Quantity(
        type=DTUSubstrateBatch,
        description='The substrate batch that was cleaned.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrateCleaning` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        self.samples = self.substrate_batch.entities
        return super().normalize(archive, logger)


m_package.__init_metainfo__()
