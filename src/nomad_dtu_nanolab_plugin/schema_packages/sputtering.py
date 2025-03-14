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
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
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
from nomad.datamodel.results import Material, Results
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
    SubstrateHeater,
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
from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
    ProcessParameterOverview,
)
from nomad_dtu_nanolab_plugin.schema_packages.substrate import (
    DTUSubstrate,
    DTUSubstrateBatch,
)
from nomad_dtu_nanolab_plugin.schema_packages.target import DTUTarget
from nomad_dtu_nanolab_plugin.sputter_log_reader import (
    GAS_FRACTION,
    Sample,
    format_logfile,
    generate_plots,
    get_nested_value,
    map_environment_params_to_nomad,
    map_gas_flow_params_to_nomad,
    map_heater_params_to_nomad,
    map_material_params_to_nomad,
    map_params_to_nomad,
    map_platen_bias_params_to_nomad,
    map_s_cracker_params_to_nomad,
    map_source_deprate_params_to_nomad,
    map_source_presput_params_to_nomad,
    map_source_up_params_to_nomad,
    map_sputter_source_params_to_nomad,
    map_step_params_to_nomad,
    plot_plotly_chamber_config,
    read_events,
    read_guns,
    read_logfile,
    read_samples,
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
            props=dict(suggestions=['BL', 'BR', 'FL', 'FR', 'G']),
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
    rotation = Quantity(
        type=np.float64,
        description="""
            The rotation of the substrate on the platen, relative to
            the width (x-axis) and height (y-axis) of the substrate.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
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
            self.substrate_batch, DTUSubstrateBatch
        ):
            substrate = self.substrate_batch.next_not_used_in(DTUSputtering)
            self.substrate = substrate
        if self.position_x is None or self.position_y is None or self.rotation is None:
            positions = {
                'BL': (-0.02, 0.035, 0),
                'BR': (0.02, 0.035, 0),
                'FL': (-0.02, -0.005, 0),
                'FR': (0.02, -0.005, 0),
                'G': (0, -0.038, np.pi / 2),
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
        description="""The DC self bias.""",
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
        description='The type of power supply.',
    )
    avg_dc_bias = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The average DC bias.',
    )
    dc_bias = SubSection(
        section_def=DtuDCBias,
    )
    avg_fwd_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
        description='The average forward power.',
    )
    fwd_power = SubSection(
        section_def=DtuForwardPower,
    )
    avg_rfl_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
        description='The average reflected power.',
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
        description="""The voltage of the power supply.""",
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
        description="""The current of the power supply.""",
        shape=['*'],
    )


class DTUSputterDCPowerSupply(DTUSputterPowerSupply):
    avg_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The average voltage of the DC power supply.',
    )
    voltage = SubSection(
        section_def=DtuVoltage,
    )
    avg_current = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'A'},
        unit='A',
        description='The average current of the DC power supply.',
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
        description="""The pulse frequency of the PDC power supply""",
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
        description="""The dead time of the PDC power supply.""",
        shape=['*'],
    )


class DTUSputterPulsedDCPowerSupply(DTUSputterDCPowerSupply):
    avg_pulse_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'kHz'},
        unit='1/s',
        description='The average pulse frequency of the PDC power supply.',
    )
    pulse_frequency = SubSection(
        section_def=DtuPulseFrequency,
    )
    avg_dead_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'ms'},
        unit='s',
        description='The average dead time of the PDC power supply.',
    )
    dead_time = SubSection(
        section_def=DtuDeadTime,
    )


class Substrate(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    setpoint_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    corrected_real_temperature = Quantity(
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
        if self.setpoint_temperature is not None:
            # Convert set_point_temp to 'kelvin' explicitly and get its magnitude
            set_point_temp_in_kelvin = self.setpoint_temperature.to('kelvin').magnitude
            # Perform the calculation using the magnitude
            r_temp = (set_point_temp_in_kelvin * 0.905) + 12
            # Assign the result back to, ensuring it's a Quantity with 'kelvin' unit
            self.corrected_real_temperature = r_temp * self.setpoint_temperature.u


class SCrackerOverview(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    zone1_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The temperature of sulfur cracker zone 1.""",
    )
    zone1_temperature_setpoint = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The temperature setpoint of sulfur cracker zone 1.""",
    )
    zone2_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The temperature of sulfur cracker zone 2.""",
    )
    zone3_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The temperature of sulfur cracker zone 3.""",
    )
    valve_on_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 's'},
        unit='s',
        description="""The valve on time of the sulfur cracker zone 2.""",
    )
    valve_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'Hz'},
        unit='1/s',
        description="""The valve frequency of the sulfur cracker zone 2.""",
    )


class DtuZoneTemp(TimeSeries):
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
    avg_zone1_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The average temperature of sulfur cracker zone 1.""",
    )
    avg_zone2_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The average temperature of sulfur cracker zone 2.""",
    )
    avg_zone3_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The average temperature of sulfur cracker zone 3.""",
    )
    avg_valve_on_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 's'},
        unit='s',
        description="""The average valve on time of the sulfur cracker zone 2.""",
    )
    avg_valve_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'Hz'},
        unit='1/s',
        description="""The average valve frequency of the sulfur cracker zone 2.""",
    )
    zone1_temperature = SubSection(
        section_def=DtuZoneTemp,
    )
    zone2_temperature = SubSection(
        section_def=DtuZoneTemp,
    )
    zone3_temperature = SubSection(
        section_def=DtuZoneTemp,
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
        description="""Position of the substrate shutter (1: open, 0: closed).""",
        shape=['*'],
    )

    mode_value = Quantity(
        type=bool,
        description="""
            Most represented (mode value) shutter
            state (1: mostly pen, 0: mostly closed).
        """,
    )


