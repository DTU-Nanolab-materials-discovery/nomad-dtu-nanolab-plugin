from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MProxy, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_material_processing.vapor_deposition.cvd.general import (
    ChemicalVaporDeposition,
    CVDStep,
)

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.sample import DTUCombinatorialLibrary

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


m_package = Package(name='DTU RTP schema')

# volume fraction in the respective gas mixture (the complementary gas is Ar)
RTP_GAS_FRACTION = {
    'Ar': 1,
    'N2': 1,
    'PH3': 0.1,
    'H2S': 0.1,
}


#################### DEFINE SUBSTRATES (SUBSECTION) ######################
class DtuRTPSubstrateMounting(ArchiveSection):
    """
    Section containing information about the mounting of the substrates on the
    susceptor.
    """

    m_def = Section()
    name = Quantity(
        type=str,
        description='The name of the substrate mounting.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    substrate_batch = Quantity(
        type=DTUCombinatorialLibrary,
        description='A reference to the batch of the substrate used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    substrate = Quantity(
        type=DTUCombinatorialLibrary,
        description='A reference to the substrate used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    relative_position = Quantity(
        type=str,
        description='The relative position of the substrate on the susceptor.',
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
        description='The x-coordinate of the substrate on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    position_y = Quantity(
        type=np.float64,
        description='The y-coordinate of the substrate on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    rotation = Quantity(
        type=np.float64,
        description="""
            The rotation of the substrate on the susceptor, relative to
            the width (x-axis) and height (y-axis) of the substrate.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuSubstrateMounting` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if isinstance(self.substrate_batch, MProxy):
            self.substrate_batch.m_proxy_resolve()
        if self.substrate is None and isinstance(
            self.substrate_batch, DTUCombinatorialLibrary
        ):
            substrate = self.substrate_batch.next_not_used_in(DtuRTP)
            self.substrate = substrate
        if self.position_x is None or self.position_y is None or self.rotation is None:
            positions = {  # TODO #CHANGE THIS TO RIGHT VALUES FROM SUSCEPTOR
                'bl': (-0.02, 0.035, 0),
                'br': (0.02, 0.035, 0),
                'fl': (-0.02, -0.005, 0),
                'fr': (0.02, -0.005, 0),
                'm': (0, -0.038, np.pi / 2),
            }
            if self.relative_position in positions:
                self.position_x, self.position_y, self.rotation = positions[
                    self.relative_position
                ]
        if self.relative_position is not None:
            self.name = self.relative_position
        elif self.position_x is not None and self.position_y is not None:
            self.name = (
                f'x{self.position_x.to("cm").magnitude:.1f}-'
                f'y{self.position_y.to("cm").magnitude:.1f}'
            ).replace('.', 'p')


#################### HUMAN READABLE OVERVIEW (SUBSECTION) ######################
class RTPOverview(ArchiveSection):
    """
    Section containing a human readable overview of the RTP process.
    """

    m_def = Section()
    material_space = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
        description='The material space explored by the RTP process.',
    )
    annealing_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='Torr',
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
        description='Temperature during the annealing plateau of the RTP process.',
    )
    annealing_Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='Ar Flow',
        ),
        unit='m**3/s',
        description='Argon flow used during the annealing plateau of the RTP process.',
    )
    annealing_N2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='N2 Flow',
        ),
        unit='m**3/s',
        description='Nitrogen flow used during the annealing plateau of the'
        ' RTP process.',
    )
    annealing_PH3_in_Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='PH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Phosphine flow used during the annealing plateau of'
        ' the RTP process.',
    )
    annealing_H2S_in_Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='H2S in Ar Flow',
        ),
        unit='m**3/s',
        description='H2S flow used during the annealing plateau of the RTP process.',
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

    def _calc_partial_pressure(self):
        annealing_Ar_flow = (
            self.annealing_Ar_flow.magnitude
            if self.annealing_Ar_flow is not None
            else 0
        )
        annealing_N2_flow = (
            self.annealing_N2_flow.magnitude
            if self.annealing_N2_flow is not None
            else 0
        )
        annealing_H2S_in_Ar_flow = (
            self.annealing_H2S_in_Ar_flow.magnitude
            if self.annealing_H2S_in_Ar_flow is not None
            else 0
        )
        annealing_PH3_in_Ar_flow = (
            self.annealing_PH3_in_Ar_flow.magnitude
            if self.annealing_PH3_in_Ar_flow is not None
            else 0
        )
        total_flow = (
            annealing_Ar_flow
            + annealing_H2S_in_Ar_flow
            + annealing_N2_flow
            + annealing_PH3_in_Ar_flow
        )

        total_pressure = self.annealing_pressure.magnitude

        annealing_PH3_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='PH3 Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of PH3 during the annealing plateau of the'
            ' RTP process.',
        )
        annealing_H2S_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='H2S Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of H2S during the annealing plateau of the'
            ' RTP process.',
        )
        annealing_N2_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='N2 Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of N2 during the annealing plateau of the'
            ' RTP process.',
        )
        annealing_Ar_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='Ar Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of Ar during the annealing plateau of the'
            ' RTP process.',
        )
        annealing_H2S_partial_pressure = (
            annealing_H2S_in_Ar_flow
            * RTP_GAS_FRACTION['H2S']
            / total_flow
            * total_pressure
        )
        self.annealing_H2S_partial_pressure = annealing_H2S_partial_pressure * ureg(
            'kg/(m*s^2)'
        )
        annealing_PH3_partial_pressure = (
            annealing_PH3_in_Ar_flow
            * RTP_GAS_FRACTION['PH3']
            / total_flow
            * total_pressure
        )
        self.annealing_PH3_partial_pressure = annealing_PH3_partial_pressure * ureg(
            'kg/(m*s^2)'
        )
        annealing_N2_partial_pressure = (
            annealing_N2_flow * RTP_GAS_FRACTION['N2'] / total_flow * total_pressure
        )
        self.annealing_N2_partial_pressure = annealing_N2_partial_pressure * ureg(
            'kg/(m*s^2)'
        )
        annealing_Ar_partial_pressure = (
            (
                annealing_H2S_in_Ar_flow * (1 - RTP_GAS_FRACTION['H2S'])
                + annealing_PH3_in_Ar_flow * (1 - RTP_GAS_FRACTION['PH3'])
                + annealing_Ar_flow * RTP_GAS_FRACTION['Ar']
            )
            / total_flow
            * total_pressure
        )
        self.annealing_Ar_partial_pressure = annealing_Ar_partial_pressure * ureg(
            'kg/(m*s^2)'
        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTPOverview` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)
        if self.annealing_Ar_flow is not None:
            self._calc_partial_pressure()
        if (
            self.annealing_H2S_in_Ar_flow is not None
            and self.annealing_PH3_in_Ar_flow is not None
        ):
            if (
                self.annealing_H2S_in_Ar_flow.magnitude != 0
                and self.annealing_PH3_in_Ar_flow.magnitude != 0
            ):
                self.ph3_h2s_ratio = (
                    self.annealing_PH3_in_Ar_flow.magnitude
                    / self.annealing_H2S_in_Ar_flow.magnitude
                )


##################### STEPS (SUBSECTION) ######################################
class RTPStepOverview(ArchiveSection):
    """
    Section containing a human readable overview of a certain step of the RTP process.
    """

    m_def = Section()
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
            defaultDisplayUnit='Torr',
            label='Pressure',
        ),
        unit='Pa',
        description='Pressure in the RTP chamber during the step.',
    )
    step_Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='Ar Flow',
        ),
        unit='m**3/s',
        description='Argon flow rate used during the step.',
    )
    step_N2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='N2 Flow',
        ),
        unit='m**3/s',
        description='Nitrogen flow rate used during the step.',
    )
    step_PH3_in_Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='PH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Phosphine flow rate used during the step.',
    )
    step_H2S_in_Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='H2S in ArFlow',
        ),
        unit='m**3/s',
        description='H2S flow rate used during the step.',
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

    def _calc_ramp(self):
        """
        Calculate the temperature ramp rate based on the initial and final temperatures
        and the duration of the step.
        """
        if (
            self.duration is not None
            and self.initial_temperature is not None
            and self.final_temperature is not None
        ):
            self.temperature_ramp = (
                (self.final_temperature - self.initial_temperature) / self.duration
            )
        else:
            self.temperature_ramp = None

    def _calc_partial_pressure(self):
        step_Ar_flow = (
            self.step_Ar_flow.magnitude if self.step_Ar_flow is not None else 0
        )
        step_N2_flow = (
            self.step_N2_flow.magnitude if self.step_N2_flow is not None else 0
        )
        step_H2S_in_Ar_flow = (
            self.step_H2S_in_Ar_flow.magnitude
            if self.step_H2S_in_Ar_flow is not None
            else 0
        )
        step_PH3_in_Ar_flow = (
            self.step_PH3_in_Ar_flow.magnitude
            if self.step_PH3_in_Ar_flow is not None
            else 0
        )
        total_flow = (
            step_Ar_flow + step_H2S_in_Ar_flow + step_N2_flow + step_PH3_in_Ar_flow
        )

        total_pressure = self.annealing_pressure.magnitude

        step_PH3_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='PH3 Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of PH3 during the annealing plateau of the'
            ' RTP process.',
        )
        step_H2S_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='H2S Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of H2S during the annealing plateau of the'
            ' RTP process.',
        )
        step_N2_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='N2 Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of N2 during the annealing plateau of the'
            ' RTP process.',
        )
        step_Ar_partial_pressure = Quantity(
            type=np.float64,
            a_eln=ELNAnnotation(
                defaultDisplayUnit='Torr',
                label='Ar Partial Pressure',
            ),
            unit='Pa',
            description='Partial pressure of Ar during the annealing plateau of the'
            ' RTP process.',
        )
        step_H2S_partial_pressure = (
            step_H2S_in_Ar_flow * RTP_GAS_FRACTION['H2S'] / total_flow * total_pressure
        )
        self.step_H2S_partial_pressure = step_H2S_partial_pressure * ureg('kg/(m*s^2)')
        step_PH3_partial_pressure = (
            step_PH3_in_Ar_flow * RTP_GAS_FRACTION['PH3'] / total_flow * total_pressure
        )
        self.step_PH3_partial_pressure = step_PH3_partial_pressure * ureg('kg/(m*s^2)')
        step_N2_partial_pressure = (
            step_N2_flow * RTP_GAS_FRACTION['N2'] / total_flow * total_pressure
        )
        self.step_N2_partial_pressure = step_N2_partial_pressure * ureg('kg/(m*s^2)')
        step_Ar_partial_pressure = (
            (
                step_H2S_in_Ar_flow * (1 - RTP_GAS_FRACTION['H2S'])
                + step_PH3_in_Ar_flow * (1 - RTP_GAS_FRACTION['PH3'])
                + step_Ar_flow * RTP_GAS_FRACTION['Ar']
            )
            / total_flow
            * total_pressure
        )
        self.step_Ar_partial_pressure = step_Ar_partial_pressure * ureg('kg/(m*s^2)')

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSteps` class.

        Args:
        archive (EntryArchive): The archive containing the section that is being
        normalized.
        logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if (
            self.initial_temperature is not None
            and self.final_temperature is not None
            and self.initial_temperature != self.final_temperature
        ):
            self._calc_ramp()


class DTURTPSteps(CVDStep, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    step_overview = SubSection(
        section_def=RTPStepOverview,
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
        links=['http://purl.obolibrary.org/obo/CHMO_0001328'],
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
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity, label='Gases log file'
        ),
        description='Cell to upload the gases log file from the RTP process.',
    )
    log_file_T2BDiagnostics = Quantity(
    log_file_eklipse = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity, label='Gases log file'
        ),
        description='Cell to upload the gases log file from the RTP process.',
    )
    log_file_T2BDiagnostics = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity, label='Temperature log file'
        ),
        description='Cell to upload the temperature log file from the RTP process.',
    )
    # log_file_pressure = Quantity(
    #    type=str,
    #    a_eln=ELNAnnotation(
    #        component=ELNComponentEnum.FileEditQuantity,
    #        label = 'Pressure log file'
    #    ),
    #    description='Cell to upload the pressure log file from the RTP process.',
    # )
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
            component=ELNComponentEnum.FileEditQuantity,
            label='Base Pressure without ballast',
            defaultDisplayUnit='mtorr',
        ),
        unit='Pa',
        description='Base pressure when ballast is OFF',
    )
    base_pressure_ballast = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
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
            defaultDisplayUnit='mTorr/minute',
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
    ########################### SUBSECTIONS ########################################
    substrates = SubSection(
        section_def=DtuRTPSubstrateMounting,
        repeats=True,
    )
    overview = SubSection(
        section_def=RTPOverview,
    )
    steps = SubSection(
        section_def=DTURTPSteps,
        repeats=True,
    )
    ############################## PLOTS #################################
    time = Quantity(
        type=np.float64,
        shape=['*'],
        description='Time points for the temperature profile plot.',
    )
    temperature_profile = Quantity(
        type=np.float64,
        shape=['*'],
        description='Temperature points for the temperature profile plot.',
    )

    def plot(self) -> None:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=self.time,
                y=self.temperature_profile,
                mode='lines+markers',
                name='Temperature Profile',
            )
        )
        fig.update_layout(
            title='RTP Temperature Profile',
            xaxis_title='Time / seconds',
            yaxis_title='Temperature / °C',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
                type='log',
            ),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False)
        self.figures.append(
            PlotlyFigure(
                label='Temperature Profile',
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
        super().normalize(archive, logger)
        times, temps, current_time = [], [], 0
        step: DTURTPSteps
        for step in getattr(self, 'steps', []):  # Loop over all DTURTPSteps
            step_overview = getattr(step, 'step_overview', None)
            if (
                step_overview is not None
                and hasattr(step_overview, 'initial_temperature')
                and hasattr(step_overview, 'final_temperature')
                and hasattr(step_overview, 'duration')
            ):
                # Add initial point for the step
                temps.append(step_overview.initial_temperature)
                times.append(current_time)
                # Add final point for the step
                current_time += step_overview.duration or 0
                temps.append(step_overview.final_temperature)
                times.append(current_time)
        self.time = times
        self.temperature_profile = temps
        self.figures = []
        self.plot()


# Lena's initial CODE
#    temperature = Quantity(
#        type=float,
#        a_eln=ELNAnnotation(
#            component=ELNComponentEnum.NumberEditQuantity,
#            defaultDisplayUnit='celsius',
#        ),
#        unit='K',
#        description='Temperature of the process.',
#    )
#    used_gases = Quantity(
#        type= str,
#        shape=['*'],
#        a_eln=ELNAnnotation(
#            component=ELNComponentEnum.StringEditQuantity,
#            label='Used gases',
#        ),
#        description='Gases used in the process.',
#    )
