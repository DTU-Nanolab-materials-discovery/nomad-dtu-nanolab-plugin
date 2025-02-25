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
from nomad.datamodel.metainfo.basesections import CompositeSystemReference
from nomad.metainfo import Package, Section
from nomad.metainfo.metainfo import Quantity
from nomad_material_processing.combinatorial import (
    CombinatorialLibrary,
    CombinatorialSample,
)
from nomad_material_processing.general import ThinFilmStack

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
        DtuNanolabMeasurement,
    )
    from nomad_dtu_nanolab_plugin.schema_packages.sputtering import DTUSputtering

m_package = Package(name='DTU customised Substrate scheme')


class DTUCombinatorialSample(CombinatorialSample, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Combinatorial Sample',
    )


class DTUCombinatorialLibrary(CombinatorialLibrary, ThinFilmStack, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Combinatorial Library',
    )
    # we store the position and rotation of the substrate on the platen
    # in the combinatorial library entry
    position_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    position_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    rotation = Quantity(
        type=np.float64,
        description='The rotation of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )

    def get_references(self, entry_type: type[Schema] = None) -> list:
        from nomad.client import ArchiveQuery

        query = {
            'entry_references.target_entry_id:all': [self.m_parent.entry_id],
        }
        if entry_type:
            query['section_defs.definition_qualified_name:all'] = [
                entry_type.m_def.qualified_name()
            ]
        a_query = ArchiveQuery(
            query=query,
            required='*',
            url=self.m_context.installation_url,
        )
        entry_list = a_query.download()
        return [entry.data for entry in entry_list]

    def get_measurements(self) -> list['DtuNanolabMeasurement']:
        from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
            DtuNanolabMeasurement,
        )

        return self.get_references(DtuNanolabMeasurement)

    def get_sputtering(self) -> 'DTUSputtering':
        from nomad_dtu_nanolab_plugin.schema_packages.sputtering import DTUSputtering

        results = self.get_references(DTUSputtering)
        if len(results) > 1:
            print('Warning: More than one sputtering reference found.')
        return results[0] if results else None


class DtuLibraryReference(CompositeSystemReference):
    reference = Quantity(
        type=DTUCombinatorialLibrary,
        description='A reference to a NOMAD `CompositeSystem` entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )


m_package.__init_metainfo__()