class DTUTargetReference(CompositeSystemReference):
    reference = Quantity(
        type=DTUTarget,
        description='A reference to a NOMAD Target entry.',
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
        from nomad.datamodel.context import ServerContext

        if (
            self.system is None
            and self.lab_id is not None
            and isinstance(archive.m_context, ServerContext)
        ):
            from nomad.search import MetadataPagination, search

            query = {'results.eln.lab_ids': self.lab_id}
            search_result = search(
                owner='all',
                query=query,
                pagination=MetadataPagination(page_size=1),
                user_id=archive.metadata.main_author.user_id,
            )
            if search_result.pagination.total > 0:
                entry_id = search_result.data[0]['entry_id']
                upload_id = search_result.data[0]['upload_id']
                self.system = f'../uploads/{upload_id}/archive/{entry_id}#data'
                if search_result.pagination.total > 1:
                    logger.warn(
                        f'Found {search_result.pagination.total} entries with lab_id: '
                        f'"{self.lab_id}". Will use the first one found.'
                    )
            else:
                logger.warn(f'Found no entries with lab_id: "{self.lab_id}".')
        elif self.lab_id is None and self.system is not None:
            self.lab_id = self.system.lab_id
        if self.name is None and self.lab_id is not None:
            self.name = self.lab_id


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
        description='The reactive gas supply.',
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
        a_eln={'component': 'StringEditQuantity', 'label': 'Gas name'},
        description='The name of the gas.',
    )
    used_gas_supply = Quantity(
        type=CompositeSystem,
        a_eln=ELNAnnotation(component=ELNComponentEnum.ReferenceEditQuantity),
        description='Reference to the gas supply used.',
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


class DtuTemperature(TimeSeries):
    m_def = Section(
        a_plot=dict(
            x='time',
            y='value',
        ),
    )

    value = Quantity(
        type=np.float64,
        unit='kelvin',
        description="""The temperature of the heater.""",
        shape=['*'],
    )


class DtuSubstrateHeater(SubstrateHeater):
    """
    Custom class for the substrate heater.
    """

    m_def = Section()

    avg_temperature_1 = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""
        The average temperature of the heater as measured by thermocouple 1.
        """,
    )
    avg_temperature_2 = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""
        The average temperature of the heater as measured by thermocouple 2.
        """,
    )
    avg_temperature_setpoint = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""The average temperature setpoint of the heater.""",
    )
    temperature_1 = SubSection(
        section_def=DtuTemperature,
    )

    temperature_2 = SubSection(
        section_def=DtuTemperature,
    )

    temperature_setpoint = SubSection(
        section_def=DtuTemperature,
    )


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
    heater_temperature = Quantity(
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

    # deposition related parameters
    target_name = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
        description='The name of the gun on which the target in mounted.',
    )
    target_material = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity', 'label': 'Target material'},
        description='The material of the target.',
    )
    target_id = SubSection(
        section_def=DTUTargetReference,
        description='A reference to the target used.',
    )
    applied_power = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'W',
            'label': 'Applied power',
        },
        unit='(kg*m^2)/s^3',
        description='The applied power.',
    )
    power_type = Quantity(
        type=MEnum(['DC', 'RF', 'pulsed_DC']),
        default='RF',
        a_eln={'component': 'RadioEnumEditQuantity'},
        description='The type of power supply.',
    )
    average_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The average voltage (DC bias in RF) of the power supply.',
    )
    std_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description="""
            'The standard deviation of the voltage (DC bias in RF) of the power supply.'
        """,
    )
    start_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The voltage (DC bias in RF) at the start of the deposition.',
    )
    end_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The voltage (DC bias in RF) at the end of the deposition.',
    )
    start_end_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The difference between the start and end voltage (DC bias in RF).',
    )
    max_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The maximum voltage (DC bias in RF) during the deposition.',
    )
    min_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The minimum voltage (DC bias in RF) during the deposition.',
    )
    range_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
        description='The difference between min and max voltage (DC bias in RF).',
    )
    voltage_comments = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
        description='Comments on the voltage (DC bias in RF) during the deposition.',
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


class SourceRampUp(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    target_name = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
        description='The name of the gun on which the target in mounted.',
    )
    # ignition related parameters
    plasma_ignition_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
        description='The power at which plasma ignites.',
    )
    plasma_ignition_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mtorr'},
        unit='kg/(m*s^2)',
        description='The pressure at which the plasma was ignited.',
    )


class SourcePresput(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    target_name = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
        description='The name of the gun on which the target in mounted.',
    )
    # presput related parameters
    presput_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
        description='The total presputtering time.',
    )
    presput_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
        description='The average power during presputtering.',
    )
    presput_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mtorr'},
        unit='kg/(m*s^2)',
        description='The average pressure during presputtering.',
    )
    presput_ar_flow = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'cm^3/minute'},
        unit='m^3/s',
        description='The average Ar flow during presputtering.',
    )


class SourceDepRate(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    target_name = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    # deposition rate related parameters
    source_deprate = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'nm/s'},
        unit='m/s',
    )
    source_deprate_ref_mat = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )


class SulfurCrackerPressure(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    sulfur_partial_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mbar'},
        unit='kg/(m*s^2)',
    )


class DepositionParameters(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    deposition_temperature = Quantity(
        type=np.float64,
        default=300,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The temperature of the deposition as measured by thermocouple 1.',
    )
    deposition_temperature_2 = Quantity(
        type=np.float64,
        default=300,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The temperature of the deposition as measured by thermocouple 2.',
    )
    deposition_temperature_setpoint = Quantity(
        type=np.float64,
        default=300,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The temperature setpoint of the deposition.',
    )
    deposition_true_temperature = Quantity(
        type=np.float64,
        a_eln={'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""
            The corrected real temperature of the deposition as calculated with :
            0.905 * (0.5 * (deposition_temperature + deposition_temperature_2)) + 12
        """,
    )
    deposition_time = Quantity(
        type=np.float64,
        default=1800,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
        description='The total deposition time.',
    )
    sputter_pressure = Quantity(
        type=np.float64,
        default=0.6666,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mtorr'},
        unit='kg/(m*s^2)',
        description='The pressure during sputtering as measured by the capman gauge.',
    )
    material_space = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
        description='The material space explored by the deposition.',
    )
    ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'Ar flow',
        },
        description="""
            Flow of 100% Ar in equivalent flow at standard conditions 0, i.e.
            the equivalent rate at a temperature of 0 °C (273.15 K) and a pressure of
            1 atm (101325 Pa).
        """,
        unit='m^3/s',
    )
    ar_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'Ar partial pressure',
        },
        description='The Ar partial pressure during the deposition.',
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
        description='The H2S partial pressure during the deposition.',
    )
    nh3_in_ar_flow = Quantity(
        type=np.float64,
        description="""
            Flow of 10% NH3 in Ar in equivalent flow at standard conditions 0, i.e.
            the equivalent rate at a temperature of 0 °C (273.15 K) and a pressure of
            1 atm (101325 Pa).
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'NH3 in Ar flow',
        },
        unit='m^3/s',
    )
    nh3_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'NH3 partial pressure',
        },
        unit='kg/(m*s^2)',
        description='The NH3 partial pressure during the deposition.',
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
        description='The PH3 partial pressure during the deposition',
    )
    n2_flow = Quantity(
        type=np.float64,
        description="""
            Flow of 100% N2 in equivalent flow at standard conditions 0, i.e.
            the equivalent rate at a temperature of 0 °C (273.15 K) and a pressure of
            1 atm (101325 Pa).
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'N2 flow',
        },
        unit='m^3/s',
    )
    n2_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'N2 partial pressure',
        },
        unit='kg/(m*s^2)',
        description='The N2 partial pressure during the deposition.',
    )
    o2_in_ar_flow = Quantity(
        type=np.float64,
        description="""
            Flow of 20% O2 in Ar in equivalent flow at standard conditions 0, i.e.
            the equivalent rate at a temperature of 0 °C (273.15 K) and a pressure of
            1 atm (101325 Pa).
        """,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'O2 in Ar flow',
        },
        unit='m^3/s',
    )
    o2_partial_pressure = Quantity(
        type=np.float64,
        a_eln={
            'defaultDisplayUnit': 'mtorr',
            'label': 'O2 partial pressure',
        },
        unit='kg/(m*s^2)',
        description='The O2 partial pressure during the deposition.',
    )
    ph3_h2s_ratio = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity'},
        description='The PH3/H2S ratio (if applicable).',
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

    def _calc_partial_pressure(self):
        ar_flow = self.ar_flow.magnitude if self.ar_flow is not None else 0
        h2s_in_ar_flow = (
            self.h2s_in_ar_flow.magnitude if self.h2s_in_ar_flow is not None else 0
        )
        nh3_in_ar_flow = (
            self.nh3_in_ar_flow.magnitude if self.nh3_in_ar_flow is not None else 0
        )
        ph3_in_ar_flow = (
            self.ph3_in_ar_flow.magnitude if self.ph3_in_ar_flow is not None else 0
        )
        n2_flow = self.n2_flow.magnitude if self.n2_flow is not None else 0
        o2_in_ar_flow = (
            self.o2_in_ar_flow.magnitude if self.o2_in_ar_flow is not None else 0
        )

        total_flow = (
            ar_flow
            + h2s_in_ar_flow
            + nh3_in_ar_flow
            + ph3_in_ar_flow
            + n2_flow
            + o2_in_ar_flow
        )

        total_pressure = self.sputter_pressure.magnitude

        h2s_partial_pressure = (
            h2s_in_ar_flow * GAS_FRACTION['h2s'] / total_flow * total_pressure
        )
        self.h2s_partial_pressure = h2s_partial_pressure * ureg('kg/(m*s^2)')

        nh3_partial_pressure = (
            nh3_in_ar_flow * GAS_FRACTION['nh3'] / total_flow * total_pressure
        )
        self.nh3_partial_pressure = nh3_partial_pressure * ureg('kg/(m*s^2)')

        ph3_partial_pressure = (
            ph3_in_ar_flow * GAS_FRACTION['ph3'] / total_flow * total_pressure
        )
        self.ph3_partial_pressure = ph3_partial_pressure * ureg('kg/(m*s^2)')

        n2_partial_pressure = n2_flow * GAS_FRACTION['n2'] / total_flow * total_pressure
        self.n2_partial_pressure = n2_partial_pressure * ureg('kg/(m*s^2)')

        o2_partial_pressure = (
            o2_in_ar_flow * GAS_FRACTION['o2'] / total_flow * total_pressure
        )
        self.o2_partial_pressure = o2_partial_pressure * ureg('kg/(m*s^2)')

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
        # p_ok = False
        # if self.ar_flow is not None:
        # flow = self.ar_flow.magnitude
        # ar = self.ar_flow.magnitude
        # if self.h2s_in_ar_flow is not None:
        # flow += self.h2s_in_ar_flow.magnitude
        # h2s = self.h2s_in_ar_flow.magnitude
        # if self.ph3_in_ar_flow is not None:
        # flow += self.ph3_in_ar_flow.magnitude
        # ph3 = self.ph3_in_ar_flow.magnitude
        # p_ok = True

        if self.ar_flow is not None:
            self._calc_partial_pressure()

        # if self.sputter_pressure is not None and p_ok:
        #   p = self.sputter_pressure.to('kg/(m*s^2)').magnitude
        #   total_ar = ar / flow * p + h2s * 0.9 / flow * p + ph3 * 0.9 / flow * p
        #   elf.ar_partial_pressure = total_ar * self.sputter_pressure.u
        #   self.h2s_partial_pressure = h2s * 0.1 / flow * p * self.sputter_pressure.u
        #   self.ph3_partial_pressure = ph3 * 0.1 / flow * p * self.sputter_pressure.u

        # if (
        #    self.deposition_temperature is not None
        #    and self.deposition_true_temperature is None
        # ):
        #    temp = self.deposition_temperature.to('degC').magnitude
        #    temp2 = self.deposition_temperature_2.to('degC').magnitude
        #    tru_temp = 0.905 * (0.5 * (temp + temp2)) + 12
        #    self.deposition_true_temperature = ureg.Quantity(tru_temp, 'degC')

        if self.h2s_in_ar_flow is not None and self.ph3_in_ar_flow is not None:
            if (
                self.ph3_in_ar_flow.magnitude != 0
                and self.h2s_in_ar_flow.magnitude != 0
            ):
                self.ph3_h2s_ratio = (
                    self.ph3_in_ar_flow.magnitude / self.h2s_in_ar_flow.magnitude
                )


