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

import json
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    Component,
    CompositeSystem,
    CompositeSystemReference,
    ElementalComposition,
    InstrumentReference,
    PureSubstanceComponent,
    PureSubstanceSection,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.datamodel.metainfo.workflow import (
    Link,
)
from nomad.metainfo import MEnum, MProxy, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_material_processing.general import (
    SubstrateReference,
    ThinFilm,
    ThinFilmReference,
)
from nomad_material_processing.vapor_deposition.general import (
    ChamberEnvironment,
    GasFlow,
    Pressure,
    TimeSeries,
    VolumetricFlowRate,
)
from nomad_material_processing.vapor_deposition.pvd.general import (
    PVDEvaporationSource,
    PVDSource,
    PVDStep,
)
from nomad_material_processing.vapor_deposition.pvd.sputtering import SputterDeposition
from nomad_measurements.utils import create_archive, merge_sections

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.gas import DTUGasSupply
from nomad_dtu_nanolab_plugin.schema_packages.sample import DTUCombinatorialLibrary
from nomad_dtu_nanolab_plugin.schema_packages.substrate import (
    DTUSubstrate,
    DTUSubstrateBatch,
)
from nomad_dtu_nanolab_plugin.schema_packages.target import DTUTarget
from nomad_dtu_nanolab_plugin.sputter_log_reader import (
    generate_timeline,
    get_nested_value,
    map_environment_params_to_nomad,
    map_gas_flow_params_to_nomad,
    map_material_params_to_nomad,
    map_params_to_nomad,
    map_s_cracker_params_to_nomad,
    map_sputter_source_params_to_nomad,
    map_step_params_to_nomad,
    read_events,
    read_logfile,
    write_params,
    # format_logfile,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import os

m_package = Package(name='DTU customised sputter Schemas')


class DtuSubstrateMounting(ArchiveSection):
    """
    Section containing information about the mounting of the substrate.
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
        type=DTUSubstrateBatch,
        description='A reference to the batch of the substrate used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    substrate = Quantity(
        type=DTUSubstrate,
        description='A reference to the substrate used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    relative_position = Quantity(
        type=str,
        description='The relative position of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(suggestions=['BL', 'BR', 'FL', 'FR']),
        ),
    )
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
    method_of_contact = Quantity(
        type=MEnum(['clamps', 'frame', 'other']),
        default='clamps',
        description='The method of contact between the substrate and the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.RadioEnumEditQuantity,
        ),
    )
    mask_used = Quantity(
        type=bool,
        default=False,
        description='Whether a mask was used during the deposition.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
        ),
    )
    mask_description = Quantity(
        type=str,
        description='A description of the mask used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.RichTextEditQuantity,
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSubstrateMounting` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if isinstance(self.substrate_batch, MProxy):
            self.substrate_batch.m_proxy_resolve()
        if self.substrate is None and isinstance(
            self.substrate_batch, DTUSubstrateBatch
        ):
            substrate = self.substrate_batch.next_not_used_in(DTUSputtering)
            self.substrate = substrate
        if self.position_x is None and self.position_y is None:
            positions = {
                'BL': (-0.02, 0.035),
                'BR': (0.02, 0.035),
                'FL': (-0.02, -0.005),
                'FR': (0.02, -0.005),
            }
            if self.relative_position in positions:
                self.position_x, self.position_y = positions[self.relative_position]
        if self.relative_position is not None:
            self.name = self.relative_position
        elif self.position_x is not None and self.position_y is not None:
            self.name = (
                f"x{self.position_x.to('cm').magnitude:.1f}-"
                f"y{self.position_y.to('cm').magnitude:.1f}"
            ).replace('.', 'p')


class DtuPowerSetPoint(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='W',
        description="""The set point power.""",
        shape=['*'],
    )


class DTUSputterPowerSupply(PVDEvaporationSource):
    power_type = Quantity(
        type=MEnum(['RF', 'DC', 'pulsed_DC']),
        default='RF',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    avg_power_sp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
    )
    power_sp = SubSection(
        section_def=DtuPowerSetPoint,
    )


class DtuDCBias(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='V',
        description="""The DC bias.""",
        shape=['*'],
    )


class DtuForwardPower(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='W',
        description="""The forward power.""",
        shape=['*'],
    )


class DtuReflectedPower(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='W',
        description="""The reflected power.""",
        shape=['*'],
    )


class DTUSputterRFPowerSupply(DTUSputterPowerSupply):
    power_type = Quantity(
        type=MEnum(['RF']),
        default='RF',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    avg_dc_bias = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
    )
    dc_bias = SubSection(
        section_def=DtuDCBias,
    )
    avg_fwd_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
    )
    fwd_power = SubSection(
        section_def=DtuForwardPower,
    )
    avg_rfl_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
    )
    rfl_power = SubSection(
        section_def=DtuReflectedPower,
    )


class DtuVoltage(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='V',
        description="""The voltage.""",
        shape=['*'],
    )


class DtuCurrent(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='A',
        description="""The current.""",
        shape=['*'],
    )


class DTUSputterDCPowerSupply(DTUSputterPowerSupply):
    avg_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
    )
    voltage = SubSection(
        section_def=DtuVoltage,
    )
    avg_current = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'A'},
        unit='A',
    )
    current = SubSection(
        section_def=DtuCurrent,
    )


class DtuPulseFrequency(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='Hz',
        description="""The pulse frequency.""",
        shape=['*'],
    )


class DtuDeadTime(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='s',
        description="""The dead time.""",
        shape=['*'],
    )


class DTUSputterPulsedDCPowerSupply(DTUSputterDCPowerSupply):
    avg_pulse_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'kHz'},
        unit='1/s',
    )
    pulse_frequency = SubSection(
        section_def=DtuPulseFrequency,
    )
    avg_dead_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'ms'},
        unit='s',
    )
    dead_time = SubSection(
        section_def=DtuDeadTime,
    )


class Substrate(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    set_point_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    corrected_real_temp = Quantity(
        type=np.float64,
        a_eln={'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `Substrate` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.set_point_temp is not None:
            # Convert set_point_temp to 'kelvin' explicitly and get its magnitude
            set_point_temp_in_kelvin = self.set_point_temp.to('kelvin').magnitude
            # Perform the calculation using the magnitude
            r_temp = (set_point_temp_in_kelvin * 0.905) + 12
            # Assign the result back to, ensuring it's a Quantity with 'kelvin' unit
            self.corrected_real_temp = r_temp * self.set_point_temp.u


class SCrackerOverview(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    zone1_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    zone2_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    zone3_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    valve_on_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 's'},
        unit='s',
    )
    valve_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'Hz'},
        unit='1/s',
    )


class DtuZone1Temp(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='K',
        description="""The temperature of zone 1.""",
        shape=['*'],
    )


class DtuZone2Temp(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='K',
        description="""The temperature of zone 2.""",
        shape=['*'],
    )


class DtuZone3Temp(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='K',
        description="""The temperature of zone 3.""",
        shape=['*'],
    )


class DtuValveOnTime(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='s',
        description="""The valve on time.""",
        shape=['*'],
    )


class DtuValveFrequency(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='Hz',
        description="""The valve frequency.""",
        shape=['*'],
    )


class SCracker(ArchiveSection):
    avg_zone1_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    avg_zone2_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    avg_zone3_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    avg_valve_on_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 's'},
        unit='s',
    )
    avg_valve_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'Hz'},
        unit='1/s',
    )
    zone1_temp = SubSection(
        section_def=DtuZone1Temp,
    )
    zone2_temp = SubSection(
        section_def=DtuZone2Temp,
    )
    zone3_temp = SubSection(
        section_def=DtuZone3Temp,
    )
    valve_on_time = SubSection(
        section_def=DtuValveOnTime,
    )
    valve_frequency = SubSection(
        section_def=DtuValveFrequency,
    )


class DTUShutter(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=bool,
        description="""Position of the substrate shutter.""",
        shape=['*'],
    )

    general_value = Quantity(
        type=bool,
        description="""Position of the general shutter.""",
    )


class DTUTargetReference(CompositeSystemReference):
    reference = Quantity(
        type=DTUTarget,
        description='A reference to a NOMAD `CompositeSystem` entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='composite system reference',
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuTargetReference` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.reference is None:
            return


class DTUTargetComponent(Component):
    system = Quantity(
        type=DTUTarget,
        description='The target material.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    lab_id = Quantity(
        type=str,
        description='The lab ID of the target material.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        pass  # TODO add fetching from lab_id


class DTUSource(PVDSource):
    pass


class DtuPlasma(DTUSource):  # TODO:reavaluate if the class should inherit DTUSource
    """
    Class similar a DTUSputteringSource with the
    exception that it does not have a material section"""

    source_shutter_open = SubSection(
        section_def=DTUShutter,
    )
    vapor_source = SubSection(
        section_def=DTUSputterPowerSupply,
        description="""
        The power supply of the sputtering source.
        """,
    )


class DTUSputteringSource(DtuPlasma):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    material = SubSection(
        section_def=DTUTargetComponent,
        repeats=True,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSource` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class DtuReactiveGasComponent(Component):
    system = Quantity(
        type=DTUGasSupply,
        description='The gas supply.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )


class DtuMassFlowController(Component):
    flow = SubSection(
        section_def=VolumetricFlowRate,
    )


class DtuReactiveGasSource(DTUSource):
    material = SubSection(
        section_def=DtuReactiveGasComponent,
    )
    vapor_source = SubSection(
        section_def=DtuMassFlowController,
    )


class DtuCrackerMaterial(PureSubstanceComponent):
    m_def = Section(
        a_template={
            'pure_substance': {
                'molecular_formula': 'S',
            },
        },
    )


class DtuCrackerSource(DTUSource):
    material = SubSection(section_def=DtuCrackerMaterial)
    vapor_source = SubSection(
        section_def=SCracker,
    )
    valve_open = SubSection(
        section_def=DTUShutter,
    )


class DTUGasFlow(GasFlow, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    gas_supply = Quantity(
        type=DTUGasSupply,
    )
    gas_name = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    used_gas_supply = Quantity(
        type=CompositeSystem,
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUGasFlow` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.used_gas_supply is None:
            return
        self.gas_name = self.used_gas_supply.name
        self.gas.name = self.used_gas_supply.name
        self.gas.iupac_name = self.used_gas_supply.iupac_name
        self.gas.molecular_formula = self.used_gas_supply.molecular_formula
        self.gas.molecular_mass = self.used_gas_supply.molecular_mass
        self.gas.inchi = self.used_gas_supply.inchi
        self.gas.inchi_key = self.used_gas_supply.inchi_key
        self.gas.smile = self.used_gas_supply.smiles
        self.gas.canonical_smile = self.used_gas_supply.canonical_smiles
        self.gas.cas_number = self.used_gas_supply.cas_number


class DtuSubstrateHeater(PureSubstanceSection):
    # TODO: Construct the heater section
    pass


class DTUChamberEnvironment(ChamberEnvironment, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    gas_flow = SubSection(
        section_def=DTUGasFlow,
        repeats=True,
    )

    platen_bias = SubSection(
        section_def=DtuPlasma,
    )
    heater = SubSection(section_def=DtuSubstrateHeater)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUChamberEnvironment` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class DTUSteps(PVDStep, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    sources = SubSection(
        section_def=DTUSource,
        repeats=True,
    )

    environment = SubSection(
        section_def=DTUChamberEnvironment,
    )  # Temp should go in there

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSteps` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class EndOfProcess(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    taken_out = Quantity(
        type=MEnum(['front', 'back']),
        default='front',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    heater_temp = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    time_in_chamber_after_deposition = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
    )
    chamber_purged = Quantity(
        type=bool,
        default=False,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )


class InstrumentParameters(InstrumentReference, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    platen_rotation = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degree'},
        unit='rad',
    )
    stage_used = Quantity(
        type=MEnum(['heating', 'cooling']),
        default='heating',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    platen_used = Quantity(
        type=MEnum(['A', 'B']),
        a_eln={'component': 'RadioEnumEditQuantity'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `InstrumentParameters` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.reference is not None:
            self.lab_id = self.reference.lab_id
            self.name = self.reference.name


class SourceOverview(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    target_material = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    target_id = SubSection(
        section_def=DTUTargetReference,
    )
    applied_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
    )
    plasma_ignition_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
    )
    power_type = Quantity(
        type=MEnum(['DC', 'RF', 'pulsed_DC']),
        default='RF',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    average_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
    )
    voltage_comments = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
    )


class UsedGas(GasFlow, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    gas_name = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    used_gas_supply = Quantity(
        type=CompositeSystem,
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `UsedGas` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        self.gas_name = self.used_gas_supply.name
        self.gas.name = self.used_gas_supply.name
        self.gas.iupac_name = self.used_gas_supply.iupac_name
        self.gas.molecular_formula = self.used_gas_supply.molecular_formula
        self.gas.molecular_mass = self.used_gas_supply.molecular_mass
        self.gas.inchi = self.used_gas_supply.inchi
        self.gas.inchi_key = self.used_gas_supply.inchi_key
        self.gas.smile = self.used_gas_supply.smiles
        self.gas.canonical_smile = self.used_gas_supply.canonical_smiles
        self.gas.cas_number = self.used_gas_supply.cas_number


class DepositionParameters(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    deposition_temp = Quantity(
        type=np.float64,
        default=300,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    deposition_time = Quantity(
        type=np.float64,
        default=1800,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
    )
    sputter_pressure = Quantity(
        type=np.float64,
        default=0.6666,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mtorr'},
        unit='kg/(m*s^2)',
    )
    material_space = Quantity(
        type=str,
        default='-P-S',
        a_eln={'component': 'StringEditQuantity'},
    )
    ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'Ar flow',
        },
        unit='m^3/s',
    )
    ar_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'Ar partial pressure',
        },
        unit='kg/(m*s^2)',
    )
    h2s_in_ar_flow = Quantity(
        type=np.float64,
        description="""
            Flow of 10% H2S in Ar in equivalent flow at standard conditions 0, i.e.
            the equivalent rate at a temperature of 0 °C (273.15 K) and a pressure of
            1 atm (101325 Pa).
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'H2S in Ar flow',
        },
        unit='m^3/s',
    )
    h2s_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'H2S partial pressure',
        },
        unit='kg/(m*s^2)',
    )
    ph3_in_ar_flow = Quantity(
        type=np.float64,
        description="""
            Flow of 10% PH3 in Ar in equivalent flow at standard conditions 0, i.e.
            the equivalent rate at a temperature of 0 °C (273.15 K) and a pressure of
            1 atm (101325 Pa).
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'PH3 in Ar flow',
        },
        unit='m^3/s',
    )
    ph3_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'PH3 partial pressure',
        },
        unit='kg/(m*s^2)',
    )
    target_image_before = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of target before the deposition',
        },
    )
    target_image_after = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of target after the deposition',
        },
    )
    heating_procedure = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
    )
    cooling_procedure = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
    )
    magkeeper3 = SubSection(
        section_def=SourceOverview,
    )
    magkeeper4 = SubSection(
        section_def=SourceOverview,
    )
    taurus = SubSection(
        section_def=SourceOverview,
    )
    s_cracker = SubSection(
        section_def=SCrackerOverview,
    )
    used_gases = SubSection(
        section_def=UsedGas,
        repeats=True,
    )
    sulfur_partial_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mbar'},
        unit='kg/(m*s^2)',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DepositionParameters` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)
        # derived quantities
        # partial pressures without the S-cracker taken into account
        p_ok = False
        if self.ar_flow is not None:
            flow = self.ar_flow.magnitude
            ar = self.ar_flow.magnitude
            if self.h2s_in_ar_flow is not None:
                flow += self.h2s_in_ar_flow.magnitude
                h2s = self.h2s_in_ar_flow.magnitude
                if self.ph3_in_ar_flow is not None:
                    flow += self.ph3_in_ar_flow.magnitude
                    ph3 = self.ph3_in_ar_flow.magnitude
                    p_ok = True

        if self.sputter_pressure is not None and p_ok:
            p = self.sputter_pressure.to('kg/(m*s^2)').magnitude
            total_ar = ar / flow * p + h2s * 0.9 / flow * p + ph3 * 0.9 / flow * p
            self.ar_partial_pressure = total_ar * self.sputter_pressure.u
            self.h2s_partial_pressure = h2s * 0.1 / flow * p * self.sputter_pressure.u
            self.ph3_partial_pressure = ph3 * 0.1 / flow * p * self.sputter_pressure.u


class DTUSputtering(SputterDeposition, PlotSection, Schema):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Sputtering',
    )
    lab_id = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity', 'label': 'Run ID'},
    )
    location = Quantity(
        type=str,
        default='DTU; IDOL Lab',
        a_eln={'component': 'StringEditQuantity'},
    )
    log_file = Quantity(
        type=str,
        a_eln={'component': 'FileEditQuantity', 'label': 'Log file'},
    )
    log_file_report = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity', 'label': 'Log file report'},
    )
    substrates = SubSection(
        section_def=DtuSubstrateMounting,
        repeats=True,
    )
    steps = SubSection(
        section_def=DTUSteps,
        repeats=True,
    )
    end_of_process = SubSection(
        section_def=EndOfProcess,
    )
    instruments = SubSection(
        section_def=InstrumentParameters,
        repeats=True,
    )
    deposition_parameters = SubSection(
        section_def=DepositionParameters,
    )

    def plot(self, events_plot, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        # Plotting the events on a timeline from the generate_timeline function
        timeline = generate_timeline(events_plot, self.lab_id)

        # Converting the timeline to a plotly json
        timeline_json = json.loads(timeline.to_json())
        timeline_json['config'] = dict(
            scrollZoom=False,
        )
        
        # Adding the plotly figure to the figures list
        self.figures.append(
            PlotlyFigure(
                label='Process timeline',
                figure=timeline_json,
            )
        )

        # # Plotting the sample positions on the platen
        # try:
        #     samples_plot = read_samples(self.samples)
        #     dep_params: DepositionParameters = self.deposition_parameters
        #     guns_plot = read_guns(
        #         [
        #             dep_params.magkeeper3,
        #             dep_params.magkeeper4,
        #             dep_params.taurus,
        #             dep_params.s_cracker,
        #         ],
        #         ['magkeeper3', 'magkeeper4', 'taurus', 's_cracker'],
        #     )
        #     condition_for_plot = (
        #         self.instruments[0].platen_rotation is not None and
        #         samples_plot is not None and
        #         guns_plot is not None
        #     )
        #     if condition_for_plot:
        #         platen_rot = (
        # self.instruments[0].platen_rotation.to('degree').magnitude)

        #     sample_pos_plot = plot_matplotlib_chamber_config(
        #         samples_plot, guns_plot, platen_rot
        #     )

        # except Exception as e:
        #     logger.warning(f'Failed to plot the sample positions: {e}')

    # Helper method to write the data
    def write_data(self, config: dict):
        input_dict = config.get('input_dict')
        input_keys = config.get('input_keys')
        output_obj = config.get('output_obj')
        output_obj_name = config.get('output_obj_name')
        output_keys = config.get('output_keys')
        unit = config.get('unit')
        logger = config.get('logger')

        joined_keys = "']['".join(input_keys)
        params_str = f"params['{joined_keys}']"
        subsection_str = f"{output_obj_name}.{'.'.join(output_keys)}"

        value = get_nested_value(input_dict, input_keys)

        # Checking that the value exists
        if value is None:
            logger.debug(f'Missing {params_str}: Could not set {subsection_str}')
            return
        # We check if the value is a TimeDelta object and convert it to seconds
        if isinstance(value, pd._libs.tslibs.timedeltas.Timedelta):
            try:
                value = value.total_seconds()
            except AttributeError:
                logger.warning(f'{params_str}.total_seconds method is invalid')
                return
            value = ureg.Quantity(value, 'second')
        elif unit is not None:
            if isinstance(value, list):
                for i in range(len(value)):
                    try:
                        value[i] = ureg.Quantity(value[i], unit)
                    except Exception as e:
                        logger.warning(f'Failed to convert {params_str} to {unit}: {e}')
                        return
            else:
                try:
                    value = ureg.Quantity(value, unit)
                except Exception as e:
                    logger.warning(f'Failed to convert {params_str} to {unit}: {e}')
                    return
        # Traverse the path to set the nested attribute
        try:
            obj = output_obj
            for attr in output_keys[:-1]:
                obj = getattr(obj, attr)
            setattr(obj, output_keys[-1], value)
            logger.info(f'Set {params_str} to {subsection_str}')
        except Exception as e:
            logger.warning(f'Failed to set {params_str} to {subsection_str}: {e}')

    def generate_general_log_data(self, params: dict, logger: 'BoundLogger') -> None:
        """
        Method for writing the log data to the respective sections.
        Args:
            params (dict): Dictionary containing the log data.
            archive (EntryArchive): The archive containing the section that
              is being written.
            logger (BoundLogger): A structlog logger.
        """

        # Overwriting the datetime and end_time
        self.datetime = params['overview']['log_start_time'].to_pydatetime()
        self.end_time = params['overview']['log_end_time'].to_pydatetime()

        gun_list = ['magkeeper3', 'magkeeper4', 'taurus']

        # Mapping the params to the respective sections
        param_nomad_map = map_params_to_nomad(params, gun_list)

        # Initializing a temporary class objects
        sputtering = DTUSputtering()
        sputtering.samples = []
        sputtering.steps = []
        sputtering.deposition_parameters = DepositionParameters()

        for gun in gun_list:
            if params['deposition'].get(gun, {}).get('enabled', False):
                # Create a SourceOverview object and set it to the relevant attribute
                source_overview = SourceOverview()
                setattr(sputtering.deposition_parameters, gun, source_overview)

                # Set the target_id attribute of the SourceOverview object
                target_reference = DTUTargetReference()
                setattr(source_overview, 'target_id', target_reference)

        if params.get('s_cracker', {}).get('enabled', False):
            sputtering.deposition_parameters.s_cracker = SCrackerOverview()

        sputtering.end_of_process = EndOfProcess()

        # Writing the params dict in the form of a report
        def format_log_for_html(log):
            # Replace spaces with non-breaking spaces
            log = log.replace(' ', '&nbsp;')
            # Replace newlines with <br> tags
            log = log.replace('\n', '<br>')
            return log

        sputtering.log_file_report = format_log_for_html(write_params(params))

        # Looping through the param_nomad_map
        for input_keys, output_keys, unit in param_nomad_map:
            config = {
                'input_dict': params,
                'input_keys': input_keys,
                'output_obj': sputtering,
                'output_obj_name': 'sputtering',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        # Getting the deposition sub-dictionary
        deposition = params.get('deposition', {})

        # Special case for the adjusted instrument parameters
        instrument_reference = InstrumentParameters()
        if 'platen_position' in deposition:
            instrument_reference.platen_rotation = ureg.Quantity(
                deposition['platen_position'], 'degree'
            )
        sputtering.instruments = [instrument_reference]

        return sputtering

    def generate_step_log_data(self, step_params: dict, logger: 'BoundLogger') -> None:
        steps = []

        for key in step_params:
            # Initializing a temporary step object
            step = DTUSteps()

            step_param_nomad_map = map_step_params_to_nomad(key)

            # Looping through the step_param_nomad_map
            for input_keys, output_keys, unit in step_param_nomad_map:
                config = {
                    'input_dict': step_params,
                    'input_keys': input_keys,
                    'output_obj': step,
                    'output_obj_name': 'step',
                    'output_keys': output_keys,
                    'unit': unit,
                    'logger': logger,
                }
                self.write_data(config)

            # generate the sources

            step.sources = []

            # generate sputtering sources
            sputter_sources = self.generate_sputtering_sources_log_data(
                step_params, key, logger
            )

            step.sources.extend(sputter_sources)

            # generate the s cracker source
            s_cracker = self.generate_s_cracker_log_data(step_params, key, logger)

            step.sources.append(s_cracker)

            # #generate the reactive gases source

            # reactive_gas_sources = self.generate_reactive_gas_sources_log_data(
            #     step_params, key, logger
            # )

            # step.sources.extend(reactive_gas_sources)

            # generate environment
            step.environment = DTUChamberEnvironment()

            environment = self.generate_environment_log_data(step_params, key, logger)

            step.environment = environment

            steps.append(step)

        return steps

    # def generate_reactive_gas_sources_log_data(
    #     self, step_params: dict, key: str, logger: 'BoundLogger'
    # ) -> None:
    #     gas_sources = []

    #     for gas_name in ['h2s', 'ph3']:
    #         single_gas_source = DtuReactiveGasSource()

    #         gas_source_param_nomad_map = map_reactive_gas_source_params_to_nomad(
    #             key, gas_name
    #         )

    #         # Looping through the gas_source_param_nomad_map
    #         for input_keys, output_keys, unit in gas_source_param_nomad_map:
    #             config = {
    #                 'input_dict': step_params,
    #                 'input_keys': input_keys,
    #                 'output_obj': single_gas_source,
    #                 'output_obj_name': 'gas_source',
    #                 'output_keys': output_keys,
    #                 'unit': unit,
    #                 'logger': logger,
    #             }
    #             self.write_data(config)

    #         gas_sources.append(single_gas_source)

    def generate_s_cracker_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        s_cracker = SCracker()

        s_cracker_param_nomad_map = map_s_cracker_params_to_nomad(key)

        # Looping through the s_cracker_param_nomad_map
        for input_keys, output_keys, unit in s_cracker_param_nomad_map:
            config = {
                'input_dict': step_params,
                'input_keys': input_keys,
                'output_obj': s_cracker,
                'output_obj_name': 's_cracker',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        return s_cracker

    def generate_sputtering_sources_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        sources = []

        for source_name in ['magkeeper3', 'magkeeper4', 'taurus']:
            # Create a DTUSource object and set it to the relevant attribute
            source = DTUSputteringSource()
            source.material = []
            source.source_shutter_open = DTUShutter()

            # Generate the power supply object
            power_type = (
                step_params.get(key, {})
                .get('sources', {})
                .get(source_name, {})
                .get('power_supply', {})
                .get('power_type', False)
            )

            if power_type == 'RF':
                source.vapor_source = DTUSputterRFPowerSupply()
                source.vapor_source.dc_bias = DtuDCBias()
                source.vapor_source.fwd_power = DtuForwardPower()
                source.vapor_source.rfl_power = DtuReflectedPower()
            elif power_type == 'DC':
                source.vapor_source = DTUSputterDCPowerSupply()
                source.vapor_source.voltage = DtuVoltage()
                source.vapor_source.current = DtuCurrent()
            elif power_type == 'pulsed_DC':  # only for pulsed_DC
                source.vapor_source = DTUSputterPulsedDCPowerSupply()
                source.vapor_source.voltage = DtuVoltage()
                source.vapor_source.current = DtuCurrent()
                source.vapor_source.pulse_frequency = DtuPulseFrequency()
                source.vapor_source.dead_time = DtuDeadTime()
            else:
                source.vapor_source = DTUSputterPowerSupply()

            source.vapor_source.power_sp = DtuPowerSetPoint()

            # Mapping the source_param_nomad_map
            source_param_nomad_map = map_sputter_source_params_to_nomad(
                key, source_name, power_type
            )

            # Looping through the source_param_nomad_map
            for input_keys, output_keys, unit in source_param_nomad_map:
                config = {
                    'input_dict': step_params,
                    'input_keys': input_keys,
                    'output_obj': source,
                    'output_obj_name': 'source',
                    'output_keys': output_keys,
                    'unit': unit,
                    'logger': logger,
                }
                self.write_data(config)

            target = self.generate_material_log_data(
                step_params, key, source_name, logger
            )

            source.material.extend(target)

            sources.append(source)

        return sources

    def generate_material_log_data(
        self, step_params: dict, key: str, source_name: str, logger: 'BoundLogger'
    ) -> None:
        target_list = []

        target = DTUTargetComponent()

        # Mapping the material_param_nomad_map
        material_param_nomad_map = map_material_params_to_nomad(key, source_name)
        for input_keys, output_keys, unit in material_param_nomad_map:
            config = {
                'input_dict': step_params,
                'input_keys': input_keys,
                'output_obj': target,
                'output_obj_name': 'target',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        target_list.append(target)

        return target_list

    def generate_environment_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        environment = DTUChamberEnvironment()
        environment.gas_flow = []
        environment.pressure = Pressure()

        environment_param_nomad_map = map_environment_params_to_nomad(key)

        # Looping through the environment_param_nomad_map
        for input_keys, output_keys, unit in environment_param_nomad_map:
            config = {
                'input_dict': step_params,
                'input_keys': input_keys,
                'output_obj': environment,
                'output_obj_name': 'environment',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        gas_flow = self.generate_gas_flow_log_data(step_params, key, logger)

        environment.gas_flow.extend(gas_flow)

        return environment

    def generate_gas_flow_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        gas_flow = []

        for gas_name in ['ar', 'h2s', 'ph3']:
            single_gas_flow = DTUGasFlow()
            single_gas_flow.flow_rate = VolumetricFlowRate()
            single_gas_flow.gas = PureSubstanceSection()

            gas_flow_param_nomad_map = map_gas_flow_params_to_nomad(key, gas_name)

            # Looping through the gas_flow_param_nomad_map
            for input_keys, output_keys, unit in gas_flow_param_nomad_map:
                config = {
                    'input_dict': step_params,
                    'input_keys': input_keys,
                    'output_obj': single_gas_flow,
                    'output_obj_name': 'gas_flow',
                    'output_keys': output_keys,
                    'unit': unit,
                    'logger': logger,
                }
                self.write_data(config)

            gas_flow.append(single_gas_flow)

        return gas_flow

    def add_libraries(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        samples = []
        substrate_mounting: DtuSubstrateMounting
        for idx, substrate_mounting in enumerate(self.substrates):
            if substrate_mounting.substrate is None:
                continue
            library = DTUCombinatorialLibrary()
            library.substrate = SubstrateReference(
                reference=substrate_mounting.substrate
            )
            sample_id = str(idx)
            if substrate_mounting.name is not None:
                sample_id = substrate_mounting.name.replace(' ', '-')
            if self.lab_id is not None:
                lab_id = self.lab_id
            else:
                lab_id = '_'.join(self.name.split())
            library.lab_id = f'{lab_id}-{sample_id}'
            elements = self.deposition_parameters.material_space.split('-')
            composition = [ElementalComposition(element=e) for e in elements if e]
            layer = ThinFilm(
                elemental_composition=composition,
                lab_id=f'{library.lab_id}-Layer',
            )
            library.layers = [
                ThinFilmReference(
                    name='Main layer',
                    reference=create_archive(
                        layer, archive, f'{layer.lab_id}.archive.json'
                    ),
                    lab_id=layer.lab_id,
                )
            ]
            samples.append(
                CompositeSystemReference(
                    name=f'Sample {sample_id}',
                    reference=create_archive(
                        library, archive, f'{library.lab_id}.archive.json'
                    ),
                    lab_id=library.lab_id,
                )
            )
        self.samples = samples

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSputtering` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        # Analysing log file
        if self.log_file:
            # Extracting the sample name from the log file name
            log_name = os.path.basename(self.log_file)
            sample_id = '_'.join(log_name.split('_')[0:3])
            # If lab_id is empty, assign the sample name to lab_id
            if self.lab_id is None:
                self.lab_id = sample_id
            # Openning the log file
            with archive.m_context.raw_file(self.log_file, 'r') as log:
                log_df = read_logfile(log.name)
                # formated_log_df = format_logfile(log_df)
                events_plot, params, step_params = read_events(log_df)
            if params is not None:
                # Writing logfile data to the respective sections
                sputtering = self.generate_general_log_data(params, logger)

            if step_params is not None and sputtering is not None:
                steps = self.generate_step_log_data(step_params, logger)
                sputtering.steps.extend(steps)

            # Merging the sputtering object with self
            merge_sections(self, sputtering, logger)

            # Run the normalizer of the deposition.parameters subsection
            self.deposition_parameters.normalize(archive, logger)

            # Run the nomalizer of the environment subsection
            for step in self.steps:
                for gas_flow in step.environment.gas_flow:
                    gas_flow.normalize(archive, logger)
                    gas_flow.gas.normalize(archive, logger)

            # Triggering the plotting of the timeline and the sample position plot
            self.figures = []
            self.plot(events_plot, archive, logger)

            if self.deposition_parameters is not None:
                self.add_libraries(archive, logger)

        archive.workflow2 = None
        super().normalize(archive, logger)
        archive.workflow2.inputs.extend(
            [
                Link(name=f'Substrate: {substrate.name}', section=substrate.substrate)
                for substrate in self.substrates
            ]
        )


m_package.__init_metainfo__()
