from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go
from ase.data import chemical_symbols
from ase.spacegroup import Spacegroup
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Process,
)
from nomad.datamodel.metainfo.basesections.v1 import (
    Activity,
    ElementalComposition,
    Entity,
    EntityReference,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.datamodel.metainfo.workflow import Link
from nomad.metainfo import MEnum, Package, Quantity, Section, SectionProxy, SubSection
from nomad_material_processing.combinatorial import (
    CombinatorialLibrary,
    CombinatorialSample,
)
from nomad_material_processing.general import (
    Cylinder,
    Geometry,
    RectangleCuboid,
    ThinFilmStack,
)
from nomad_measurements.utils import create_archive

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
        DtuNanolabMeasurement,
    )
    from nomad_dtu_nanolab_plugin.schema_packages.sputtering import DTUSputtering

# Constants
MAX_SPACE_GROUP_NUMBER = 231  # 1-230 space groups, so range goes to 231
SPACE_GROUP_SYMBOL_TO_NUMBER = {
    Spacegroup(no).symbol: no for no in range(1, MAX_SPACE_GROUP_NUMBER)
} # Map of space group symbols to numbers

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
    method = Quantity(
        type=MEnum('Sputtering', 'Rapid Thermal Processing', 'Other'),
        description='The deposition method used to create the sample.',
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
    space_group_nbr = Quantity(
        type=int,
        description='The space group number (1-230)',
    )
    space_group = Quantity(
        type=MEnum([Spacegroup(no).symbol for no in range(1, MAX_SPACE_GROUP_NUMBER)]),
        description='The space group symbol',
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizes the crystal structure by ensuring that both
        space group number and symbol are set.

        If only one of the space group number or symbol is provided, the other
        is derived using the ASE Spacegroup class.

        Parameters
        ----------
        archive : Archive
            The archive object being normalized.
        logger : Logger
            Logger for recording normalization events or warnings.
        """
        super().normalize(archive, logger)

        if self.space_group_nbr and not self.space_group:
            if 1 <= self.space_group_nbr < MAX_SPACE_GROUP_NUMBER:
                self.space_group = Spacegroup(self.space_group_nbr).symbol
            else:
                logger.warning(
                    f'Invalid space group number {self.space_group_nbr}. '
                    'It should be between 1 and 230.'
                )
        elif self.space_group and not self.space_group_nbr:
            space_group_nbr_temp = SPACE_GROUP_SYMBOL_TO_NUMBER.get(self.space_group)
            if space_group_nbr_temp:
                self.space_group_nbr = space_group_nbr_temp
            else:
                logger.warning(
                    f'Invalid space group symbol {self.space_group}. '
                    'It does not correspond to any known space group.'
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
                editable=Filter(include=[]),
            ),
        ),
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
            for e, v in composition.items()
            if e in chemical_symbols and v
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


class ProcessParameterOverview(ArchiveSection):
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

    process_parameter_overview = SubSection(
        section_def=ProcessParameterOverview,
        description='An overview of the process parameters used to create the library.',
    )

    geometry = SubSection(
        section_def=Geometry,
        description='The geometries of the samples in the library.',
    )

    parent_library = SubSection(
        section_def=SectionProxy('DtuLibraryReference'),
        description='The parent library of the combinatorial library. '
        'Only applicable if this library is a child of another library.',
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
        """
        Normalizes the combinatorial library entry by ensuring required fields are set.

        This method first calls the superclass's normalize method. It then checks if the
        geometry attribute is not set and, if so, attempts to set it from
        the substrate's reference geometry if available.

        Parameters
        ----------
        archive : Archive
            The archive object being normalized.
        logger : Logger
            Logger for recording normalization events or warnings.
        """
        super().normalize(archive, logger)

        # Ensure that the geometry is set to the default if not provided
        if not self.geometry and self.substrate.reference:
            substrate_geometry = self.substrate.reference.geometry
            if substrate_geometry:
                self.geometry = substrate_geometry


class DtuLibraryReference(CompositeSystemReference):
    reference = Quantity(
        type=DTUCombinatorialLibrary,
        description='A reference to a NOMAD `CompositeSystem` entry.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )


class DTULibraryParts(ArchiveSection):
    """
    Schema for parts of a DTU combinatorial library.
    """

    name = Quantity(
        type=str,
        description='The name of the library part.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    library_name = Quantity(
        type=str,
        description='The name of the library.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    lab_id = Quantity(
        type=str,
        description='The ID of the new library part.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    upper_left_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the upper left corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='mm'
        ),
        unit='m',
    )
    upper_left_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the upper left corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='mm'
        ),
        unit='m',
    )
    lower_right_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the lower right corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='mm'
        ),
        unit='m',
    )
    lower_right_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the lower right corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='mm'
        ),
        unit='m',
    )
    part_size = Quantity(
        type=np.float64,
        shape=[2],
        description='The size of the library in the x and y direction.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='mm'
        ),
        unit='m',
    )
    geometry = SubSection(
        section_def=Geometry,
        description='The geometries of the samples in the library.',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTULibraryParts` class.
        Placeholder for normalization logic.
        """
        pass


class DTULibraryCleaving(Process, Schema, PlotSection):
    """
    Schema for substrate cleaving at the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Library Cleaving',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'datetime',
                    'combinatorial_library',
                    'fetch_library_size',
                    'library_x_length',
                    'library_y_length',
                    'pattern',
                    'number_of_pieces',
                    'generate_pattern',
                    'new_pieces',
                    'create_child_libraries',
                    'child_libraries',
                    'end_time',
                    'description',
                    'method',
                    'location',
                ],
                visible=Filter(
                    exclude=[
                        'end_time',
                    ]
                ),
            )
        ),
    )
    combinatorial_library = Quantity(
        type=DTUCombinatorialLibrary,
        description='The combinatorial sample that is broken into pieces .',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )
    fetch_library_size = Quantity(
        type=bool,
        description='Fetch the size of the library.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ActionEditQuantity),
    )
    library_x_length = Quantity(
        type=np.float64,
        description='The length of the library in the x direction.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
            label='Library width (x)',
        ),
        unit='m',
    )
    library_y_length = Quantity(
        type=np.float64,
        description='The length of the library in the y direction.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
            label='Library height (y)',
        ),
        unit='m',
    )
    pattern = Quantity(
        type=MEnum(
            'squares',
            'horizontal stripes',
            'vertical stripes',
            'custom',
        ),
        description='The pattern according to which the original library is broken.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RadioEnumEditQuantity),
        default='custom',
    )
    number_of_pieces = Quantity(
        type=int,
        description='The number of pieces the original library is broken into '
        'for horizontal, vertical and custom. '
        'For squares it is the number of squares in one direction.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    generate_pattern = Quantity(
        type=bool,
        description='Create the new pieces from the pattern.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ActionEditQuantity),
        default=False,
    )
    create_child_libraries = Quantity(
        type=bool,
        description='Create child libraries from the new pieces.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ActionEditQuantity),
        default=False,
    )
    new_pieces = SubSection(
        section_def=DTULibraryParts,
        repeats=True,
    )
    child_libraries = SubSection(
        section_def=DtuLibraryReference,
        repeats=True,
        description='The child libraries created from the combinatorial library.',
    )

    def recognize_pattern(self, logger: 'BoundLogger') -> None:
        """
        Recognizes the pattern of the library and creates the new pieces accordingly.
        """
        height = None
        if self.combinatorial_library.geometry:
            height = self.combinatorial_library.geometry.height
        start_x = (self.library_x_length / 2) * (-1)
        start_y = self.library_y_length / 2

        if self.pattern == 'squares':
            total_nr = self.number_of_pieces**2
            size = self.library_x_length / self.number_of_pieces
            for j in range(self.number_of_pieces):
                for i in range(self.number_of_pieces):
                    piece = DTULibraryParts()
                    number = 1 + j * self.number_of_pieces + i
                    piece.library_name = (
                        f'{self.combinatorial_library.name} S{number}-{total_nr}'
                    )
                    piece.name = f'Square {number} of {total_nr}'
                    piece.lab_id = piece.library_name.replace(' ', '_')
                    piece.upper_left_x = start_x + i * size
                    piece.upper_left_y = start_y - (j) * size
                    piece.lower_right_x = start_x + (i + 1) * size
                    piece.lower_right_y = start_y - (j + 1) * size
                    piece.part_size = (size, size)
                    piece.geometry = RectangleCuboid(
                        length=size,
                        width=size,
                        height=height,
                        surface_area=(size * size),
                    )
                    if height is not None:
                        piece.geometry.volume = size * size * height

                    self.new_pieces.append(piece)
        elif self.pattern == 'horizontal stripes':
            size = self.library_y_length / self.number_of_pieces

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                number = i + 1
                piece.library_name = (
                    f'{self.combinatorial_library.name} H{number}-'
                    f'{self.number_of_pieces}'
                )
                piece.name = f'Horizontal stripe {number} of {self.number_of_pieces}'
                piece.lab_id = piece.library_name.replace(' ', '_')
                piece.upper_left_x = start_x
                piece.upper_left_y = start_y - i * size
                piece.lower_right_x = start_x + self.library_x_length
                piece.lower_right_y = start_y - (i + 1) * size
                piece.part_size = (self.library_x_length, size)
                piece.geometry = RectangleCuboid(
                    length=size,
                    width=self.library_x_length,
                    height=height,
                    surface_area=(self.library_x_length * size),
                )
                if height is not None:
                    piece.geometry.volume = self.library_x_length * size * height

                self.new_pieces.append(piece)
        elif self.pattern == 'vertical stripes':
            size = self.library_x_length / self.number_of_pieces

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                number = i + 1
                piece.library_name = (
                    f'{self.combinatorial_library.name} V{number}-'
                    f'{self.number_of_pieces}'
                )
                piece.name = f'Vertical stripe {number} of {self.number_of_pieces}'
                piece.lab_id = piece.library_name.replace(' ', '_')
                piece.upper_left_x = start_x + i * size
                piece.upper_left_y = start_y
                piece.lower_right_x = start_x + (i + 1) * size
                piece.lower_right_y = start_y - self.library_y_length
                piece.part_size = (size, self.library_y_length)
                piece.geometry = RectangleCuboid(
                    length=self.library_y_length,
                    width=size,
                    height=height,
                    surface_area=(size * self.library_y_length),
                )
                if height is not None:
                    piece.geometry.volume = size * self.library_y_length * height

                self.new_pieces.append(piece)
        elif self.pattern == 'custom':
            self.handle_custom_pattern()

    def handle_custom_pattern(self) -> None:
        """
        Handles the filling of custom pattern for the library pieces.
        """
        for i in range(self.number_of_pieces):
            piece = DTULibraryParts()
            piece.library_name = (
                f'{self.combinatorial_library.name} C{i + 1}-{self.number_of_pieces}'
            )
            piece.name = f'Custom piece {i + 1} of {self.number_of_pieces}'
            piece.lab_id = piece.library_name.replace(' ', '_')
            self.new_pieces.append(piece)

    def handle_custom_plot(self) -> None:
        """
        Handles the plotting of the custom pattern for the library pieces.
        """
        if self.new_pieces is None or len(self.new_pieces) == 0:
            return
        fig = go.Figure()

        # self.add_original_library_to_plot(fig)

        # TODO : add the custom pieces to the plot considering their shapes

        fig.update_layout(
            title='Positions of the new pieces in the library',
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            width=800,
            height=700,
            xaxis=dict(
                range=[
                    -self.library_x_length.to('mm').magnitude * 1.1 / 2,
                    self.library_x_length.to('mm').magnitude * 1.1 / 2,
                ],
            ),
            yaxis=dict(
                range=[
                    -self.library_y_length.to('mm').magnitude * 1.1 / 2,
                    self.library_y_length.to('mm').magnitude * 1.1 / 2,
                ],
            ),
        )

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )

        self.figures.append(
            PlotlyFigure(
                label='Positions of the new pieces in the library',
                figure=plot_json,
            )
        )

    def add_original_library_to_plot(self, fig: go.Figure) -> None:
        """
        Adds the original library to the plot.
        """

        x0 = -self.library_x_length.to('mm').magnitude / 2
        y0 = self.library_y_length.to('mm').magnitude / 2
        x1 = self.library_x_length.to('mm').magnitude / 2
        y1 = -self.library_y_length.to('mm').magnitude / 2

        if self.combinatorial_library is not None:
            if isinstance(self.combinatorial_library.geometry, Cylinder):
                fig.add_shape(
                    type='circle',
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    line=dict(color='red', width=3),
                    fillcolor='white',
                    opacity=0.5,
                )
            elif isinstance(self.combinatorial_library.geometry, RectangleCuboid):
                fig.add_shape(
                    type='rect',
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    line=dict(color='red', width=3),
                    fillcolor='white',
                    opacity=0.5,
                )
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(y0 + y1) / 2,
                text=self.combinatorial_library.name,
                showarrow=False,
            )

    def plot(self) -> None:
        """
        Plots the positions of the new pieces in the library.
        """

        # Removed redundant import of plotly.graph_objects as go
        if self.new_pieces is None or len(self.new_pieces) == 0:
            return
        fig = go.Figure()

        x0 = -self.library_x_length.to('mm').magnitude / 2
        y0 = self.library_y_length.to('mm').magnitude / 2
        x1 = self.library_x_length.to('mm').magnitude / 2
        y1 = -self.library_y_length.to('mm').magnitude / 2

        if self.combinatorial_library is not None:
            if isinstance(self.combinatorial_library.geometry, Cylinder):
                fig.add_shape(
                    type='circle',
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    line=dict(color='red', width=3),
                    fillcolor='white',
                    opacity=0.5,
                )
            elif isinstance(self.combinatorial_library.geometry, RectangleCuboid):
                fig.add_shape(
                    type='rect',
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    line=dict(color='red', width=3),
                    fillcolor='white',
                    opacity=0.5,
                )
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(y0 + y1) / 2,
                text=self.combinatorial_library.name,
                showarrow=False,
            )

        if self.pattern != 'custom':
            for piece in self.new_pieces:
                if piece.part_size is None:
                    continue

                fig.add_shape(
                    type='rect',
                    x0=(
                        piece.upper_left_x.to('mm').magnitude
                        + (0.01 * piece.part_size[0].to('mm').magnitude)
                    ),
                    y0=(
                        piece.upper_left_y.to('mm').magnitude
                        - (0.01 * piece.part_size[1].to('mm').magnitude)
                    ),
                    x1=(
                        piece.lower_right_x.to('mm').magnitude
                        - (0.01 * piece.part_size[0].to('mm').magnitude)
                    ),
                    y1=(
                        piece.lower_right_y.to('mm').magnitude
                        + (0.01 * piece.part_size[1].to('mm').magnitude)
                    ),
                    name=piece.library_name,
                    line=dict(color='green'),
                    fillcolor='lightgreen',
                    opacity=0.4,
                )
                fig.add_annotation(
                    x=(
                        (
                            piece.upper_left_x.to('mm').magnitude
                            + piece.lower_right_x.to('mm').magnitude
                        )
                        / 2
                    ),
                    y=(
                        (
                            piece.upper_left_y.to('mm').magnitude
                            + piece.lower_right_y.to('mm').magnitude
                        )
                        / 2
                    ),
                    text=piece.library_name,
                    showarrow=False,
                )
        fig.update_layout(
            title='Positions of the new pieces in the library',
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            width=800,
            height=700,
            xaxis=dict(
                range=[
                    -self.library_x_length.to('mm').magnitude * 1.1 / 2,
                    self.library_x_length.to('mm').magnitude * 1.1 / 2,
                ],
            ),
            yaxis=dict(
                range=[
                    -self.library_y_length.to('mm').magnitude * 1.1 / 2,
                    self.library_y_length.to('mm').magnitude * 1.1 / 2,
                ],
            ),
        )

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )

        self.figures.append(
            PlotlyFigure(
                label='Positions of the new pieces in the library',
                figure=plot_json,
            )
        )

    def add_libraries(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Create and add child combinatorial library entries based on
        the new pieces in the current library.

        For each new piece (if not using a 'custom' pattern and if the piece has
        a defined size), this method:
        - Creates a new DTUCombinatorialLibrary instance with relevant attributes.
        - Normalizes the new library and creates an associated archive.
        - Appends a CompositeSystemReference to the list of child libraries.

        Parameters:
            archive (EntryArchive): The parent entry archive to which
            new child archives are linked.
            logger (BoundLogger): Logger for logging errors
            or information during processing.

        Side Effects:
            Updates self.child_libraries with references to the
            newly created child libraries.
        """

        origin: DTUCombinatorialLibrary = self.combinatorial_library
        origin_ref = DtuLibraryReference(
            reference=origin.m_proxy_value,
            name=origin.name,
            lab_id=origin.lab_id,
        )
        children = []

        if self.pattern == 'custom':
            return
        piece: DTULibraryParts
        for piece in self.new_pieces:
            if piece.part_size is None:
                continue
            library = DTUCombinatorialLibrary(
                name=piece.library_name,
                datetime=self.datetime,
                lab_id=piece.lab_id,
                geometry=piece.geometry,
                description=f'Part of {origin.name} library',
                process_parameter_overview=origin.process_parameter_overview,
                elemental_composition=origin.elemental_composition,
                components=origin.components,
                layers=origin.layers,
                substrate=origin.substrate,
                parent_library=origin_ref,
            )
            file_name = f'{library.lab_id}.archive.json'
            children.append(
                CompositeSystemReference(
                    reference=create_archive(library, archive, file_name),
                    name=library.name,
                    lab_id=library.lab_id,
                )
            )
        self.child_libraries = children

    def fill_library_size(self, logger: 'BoundLogger') -> None:
        """
        Sets the `library_x_length` and `library_y_length` attributes based on
        the geometry of the associated combinatorial library.

        If the geometry is a RectangleCuboid, sets the size to [width, length].
        If the geometry is a Cylinder, sets the size to [diameter, diameter].
        If the geometry is unrecognized, logs an error and does not set the size.

        Args:
            logger (BoundLogger): Logger for error reporting.
        """
        # fetch the size of the library from its geometry subsection
        if isinstance(self.combinatorial_library.geometry, RectangleCuboid):
            self.library_x_length = self.combinatorial_library.geometry.width
            self.library_y_length = self.combinatorial_library.geometry.length
        elif isinstance(self.combinatorial_library.geometry, Cylinder):
            self.library_x_length = self.combinatorial_library.geometry.radius * 2
            self.library_y_length = self.combinatorial_library.geometry.radius * 2
        else:
            logger.error(
                'The library size could not be determined from the geometry. '
                'Please add it manually.'
            )
            return

    def handle_workflow(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        if self.combinatorial_library is not None:
            archive.workflow2.inputs.append(
                Link(
                    name=f'Parent library: {self.combinatorial_library.name}',
                    section=self.combinatorial_library,
                )
            )
        if self.child_libraries is not None and len(self.child_libraries) > 0:
            archive.workflow2.outputs.extend(
                [
                    Link(name=f'Child library: {lib.name}', section=lib.reference)
                    for lib in self.child_libraries
                ]
            )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrateCleaning` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        archive.workflow2 = None
        super().normalize(archive, logger)
        self.end_time = self.datetime
        self.method = 'Sample splitting'
        if not self.location:
            self.location = 'DTU Nanolab'

        if self.fetch_library_size and self.combinatorial_library is not None:
            try:
                self.fill_library_size(logger)
            finally:
                self.fetch_library_size = False

        # Check the pattern input and create the new pieces according to selection
        if self.generate_pattern:
            self.generate_pattern = False
            if self.number_of_pieces is None or self.number_of_pieces <= 1:
                logger.error(
                    'The number of pieces must be at least 2 to create a pattern.'
                )
                return
            elif self.pattern not in [
                'squares',
                'horizontal stripes',
                'vertical stripes',
                'custom',
            ]:
                logger.error(f'Unknown pattern {self.pattern}.')
                return
            else:
                self.new_pieces = []
                self.recognize_pattern(logger)

        if self.new_pieces:
            # update the plot with the new pieces
            self.figures = []
            if self.pattern == 'custom':
                self.handle_custom_plot()
            else:
                self.plot()
            # if the user wants to create child libraries from the new pieces
            # then we create them and add them to the archive
            # and reset the create_child_libraries flag
            if self.create_child_libraries:
                self.create_child_libraries = False
                origin = self.combinatorial_library
                if origin is None:
                    logger.error(
                        'A combinatorial library must be set to create child libraries.'
                    )
                    return
                else:
                    self.add_libraries(archive, logger)

        self.handle_workflow(archive, logger)


m_package.__init_metainfo__()