class TempRampUp(ArchiveSection):
    duration = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
        description='The duration of the temperature ramp up.',
    )
    start_temperature_setpoint = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The start temperature setpoint.',
    )
    end_temperature_setpoint = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The end temperature setpoint.',
    )
    temperature_slope = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC/minute'},
        unit='kelvin/s',
        description='The temperature slope.',
    )
    avg_capman_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mbar'},
        unit='kg/(m*s^2)',
        description='The average pressure during the temperature ramp up.',
    )
    avg_ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'Ar flow',
        },
        unit='m^3/s',
        description='The average Ar flow during the temperature ramp up.',
    )
    avg_h2s_in_ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'H2S in Ar flow',
        },
        unit='m^3/s',
        description='The average H2S flow during the temperature ramp up.',
    )
    avg_ph3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'PH3 in Ar flow',
        },
        unit='m^3/s',
        description='The average PH3 flow during the temperature ramp up.',
    )
    cracker_enabled = Quantity(
        type=bool,
        default=False,
        a_eln={'component': 'BoolEditQuantity'},
        description='Boolean to indicate if the cracker was enabled.',
    )
    heating_procedure = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
        description='Comment on the heating procedure.',
    )


class TempRampDown(ArchiveSection):
    duration = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
        description='The duration of the temperature ramp down.',
    )
    start_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The start temperature.',
    )
    end_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description='The end temperature.',
    )
    avg_capman_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mbar'},
        unit='kg/(m*s^2)',
        description='The average pressure during the temperature ramp down.',
    )
    avg_ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'Ar flow',
        },
        unit='m^3/s',
        description='The average Ar flow during the temperature ramp down.',
    )
    avg_h2s_in_ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'H2S in Ar flow',
        },
        unit='m^3/s',
        description='The average H2S flow during the temperature ramp down.',
    )
    avg_ph3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln={
            'component': 'NumberEditQuantity',
            'defaultDisplayUnit': 'cm^3/minute',
            'label': 'PH3 in Ar flow',
        },
        unit='m^3/s',
        description='The average PH3 flow during the temperature ramp down.',
    )
    cracker_enabled = Quantity(
        type=bool,
        default=False,
        a_eln={'component': 'BoolEditQuantity'},
        description='Boolean to indicate if the cracker was enabled.',
    )
    anion_input_cutoff_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
        description="""
            The temperature at which the anion input (H2S, S-cracker, PH3, NH3, O2
            or N2) was cut off.'
        """,
    )
    cooling_procedure = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
        description='Comment on the cooling procedure.',
    )


