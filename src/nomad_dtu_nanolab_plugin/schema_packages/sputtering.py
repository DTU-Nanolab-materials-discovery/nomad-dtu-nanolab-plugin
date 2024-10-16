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
import pandas as pd
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    CompositeSystem,
    CompositeSystemReference,
    InstrumentReference,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_material_processing.vapor_deposition.general import (
    ChamberEnvironment,
    GasFlow,
    Pressure,
    PureSubstanceSection,
    VolumetricFlowRate,
)
from nomad_material_processing.vapor_deposition.pvd.general import PVDSource, PVDStep
from nomad_material_processing.vapor_deposition.pvd.sputtering import SputterDeposition
from nomad_measurements.utils import merge_sections

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.gas import DTUGasSupply
from nomad_dtu_nanolab_plugin.sputter_log_reader import (
    get_nested_value,
    map_environment_params_to_nomad,
    map_gas_flow_params_to_nomad,
    map_params_to_nomad,
    map_step_params_to_nomad,
    plot_plotly_extimeline,
    read_events,
    read_logfile,
    write_params,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

import os

m_package = Package(name='DTU customised sputter Schemas')


class DTUsamples(CompositeSystemReference, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    relative_position = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    m_def = Section()
    Substrate_position_x = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'cm'},
        unit='m',
    )
    Substrate_position_y = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'cm'},
        unit='m',
    )
    method_of_contact = Quantity(
        type=MEnum(['clamps', 'frame', 'other']),
        default='clamps',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    mask_used = Quantity(
        type=bool,
        default=False,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    mask_description = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUsamples` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        if self.Substrate_position_x is None and self.Substrate_position_y is None:
            if self.relative_position == 'BL':
                self.Substrate_position_x = -0.02
                self.Substrate_position_y = 0.035
            elif self.relative_position == 'BR':
                self.Substrate_position_x = 0.02
                self.Substrate_position_y = 0.035
            elif self.relative_position == 'FL':
                self.Substrate_position_x = -0.02
                self.Substrate_position_y = -0.005
            elif self.relative_position == 'FR':
                self.Substrate_position_x = 0.02
                self.Substrate_position_y = -0.005


class Chamber(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    shutters_open = Quantity(
        type=bool,
        default=False,
        description="""
            Position of the substrate shutter.
        """,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    applied_RF_bias_platen = Quantity(
        type=np.float64,
        default=0,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
    )
    total_pressure = Quantity(
        type=np.float64,
        default=0.6666,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mtorr'},
        unit='kg/(m*s^2)',
    )


class Substrate(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    set_point_temperature = Quantity(
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
        if self.set_point_temperature is not None:
            # Convert set_point_temperature to 'kelvin' explicitly and get its magnitude
            set_point_temp_in_kelvin = self.set_point_temperature.to('kelvin').magnitude
            # Perform the calculation using the magnitude
            r_temp = (set_point_temp_in_kelvin * 0.905) + 12
            # Assign the result back to, ensuring it's a Quantity with 'kelvin' unit
            self.corrected_real_temperature = r_temp * self.set_point_temperature.u


class SCracker(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    Zone1_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    Zone2_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    Zone3_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    valve_ON_time = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 's'},
        unit='s',
    )
    valve_frequency = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'Hz'},
        unit='1/s',
    )
    S_partial_pressure = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'mbar'},
        unit='kg/(m*s^2)',
    )


class Special(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    platen_temperature_ramp_rate = Quantity(
        type=np.float64,
        default=0.3333,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC/minute'},
        unit='kelvin/s',
    )
    target_ramp_rate = Quantity(
        type=np.float64,
        default=1,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W/second'},
        unit='(kg*m^2)/s^4',
    )
    active_targets = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    active_gases = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
    )
    total_deposition_rate = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'angstrom/s'},
        unit='m/s',
    )


class DTUsputter_parameters(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    chamber = SubSection(
        section_def=Chamber,
    )
    substrate = SubSection(
        section_def=Substrate,
    )
    S_cracker = SubSection(
        section_def=SCracker,
    )
    special = SubSection(
        section_def=Special,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUsputter_parameters` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class DTUsource(PVDSource, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    source_shutter_open = Quantity(
        type=bool,
        default=False,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )

    power_type = Quantity(
        type=MEnum(['RF', 'DC', 'pulsed_DC']),
        default='RF',
        a_eln={'component': 'RadioEnumEditQuantity'},
    )
    applied_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
    )
    applied_power = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'W'},
        unit='(kg*m^2)/s^3',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUsource` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


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


class DTUChamberEnvironment(ChamberEnvironment, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    gas_flow = SubSection(
        section_def=DTUGasFlow,
        repeats=True,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUChamberEnvironment` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class DTUsteps(PVDStep, ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    m_def = Section()
    sources = SubSection(
        section_def=DTUsource,
        repeats=True,
    )
    sputter_parameters = SubSection(
        section_def=DTUsputter_parameters,
        repeats=True,
    )
    environment = SubSection(
        section_def=DTUChamberEnvironment,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUsteps` class.

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
    Heater_temperature = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'degC'},
        unit='kelvin',
    )
    time_in_chamber_after_ending_deposition = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'minute'},
        unit='s',
    )
    chamber_purged = Quantity(
        type=bool,
        default=False,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )


class AdjustedInstrumentParameters(InstrumentReference, ArchiveSection):
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
        The normalizer for the `AdjustedInstrumentParameters` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.reference is not None:
            self.lab_id = self.reference.lab_id
            self.name = self.reference.name


class GunOverview(ArchiveSection):
    """
    Class autogenerated from yaml schema.
    """

    target_material = Quantity(
        type=str,
        a_eln={'component': 'StringEditQuantity'},
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
    stable_average_voltage = Quantity(
        type=np.float64,
        a_eln={'component': 'NumberEditQuantity', 'defaultDisplayUnit': 'V'},
        unit='V',
    )
    comments_about_voltage = Quantity(
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
    deposition_temperature = Quantity(
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
    h2s_in_Ar_flow = Quantity(
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
    ph3_in_Ar_flow = Quantity(
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
    heating_procedure_description = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
    )
    cooling_procedure_description = Quantity(
        type=str,
        a_eln={'component': 'RichTextEditQuantity'},
    )
    Magkeeper3 = SubSection(
        section_def=GunOverview,
    )
    Magkeeper4 = SubSection(
        section_def=GunOverview,
    )
    Taurus = SubSection(
        section_def=GunOverview,
    )
    SCracker = SubSection(
        section_def=SCracker,
    )
    used_gases = SubSection(
        section_def=UsedGas,
        repeats=True,
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
            if self.h2s_in_Ar_flow is not None:
                flow += self.h2s_in_Ar_flow.magnitude
                h2s = self.h2s_in_Ar_flow.magnitude
                if self.ph3_in_Ar_flow is not None:
                    flow += self.ph3_in_Ar_flow.magnitude
                    ph3 = self.ph3_in_Ar_flow.magnitude
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
    samples = SubSection(
        section_def=DTUsamples,
        repeats=True,
    )
    steps = SubSection(
        section_def=DTUsteps,
        repeats=True,
    )
    end_of_process = SubSection(
        section_def=EndOfProcess,
    )
    instruments = SubSection(
        section_def=AdjustedInstrumentParameters,
        repeats=True,
    )
    deposition_parameters = SubSection(
        section_def=DepositionParameters,
    )

    def plot(self, events_plot, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        # Plotting the events on a timeline from the plot_plotly_extimeline function
        try:
            timeline = plot_plotly_extimeline(events_plot, self.lab_id)

            # Converting the timeline to a plotly json
            timeline_json = timeline.to_plotly_json()
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
        except Exception as e:
            logger.warning(f'Failed to plot the events: {e}')

        # # Plotting the sample positions on the platen
        # try:
        #     samples_plot = read_samples(self.samples)
        #     dep_params: DepositionParameters = self.deposition_parameters
        #     guns_plot = read_guns(
        #         [
        #             dep_params.Magkeeper3,
        #             dep_params.Magkeeper4,
        #             dep_params.Taurus,
        #             dep_params.SCracker,
        #         ],
        #         ['Magkeeper3', 'Magkeeper4', 'Taurus', 'SCracker'],
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

        gun_list = ['Magkeeper3', 'Magkeeper4', 'Taurus']

        # Mapping the params to the respective sections
        param_nomad_map = map_params_to_nomad(params, gun_list)

        # Initializing a temporary class objects
        sputtering = DTUSputtering()
        sputtering.samples = []
        sputtering.steps = []
        sputtering.deposition_parameters = DepositionParameters()

        for gun in gun_list:
            if params['deposition'].get(gun, {}).get('enabled', False):
                setattr(sputtering.deposition_parameters, gun, GunOverview())

        sputtering.deposition_parameters.SCracker = SCracker()
        sputtering.end_of_process = EndOfProcess()

        # Writing the params dict in the form of a report
        sputtering.log_file_report = write_params(params)

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
        instrument_reference = AdjustedInstrumentParameters()
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
            step = DTUsteps()

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

            step.environment = DTUChamberEnvironment()

            environment = self.generate_environment_log_data(step_params, key, logger)

            step.environment = environment

            steps.append(step)

        return steps

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

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSputtering` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)

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
            # self.figures = []
            # self.plot(events_plot, archive, logger)

            # sample_number = len(self.samples)
            # j = 0
            # for j in range(sample_number):
            #    sample_name = (
            # str(self.name) + '_' + str(self.samples[j].relative_position))
            #    self.samples[j].name = sample_name
            #    self.samples[j].lab_id = sample_name


m_package.__init_metainfo__()
