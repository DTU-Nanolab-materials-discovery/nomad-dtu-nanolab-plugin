import tempfile
import time
import warnings
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.datamodel.results import Material, Results
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_material_processing.general import (
    ThinFilm,
    ThinFilmReference,
)
from nomad_material_processing.vapor_deposition.cvd.general import (
    ChemicalVaporDeposition,
    CVDSource,
    CVDStep,
)
from nomad_measurements.utils import create_archive

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.rtp_log_reader import parse_rtp_logfiles
from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
    DtuLibraryReference,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_dtu_nanolab_plugin.schema_packages import RTPEntryPoint

from nomad.config import config

configuration: 'RTPEntryPoint' = config.get_plugin_entry_point(
    'nomad_dtu_nanolab_plugin.schema_packages:rtp'
)

m_package = Package(name='DTU RTP schema')

# volume fraction in the respective gas mixture (the complementary gas is Ar)
RTP_GAS_FRACTION = {
    'Ar': 1,
    'N2': 1,
    'PH3': 0.1,
    'H2S': 0.1,
}


#################### DEFINE INPUT_SAMPLES (SUBSECTION) ######################
class DtuRTPInputSampleMounting(ArchiveSection):
    """
    Section containing information about the mounting of the combinatiorial libraries
    (input samples) on the susceptor.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'input_combi_lib',
                    'relative_position',
                    'position_x',
                    'position_y',
                    'rotation',
                ],
            )
        ),
    )
    name = Quantity(
        type=str,
        description='The name of the input sample mounting.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    input_combi_lib = Quantity(
        type=DTUCombinatorialLibrary,
        description='The input sample (combinatorial library) that is used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )

    relative_position = Quantity(
        type=str,
        description='The relative position of the input sample on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(
                suggestions=[
                    'bl',
                    'br',
                    'fl',
                    'fr',
                    'm',
                    'ha',
                    'hb',
                    'hc',
                    'hd',
                    'va',
                    'vb',
                    'vc',
                    'vd',
                ]
            ),
        ),
    )
    position_x = Quantity(
        type=np.float64,
        description='The x-coordinate of the input sample on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    position_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the input sample on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    rotation = Quantity(
        type=np.float64,
        description="""
            The angle between the initial position in the "mother" sample
            and the position on the susceptor.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuRTPInputSampleMounting` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.position_x is None or self.position_y is None:
            positions = {
                'bl': (-0.0125, 0.0125),
                'br': (0.0125, 0.0125),
                'fl': (-0.0125, -0.0125),
                'fr': (0.0125, -0.0125),
                'm': (0, 0),
                'ha': (0, 0.015),
                'hb': (0, 0.005),
                'hc': (0, -0.005),
                'hd': (0, -0.015),
                'va': (-0.015, 0),
                'vb': (-0.005, 0),
                'vc': (0.005, 0),
                'vd': (0.015, 0),
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


#################### HUMAN READABLE OVERVIEW (SUBSECTION) ######################
class RTPOverview(ArchiveSection):
    """
    Section containing a human readable overview of the RTP process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'material_space',
                    'annealing_temperature',
                    'total_heating_time',
                    'annealing_time',
                    'total_cooling_time',
                    'annealing_pressure',
                    'annealing_ar_flow',
                    'annealing_n2_flow',
                    'annealing_ph3_in_ar_flow',
                    'annealing_h2s_in_ar_flow',
                    'end_of_process_temperature',
                    'annealing_h2s_partial_pressure',
                    'annealing_ph3_partial_pressure',
                    'annealing_n2_partial_pressure',
                    'annealing_ar_partial_pressure',
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
        description='The material space explored by the RTP process.',
    )
    annealing_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='torr',
            label='Annealing Pressure',
        ),
        unit='Pa',
        description='Pressure in the RTP chamber during the annealing plateau',
    )
    annealing_time = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Annealing Time',
        ),
        unit='s',
        description='Time spent at the annealing plateau of the RTP process.',
    )
    annealing_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='Annealing Temperature',
        ),
        unit='K',
        description=(
            'Temperature (average) during the annealing plateau of the RTP process.'
        ),
    )
    annealing_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Ar Flow',
        ),
        unit='m**3/s',
        description='Argon flow used during the annealing plateau of the RTP process.'
        'The unit "cm^3/minute" is used equal to sccm.',
    )
    annealing_n2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='N2 Flow',
        ),
        unit='m**3/s',
        description='Nitrogen flow used during the annealing plateau of the'
        ' RTP process. The unit "cm^3/minute" is used equal to sccm.',
    )
    annealing_ph3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='PH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Phosphine flow used during the annealing plateau of'
        ' the RTP process. The unit "cm^3/minute" is used equal to sccm.',
    )
    annealing_h2s_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='H2S in Ar Flow',
        ),
        unit='m**3/s',
        description='H2S flow used during the annealing plateau of the RTP process.'
        'The unit "cm^3/minute" is used equal to sccm.',
    )
    total_heating_time = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Total heating up time',
        ),
        unit='s',
        description='Total time spent until maximum (main annealing plateau)'
        'temperature is reached.',
    )
    total_cooling_time = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Total cooling down time',
        ),
        unit='s',
        description='Total time spent between the end of the main annealing plateau '
        'until the samples are cooled down to room temperature.',
    )
    end_of_process_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='End of process temperature',
        ),
        unit='K',
        description='Temperature at the cooling state of the RTP process, when the'
        ' gases are shut off and final pump-purge procedure is initiated to '
        'remove samples from chamber.',
    )
    annealing_ph3_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='PH3 Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of PH3 during the annealing plateau of the'
        ' RTP process.',
    )
    annealing_h2s_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='H2S Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of H2S during the annealing plateau of the'
        ' RTP process.',
    )
    annealing_n2_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='N2 Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of N2 during the annealing plateau of the'
        ' RTP process.',
    )
    annealing_ar_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Ar Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of Ar during the annealing plateau of the'
        ' RTP process.',
    )

    def calc_partial_pressure(self):
        annealing_ar_flow = (
            self.annealing_ar_flow.magnitude
            if self.annealing_ar_flow is not None
            else 0
        )
        annealing_n2_flow = (
            self.annealing_n2_flow.magnitude
            if self.annealing_n2_flow is not None
            else 0
        )
        annealing_h2s_in_ar_flow = (
            self.annealing_h2s_in_ar_flow.magnitude
            if self.annealing_h2s_in_ar_flow is not None
            else 0
        )
        annealing_ph3_in_ar_flow = (
            self.annealing_ph3_in_ar_flow.magnitude
            if self.annealing_ph3_in_ar_flow is not None
            else 0
        )
        total_flow = (
            annealing_ar_flow
            + annealing_h2s_in_ar_flow
            + annealing_n2_flow
            + annealing_ph3_in_ar_flow
        )

        total_pressure = self.annealing_pressure.magnitude

        annealing_h2s_partial_pressure = ureg.Quantity(
            annealing_h2s_in_ar_flow
            * RTP_GAS_FRACTION['H2S']
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_h2s_partial_pressure = annealing_h2s_partial_pressure

        annealing_ph3_partial_pressure = ureg.Quantity(
            annealing_ph3_in_ar_flow
            * RTP_GAS_FRACTION['PH3']
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_ph3_partial_pressure = annealing_ph3_partial_pressure

        annealing_n2_partial_pressure = ureg.Quantity(
            annealing_n2_flow * RTP_GAS_FRACTION['N2'] / total_flow * total_pressure,
            'Pa',
        )
        self.annealing_n2_partial_pressure = annealing_n2_partial_pressure

        annealing_ar_partial_pressure = ureg.Quantity(
            (
                annealing_h2s_in_ar_flow * (1 - RTP_GAS_FRACTION['H2S'])
                + annealing_ph3_in_ar_flow * (1 - RTP_GAS_FRACTION['PH3'])
                + annealing_ar_flow * RTP_GAS_FRACTION['Ar']
            )
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_ar_partial_pressure = annealing_ar_partial_pressure

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTPOverview` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)
        flows = [
            self.annealing_ar_flow,
            self.annealing_n2_flow,
            self.annealing_ph3_in_ar_flow,
            self.annealing_h2s_in_ar_flow,
        ]
        if any(
            flow is not None and getattr(flow, 'magnitude', flow) != 0 for flow in flows
        ):
            self.calc_partial_pressure()


