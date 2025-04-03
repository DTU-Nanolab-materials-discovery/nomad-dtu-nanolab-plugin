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
from ase.data import chemical_symbols
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import CompositeSystemReference
from nomad.datamodel.metainfo.basesections.v1 import Activity
from nomad.metainfo import Package, Section
from nomad.metainfo.metainfo import MEnum, Quantity, SubSection
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


class SampleProperty(ArchiveSection):
    source = Quantity(
        type=Activity,
        description='The source of the sample property.',
    )
    interpolation = Quantity(
        type=MEnum(['None', 'Nearest', 'Linear', 'Cubic']),
        description='The interpolation method used to obtain the sample property.',
        default='None',
    )


class Composition(SampleProperty):
    for element in chemical_symbols:
        locals()[f'{element}'] = Quantity(
            type=np.float64,
            description=f'Atomic fraction of {element} in the sample.',
        )


class Deposition(SampleProperty):
    temperature = Quantity(
        type=np.float64,
        description='The (mean) temperature of the substrate during deposition.',
        unit='K',
    )
    pressure = Quantity(
        type=np.float64,
        description='The (mean) pressure of the deposition chamber during deposition.',
        unit='Pa',
    )
    time = Quantity(
        type=np.float64,
        description='The duration of the deposition.',
        unit='s',
    )
    material_space = Quantity(
        type=str,
        description='The material space of the sample.',
    )
    operator = Quantity(
        type=str,
        description='The name of the operator who created the sample.',
    )


class XrdPeak(ArchiveSection):
    position = Quantity(
        type=np.float64,
        description='The position of the peak.',
        unit='nm^-1',
    )
    intensity = Quantity(
        type=np.float64,
        description='The intensity of the peak.',
    )
    fwhm = Quantity(
        type=np.float64,
        description='The full width at half maximum of the peak.',
        unit='nm^-1',
    )


class XpsPeak(ArchiveSection):
    position = Quantity(
        type=np.float64,
        description='The position of the peak.',
        unit='eV',
    )
    intensity = Quantity(
        type=np.float64,
        description='The intensity of the peak.',
    )
    fwhm = Quantity(
        type=np.float64,
        description='The full width at half maximum of the peak.',
        unit='eV',
    )


class BandGap(SampleProperty):
    value = Quantity(
        type=np.float64,
        description='The band gap of the sample.',
        unit='eV',
    )


class Thickness(SampleProperty):
    value = Quantity(
        type=np.float64,
        description='The thickness of the sample.',
        unit='nm',
    )


class XrdData(SampleProperty):
    xrd_peaks = SubSection(
        section_def=XrdPeak,
        repeats=True,
        description='The x-ray diffraction peaks of the sample.',
    )


class XpsData(SampleProperty):
    xps_peaks = SubSection(
        section_def=XpsPeak,
        repeats=True,
        description='The x-ray photoelectron spectroscopy peaks of the sample.',
    )


class DTUCombinatorialSample(CombinatorialSample, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Combinatorial Sample',
    )
    band_gap = SubSection(section_def=BandGap)
    thickness = SubSection(section_def=Thickness)
    composition = SubSection(section_def=Composition)
    surface_composition = SubSection(section_def=Composition)
    deposition = SubSection(section_def=Deposition)
    xrd_data = SubSection(section_def=XrdData)
    xps_data = SubSection(section_def=XpsData)


class ProcessParameterOverview(Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Process Parameter Overview',
    )

    position_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    position_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
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
    width = Quantity(
        type=np.float64,
        description='The width of the substrate.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    length = Quantity(
        type=np.float64,
        description='The length of the substrate.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )


class DTUCombinatorialLibrary(CombinatorialLibrary, ThinFilmStack, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Combinatorial Library',
    )

    process_parameter_overview = Quantity(
        type=ProcessParameterOverview,
        description='An overview of the process parameters used to create the library.',
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
