import numpy as np
import numpy as np
from typing import TYPE_CHECKING

from nomad.datamodel.data import Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ChemicalVaporDeposition
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Package, Quantity, Section
from nomad_material_processing.vapor_deposition.cvd.general import (
    ChemicalVaporDeposition,
)

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


m_package = Package(name='DTU RTP Schemas')


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
        description='The ID of the run. Format: name_number_material_quarter_piece'
        '-totalpieces ',
        description='The ID of the run. Format: name_number_material_quarter_piece'
        '-totalpieces ',
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
            component=ELNComponentEnum.FileEditQuantity,
            label= 'Gases log file'
        ),
        description='Cell to upload the gases log file from the RTP process.',
    )
    log_file_T2BDiagnostics = Quantity(
    log_file_eklipse = Quantity(
        type=str,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
            label= 'Gases log file'
        ),
        description='Cell to upload the gases log file from the RTP process.',
    )
    log_file_T2BDiagnostics = Quantity(
        type=str,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
            label = 'Temperature log file'
            label = 'Temperature log file'
        ),
        description='Cell to upload the temperature log file from the RTP process.',
    )
    #log_file_pressure = Quantity(
    #    type=str,
    #    shape=['*'],
    #    a_eln=ELNAnnotation(
    #        component=ELNComponentEnum.FileEditQuantity,
    #        label = 'Pressure log file'
    #    ),
    #    description='Cell to upload the pressure log file from the RTP process.',
    #)

    #################### HEATING RAMPING UP ######################

    uses_toxic_gases = Quantity(
    type=bool,
    a_eln=ELNAnnotation(
        component=ELNComponentEnum.BooleanEditQuantity,
        label='Are toxic gases used?',
    ),
    description='Check if toxic gases are used in the process.',
)
    base_pressure = Quantity(
        type=np.float64,
        a_eln= ELNAnnotation(
            component= ELNComponentEnum.FileEditQuantity,
            label='Base Pressure without ballast',
            defaultDisplayUnit = 'mtorr'
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
        visibleIf={'uses_toxic_gases': True}  # <- Only visible if toxic gases used
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
    description='Rate of rise of the pressure in the RTP chamber during static vacuum',
    )
    chiller_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='l/minute',
            label='Chiller Flow',
        ),
    unit='m³/s',
    description='Chiller flow rate during the RTP process.',
    )
    Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='Ar Flow',
            visibleIf={'uses_toxic_gases': False}  # <- Only visible if tox gases not used
        ),
        unit='m³/s',
        description='Argon flow rate used during the RTP process.',
    )
    N2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='N2 Flow',
            visibleIf={'uses_toxic_gases': False}  # <- Only visible if tox gases not used
        ),
        unit='m³/s',
        description='Nitrogen flow rate used during the RTP process.',
    )
    PH3_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='PH3 Flow',
            visibleIf={'uses_toxic_gases': True}  # <- Only visible if toxic gases used
        ),
        unit='m³/s',
        description='Phosphine flow rate used during the RTP process.',
    )
    H2S_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='H2S Flow',
            visibleIf={'uses_toxic_gases': True}  # <- Only vis if toxic gases used
        ),
        unit='m³/s',
        description='H2S flow rate used during the RTP process.',
    )
    heating_up_rate = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='Celsius/minute',
            label='Heating Up Rate',
        ),
    unit='K/s',
    description='Rate of temperature increase during the heating up phase of the' \
    ' RTP process.',
    )
    heating_up_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='Torr',
            label='HEating up pressure',
        ),
    unit='Pa',
    description='Pressure in the RTP chamber during the heating up phase of the' \
    ' RTP process.',
    )

################### ANNEALING PLATEAU ######################

        description='Cell to upload the temperature log file from the RTP process.',
    )
    #log_file_pressure = Quantity(
    #    type=str,
    #    shape=['*'],
    #    a_eln=ELNAnnotation(
    #        component=ELNComponentEnum.FileEditQuantity,
    #        label = 'Pressure log file'
    #    ),
    #    description='Cell to upload the pressure log file from the RTP process.',
    #)

    #################### HEATING RAMPING UP ######################

    uses_toxic_gases = Quantity(
    type=bool,
    a_eln=ELNAnnotation(
        component=ELNComponentEnum.BooleanEditQuantity,
        label='Are toxic gases used?',
    ),
    description='Check if toxic gases are used in the process.',
)
    base_pressure = Quantity(
        type=np.float64,
        a_eln= ELNAnnotation(
            component= ELNComponentEnum.FileEditQuantity,
            label='Base Pressure without ballast',
            defaultDisplayUnit = 'mtorr'
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
        visibleIf={'uses_toxic_gases': True}  # <- Only visible if toxic gases used
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
    description='Rate of rise of the pressure in the RTP chamber during static vacuum',
    )
    chiller_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='l/minute',
            label='Chiller Flow',
        ),
    unit='m³/s',
    description='Chiller flow rate during the RTP process.',
    )
    Ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='Ar Flow',
            visibleIf={'uses_toxic_gases': False}  # <- Only visible if tox gases not used
        ),
        unit='m³/s',
        description='Argon flow rate used during the RTP process.',
    )
    N2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='N2 Flow',
            visibleIf={'uses_toxic_gases': False}  # <- Only visible if tox gases not used
        ),
        unit='m³/s',
        description='Nitrogen flow rate used during the RTP process.',
    )
    PH3_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='PH3 Flow',
            visibleIf={'uses_toxic_gases': True}  # <- Only visible if toxic gases used
        ),
        unit='m³/s',
        description='Phosphine flow rate used during the RTP process.',
    )
    H2S_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='sccm',
            label='H2S Flow',
            visibleIf={'uses_toxic_gases': True}  # <- Only vis if toxic gases used
        ),
        unit='m³/s',
        description='H2S flow rate used during the RTP process.',
    )
    heating_up_rate = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='Celsius/minute',
            label='Heating Up Rate',
        ),
    unit='K/s',
    description='Rate of temperature increase during the heating up phase of the' \
    ' RTP process.',
    )
    heating_up_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='Torr',
            label='HEating up pressure',
        ),
    unit='Pa',
    description='Pressure in the RTP chamber during the heating up phase of the' \
    ' RTP process.',
    )

################### ANNEALING PLATEAU ######################

    duration = Quantity(
        type=np.float64,
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute'
            label= 'Duration',
        ),
        unit='s',
        description='Duration of the plateau',
        unit='s',
        description='Duration of the plateau',
    )
    temperature = Quantity(
        type=float,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree_Celsius',
        ),
        unit='K',
        unit='K',
        description='Temperature of the process.',
    )
    used_gases = Quantity(
        type= str,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Used gases',
        ),
        description='Gases used in the process.',
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