class DtuFlag(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()

    flag = Quantity(
        type=str,
        description="""
            Flag name associated with the deposition. Flags are used to
            indicate issues that occurred during the deposition (see description).
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(
                suggestions=[
                    'WRONG_TOXIC_GAS_FLOW',
                    'WRONG_CRACKER_SIGNAL',
                    'INTERRUPTED_DEPOSITION',
                ]
            ),
        ),
    )

    flag_description = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity', 'label': 'Flag description'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuFlag` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        FLAG_DICT = {
            'WRONG_TOXIC_GAS_FLOW': (
                'The Ar bottle was leaking into the toxic gas line. Therefore,'
                'the toxic gas flows (PH2, H2S) are wrong. The impacted signals'
                '(MFC Flows) have been replaced by 999 in the logfile.'
            ),
            'WRONG_CRACKER_SIGNAL': (
                'The appropriate sulfur cracker signal were not being logged '
                '(Scracker pulse frequency and pulse width). The corresponding '
                'signal columns value have all been replaced the value cooresponding '
                'to the true signal as logged in the phosphosulfide_logbook for '
                ' timestamps during deposition. Therefore, the signal values are only'
                'correct for the timestamps corresponding to the deposition.'
            ),
            'INTERRUPTED_DEPOSITION': (
                'The deposition was interrupted due to the target turning off  '
                'spontenously. The deposition might have been resumed after the '
                'target was turned on again. The deposition time in the logfile '
                'might not be accurate.'
            ),
        }

        super().normalize(archive, logger)
        if self.flag is not None and self.flag_description is None:
            self.flag_description = FLAG_DICT.get(self.flag, None)


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
        description='The ID of the run. Format: user_XXXX_ElemementSymbol',
    )
    location = Quantity(
        type=str,
        default='DTU; IDOL Lab',
        a_eln={'component': 'StringEditQuantity'},
    )
    log_file = Quantity(
        type=str,
        a_eln={'component': 'FileEditQuantity', 'label': 'Log file'},
        description='Cell to upload the log file containing the deposition data.',
    )
    process_log_file = Quantity(
        type=bool,
        default=True,
        description='Boolean to indicate if the log_file should be processed.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Process log file',
        ),
    )
    overwrite = Quantity(
        type=bool,
        default=False,
        description="""
            Boolean to indicate if the data present in the class should be
            overwritten by data incoming from the log file.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Overwrite existing data ?',
        ),
    )
    cracker_warmup_log_file = Quantity(
        type=str,
        a_eln={'component': 'FileEditQuantity', 'label': 'Cracker warmup log file'},
        description='Cell to upload the log file containing the cracker warmup data.',
    )
    platen_used = Quantity(
        type=MEnum(['A', 'B']),
        a_eln={'component': 'RadioEnumEditQuantity'},
        description='The platen used for the deposition.',
    )
    base_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'torr'},
        unit='kg/(m*s^2)',
        description='The base pressure of the chamber before deposition.',
    )
    target_image_before = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of target before the deposition',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the image of the target before the deposition.',
    )
    target_image_after = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of target after the deposition',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the image of the target after the deposition.',
    )
    plasma_image = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of plasma during deposition',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the image of the plasma during the deposition.',
    )
    sample_image = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
            label='Image of sample',
        ),
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the image of the sample.',
    )
    optix_spectra = Quantity(
        type=str,
        a_eln={'component': 'FileEditQuantity', 'label': 'Optix spectra'},
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the Optix spectra data.',
    )
    rga_file = Quantity(
        type=str,
        a_eln={'component': 'FileEditQuantity', 'label': 'RGA file'},
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description='Cell to upload the RGA data associated by the Optix spectra data.',
    )
    optix_power_type = Quantity(
        type=MEnum(['DC', 'PDC']),
        a_eln={'component': 'RadioEnumEditQuantity'},
        description='The type of power used for the Optix. DC (default) or PDC.',
    )
    optix_current = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'uA'},
        unit='A',
        description='The current used for the Optix.',
    )
    flags = SubSection(
        section_def=DtuFlag,
        repeats=True,
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
    source_ramp_up = SubSection(
        section_def=SourceRampUp,
        repeats=True,
    )
    source_presput = SubSection(
        section_def=SourcePresput,
        repeats=True,
    )
    source_deprate = SubSection(
        section_def=SourceDepRate,
        repeats=True,
    )
    sulfur_cracker_pressure = SubSection(
        section_def=SulfurCrackerPressure,
    )
    temperature_ramp_up = SubSection(
        section_def=TempRampUp,
    )
    temperature_ramp_down = SubSection(
        section_def=TempRampDown,
    )

    def plot_plotly_chamber_config(self, logger: 'BoundLogger') -> dict:
        plots = {}

        # checking if the data is available for plotting, else return empty plots
        condition_for_plot = (
            self.instruments[0].platen_rotation is not None
            and self.substrates is not None
            and any(
                gun is not None
                for gun in [
                    self.deposition_parameters.magkeeper3,
                    self.deposition_parameters.magkeeper4,
                    self.deposition_parameters.taurus,
                    self.deposition_parameters.s_cracker,
                ]
            )
        )
        if not condition_for_plot:
            # if the conditions is not met, we return an empty dict of plots
            return plots

        # debbug logger warning
        if self.substrates is not None:
            for substrate in self.substrates:
                pos_x = getattr(substrate, 'position_x', None)
                pos_y = getattr(substrate, 'position_y', None)
                rotation = getattr(substrate, 'rotation', None)
                width = (
                    getattr(substrate.substrate.geometry, 'width', None)
                    if hasattr(substrate, 'substrate')
                    and hasattr(substrate.substrate, 'geometry')
                    else None
                )
                length = (
                    getattr(substrate.substrate.geometry, 'length', None)
                    if hasattr(substrate, 'substrate')
                    and hasattr(substrate.substrate, 'geometry')
                    else None
                )
                logger.debug(
                    f'Substrate: {substrate.name} - '
                    f'pos_x: {pos_x}, pos_y: {pos_y}, rotation: {rotation}, '
                    f'width: {width}, length: {length}'
                )  # can be removed in the future if the position plot is fixed

        # Plotting the sample positions on the platen
        # trying to read the sample positions else default
        # to the default positions
        try:
            samples_plot = read_samples(self.substrates)
        except Exception as e:
            samples_plot = [
                Sample('BR', [20, 35], 0, [40, 40]),
                Sample('BL', [-20, 35], 0, [40, 40]),
                Sample('FR', [20, -5], 0, [40, 40]),
                Sample('FL', [-20, -5], 0, [40, 40]),
                Sample('G', [0, -38], 90, [26, 76]),
            ]
            logger.warning(
                'Failed to read the sample positions. '
                f'Defaulting to BL, BR, FL, FR, and G: {e}'
            )

        dep_params: DepositionParameters = self.deposition_parameters
        guns_plot = read_guns(
            [
                dep_params.magkeeper3,
                dep_params.magkeeper4,
                dep_params.taurus,
                dep_params.s_cracker,
            ],
            ['magkeeper3', 'magkeeper4', 'taurus', 's_cracker'],
        )

        platen_rot = self.instruments[0].platen_rotation.to('degree').magnitude
        sample_pos_plot = plot_plotly_chamber_config(
            samples_plot,
            guns_plot,
            platen_rot,
            plot_title='DEPOSITION CONFIG :',
        )

        plots['Deposition sub. configuration'] = sample_pos_plot

        sample_mounting_plot = plot_plotly_chamber_config(
            samples_plot,
            guns_plot,
            90,
            plot_title='MOUNTING CONFIG :',
            in_chamber=False,
        )
        plots['Mounting sub. configuration'] = sample_mounting_plot

        return plots

    def plot(self, plots, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        for plot_name, plot in plots.items():
            plot_json = json.loads(plot.to_json())
            plot_json['config'] = dict(
                scrollZoom=False,
            )
            self.figures.append(
                PlotlyFigure(
                    label=plot_name,
                    figure=plot_json,
                )
            )

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
        subsection_str = f'{output_obj_name}.{".".join(output_keys)}'

        value = get_nested_value(input_dict, input_keys)

        # Checking that the value exists
        if value is None:
            logger.warning(f'Missing {params_str}: Could not set {subsection_str}')
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
                try:
                    value = ureg.Quantity(value, unit)
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
        sputtering.source_ramp_up = []
        sputtering.source_presput = []
        sputtering.source_deprate = []
        sputtering.temperature_ramp_up = TempRampUp()
        sputtering.temperature_ramp_down = TempRampDown()

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

        # Special case for the adjusted instrument parameters
        instrument_reference = InstrumentParameters()
        if 'platen_position' in params['deposition']:
            instrument_reference.platen_rotation = ureg.Quantity(
                params['deposition']['platen_position'], 'degree'
            )
        sputtering.instruments = [instrument_reference]

        targets_ramp_up, targets_presput, targets_deprate = (
            self.generate_source_up_presput_deprate_log_data(params, logger)
        )

        sputtering.source_ramp_up.extend(targets_ramp_up)

        sputtering.source_presput.extend(targets_presput)

        sputtering.source_deprate.extend(targets_deprate)

        if params['deposition']['interrupted']:
            sputtering.flags.append(DtuFlag(flag='INTERRUPTED_DEPOSITION'))

        return sputtering

    def generate_source_up_presput_deprate_log_data(
        self, params: dict, logger: 'BoundLogger'
    ) -> None:
        targets_ramp_up = []
        targets_presput = []
        targets_deprate = []

        for target_name in ['taurus', 'magkeeper3', 'magkeeper4']:
            if params.get('deposition', {}).get(target_name, {}).get('enabled', False):
                target_ramp_up = SourceRampUp()

                source_ramp_up_param_nomad_map = map_source_up_params_to_nomad(
                    target_name
                )

                # Looping through the source_ramp_up_param_nomad_map
                for input_keys, output_keys, unit in source_ramp_up_param_nomad_map:
                    config = {
                        'input_dict': params,
                        'input_keys': input_keys,
                        'output_obj': target_ramp_up,
                        'output_obj_name': 'ramp_up',
                        'output_keys': output_keys,
                        'unit': unit,
                        'logger': logger,
                    }
                    self.write_data(config)

                targets_ramp_up.append(target_ramp_up)

                target_presput = SourcePresput()

                source_presput_param_nomad_map = map_source_presput_params_to_nomad(
                    target_name
                )

                # Looping through the source_presput_param_nomad_map
                for input_keys, output_keys, unit in source_presput_param_nomad_map:
                    config = {
                        'input_dict': params,
                        'input_keys': input_keys,
                        'output_obj': target_presput,
                        'output_obj_name': 'presput',
                        'output_keys': output_keys,
                        'unit': unit,
                        'logger': logger,
                    }
                    self.write_data(config)

                targets_presput.append(target_presput)

                target_deprate = SourceDepRate()

                source_deprate_param_nomad_map = map_source_deprate_params_to_nomad(
                    target_name
                )

                # Looping through the source_deprate_param_nomad_map
                for input_keys, output_keys, unit in source_deprate_param_nomad_map:
                    config = {
                        'input_dict': params,
                        'input_keys': input_keys,
                        'output_obj': target_deprate,
                        'output_obj_name': 'deprate',
                        'output_keys': output_keys,
                        'unit': unit,
                        'logger': logger,
                    }
                    self.write_data(config)

                targets_deprate.append(target_deprate)

        all_targets = SourceDepRate()

        all_deprate_param_nomad_map = map_source_deprate_params_to_nomad('all')

        # Looping through the source_deprate_param_nomad_map
        for input_keys, output_keys, unit in all_deprate_param_nomad_map:
            config = {
                'input_dict': params,
                'input_keys': input_keys,
                'output_obj': all_targets,
                'output_obj_name': 'deprate',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        targets_deprate.append(all_targets)

        return targets_ramp_up, targets_presput, targets_deprate

    def generate_step_log_data(
        self, step_params: dict, archive: 'EntryArchive', logger: 'BoundLogger'
    ) -> None:
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
                step_params, key, archive, logger
            )

            step.sources.extend(sputter_sources)

            # generate the s cracker source
            if (
                step_params.get(key, {})
                .get('sources', {})
                .get('s_cracker', {})
                .get('cracker_record', False)
            ):
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

            if 'Deposition' in step.name:
                step.creates_new_thin_film = True
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
        cracker_source = DtuCrackerSource()
        cracker_source.vapor_source = SCracker()
        cracker_source.vapor_source.zone1_temperature = DtuZoneTemp()

        cracker_source.vapor_source.zone2_temperature = DtuZoneTemp()
        cracker_source.vapor_source.zone3_temperature = DtuZoneTemp()
        cracker_source.valve_open = DTUShutter()

        s_cracker_param_nomad_map = map_s_cracker_params_to_nomad(key)

        # Looping through the s_cracker_param_nomad_map
        for input_keys, output_keys, unit in s_cracker_param_nomad_map:
            config = {
                'input_dict': step_params,
                'input_keys': input_keys,
                'output_obj': cracker_source,
                'output_obj_name': 'cracker_source',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)
        cracker_source.material = [
            DtuCrackerMaterial(
                pure_substance=PureSubstanceSection(molecular_formula='S')
            )
        ]
        return cracker_source

    def generate_sputtering_sources_log_data(
        self,
        step_params: dict,
        key: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
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
                # source.vapor_source = DTUSputterPowerSupply()
                continue

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
                step_params, key, source_name, archive, logger
            )

            source.material.extend(target)

            sources.append(source)

        return sources

    def generate_material_log_data(
        self,
        step_params: dict,
        key: str,
        source_name: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
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
        # Run the normalizer of the target subsection to find reference from lab_id
        target.normalize(archive, logger)
        target_list.append(target)

        return target_list

    def generate_environment_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        environment = DTUChamberEnvironment()
        environment.gas_flow = []
        environment.pressure = Pressure()
        environment.platen_bias = DtuPlasma()
        environment.heater = DtuSubstrateHeater()

        environment_param_nomad_map = map_environment_params_to_nomad(key)

        # Looping through the environment_param_nomad_map (writing pressure data)
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

        # write platen bias data
        platen_bias = self.generate_platen_bias_log_data(step_params, key, logger)

        environment.platen_bias = platen_bias

        # write heater data

        heater = self.generate_heater_log_data(step_params, key, logger)

        environment.heater = heater

        return environment

    def generate_platen_bias_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        platen_bias = DtuPlasma()

        platen_bias.source_shutter_open = DTUShutter()

        platen_bias.vapor_source = DTUSputterRFPowerSupply()
        platen_bias.vapor_source.power_sp = DtuPowerSetPoint()
        platen_bias.vapor_source.dc_bias = DtuDCBias()
        platen_bias.vapor_source.fwd_power = DtuForwardPower()
        platen_bias.vapor_source.rfl_power = DtuReflectedPower()

        platen_bias_param_nomad_map = map_platen_bias_params_to_nomad(key, step_params)

        # Looping through the platen_bias_param_nomad_map
        for input_keys, output_keys, unit in platen_bias_param_nomad_map:
            config = {
                'input_dict': step_params,
                'input_keys': input_keys,
                'output_obj': platen_bias,
                'output_obj_name': 'platen_bias',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        return platen_bias

    def generate_heater_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        heater = DtuSubstrateHeater()

        heater.temperature_1 = DtuTemperature()
        heater.temperature_2 = DtuTemperature()
        heater.temperature_setpoint = DtuTemperature()

        heater_param_nomad_map = map_heater_params_to_nomad(key)

        # Looping through the heater_param_nomad_map
        for input_keys, output_keys, unit in heater_param_nomad_map:
            config = {
                'input_dict': step_params,
                'input_keys': input_keys,
                'output_obj': heater,
                'output_obj_name': 'heater',
                'output_keys': output_keys,
                'unit': unit,
                'logger': logger,
            }
            self.write_data(config)

        return heater

    def generate_gas_flow_log_data(
        self, step_params: dict, key: str, logger: 'BoundLogger'
    ) -> None:
        gas_flow = []

        for gas_name in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
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
            library.lab_id = f'{lab_id}_{sample_id}'
            elements = self.deposition_parameters.material_space.split('-')
            composition = [ElementalComposition(element=e) for e in elements if e]
            layer = ThinFilm(
                elemental_composition=composition,
                lab_id=f'{library.lab_id}-Layer',
            )
            layer_ref = create_archive(layer, archive, f'{layer.lab_id}.archive.json')
            library.layers = [
                ThinFilmReference(
                    name='Main layer',
                    reference=layer_ref,
                    lab_id=layer.lab_id,
                )
            ]

            library.process_parameter_overview = ProcessParameterOverview()
            # we write some important process parameters to the library
            library.process_parameter_overview.position_x = (
                substrate_mounting.position_x
            )
            library.process_parameter_overview.position_y = (
                substrate_mounting.position_y
            )
            library.process_parameter_overview.rotation = substrate_mounting.rotation
            library.process_parameter_overview.width = (
                substrate_mounting.substrate.geometry.width
            )
            library.process_parameter_overview.length = (
                substrate_mounting.substrate.geometry.length
            )
            # TODO add more process parameters

            library_ref = create_archive(
                library, archive, f'{library.lab_id}.archive.json'
            )
            samples.append(
                CompositeSystemReference(
                    name=f'Sample {sample_id}',
                    reference=library_ref,
                    lab_id=library.lab_id,
                )
            )
            # step: DTUSteps
            # for step in self.steps:
            #     if not step.creates_new_thin_film:
            #         continue
            #     print(f'{step.sample_parameters = }')
            #     if step.sample_parameters is None:
            #         step.sample_parameters = SampleParameters()
            #     print(f'{step.sample_parameters = }')
            #     step.sample_parameters.layer = ThinFilmReference(
            #         reference=layer_ref,
            #         lab_id=layer.lab_id,
            #     )
            #     step.sample_parameters.substrate = ThinFilmStackReference(
            #         reference=library_ref,
            #         lab_id=library.lab_id,
            #     )

        self.samples = samples

    def add_target_to_workflow(self, archive: 'EntryArchive') -> None:
        """
        Temporary method to add the target to the workflow2.inputs list.
        """
        for step in self.steps:
            step: DTUSteps
            for source in step.sources:
                source: DTUSource
                for m in source.material:
                    if isinstance(m, DTUTargetComponent):
                        archive.workflow2.inputs.append(
                            Link(name=f'Target: {m.name}', section=m.system)
                        )
                        return

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSputtering` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        # Analysing log file
        if self.log_file and self.process_log_file:
            # Extracting the sample name from the log file name
            log_name = os.path.basename(self.log_file)
            sample_id = '_'.join(log_name.split('_')[0:3])
            # If lab_id is empty, assign the sample name to lab_id
            if self.lab_id is None:
                self.lab_id = sample_id
            # Openning the log file
            with archive.m_context.raw_file(self.log_file, 'r') as log:
                log_df = read_logfile(log.name)
                formated_log_df, _ = format_logfile(log_df)
                events_plot, params, step_params = read_events(log_df)
            if params is not None:
                # Writing logfile data to the respective sections
                sputtering = self.generate_general_log_data(params, logger)

            if step_params is not None and sputtering is not None:
                steps = self.generate_step_log_data(step_params, archive, logger)
                sputtering.steps.extend(steps)

            # Merging the sputtering object with self
            if self.overwrite:
                merge_sections(sputtering, self, logger)
            else:
                merge_sections(self, sputtering, logger)

            # Run the nomalizer of the environment subsection
            for step in self.steps:
                for gas_flow in step.environment.gas_flow:
                    gas_flow.normalize(archive, logger)
                    gas_flow.gas.normalize(archive, logger)

            # Triggering the plotting of multiple plots
            self.figures = []

            plots = generate_plots(
                formated_log_df,
                events_plot,
                params,
                self.lab_id,
            )

            plots.update(self.plot_plotly_chamber_config(logger))

            self.plot(plots, archive, logger)

            if self.deposition_parameters is not None:
                self.add_libraries(archive, logger)

        archive.workflow2 = None
        super().normalize(archive, logger)
        self.add_target_to_workflow(archive)
        archive.workflow2.inputs.extend(
            [
                Link(name=f'Substrate: {substrate.name}', section=substrate.substrate)
                for substrate in self.substrates
            ]
        )
        if self.deposition_parameters is not None:
            if archive.results is None:
                archive.results = Results()
            if archive.results.material is None:
                archive.results.material = Material()
            elements = self.deposition_parameters.material_space.split('-')
            archive.results.material.elements = elements


m_package.__init_metainfo__()
