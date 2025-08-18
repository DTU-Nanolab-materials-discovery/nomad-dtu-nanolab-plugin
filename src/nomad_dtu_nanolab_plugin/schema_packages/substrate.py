from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
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
from nomad.datamodel.metainfo.workflow import Link
from nomad.metainfo import MEnum, MProxy, Package, Quantity, Section, SubSection
from nomad_material_processing.general import (
    CrystallineSubstrate,
    Cylinder,
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
        default=0.1524,  # 6 inch
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'inch'},
        unit='m',
        description=(
            'Only used if the shape is circular. The diameter of the substrate.'
        ),
    )
    length = Quantity(
        type=np.float64,
        default=0.04,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
        description=(
            'Only used if the shape is rectangular. The length of the substrate.'
        ),
    )
    width = Quantity(
        type=np.float64,
        default=0.04,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
        description=(
            'Only used if the shape is rectangular. The width of the substrate.'
        ),
    )
    thickness = Quantity(
        type=np.float64,
        default=0.000675,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mm'},
        unit='m',
    )
    create_substrates = Quantity(
        type=bool,
        description='(Re)create the substrate entities.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.ActionEditQuantity),
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
            geometry.radius = self.diameter / 2
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
                        volume=size * size * height,
                        surface_area=(size * size),
                    )

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
                    volume=self.library_x_length * size * height,
                    surface_area=(self.library_x_length * size),
                )

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
                    volume=size * self.library_y_length * height,
                    surface_area=(size * self.library_y_length),
                )

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
            archive.workflow2.inputs.extend(
                Link(
                    name=f'Substrate: {self.combinatorial_library.name}',
                    section=self.combinatorial_library,
                )
            )
        if self.child_libraries is not None and len(self.child_libraries) > 0:
            archive.workflow2.outputs.extend(
                [
                    Link(name=f'New libraries of {lib.name}', section=lib)
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
        super().normalize(archive, logger)
        self.end_time = self.datetime
        self.method = 'Sample splitting'
        if not self.location:
            self.location = 'DTU Nanolab'

        if self.fetch_library_size and self.combinatorial_library is not None:
            self.fetch_library_size = False
            self.fill_library_size(logger)

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

        # archive.workflow2 = None
        # super().normalize(archive, logger)
        # self.handle_workflow(archive, logger)


m_package.__init_metainfo__()