##################### STEPS (SUBSECTION) ######################################
class RTPStepOverview(ArchiveSection):
    """
    Section containing a human readable overview of a certain step of the RTP process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'duration',
                    'initial_temperature',
                    'final_temperature',
                    'pressure',
                    'step_ar_flow',
                    'step_n2_flow',
                    'step_ph3_in_ar_flow',
                    'step_h2s_in_ar_flow',
                    'temperature_ramp',
                    'step_ar_partial_pressure',
                    'step_n2_partial_pressure',
                    'step_ph3_partial_pressure',
                    'step_h2s_partial_pressure',
                ],
            )
        ),
    )
    duration = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Duration',
        ),
        unit='s',
        description='Duration of the step.',
    )
    pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='torr',
            label='Pressure',
        ),
        unit='Pa',
        description='Pressure in the RTP chamber during the step.',
    )
    step_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Ar Flow',
        ),
        unit='m**3/s',
        description='Argon flow rate used during the step.'
        'The unit "cm^3/minute" is used equal to sccm.',
    )
    step_n2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='N2 Flow',
        ),
        unit='m**3/s',
        description='Nitrogen flow rate used during the step. '
        'The unit "cm^3/minute" is used equal to sccm.',
    )
    step_ph3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='PH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Phosphine flow rate used during the step.'
        'The unit "cm^3/minute" is used equal to sccm.',
    )
    step_h2s_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='H2S in ArFlow',
        ),
        unit='m**3/s',
        description='H2S flow rate used during the step.'
        'The unit "cm^3/minute" is used equal to sccm.',
    )
    initial_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='Initial Temperature',
        ),
        unit='K',
        description='Temperature at the beginning of the step.',
    )
    final_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='Final Temperature',
        ),
        unit='K',
        description='Temperature at the end of the step.',
    )
    temperature_ramp = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='celsius/minute',
            label='Temperature ramp rate. ',
        ),
        unit='K/s',
        description='Rate of temperature increase or decrease during the step',
    )
    step_ph3_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='PH3 Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of PH3 during the annealing plateau of the'
        ' RTP process.',
    )
    step_h2s_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='H2S Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of H2S during the annealing plateau of the'
        ' RTP process.',
    )
    step_n2_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='N2 Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of N2 during the annealing plateau of the'
        ' RTP process.',
    )
    step_ar_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Ar Partial Pressure',
        ),
        unit='Pa',
        description='Partial pressure of Ar during the annealing plateau of the'
        ' RTP process.',
    )

    def calc_ramp(self):
        """
        Calculate the temperature ramp rate based on the initial and final temperatures
        and the duration of the step.
        """
        if (
            self.initial_temperature is None
            or self.final_temperature is None
            or self.duration is None
        ):
            warnings.warn(
                'Cannot calculate temperature ramp: initial_temperature,'
                ' final_temperature, or duration is missing.',
                UserWarning,
            )
            return

        initial_temperature = self.initial_temperature.magnitude
        final_temperature = self.final_temperature.magnitude
        duration = self.duration.magnitude

        temperature_ramp = ureg.Quantity(
            ((final_temperature - initial_temperature) / duration),
            'K/s',
        )
        self.temperature_ramp = temperature_ramp

    def calc_partial_pressure(self):
        step_ar_flow = (
            self.step_ar_flow.magnitude if self.step_ar_flow is not None else 0
        )
        step_n2_flow = (
            self.step_n2_flow.magnitude if self.step_n2_flow is not None else 0
        )
        step_h2s_in_ar_flow = (
            self.step_h2s_in_ar_flow.magnitude
            if self.step_h2s_in_ar_flow is not None
            else 0
        )
        step_ph3_in_ar_flow = (
            self.step_ph3_in_ar_flow.magnitude
            if self.step_ph3_in_ar_flow is not None
            else 0
        )
        total_flow = (
            step_ar_flow + step_h2s_in_ar_flow + step_n2_flow + step_ph3_in_ar_flow
        )

        total_pressure = self.pressure.magnitude

        step_h2s_partial_pressure = ureg.Quantity(
            step_h2s_in_ar_flow * RTP_GAS_FRACTION['H2S'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_h2s_partial_pressure = step_h2s_partial_pressure

        step_ph3_partial_pressure = ureg.Quantity(
            step_ph3_in_ar_flow * RTP_GAS_FRACTION['PH3'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_ph3_partial_pressure = step_ph3_partial_pressure

        step_n2_partial_pressure = ureg.Quantity(
            step_n2_flow * RTP_GAS_FRACTION['N2'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_n2_partial_pressure = step_n2_partial_pressure

        step_ar_partial_pressure = ureg.Quantity(
            (
                step_h2s_in_ar_flow * (1 - RTP_GAS_FRACTION['H2S'])
                + step_ph3_in_ar_flow * (1 - RTP_GAS_FRACTION['PH3'])
                + step_ar_flow * RTP_GAS_FRACTION['Ar']
            )
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.step_ar_partial_pressure = step_ar_partial_pressure

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSteps` class.

        Args:
        archive (EntryArchive): The archive containing the section that is being
        normalized.
        logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        flows = [
            self.step_ar_flow,
            self.step_n2_flow,
            self.step_ph3_in_ar_flow,
            self.step_h2s_in_ar_flow,
        ]
        if any(
            flow is not None and getattr(flow, 'magnitude', flow) != 0 for flow in flows
        ):
            self.calc_partial_pressure()

        if (
            self.initial_temperature is not None
            and self.final_temperature is not None
            and self.initial_temperature != self.final_temperature
        ):
            self.calc_ramp()


class DtuRTPSources(CVDSource, ArchiveSection):
    """
    Information regarding the sources (gases) used in the RTP process.
    """

    sources = Quantity(
        type=str,
        shape=['*'],
        description='Automatically generated list of sources (gases) for this step',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class DTURTPSteps(CVDStep, ArchiveSection):
    """
    Class representing each step in the RTP process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'creates_new_thin_film',
                    'step_overview',
                    'sources',
                    'comment',
                ],
                visible=Filter(
                    exclude=[
                        'start_time',
                        'duration',
                        'step_index',
                        'environment',
                        'sample_parameters',
                    ]
                ),
            )
        ),
    )
    step_overview = SubSection(
        section_def=RTPStepOverview,
    )
    sources = SubSection(
        section_def=DtuRTPSources,
        repeats=True,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTURTPSteps` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        # Ensure derived step_overview values (temperature ramp and partial
        # pressures) are always computed during step normalization.
        if self.step_overview is not None:
            self.step_overview.normalize(archive, logger)

        # Clear existing sources
        self.sources = []
        # Get used_gases from DtuRTP main class
        parent = getattr(self, 'm_parent', None)
        if parent is not None and hasattr(parent, 'used_gases'):
            for gas in parent.used_gases or []:
                source = DtuRTPSources()
                source.sources = [gas]
                source.name = gas
                self.sources.append(source)


###################### 1ST LEVEL CLASS (RTP) #################################
class DtuRTP(ChemicalVaporDeposition, PlotSection, Schema):
    """
    A synthesis method where a rapidly heated substrate is exposed to one or more
    volatile precursors, which react or decompose on the surface to produce a deposit.
    [database_cross_reference: https://orcid.org/0000-0002-0640-0422]

    Synonyms:
    - rapid thermal chemical vapor deposition
    - rapid thermal CVD
    - RTCVD
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='RTP',
        links=['http://purl.obolibrary.org/obo/CHMO_0001328'],
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'datetime',
                    'lab_id',
                    'location',
                    'log_file_eklipse',
                    'log_file_T2BDiagnostics',
                    'process_log_files',
                    'overwrite_existing_data',
                    'samples_susceptor_before',
                    'samples_susceptor_after',
                    'base_pressure',
                    'base_pressure_ballast',
                    'rate_of_rise',
                    'chiller_flow',
                    'used_gases',
                    'overview',
                    'steps',
                    'input_samples',
                    'samples',
                    'figures',
                ],
                visible=Filter(exclude=['end_time', 'instruments', 'method']),
            )
        ),
    )
    lab_id = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Run ID',
        ),
        description='The ID of the run. Format: user_number_RTP.',
    )
    location = Quantity(
        type=str,
        default='DTU; IDOL Lab',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    log_file_eklipse = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity, label='Gas/Pressure log file'
        ),
        description='Cell to upload the gas/pressurelog file obtained with Eklipse.',
    )
    log_file_T2BDiagnostics = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity, label='Temperature log file'
        ),
        description=(
            'Cell to upload the temperature log file obtained with T2BDiagnostics.'
        ),
    )
    process_log_files = Quantity(
        type=bool,
        default=True,
        description='Boolean to indicate if the RTP log files should be processed.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Process log files',
        ),
    )
    overwrite_existing_data = Quantity(
        type=bool,
        default=True,
        description=(
            'Boolean to indicate if the data present in the entry should be '
            'overwritten by data incoming from the log files.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Overwrite existing data ?',
        ),
    )
    samples_susceptor_before = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of the samples on susceptor before RTP process',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the image of the samples on susceptor before the'
        'RTP process.',
    )
    samples_susceptor_after = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of the samples on susceptor after RTP process',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the image of the samples on susceptor after the'
        'RTP process.',
    )
    used_gases = Quantity(
        type=str,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Used gases',
        ),
        description='Gases used in the process.',
    )
    #################### GENERAL CHECKS ######################
    base_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Base Pressure without ballast',
            defaultDisplayUnit='mtorr',
        ),
        unit='Pa',
        description='Base pressure when ballast is OFF',
    )
    base_pressure_ballast = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Base Pressure with ballast',
            defaultDisplayUnit='mtorr',
        ),
        unit='Pa',
        description='Base pressure when ballast is ON.',
    )
    rate_of_rise = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mtorr/minute',
            label='Rate of Rise',
        ),
        unit='Pa/s',
        description='Rate of rise of the pressure in the RTP chamber during static '
        'vacuum',
    )
    chiller_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='l/minute',
            label='Chiller Flow',
        ),
        unit='m**3/s',
        description='Chiller flow rate during the RTP process.',
    )
    ############################## SUBSECTIONS ########################################
    input_samples = SubSection(
        section_def=DtuRTPInputSampleMounting,
        repeats=True,
    )
    overview = SubSection(
        section_def=RTPOverview,
    )
    steps = SubSection(
        section_def=DTURTPSteps,
        repeats=True,
    )

    ############################## CREATING RTP SAMPLE LIBRARY ######################
    def _sync_step_sources_from_used_gases(self) -> None:
        gases = [gas for gas in (self.used_gases or []) if gas]
        for step in getattr(self, 'steps', []) or []:
            step.sources = []
            for gas in gases:
                source = DtuRTPSources()
                source.sources = [gas]
                source.name = gas
                step.sources.append(source)

    def _get_input_sample_material_elements(self) -> list[str]:
        ordered_elements: list[str] = []

        def _append_symbol(raw_symbol) -> None:
            if raw_symbol is None:
                return
            symbol = str(raw_symbol).strip()
            if symbol and symbol not in ordered_elements:
                ordered_elements.append(symbol)

        for rtp_sample in getattr(self, 'input_samples', []) or []:
            origin = getattr(rtp_sample, 'input_combi_lib', None)
            if origin is None:
                continue

            layer_ref = (
                origin.layers[0].reference if getattr(origin, 'layers', None) else None
            )
            layer_comp = getattr(layer_ref, 'elemental_composition', None)
            if layer_comp is None:
                layer_comp = getattr(origin, 'elemental_composition', None)

            if not layer_comp:
                continue

            for elem in layer_comp:
                _append_symbol(getattr(elem, 'element', elem))

        return ordered_elements

    def _autofill_material_space(self) -> None:
        """Always recompute material_space from input-sample composition + gas elements.

        - No input samples with composition → material_space is cleared to None.
        - Input samples present → their elements first, then any new gas-derived
          elements (PH3→P, H2S→S) appended if not already included.
        """
        if self.overview is None:
            self.overview = RTPOverview()

        ordered_elements = self._get_input_sample_material_elements()
        if not ordered_elements:
            self.overview.material_space = None
            return

        gas_to_element = {'PH3': 'P', 'H2S': 'S'}
        for gas, symbol in gas_to_element.items():
            if gas in (self.used_gases or []):
                if symbol not in ordered_elements:
                    ordered_elements.append(symbol)

        self.overview.material_space = '-'.join(ordered_elements)

    def add_libraries(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        samples = []
        rtp_name = self.name
        rtp_datetime = self.datetime
        rtp_materialspace = self.overview.material_space
        if not rtp_materialspace:
            return
        for rtp_sample in self.input_samples:
            # Get the the input sample and original sample
            origin = rtp_sample.input_combi_lib
            origin_layer = origin.layers[0].reference if origin.layers else None

            # Get elemental compositions
            origin_elements = set(e.element for e in origin.elemental_composition)
            rtp_elements = set(rtp_materialspace.split('-'))

            # Merge for library
            if rtp_elements == origin_elements:
                elemental_composition = origin.elemental_composition
            else:
                # Merge and remove duplicates, keep order from origin first
                merged_elements = list(origin_elements) + [
                    e for e in rtp_elements if e not in origin_elements
                ]
                elemental_composition = [
                    type(origin.elemental_composition[0])(element=e)
                    for e in merged_elements
                ]

            # Merge for the layer
            if (
                origin_layer is not None
                and origin_layer.elemental_composition is not None
            ):
                layer_origin_elements = set(
                    e.element for e in origin_layer.elemental_composition
                )
                # Merge origin_layer and library compositions
                merged_layer_elements = list(layer_origin_elements) + [
                    e for e in rtp_elements if e not in layer_origin_elements
                ]
                layer_elemental_composition = [
                    type(origin_layer.elemental_composition[0])(element=e)
                    for e in merged_layer_elements
                ]
            else:
                warnings.warn(
                    (
                        f'Could not determine elemental composition for the '
                        f"new layer of sample '{rtp_sample.name}'. "
                        'No origin layer or missing elemental composition in origin'
                        ' layer.'
                    ),
                    UserWarning,
                )

            # Create new layer and library only if an input sample has been specified
            # and overview is filled (to get material space -> elemental composition)
            if rtp_sample.name is not None:
                # Create a new ThinFilm layer for this sample
                layer = ThinFilm(
                    elemental_composition=layer_elemental_composition,
                    lab_id=f'{rtp_name} {rtp_sample.name}-Layer'.replace(' ', '_'),
                )
                layer_ref = create_archive(
                    layer,
                    archive,
                    f'{layer.lab_id}.archive.json',
                    overwrite=configuration.overwrite_layers,
                )
                # Create new library
                library = DTUCombinatorialLibrary(
                    name=f'{rtp_name} {rtp_sample.name}',
                    datetime=rtp_datetime,
                    lab_id=f'{rtp_name} {rtp_sample.name}'.replace(' ', '_'),
                    description=f'RTP library for {rtp_name} {rtp_sample.name}',
                    elemental_composition=elemental_composition,
                    layers=[
                        ThinFilmReference(
                            name='Main Layer',
                            reference=layer_ref,
                            lab_id=layer.lab_id,
                        )
                    ],
                    geometry=origin.geometry,
                    substrate=origin.substrate,
                    process_parameter_overview=origin.process_parameter_overview,
                    parent_library=DtuLibraryReference(
                        reference=origin.m_proxy_value,
                        name=origin.name,
                        lab_id=origin.lab_id,
                    ),
                )
                samples.append(library)
        if configuration.overwrite_libraries:
            time.sleep(5)  # to ensure that layers are processed before samples
        self.samples = [
            CompositeSystemReference(
                name=f'Sample {library.name}',
                reference=create_archive(
                    library,
                    archive,
                    f'{library.lab_id}.archive.json',
                    overwrite=configuration.overwrite_libraries,
                ),
                lab_id=library.lab_id,
            )
            for library in samples
        ]
        if not samples:
            warnings.warn(
                'No RTP sample libraries were created. '
                'Check that input_samples have valid input_combi_lib and name and'
                'that overview.material_space is filled.',
                UserWarning,
            )

    ############################## PLOTS #################################
    def _get_full_plot_time_range(self) -> tuple[float, float] | None:
        series = getattr(self, '_log_time_s', []) or getattr(self, '_time', []) or []
        if not series:
            return None
        return (float(series[0]), float(series[-1]))

    def _build_phase_segments(self) -> list[tuple[str, float, float]]:
        segments: list[tuple[str, float, float]] = []
        cursor = 0.0
        for step in getattr(self, 'steps', []) or []:
            step_overview = getattr(step, 'step_overview', None)
            if step_overview is None or step_overview.duration is None:
                continue
            duration = step_overview.duration
            duration_s = (
                float(duration.to('s').magnitude)
                if hasattr(duration, 'to')
                else float(getattr(duration, 'magnitude', duration))
            )
            if duration_s <= 0:
                continue
            name = (step.name or '').strip() or 'Step'
            segments.append((name, cursor, cursor + duration_s))
            cursor += duration_s
        return segments

    def _add_phase_delimiters(self, fig: go.Figure) -> None:
        segments = getattr(self, '_phase_segments', []) or []
        if not segments:
            return

        band_colors = ['rgba(120, 120, 120, 0.08)', 'rgba(120, 120, 120, 0.14)']
        for idx, (name, start, end) in enumerate(segments):
            fig.add_vrect(
                x0=start,
                x1=end,
                fillcolor=band_colors[idx % len(band_colors)],
                opacity=1.0,
                layer='below',
                line_width=0,
            )
            center = (start + end) / 2
            fig.add_annotation(
                x=center,
                y=1.02,
                xref='x',
                yref='paper',
                text=name,
                showarrow=False,
                font=dict(size=10, color='gray'),
                xanchor='center',
            )

    # Set up temperature profile plot
    def plot_temperature_profile(self) -> None:
        time_s = getattr(self, '_time', []) or []
        temperature_c = getattr(self, '_temperature_profile', []) or []
        setpoint_c = getattr(self, '_temperature_setpoint_profile', []) or []
        lamp_power = getattr(self, '_lamp_power_profile', []) or []

        if not time_s or not temperature_c:
            return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=time_s,
                y=temperature_c,
                mode='lines',
                name='Actual Temperature',
            )
        )
        if setpoint_c and len(setpoint_c) == len(time_s):
            fig.add_trace(
                go.Scatter(
                    x=time_s,
                    y=setpoint_c,
                    mode='lines',
                    name='Temperature Setpoint',
                    line=dict(dash='dash'),
                )
            )
        if lamp_power and len(lamp_power) == len(time_s):
            fig.add_trace(
                go.Scatter(
                    x=time_s,
                    y=lamp_power,
                    mode='lines',
                    name='Lamp Power',
                    yaxis='y2',
                )
            )
        self._add_phase_delimiters(fig)

        x_range = self._get_full_plot_time_range()
        fig.update_layout(
            title='RTP Temperature and Lamp Power',
            xaxis_title='Time / s',
            yaxis_title='Temperature / °C',
            yaxis2=dict(
                title='Lamp Power',
                overlaying='y',
                side='right',
                showgrid=False,
            ),
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
                showline=True,
                showgrid=True,
                zeroline=True,
                range=list(x_range) if x_range is not None else None,
            ),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        self.figures.append(
            PlotlyFigure(
                label='Temperature Profile',
                figure=plot_json,
            )
        )

    def plot_gas_flows_profile(self) -> None:
        time_s = getattr(self, '_log_time_s', []) or []
        if not time_s:
            return

        flow_series = {
            'Ar Flow': getattr(self, '_log_ar_flow_sccm', []),
            'N2 Flow': getattr(self, '_log_n2_flow_sccm', []),
            'PH3 in Ar Flow': getattr(self, '_log_ph3_flow_sccm', []),
            'H2S in Ar Flow': getattr(self, '_log_h2s_flow_sccm', []),
        }

        fig = go.Figure()
        plotted = False
        for name, values in flow_series.items():
            if values and len(values) == len(time_s):
                plotted = True
                fig.add_trace(
                    go.Scatter(
                        x=time_s,
                        y=values,
                        mode='lines',
                        name=name,
                    )
                )

        if not plotted:
            return

        self._add_phase_delimiters(fig)
        x_range = self._get_full_plot_time_range()

        fig.update_layout(
            title='RTP Gas Flows Evolution',
            xaxis_title='Time / s',
            yaxis_title='Flow / sccm',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(range=list(x_range) if x_range is not None else None),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Gas Flows Evolution',
                figure=plot_json,
            )
        )

    def plot_pressure_profile(self) -> None:
        time_s = getattr(self, '_log_time_s', []) or []
        pressure_torr = getattr(self, '_log_pressure_torr', []) or []
        if not time_s or not pressure_torr or len(pressure_torr) != len(time_s):
            return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=time_s,
                y=pressure_torr,
                mode='lines',
                name='Chamber Pressure',
            )
        )
        self._add_phase_delimiters(fig)
        x_range = self._get_full_plot_time_range()
        fig.update_layout(
            title='RTP Pressure Evolution',
            xaxis_title='Time / s',
            yaxis_title='Pressure / torr',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(range=list(x_range) if x_range is not None else None),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Pressure Evolution',
                figure=plot_json,
            )
        )

    # Helper function to plot a sample on the susceptor. It is called in the next.
    def plot_sample_on_susceptor(self, fig, input_sample):
        geometry = getattr(input_sample.input_combi_lib, 'geometry', None)
        rel_pos = getattr(input_sample, 'relative_position', None)
        x = getattr(input_sample, 'position_x', None)
        y = getattr(input_sample, 'position_y', None)
        rotation = getattr(input_sample, 'rotation', None)
        if rel_pos is None and x is None and y is None:
            warnings.warn(
                f"Input sample '{getattr(input_sample, 'name', 'Unnamed')}'"
                ' has no relative position, x, or y set.'
                ' It will be placed at the center by default.',
                UserWarning,
            )
        if geometry is not None:
            width = getattr(geometry, 'width', 10)
            length = getattr(geometry, 'length', 10)
            if hasattr(width, 'magnitude'):
                width = width.to('mm').magnitude
            if hasattr(length, 'magnitude'):
                length = length.to('mm').magnitude
        else:
            square_positions = {'bl', 'br', 'fl', 'fr', 'm'}
            rectangle_horizontal = {'ha', 'hb', 'hc', 'hd'}
            rectangle_vertical = {'va', 'vb', 'vc', 'vd'}
            if rel_pos in square_positions:
                width, length = 20, 20
            elif rel_pos in rectangle_horizontal:
                width, length = 40, 9.5
            elif rel_pos in rectangle_vertical:
                width, length = 9.5, 40
            else:
                width, length = 10, 10
        if x is None or y is None:
            x = 0
            y = 0
        if hasattr(x, 'magnitude'):
            x = x.to('mm').magnitude
        if hasattr(y, 'magnitude'):
            y = y.to('mm').magnitude
        if rotation is None:
            angle_rad = 0.0
        elif hasattr(rotation, 'to'):
            angle_rad = float(rotation.to('rad').magnitude)
        else:
            angle_rad = float(rotation)

        half_w, half_l = width / 2, length / 2
        local_corners = [
            (-half_w, -half_l),
            (half_w, -half_l),
            (half_w, half_l),
            (-half_w, half_l),
        ]
        cos_a = float(np.cos(angle_rad))
        sin_a = float(np.sin(angle_rad))
        rotated_corners = [
            (
                x + (cx * cos_a - cy * sin_a),
                y + (cx * sin_a + cy * cos_a),
            )
            for cx, cy in local_corners
        ]
        path = 'M ' + ' L '.join(f'{px},{py}' for px, py in rotated_corners) + ' Z'
        fig.add_shape(
            type='path',
            path=path,
            line=dict(color='blue', width=2),
            fillcolor='rgba(100,100,255,0.3)',
        )
        label = rel_pos if rel_pos else input_sample.name
        fig.add_annotation(
            x=x,
            y=y,
            text=label,
            showarrow=False,
            font=dict(color='black', size=12),
            bgcolor='white',
        )

    # Set up the sample-on-susceptor graphical visualization
    def plot_susceptor(self) -> None:
        fig = go.Figure()

        # Draw susceptor outline (square 50x50 mm centered at 0,0)
        susceptor_size = 50  # mm
        half_susceptor = susceptor_size / 2
        fig.add_shape(
            type='rect',
            x0=-half_susceptor,
            y0=-half_susceptor,
            x1=half_susceptor,
            y1=half_susceptor,
            line=dict(color='black', width=3),
            fillcolor='rgba(200,200,200,0.1)',
            layer='below',
        )
        # Add 'chamber' label to the left side
        fig.add_annotation(
            x=-half_susceptor - 2,  # 2 mm left of the susceptor edge
            y=0,
            text='RTP chamber',
            showarrow=False,
            font=dict(color='black', size=16),
            xanchor='right',
            yanchor='middle',
            textangle=-90,  # Rotate text to be vertical
        )
        # Add 'user' label to the bottom side
        fig.add_annotation(
            x=0,
            y=-half_susceptor - 2,  # 2 mm below the susceptor edge
            text='User',
            showarrow=False,
            font=dict(color='black', size=16),
            xanchor='center',
            yanchor='top',
        )
        # Loop through input_samples and plot them, using the helper function.
        for input_sample in getattr(self, 'input_samples', []):
            self.plot_sample_on_susceptor(fig, input_sample)
        fig.update_layout(
            title='Samples on Susceptor',
            xaxis=dict(
                range=[-half_susceptor - 15, half_susceptor + 15],
                scaleanchor='y',
                scaleratio=1,
                showgrid=False,
                zeroline=False,
                visible=False,
            ),
            yaxis=dict(
                range=[-half_susceptor - 5, half_susceptor + 5],
                showgrid=False,
                zeroline=False,
                visible=False,
            ),
            width=500,
            height=500,
            plot_bgcolor='white',
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Samples-on-Susceptor Map',
                figure=plot_json,
            )
        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTP` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if (
            self.log_file_eklipse
            and self.log_file_T2BDiagnostics
            and self.process_log_files
        ):
            self.parse_log_files(
                archive,
                logger,
                overwrite=bool(self.overwrite_existing_data),
            )
        super().normalize(archive, logger)
        # Ensure nested step normalizers are executed so derived step_overview
        # quantities (ramps and partial pressures) are populated reliably.
        for step in getattr(self, 'steps', []) or []:
            step.normalize(archive, logger)

        # Populate lab_id according to generated name
        if self.lab_id is None:
            self.lab_id = self.name.replace(' ', '_')
        self._phase_segments = self._build_phase_segments()
        log_time_s = getattr(self, '_log_time_s', []) or []
        log_temp_c = getattr(self, '_log_temperature_c', []) or []
        if log_time_s and log_temp_c and len(log_time_s) == len(log_temp_c):
            self._time = log_time_s
            self._temperature_profile = log_temp_c
        else:
            times, temps, current_time = [], [], 0
            step: DTURTPSteps
            for step in getattr(self, 'steps', []):  # Loop over all DTURTPSteps
                step_overview = getattr(step, 'step_overview', None)
                if (
                    step_overview is not None
                    and isinstance(step_overview.initial_temperature, ureg.Quantity)
                    and isinstance(step_overview.final_temperature, ureg.Quantity)
                    and isinstance(step_overview.duration, ureg.Quantity)
                ):
                    # Add initial point for the step
                    temps.append(
                        step_overview.initial_temperature.to('celsius').magnitude
                    )
                    times.append(current_time)
                    # Add final point for the step
                    current_time += step_overview.duration or 0
                    temps.append(
                        step_overview.final_temperature.to('celsius').magnitude
                    )
                    times.append(current_time)
            self._time = times
            self._temperature_profile = temps
        self.figures = []
        self._sync_step_sources_from_used_gases()
        self._autofill_material_space()
        if self.overview is not None:
            self.add_libraries(archive, logger)
        self.plot_temperature_profile()
        self.plot_gas_flows_profile()
        self.plot_pressure_profile()
        self.plot_susceptor()

        # Populate results with material elements for periodic table filtering
        if self.overview is not None and self.overview.material_space:
            if archive.results is None:
                archive.results = Results()
            if archive.results.material is None:
                archive.results.material = Material()
            elements = self.overview.material_space.split('-')
            archive.results.material.elements = elements

    def parse_log_files(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        overwrite: bool = False,
    ) -> None:
        """Parse RTP gas and diagnostics log files and populate RTP quantities."""
        if not self.log_file_eklipse or not self.log_file_T2BDiagnostics:
            return

        def _sanitize_path_value(path_value: str) -> str:
            raw = str(path_value).strip().strip('"').strip("'")
            # Some serialized paths can contain escaped control chars where
            # backslashes were interpreted (e.g. "\raw" -> "\r" + "aw").
            raw = raw.replace('\r', '/').replace('\n', '/').replace('\t', '/')
            raw = raw.replace('\\', '/')
            return raw

        def _candidate_raw_paths(path_value: str) -> list[str]:
            normalized = _sanitize_path_value(path_value)
            candidates = [normalized]

            if normalized.startswith('./'):
                candidates.append(normalized[2:])
            if normalized.startswith('/'):
                candidates.append(normalized.lstrip('/'))
            if '/raw/' in normalized:
                candidates.append(normalized.split('/raw/', 1)[1])
            if normalized.startswith('raw/'):
                candidates.append(normalized[4:])

            filename = normalized.rsplit('/', 1)[-1]
            if filename:
                candidates.append(filename)

            deduped: list[str] = []
            for candidate in candidates:
                if candidate and candidate not in deduped:
                    deduped.append(candidate)
            return deduped

        def _resolve_input_path(
            path_value: str, expected_suffix: str
        ) -> tuple[str, str]:
            last_exc: Exception | None = None
            for candidate in _candidate_raw_paths(path_value):
                try:
                    with archive.m_context.raw_file(candidate, 'r'):
                        return ('raw', candidate)
                except Exception as exc:
                    last_exc = exc

            # Fallback for local processing where values can point to staging
            # paths directly (e.g. .volumes/fs/staging/.../raw/file.csv).
            fs_candidates = _candidate_raw_paths(path_value)
            fs_candidates.insert(0, _sanitize_path_value(path_value))

            base_dirs = [
                Path.cwd(),
                Path(__file__).resolve().parents[5],
                Path(__file__).resolve().parents[4],
                Path(__file__).resolve().parents[3],
                Path(__file__).resolve().parents[4] / 'nomad-FAIR',
            ]
            for candidate in fs_candidates:
                try:
                    p = Path(candidate)
                    if p.is_file():
                        return ('fs', str(p))

                    if not p.is_absolute():
                        for base in base_dirs:
                            resolved = (base / p).resolve()
                            if resolved.is_file():
                                return ('fs', str(resolved))
                except Exception:
                    continue

            # Final fallback: find staged file by basename under .volumes staging.
            filename = _sanitize_path_value(path_value).rsplit('/', 1)[-1]
            if filename:
                for base in base_dirs:
                    try:
                        staging_root = (base / '.volumes' / 'fs' / 'staging').resolve()
                        if not staging_root.exists():
                            continue
                        for hit in staging_root.rglob(filename):
                            if hit.is_file() and 'raw' in hit.parts:
                                return ('fs', str(hit))
                    except Exception:
                        continue

                # Broader fallback inspired by sputter parser pragmatism:
                # search all known .volumes/fs trees regardless of subfolder.
                for base in base_dirs:
                    try:
                        fs_root = (base / '.volumes' / 'fs').resolve()
                        if not fs_root.exists():
                            continue
                        for hit in fs_root.rglob(filename):
                            if hit.is_file():
                                return ('fs', str(hit))
                    except Exception:
                        continue

            # Format-driven fallback for variable file names:
            # search latest matching file by expected extension and typical RTP naming.
            suffix = expected_suffix.lower().lstrip('.')
            for base in base_dirs:
                try:
                    fs_root = (base / '.volumes' / 'fs').resolve()
                    if not fs_root.exists():
                        continue

                    pattern = f'*.{suffix}'
                    candidates = [
                        hit
                        for hit in fs_root.rglob(pattern)
                        if hit.is_file() and 'raw' in hit.parts
                    ]

                    if not candidates:
                        continue

                    if suffix == 'csv':
                        preferred = [
                            p
                            for p in candidates
                            if 'recording set' in p.name.lower()
                            or '_rtp_' in p.name.lower()
                        ]
                    else:
                        preferred = [
                            p
                            for p in candidates
                            if 'logfile' in p.name.lower() or '_rtp_' in p.name.lower()
                        ]

                    pool = preferred if preferred else candidates
                    newest = max(pool, key=lambda p: p.stat().st_mtime)
                    return ('fs', str(newest))
                except Exception:
                    continue

            if last_exc is not None:
                raise last_exc
            raise FileNotFoundError(path_value)

        try:
            eklipse_kind, eklipse_ref = _resolve_input_path(
                self.log_file_eklipse, 'csv'
            )
            diagnostics_kind, diagnostics_ref = _resolve_input_path(
                self.log_file_T2BDiagnostics, 'txt'
            )

            with ExitStack() as stack:

                def _materialize_raw_to_temp(raw_ref: str, suffix: str) -> str:
                    raw_handle = stack.enter_context(
                        archive.m_context.raw_file(raw_ref, 'r')
                    )
                    temp_file = tempfile.NamedTemporaryFile(
                        mode='w',
                        encoding='utf-8',
                        delete=False,
                        suffix=suffix,
                        newline='',
                    )
                    try:
                        temp_file.write(raw_handle.read())
                    finally:
                        temp_file.close()
                    stack.callback(
                        lambda p=temp_file.name: Path(p).unlink(missing_ok=True)
                    )
                    return temp_file.name

                if eklipse_kind == 'raw':
                    eklipse_suffix = (
                        '.csv' if eklipse_ref.lower().endswith('.csv') else '.txt'
                    )
                    eklipse_path = _materialize_raw_to_temp(eklipse_ref, eklipse_suffix)
                else:
                    eklipse_path = eklipse_ref

                if diagnostics_kind == 'raw':
                    diagnostics_suffix = (
                        '.txt' if diagnostics_ref.lower().endswith('.txt') else '.csv'
                    )
                    diagnostics_path = _materialize_raw_to_temp(
                        diagnostics_ref, diagnostics_suffix
                    )
                else:
                    diagnostics_path = diagnostics_ref

                parsed = parse_rtp_logfiles(
                    eklipse_csv_path=eklipse_path,
                    t2b_diagnostics_txt_path=diagnostics_path,
                )
        except Exception as exc:
            logger.warning(f'Failed to parse RTP log files: {exc}')
            return

        # Keep explicitly entered values by default; optionally overwrite.
        if overwrite or self.used_gases in (None, []):
            self.used_gases = parsed.used_gases

        if (
            overwrite or self.base_pressure is None
        ) and parsed.base_pressure_pa is not None:
            self.base_pressure = parsed.base_pressure_pa
        if (
            overwrite or self.base_pressure_ballast is None
        ) and parsed.base_pressure_ballast_pa is not None:
            self.base_pressure_ballast = parsed.base_pressure_ballast_pa
        if (
            overwrite or self.rate_of_rise is None
        ) and parsed.rate_of_rise_pa_s is not None:
            self.rate_of_rise = parsed.rate_of_rise_pa_s
        if (
            overwrite or self.chiller_flow is None
        ) and parsed.chiller_flow_m3_s is not None:
            self.chiller_flow = parsed.chiller_flow_m3_s

        # Store timeseries for plotting.
        ts = parsed.timeseries or {}
        self._log_time_s = ts.get('time_s', [])
        self._log_temperature_c = ts.get('temperature_c', [])
        self._temperature_setpoint_profile = ts.get('temperature_setpoint_c', [])
        self._lamp_power_profile = ts.get('lamp_power', [])
        self._log_pressure_torr = ts.get('pressure_torr', [])
        self._log_ar_flow_sccm = ts.get('ar_flow_sccm', [])
        self._log_n2_flow_sccm = ts.get('n2_flow_sccm', [])
        self._log_ph3_flow_sccm = ts.get('ph3_in_ar_flow_sccm', [])
        self._log_h2s_flow_sccm = ts.get('h2s_in_ar_flow_sccm', [])

        if self.overview is None:
            self.overview = RTPOverview()

        if overwrite or self.overview.annealing_pressure is None:
            self.overview.annealing_pressure = parsed.overview.get('annealing_pressure')
        if overwrite or self.overview.annealing_time is None:
            self.overview.annealing_time = parsed.overview.get('annealing_time')
        if overwrite or self.overview.annealing_temperature is None:
            self.overview.annealing_temperature = parsed.overview.get(
                'annealing_temperature'
            )
        if overwrite or self.overview.annealing_ar_flow is None:
            self.overview.annealing_ar_flow = parsed.overview.get('annealing_ar_flow')
        if overwrite or self.overview.annealing_n2_flow is None:
            self.overview.annealing_n2_flow = parsed.overview.get('annealing_n2_flow')
        if overwrite or self.overview.annealing_ph3_in_ar_flow is None:
            self.overview.annealing_ph3_in_ar_flow = parsed.overview.get(
                'annealing_ph3_in_ar_flow'
            )
        if overwrite or self.overview.annealing_h2s_in_ar_flow is None:
            self.overview.annealing_h2s_in_ar_flow = parsed.overview.get(
                'annealing_h2s_in_ar_flow'
            )
        if overwrite or self.overview.total_heating_time is None:
            self.overview.total_heating_time = parsed.overview.get('total_heating_time')
        if overwrite or self.overview.total_cooling_time is None:
            self.overview.total_cooling_time = parsed.overview.get('total_cooling_time')
        if overwrite or self.overview.end_of_process_temperature is None:
            self.overview.end_of_process_temperature = parsed.overview.get(
                'end_of_process_temperature'
            )

        if overwrite or not self.steps:
            self.steps = []
            for i, parsed_step in enumerate(parsed.steps, start=1):
                step = DTURTPSteps(name=f'{parsed_step.name} {i}')
                step.step_overview = RTPStepOverview(
                    duration=parsed_step.duration_s,
                    pressure=parsed_step.pressure_pa,
                    step_ar_flow=parsed_step.ar_flow_m3_s,
                    step_n2_flow=parsed_step.n2_flow_m3_s,
                    step_ph3_in_ar_flow=parsed_step.ph3_in_ar_flow_m3_s,
                    step_h2s_in_ar_flow=parsed_step.h2s_in_ar_flow_m3_s,
                    initial_temperature=parsed_step.initial_temperature_k,
                    final_temperature=parsed_step.final_temperature_k,
                )
                self.steps.append(step)
