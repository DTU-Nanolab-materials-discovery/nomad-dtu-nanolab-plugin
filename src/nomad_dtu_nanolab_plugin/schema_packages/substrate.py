from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    Collection,
    CompositeSystemReference,
    Process,
    ProcessStep,
    PubChemPureSubstanceSection,
    PureSubstanceComponent,
    ReadableIdentifiers,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, MProxy, Package, Quantity, Section, SubSection
from nomad_material_processing.general import (
    CrystallineSubstrate,
    Dopant,
    ElectronicProperties,
    Geometry,
    RectangleCuboid,
)
from nomad_material_processing.utils import create_archive
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
    DtuLibraryReference,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU customised Substrate scheme')


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



class DTUSubstrateReference(CompositeSystemReference):
    reference = Quantity(
        type=DTUSubstrate,
        description='The reference to the substrate entity.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )


class DTUSubstrateBatch(Collection, Schema):
    """
    Schema for substrate batches in the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Substrate Batch',
        a_template=dict(
            substrate_identifiers=dict(),
        ),
    )
    entities = SubSection(
        section_def=DTUSubstrateReference,
        description='References to the entities that make up the collection.',
        repeats=True,
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
    shape = Quantity(
        type=MEnum(['Rectangular', 'Circular']),
        description=(
            'The shape of the substrate. Circular (wafer) or rectangular. '
            'If the shape is circular, the diameter is used to define the size '
            'of the substrate. If the shape is rectangular, the length and '
            'width are used to define the size of the substrate.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.RadioEnumEditQuantity,
        ),
        default='Rectangular',
    )
    diameter = Quantity(
        type=np.float64,
        default=0.1524, #6 inch
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'inch'},
        unit='m',
        description=(
            'Only used if the shape is circular. The diameter of the substrate.'
        )
    )
    length = Quantity(
        type=np.float64,
        default=0.04,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
        description=(
            'Only used if the shape is rectangular. The length of the substrate.'
        )
    )
    width = Quantity(
        type=np.float64,
        default=0.04,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
        description=(
            'Only used if the shape is rectangular. The width of the substrate.'
        )
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

    def next_used_in(
        self, entry_type: type[Schema], negate: bool = False
    ) -> DTUSubstrate:
        from nomad.search import MetadataPagination, search

        ref: DTUSubstrateReference
        for ref in self.entities:
            if isinstance(ref.reference, MProxy):
                ref.reference.m_proxy_resolve()
            if not isinstance(ref.reference, DTUSubstrate):
                continue
            substrate = ref.reference
            query = {
                'section_defs.definition_qualified_name:all': [
                    entry_type.m_def.qualified_name()
                ],
                'entry_references.target_entry_id:all': [substrate.m_parent.entry_id],
            }
            search_result = search(
                owner='all',
                query=query,
                pagination=MetadataPagination(page_size=1),
                user_id=self.m_parent.metadata.main_author.user_id,
            )
            if search_result.pagination.total > 0 and not negate:
                return substrate
            elif search_result.pagination.total == 0 and negate:
                return substrate
        return None

    def next_not_used_in(self, entry_type: type[Schema]) -> DTUSubstrate:
        return self.next_used_in(entry_type, negate=True)

    def generate_geometry(self) -> Geometry:
        """
        Generate the geometry of the substrate based on its shape.

        Returns:
            object: The geometry of the substrate.
        """
        if self.shape == 'Rectangular':
            geometry = RectangleCuboid()
            geometry.length = self.length
            geometry.width = self.width
        elif self.shape == 'Circular':
            geometry = Cylinder()
            geometry.radius = self.diameter/2
        else:
            raise ValueError(f'Unknown shape: {self.shape}')

        geometry.height = self.thickness
        return geometry

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrateBatch` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.create_substrates:
            self.entities = []
            substrate = DTUSubstrate()

            substrate.geometry = self.generate_geometry()

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
            electronic_properties.electrical_resistivity = self.doping_of_substrate
            substrate.electronic_properties = electronic_properties

            substrate.supplier = self.supplier
            substrate.substrate_polishing = self.substrate_polishing

            substrate.normalize(archive, logger)

            for i in range(self.number_of_substrates):
                substrate.name = f'{self.name} Substrate {i}'
                substrate.datetime = self.datetime
                substrate.lab_id = f'{self.lab_id}-{i}'
                file_name = f'{substrate.lab_id}.archive.json'
                substrate_archive = create_archive(substrate, archive, file_name)
                self.entities.append(
                    CompositeSystemReference(
                        reference=substrate_archive,
                        name=substrate.name,
                        lab_id=substrate.lab_id,
                    )
                )
            self.create_substrates = False


class CleaningStep(ProcessStep):
    m_def = Section()
    cleaning_agent = Quantity(
        type=MEnum(['N2-gun', 'Ethanol', 'Acetone', 'IPA', 'H2O']),
        default='N2-gun',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RadioEnumEditQuantity),
    )
    sonication = Quantity(
        type=bool,
        default=False,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
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
    steps = SubSection(
        section_def=CleaningStep,
        repeats=True,
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


class DTUSubstrateCutting(Process, Schema):
    """
    Schema for substrate cutting at the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Substrate Cutting',
    )
    substrate_batch = Quantity(
        type=DTUSubstrateBatch,
        description='The substrate batch that was cut.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )
    instrument_name = Quantity(
        type=str,
        default='microSTRUCT vario from the company 3D-Micromac AG',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    laser_power = Quantity(
        type=np.float64,
        default=50,
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
        unit='W',
    )
    laser_wavelength = Quantity(
        type=np.float64,
        default=532 * 1e-9,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
        ),
        unit='m',
    )
    repetition_rate = Quantity(
        type=np.float64,
        default=200,
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
        unit='Hz',
    )
    pattern_repetitions = Quantity(
        type=int,
        default=6,
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    writing_speed = Quantity(
        type=np.float64,
        default=50 * 1e-3,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm/s',
        ),
        unit='m/s',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrateCutting` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        self.samples = self.substrate_batch.entities
        return super().normalize(archive, logger)


m_package.__init_metainfo__()

class DTULibraryParts(Collection, Schema):
    """
    Schema for parts of a DTU combinatorial library.
    """

    m_def = Section(    )

    library_name = Quantity(
        type=str,
        description='The name of the library.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    upper_left_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the upper left corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm'
            ),
        unit='m',
    )

    upper_left_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the upper left corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm'
            ),
        unit='m',
    )
    lower_right_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the lower right corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm'
            ),
        unit='m',
    )
    lower_right_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the lower right corner of the library.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm'
            ),
        unit='m',
    )
    part_size = Quantity(
        type = tuple[np.float64, np.float64],
        description='The size of the library in the x and y direction.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.TupleEditQuantity,
            defaultDisplayUnit='mm'
            ),
        unit='m',
    )
    geometry = SubSection(
        section_def=Geometry,
        description='The geometries of the samples in the library.',
    )

     #add a section that creates a new DTUCombinatorialLibrary from these information


class DTULibraryCleaving(Process, Schema, PlotSection):
    """
    Schema for substrate cleaning at the DTU Nanolab.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Substrate Cleaving',
    )
    combinatorial_Library = Quantity(
        type=DTUCombinatorialLibrary,
        description='The combinatorial sample that is broken into pieces .',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )
    library_size = Quantity(
        type = tuple[np.float64, np.float64],
        description='The size of the library in the x and y direction.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.TupleEditQuantity,
            defaultDisplayUnit='mm'
            ),
        unit='m',
    )

    pattern= Quantity(
        type = MEnum(
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
        description='The number of pieces the original library is broken into ' \
        'for horizontal, vertical and custom. ' \
        'For squares it is the number of squares in one direction.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )

    create_from_pattern = Quantity(
        type=bool,
        description='Whether to create the new pieces from the pattern.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
        default=False,
    )

    create_child_libraries = Quantity(
        type=bool,
        description='Whether to create child libraries from the new pieces.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
        default=False,
    )

    new_pieces = SubSection(
        section_def= DTULibraryParts,
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
        heig = self.combinatorial_Library.geometry.height
        start_x = (self.library_size[0]/2) *(-1)
        start_y = self.library_size[1]/2

        if self.pattern == 'squares':
            total_nr = self.number_of_pieces ** 2
            size = self.library_size[0] / self.number_of_pieces
            for j in range(self.number_of_pieces):
                for i in range(self.number_of_pieces):
                    piece = DTULibraryParts()
                    number = 1+j * self.number_of_pieces + i
                    piece.library_name = (
                        f'{self.combinatorial_Library.name}_S{number}-{total_nr}'
                    )
                    piece.upper_left_x = start_x + i * size
                    piece.upper_left_y = start_y - (j) * size
                    piece.lower_right_x = start_x + (i + 1) * size
                    piece.lower_right_y = start_y - (j + 1) * size
                    piece.part_size = (size, size)
                    piece.geometry = Geometry(
                        geometry=RectangleCuboid(
                            length=size,
                            width=size,
                            height=heig,
                        )
                    )
                    self.new_pieces.append(piece)
        elif self.pattern == 'horizontal stripes':
            size = self.library_size[1] / self.number_of_pieces

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                number = i + 1
                piece.library_name = (
                    f'{self.combinatorial_Library.name}_H{number}-{self.number_of_pieces}'
                )
                piece.upper_left_x = start_x
                piece.upper_left_y = start_y - i * size
                piece.lower_right_x = start_x + self.library_size[0]
                piece.lower_right_y = start_y - (i + 1) * size
                piece.part_size = (self.library_size[0], size)
                piece.geometry = Geometry(
                    geometry=RectangleCuboid(
                        length=self.library_size[0],
                        width=size,
                        height=heig,
                    )
                )
                self.new_pieces.append(piece)
        elif self.pattern == 'vertical stripes':
            size = self.library_size[0] / self.number_of_pieces

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                number = i + 1
                piece.library_name = (
                    f'{self.combinatorial_Library.name}_V{number}-{self.number_of_pieces}'
                )
                piece.upper_left_x = start_x + i * size
                piece.upper_left_y = start_y
                piece.lower_right_x = start_x + (i + 1) * size
                piece.lower_right_y = start_y - self.library_size[1]
                piece.part_size = (size, self.library_size[1])
                piece.geometry = Geometry(
                    geometry=RectangleCuboid(
                        length=size,
                        width=self.library_size[1],
                        height=heig,
                    )
                )
                self.new_pieces.append(piece)
        elif self.pattern == 'custom':

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                piece.library_name = (
                    f'{self.combinatorial_Library.name}_C{i+1}-{self.number_of_pieces}'
                )
                piece.part_size = None  # Will be set later
                self.new_pieces.append(piece)
        else:
            logger.error(f'Unknown pattern {self.pattern}.')

    def plot(self) -> None:
        """
        Plots the positions of the new pieces in the library.
        """
        import plotly.graph_objects as go
        if self.new_pieces is None or len(self.new_pieces) == 0:
            return
        fig = go.Figure()
        #add the original library to the plot
        if self.combinatorial_Library is not None:
            x0 = self.library_size[0] / 2 * (-1)
            y0 = self.library_size[1] / 2
            x1 = self.library_size[0] / 2
            y1 = -self.library_size[1] / 2
            fig.add_shape(
                type='rect',
                x0=x0,
                y0=y0,
                x1=x1,
                y1=y1,
                line=dict(color='red', width = 3),
                fillcolor='white ',
                opacity=0.5,
            )
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(y0 + y1) / 2,
                text=self.combinatorial_Library.name,
                showarrow=False,
            )

        #add the new pieces
        if self.pattern != 'custom':
            for piece in self.new_pieces:
                if piece.part_size is None:
                    continue

                fig.add_shape(
                    type='rect',
                    x0=piece.upper_left_x+(0.01*piece.part_size[0]),
                    y0=piece.upper_left_y-(0.01*piece.part_size[1]),
                    x1=piece.lower_right_x-(0.01*piece.part_size[0]),
                    y1=piece.lower_right_y+(0.01*piece.part_size[1]),
                    name=piece.library_name,
                    line=dict(color='green'),
                    fillcolor='lightgreen',
                    opacity=0.4,
                )
                fig.add_annotation(
                    x=(piece.upper_left_x + piece.lower_right_x) / 2,
                    y=(piece.upper_left_y + piece.lower_right_y) / 2,
                    text=piece.new_name,
                    showarrow=False,
                )
        fig.update_layout(
            title='Positions of the new pieces in the library',
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            width=800,
            height=700,
            xaxis=dict(
                range=[-self.library_size[0]*1.1/2, self.library_size[0]*1.1/2],
            ),
            yaxis=dict(
                range=[-self.library_size[1]*1.1/2, self.library_size[1]*1.1/2],
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
            pieces = []
            for idx, piece in enumerate(self.new_pieces):
                if piece.part_size is None:
                    continue

        if self.pattern == 'squares':
            total_nr = self.number_of_pieces ** 2
            size = self.library_size[0] / self.number_of_pieces
            for j in range(self.number_of_pieces):
                for 1 in range(self.number_of_pieces):
                    piece = DTULibraryParts()
                    number = 1+j * self.number_of_pieces + i
                    piece.library_name = (
                        f'{self.combinatorial_Library.name}_S{number}-{total_nr}'
                    )
                    piece.upper_left_x = start_x + i * size
                    piece.upper_left_y = start_y - (j) * size
                    piece.lower_right_x = start_x + (i + 1) * size
                    piece.lower_right_y = start_y - (j + 1) * size
                    piece.part_size = (size, size)
                    piece.geometry = Geometry(
                        geometry=RectangleCuboid(
                            length=size,
                            width=size,
                            height=heig,
                        )
                    )
                    self.new_pieces.append(piece)
        elif self.pattern == 'horizontal stripes':
            size = self.library_size[1] / self.number_of_pieces

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                number = i + 1
                piece.library_name = (
                    f'{self.combinatorial_Library.name}_H{number}-{self.number_of_pieces}'
                )
                piece.upper_left_x = start_x
                piece.upper_left_y = start_y - i * size
                piece.lower_right_x = start_x + self.library_size[0]
                piece.lower_right_y = start_y - (i + 1) * size
                piece.part_size = (self.library_size[0], size)
                piece.geometry = Geometry(
                    geometry=RectangleCuboid(
                        length=self.library_size[0],
                        width=size,
                        height=heig,
                    )
                )
                self.new_pieces.append(piece)
        elif self.pattern == 'vertical stripes':
            size = self.library_size[0] / self.number_of_pieces

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                number = i + 1
                piece.library_name = (
                    f'{self.combinatorial_Library.name}_V{number}-{self.number_of_pieces}'
                )
                piece.upper_left_x = start_x + i * size
                piece.upper_left_y = start_y
                piece.lower_right_x = start_x + (i + 1) * size
                piece.lower_right_y = start_y - self.library_size[1]
                piece.part_size = (size, self.library_size[1])
                piece.geometry = Geometry(
                    geometry=RectangleCuboid(
                        length=size,
                        width=self.library_size[1],
                        height=heig,
                    )
                )
                self.new_pieces.append(piece)
        elif self.pattern == 'custom':

            for i in range(self.number_of_pieces):
                piece = DTULibraryParts()
                piece.library_name = (
                    f'{self.combinatorial_Library.name}_C{i+1}-{self.number_of_pieces}'
                )
                piece.part_size = None  # Will be set later
                self.new_pieces.append(piece)
        else:
            logger.error(f'Unknown pattern {self.pattern}.')


        #add the new pieces
        if self.pattern != 'custom':
            for piece in self.new_pieces:
                if piece.part_size is None:
                    continue

                fig.add_shape(
                    type='rect',
                    x0=piece.upper_left_x+(0.01*piece.part_size[0]),
                    y0=piece.upper_left_y-(0.01*piece.part_size[1]),
                    x1=piece.lower_right_x-(0.01*piece.part_size[0]),
                    y1=piece.lower_right_y+(0.01*piece.part_size[1]),
                    name=piece.library_name,
                    line=dict(color='green'),
                    fillcolor='lightgreen',
                    opacity=0.4,
                )
                fig.add_annotation(
                    x=(piece.upper_left_x + piece.lower_right_x) / 2,
                    y=(piece.upper_left_y + piece.lower_right_y) / 2,
                    text=piece.new_name,
                    showarrow=False,
                )
        fig.update_layout(
            title='Positions of the new pieces in the library',
            xaxis_title='X (mm)',
            yaxis_title='Y (mm)',
            width=800,
            height=700,
            xaxis=dict(
                range=[-self.library_size[0]*1.1/2, self.library_size[0]*1.1/2],
            ),
            yaxis=dict(
                range=[-self.library_size[1]*1.1/2, self.library_size[1]*1.1/2],
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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrateCleaning` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.create_from_pattern:
            if self.number_of_pieces is None or self.number_of_pieces <=1:
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
                self.recognize_pattern(logger)
                self.create_from_pattern = False

        if self.new_pieces is not None and len(self.new_pieces) > 0:
            if self.create_child_libraries:
                origin= self.combinatorial_Library
                if origin is None:
                    logger.error(
                        'A combinatorial library must be set to create child libraries.'
                    )
                    return
                else :
                    for piece in self.new_pieces:
                        library = DTUCombinatorialLibrary(
                            name=piece.library_name,
                            datetime=self.datetime,
                            lab_id=piece.library_name,
                            geometry=piece.geometry,
                            description=f'Part of {origin.name} library',
                            process_parameter_overview=origin.process_parameter_overview,
                            elemental_composition=origin.elemental_composition,
                            components=origin.components,
                            layers=origin.layers,
                            substrate=origin.substrate,
                        )

                        library.normalize(archive, logger)
                        file_name = f'{library.lab_id}.archive.json'
                        substrate_archive = create_archive(library, archive, file_name)

                        self.child_libraries.append(
                            CompositeSystemReference(
                            reference=substrate_archive,
                            name=library.name,
                            lab_id=library.lab_id,
                            )
                        )



        return super().normalize(archive, logger)
