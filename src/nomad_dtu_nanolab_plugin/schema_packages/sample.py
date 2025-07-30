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
from ase.spacegroup import Spacegroup
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import CompositeSystemReference
from nomad.datamodel.metainfo.basesections.v1 import (
    Activity,
    ElementalComposition,
    Entity,
    EntityReference,
)
from nomad.metainfo import Package, Section
from nomad.metainfo.metainfo import MEnum, Quantity, SubSection
from nomad_material_processing.combinatorial import (
    CombinatorialLibrary,
    CombinatorialSample,
)
from nomad_material_processing.general import Geometry, ThinFilmStack

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
        DtuNanolabMeasurement,
    )
    from nomad_dtu_nanolab_plugin.schema_packages.sputtering import DTUSputtering

m_package = Package()


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


class AbsorptionCoefficient(SampleProperty):
    value = Quantity(
        type=np.float64,
        shape=['*'],
        description='The absorption coefficient of the sample.',
        unit='cm^-1',
    )
    energy = Quantity(
        type=np.float64,
        shape=['*'],
        description='The corresponding energies for the absorption coefficient values.',
        unit='nm',
    )
    absorption_edge = Quantity(
        type=np.float64,
        description='The inflection point of the absorption spectrum.',
        unit='eV',
    )
    mean_absorption_above_edge = Quantity(
        type=np.float64,
        description='The mean absorption coefficient above the absorption edge.',
        unit='cm^-1',
    )



class Thickness(SampleProperty):
    value = Quantity(
        type=np.float64,
        description='The thickness of the sample.',
        unit='nm',
    )


class CrystalStructure(SampleProperty):
    space_group = Quantity(
        type=MEnum([Spacegroup(no).symbol for no in range(1, 231)]),
    )
    a = Quantity(
        type=np.float64,
        description='The lattice parameter a of the crystal structure.',
        unit='nm',
    )
    b = Quantity(
        type=np.float64,
        description='The lattice parameter b of the crystal structure.',
        unit='nm',
    )
    c = Quantity(
        type=np.float64,
        description='The lattice parameter c of the crystal structure.',
        unit='nm',
    )
    alpha = Quantity(
        type=np.float64,
        description='The angle alpha of the crystal structure.',
        unit='degree',
    )
    beta = Quantity(
        type=np.float64,
        description='The angle beta of the crystal structure.',
        unit='degree',
    )
    gamma = Quantity(
        type=np.float64,
        description='The angle gamma of the crystal structure.',
        unit='degree',
    )


class XrdData(SampleProperty):
    diffraction_intensity = Quantity(
        type=np.float64,
        shape=['*'],
        description='The intensity of the x-ray diffraction peaks.',
        unit='dimensionless',
    )
    scattering_vector = Quantity(
        type=np.float64,
        shape=['*'],
        description='The scattering vector of the x-ray diffraction peaks.',
        unit='nm^-1',
    )
    xrd_peaks = SubSection(
        section_def=XrdPeak,
        repeats=True,
        description='The x-ray diffraction peaks of the sample.',
    )
    unique_peak_sets = SubSection(
        section_def='UniqueXrdPeaksReference',
        repeats=True,
        description='The sets of unique x-ray diffraction peaks of the sample.',
    )


class XpsData(SampleProperty):
    intensity = Quantity(
        type=np.float64,
        shape=['*'],
        description='The intensity of the x-ray photoelectron spectroscopy peaks.',
        unit='dimensionless',
    )
    binding_energy = Quantity(
        type=np.float64,
        shape=['*'],
        description='The binding energy of the x-ray photoelectron spectroscopy peaks.',
        unit='eV',
    )
    xps_peaks = SubSection(
        section_def=XpsPeak,
        repeats=True,
        description='The x-ray photoelectron spectroscopy peaks of the sample.',
    )


class EllipsometryData(SampleProperty):
    refractive_index = Quantity(
        type=np.float64,
        shape=['*'],
        description='The refractive index of the sample.',
        unit='dimensionless',
    )
    extinction_coefficient = Quantity(
        type=np.float64,
        shape=['*'],
        description='The extinction coefficient of the sample.',
        unit='dimensionless',
    )
    wavelength = Quantity(
        type=np.float64,
        shape=['*'],
        description='The wavelength of the light used for ellipsometry.',
        unit='nm',
    )


class UvVisData(SampleProperty):
    reflectance = Quantity(
        type=np.float64,
        shape=['*'],
        description='The reflectance of the sample.',
        unit='dimensionless',
    )
    transmittance = Quantity(
        type=np.float64,
        shape=['*'],
        description='The transmittance of the sample.',
        unit='dimensionless',
    )
    wavelength = Quantity(
        type=np.float64,
        shape=['*'],
        description='The wavelength of the light used for UV-Vis spectroscopy.',
        unit='nm',
    )


class DTUCombinatorialSample(CombinatorialSample, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Combinatorial Sample',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                visible=Filter(exclude=['elemental_composition', 'components']),
                editable=Filter(include=[])
            ),
        )
    )
    band_gap = SubSection(section_def=BandGap)
    absorption_coefficient = SubSection(section_def=AbsorptionCoefficient)
    thickness = SubSection(section_def=Thickness)
    composition = SubSection(section_def=Composition)
    surface_composition = SubSection(section_def=Composition)
    deposition = SubSection(section_def=Deposition)
    main_phase = SubSection(section_def=CrystalStructure)
    secondary_phases = SubSection(section_def=CrystalStructure, repeats=True)
    xrd_data = SubSection(section_def=XrdData)
    xps_data = SubSection(section_def=XpsData)
    ellipsometry_data = SubSection(section_def=EllipsometryData)
    uv_vis_data = SubSection(section_def=UvVisData)

    def normalize(self, archive, logger):
        composition = {}
        if self.composition:
            composition = self.composition.m_to_dict()
        if len(composition) == 0 and self.surface_composition:
            composition = self.surface_composition.m_to_dict()

        self.elemental_composition = [
            ElementalComposition(element=e, atomic_fraction=v)
            for e,v in composition.items() if v
        ]

        super().normalize(archive, logger)


class UniqueXrdPeaks(Entity):
    peak_positions = Quantity(
        type=np.float64,
        shape=['*'],
        description='The positions of the unique x-ray diffraction peaks.',
    )
    max_q = Quantity(
        type=np.float64,
        description='The maximum scattering vector of the pattern.',
        unit='nm^-1',
    )
    min_q = Quantity(
        type=np.float64,
        description='The minimum scattering vector of the pattern.',
        unit='nm^-1',
    )
    crystal_structure = SubSection(
        section_def=CrystalStructure,
    )
    sub_sets = SubSection(
        section_def='UniqueXrdPeaksReference',
        repeats=True,
    )


class UniqueXrdPeaksReference(EntityReference):
    reference = Quantity(
        type=UniqueXrdPeaks,
        description='A reference to a unique set of x-ray diffraction peaks.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )


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

    geometry = SubSection(
        section_def=Geometry,
        description='The geometries of the samples in the library.',
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

    def normalize(self, archive, logger):
        super().normalize(archive, logger)

        # Ensure that the geometry is set to the default if not provided
        # if not self.geometry and self.substrate.reference:
        #    self.geometry = self.substrate.reference.geometry

class DtuLibraryReference(CompositeSystemReference):
    reference = Quantity(
        type=DTUCombinatorialLibrary,
        description='A reference to a NOMAD `CompositeSystem` entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )


m_package.__init_metainfo__()
