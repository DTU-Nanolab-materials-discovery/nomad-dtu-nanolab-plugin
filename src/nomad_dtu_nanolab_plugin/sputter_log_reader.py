"""
Created on Fri Jun  7 10:46:17 2024

@author: eugbe

"""
# ---------PACKAGES-------------

import copy
import operator
import os
import re
from functools import reduce

import pandas as pd
import plotly.express as px
from mendeleev import element

# ---------REFERENCE VALUES-------------
# Set of reference values used in different parts of the script
# Proportion of values needed to be above the threshold to consider the
# plasma rf or dc
TOLERANCE = 0.85
# Eletrical current threshold above which a dc plasma is considered on
CURRENT_THRESHOLD = 0.01  # miliamps
# Bias threshold above which a rf plasma is considered on
BIAS_THRESHOLD = 0.01  # volts
# Power setpoint difference threshold above which a
# plasma is considered ramping up
POWER_SETPOINT_DIFF_THRESHOLD = 0.01  # watts
# Temperature setpoint difference threshold above which the
# substrate temp is considered ramping up
TEMP_SETPOINT_DIFF_THRESHOLD = 0.11  # degrees
# Temperature setpoint of cracker's zones above which the
# the cracker is considered on
CRACKER_ZONE_1_MIN_TEMP = 70  # degrees
CRACKER_ZONE_2_MIN_TEMP = 150  # degrees
CRACKER_ZONE_3_MIN_TEMP = 200  # degrees
# Temperature below which the deposition is considered room temperature
RT_TEMP_THRESHOLD = 30  # degrees
# Time for the qcm to stabilize after the Xtal 2 shutter opens
STAB_TIME = 30  # seconds
# Threshold above which the flow of the mfc is considered on
MFC_FLOW_THRESHOLD = 1  # sccm
# Fraction of the length of the deposition dataframe to consider for the
# beginning and end of the deposition voltage averaging
FRAQ_ROWS_AVG_VOLTAGE = 5  # %
# Number of timesteps to consider for the continuity limit
CONTINUITY_LIMIT = 10
# Special continuity limit for deposition events
DEPOSITION_CONTINUITY_LIMIT = 200
# Minimum size of a domain in terms of numbers of average timestep
MIN_DOMAIN_SIZE = 10
# Minimum size of a deposition in terms of numbers of average timestep
MIN_DEPOSITION_SIZE = 60
# Minimum size for the temp ramp down events
MIN_TEMP_RAMP_DOWN_SIZE = 100
# Size of the temperature control domains above which we consider that the
# temperature control makes a domain
MIN_TEMP_CTRL_SIZE = 20
# Max pressure to read the base pressure
MAX_BASE_PRESSURE = 1e-6  # Torr
# variation in percent to consider that the cracker temperature is the same
# as the cracker temperature during deposition to read the cracker induced
# base pressure
WITHIN_RANGE_PARAM = 5  # %
# FWD and RFL Power difference threshold above which the plasma is considered
# on
POWER_FWD_REFL_THRESHOLD = 10  # watts
# Categories of events to be considered in the main report
CATEGORIES_MAIN_REPORT = [
    'deposition',
    'ramp_up_temp',
    'ramp_down_high_temp',
    'source_presput',
    'source_ramp_up',
    'cracker_base_pressure',
    'source_deprate2_film_meas',
]
# Categories of events to select the last event before the deposition, if possible
CATEGORIES_LAST_EVENT = ['source_deprate2_film_meas', 'ramp_up_temp', 'source_ramp_up']
# Categories of events to put in the bottom of the timeline plot
CATEGORIES_FIRST = {
    'deposition',
    'ramp_up_temp',
    'ramp_down_high_temp',
    'ramp_down_low_temp',
}
# Define a dictionary for step colors in the timeline plot
STEP_COLORS = {
    'Deposition': 'blue',
    'Sub Temp Ramp Up': 'green',
    'Sub High Temp Ramp Down': 'red',
    'Sub Low Temp Ramp Down': 'pink',
    'Source 4 Ramp Up': 'purple',
    'Source 4 On': '#EE82EE',  # Violet
    'Source 4 On Open': '#FF00FF',  # Fuchsia
    'Source 4 Presput': 'magenta',
    'Source 4 Film Dep Rate Meas': '#DA70D6',  # Orchid
    'Source 3 Ramp Up': 'blue',
    'Source 3 On': '#1E90FF',  # Dodger Blue
    'Source 3 On Open': '#6495ED',  # Cornflower Blue
    'Source 3 Presput': '#87CEFA',  # Light Sky Blue
    'Source 3 Film Dep Rate Meas': '#4682B4',  # Steel Blue
    'Source 1 Ramp Up': '#006400',  # Dark Green
    'Source 1 On': 'green',
    'Source 1 On Open': '#008000',  # Green
    'Source 1 Presput': '#90EE90',  # Light Green
    'Source 1 Film Dep Rate Meas': '#32CD32',  # Lime Green
    'All Source Film Dep Rate Meas': 'grey',
    'Cracker On Open': '#CCCC00',
    'H2S On': 'orange',
    'PH3 On': 'cyan',
    'Ar On': 'black',
    'S Dep Rate Meas': '#B22222',  # Firebrick
    'Cracker Pressure Meas': 'brown',
}
source_name = {'1': 'Taurus', '3': 'Magkeeper3', '4': 'Magkeeper4', 'all': 'All'}

##------EVENT CLASS DEFINITION------


class Lf_Event:
    def __init__(self, name: str, source=None, category=None, step_number=None):
        self.name = name
        self.category = category
        self.source = source
        self.step_number = step_number
        self.step_id = category
        if category != 'deposition':
            if source is not None:
                self.step_id += f'_s{source}'
            if step_number is not None:
                self.step_id += f'_n{step_number}'
        self.avg_timestep = None
        self.cond = pd.DataFrame()
        self.data = pd.DataFrame()
        self.bounds = []
        self.events = 0
        self.sep_data = [pd.DataFrame()]
        self.sep_name = ['']
        self.sep_bounds = []

    def set_data(self, data, raw_data, continuity_limit=CONTINUITY_LIMIT):
        self.data = data
        self.avg_timestep = cal_avg_timestep(raw_data)
        self.bounds = self.extract_domains(continuity_limit)
        self.update_events_and_separated_data()

    def set_bounds(self, bounds):
        self.bounds = bounds
        self.update_events_and_separated_data()

    def update_events_and_separated_data(self):
        """Helper method to update events, sep_data, sep_name, and sep_bounds after
        bounds change."""
        self.events = len(self.bounds)
        self.sep_data = [event_filter(self.data, bound) for bound in self.bounds]
        self.sep_name = [f'{self.name}({i})' for i in range(self.events)]
        self.sep_bounds = [self.bounds[i] for i in range(self.events)]

    # def _generate_sep_data(self):
    #     return

    # def _generate_sep_name(self):
    #     return [f'{self.name}({i})' for i in range(self._events)]

    # def _generate_sep_bounds(self):
    #     return [self._bounds[i] for i in range(self._events)]
    def extract_domains(self, continuity_limit, timestamp_col='Time Stamp'):
        """
        This function extracts the bounds of continuous time domains in a
        DataFrame based on the time continuity
        For example, if the time difference between two consecutive
        timestamps of df1 is greater than the avg_timestep of df2,
        then the two timestamps are considered to be in
        different timedomains.
        """

        if self.data.empty:
            return []
        else:
            # work on a copy of the DataFrame
            df3 = pd.DataFrame()
            # Set the continuity limit as CONTINUITY_LIMIT the average time step
            continuity_time = continuity_limit * self.avg_timestep
            # Parse the timestamps in df
            df3[timestamp_col] = pd.to_datetime(
                self.data[timestamp_col], format='%b-%d-%Y %I:%M:%S.%f %p'
            )
            # Calculate the time differences between consecutive timestamps
            df3['time_diff'] = df3[timestamp_col].diff()
            # Identify the points where the discontinuity is
            # greater than the continuity limit
            discontinuities = df3['time_diff'] > continuity_time
            # Extract the bounds of the continuous domains
            bounds = []
            start_idx = 0
            for i in range(1, len(self.data)):
                if discontinuities.iloc[i]:
                    end_idx = i - 1
                    bounds.append(
                        (
                            self.data[timestamp_col].iloc[start_idx],
                            self.data[timestamp_col].iloc[end_idx],
                        )
                    )
                    start_idx = i
            # Add the last continuous domain
            bounds.append(
                (
                    self.data[timestamp_col].iloc[start_idx],
                    self.data[timestamp_col].iloc[-1],
                )
            )
            # remove all the bounds that are less than a certain time
            # interval to only keep big domains
            bounds = [
                bound
                for bound in bounds
                if (bound[1] - bound[0]) > MIN_DOMAIN_SIZE * self.avg_timestep
            ]
            return bounds

    def filter_data(self, raw_data):
        if not self.cond.empty:
            self.avg_timestep = cal_avg_timestep(raw_data)
            filtered_data = raw_data[self.cond]
            self.set_data(filtered_data, raw_data)
        else:
            print(f'Error: Unable to filter. No condition set for event {self.name}')

    def set_condition(self, condition):
        self.cond = condition

    def set_source(self, source):
        self.source = source

    def set_name(self, name):
        self.name = name

    def set_category(self, category):
        self.category = category

    def stitch_source_ramp_up_events(self):
        i = 0
        while i < len(self.bounds) - 1:
            # Find the timestamps of the end of the first event and the start of
            # the next event
            end_timestamp = self.bounds[i][1]
            start_timestamp_next = self.bounds[i + 1][0]

            # Convert timestamps to integer indices
            try:
                end_index = self.data[self.data['Time Stamp'] == end_timestamp].index[0]
                start_index_next = self.data[
                    self.data['Time Stamp'] == start_timestamp_next
                ].index[0]
            except IndexError:
                print(f'Error: Unable to stitch events for {self.name}')
                return

            # Check if the output setpoint power value of the first event is the
            # same as the next event
            if (
                self.data[f'Source {self.source} Output Setpoint'].loc[end_index]
                == self.data[f'Source {self.source} Output Setpoint'].loc[
                    start_index_next
                ]
            ):
                # If so, merge the two events
                self.bounds[i] = (
                    self.bounds[i][0],
                    self.bounds[i + 1][1],
                )
                self.bounds.pop(i + 1)
            else:
                i += 1  # Only increment i if no merge occurred
        self.update_events_and_separated_data()

    def filter_out_small_events(self, min_domain_size):
        data_list = []
        for i in range(self.events):
            if len(self.sep_data[i]) > min_domain_size:
                data_list.append(self.sep_data[i])

        # Concatenate the list of DataFrames
        data = pd.concat(data_list, ignore_index=True)
        self.set_data(data, data)

    def select_event(self, raw_data, event_loc: int, ref_time=None):
        event_list = []
        if ref_time is None:
            ref_time = self.data['Time Stamp'].iloc[-1]
        for i in range(self.events):
            if self.bounds[i][1] < ref_time:
                event_list.append(self.sep_data[i])
        self.set_data(event_list[event_loc], raw_data)

    def get_params(self, raw_data, source_list, params=None):
        if self.category == 'deposition':
            params = self.get_all_deposition_params(
                source_list, raw_data, params=params
            )
        if self.category == 'ramp_up_temp':
            params = self.get_sub_ramp_up_params(raw_data, params=params)
        if self.category == 'ramp_down_high_temp':
            params = self.get_sub_ramp_down_high_temp_params(params=params)
        if self.category == 'ramp_down_low_temp':
            params = self.get_sub_ramp_down_low_temp_params(params=params)
        if self.category == 'source_presput':
            params = self.get_source_presput_params(params=params)
        if self.category == 'source_ramp_up':
            params = self.get_source_ramp_up_params(raw_data, params=params)
        if self.category == 'cracker_base_pressure':
            params = self.get_cracker_pressure_params(params=params)
        if self.category == 'source_deprate2_film_meas':
            params = self.get_deposition_rate_params(params=params)
        return params

    def get_nomad_step_params(self, params=None, source_list = None):
        #Set a default value for the source list
        if source_list is None:
            source_list = [self.source]
        #Initialize the params dictionary if it is not provided
        if params is None:
            params = {}
        # Write the event step_id as the key of the dictionary
        if self.step_id not in params:
            params[self.step_id] = {}
            params[self.step_id]['sources'] = {}

        for source_number in source_list:
            source_key = f'{source_name[str(source_number)]}'
            if source_key not in params[self.step_id]['sources']:
                params[self.step_id][
                    'sources'
                    ][f'{source_name[str(source_number)]}'] = {}

        params[self.step_id]['name'] = self.name
        params[self.step_id]['lab_id'] = self.step_id
        params[self.step_id]['category'] = self.category
        # Extract the start and end time, and duration of the event
        params[self.step_id]['start_time'] = self.data['Time Stamp'].iloc[0]
        params[self.step_id]['end_time'] = self.data['Time Stamp'].iloc[-1]
        params[self.step_id]['duration'] = (
            params[self.step_id]['end_time'] - params[self.step_id]['start_time']
        )
        params[self.step_id]['creates_new_thin_film'] = (self.category == 'deposition')

        return params

    def get_all_deposition_params(self, source_list, raw_data, params=None):
        if self.category != 'deposition':
            raise ValueError('This method is only available for the deposition event')

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        params = self.get_rt_bool(params=params)
        params = self.get_source_used_deposition(source_list, params=params)
        params = self.get_cracker_params(params=params)
        params = self.get_pressure_params(raw_data, params=params)
        params = self.get_simple_deposition_params(params=params)
        params = self.get_source_depostion_params(source_list, params=params)
        return params

    def get_rt_bool(self, params=None):
        # Extract if the deposition was done at room temperature as :
        # - the temperature control is disabled or
        # - the temperature control is enabled but the temperature setpoint
        # is below the RT threshold defined in the reference values
        if self.category != 'deposition':
            raise ValueError

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if (
            self.data['Substrate Heater Temperature Setpoint'] < RT_TEMP_THRESHOLD
        ).all():
            params[self.category]['rt'] = True
        elif (
            self.data['Substrate Heater Temperature Setpoint'] > RT_TEMP_THRESHOLD
        ).all():
            params[self.category]['rt'] = False
        return params

    def get_source_used_deposition(self, source_list, params=None):
        # Extract the source used for deposition
        # For all sources, we check if the source is enabled during deposition
        # and if it is, we set the source as the source enabled for deposition
        # which implies that the source was also ramped up and presputtered
        if self.category != 'deposition':
            raise ValueError('This method is only available for the deposition event')

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}
        for source_number in source_list:
            if f'{source_name[str(source_number)]}' not in params[self.category]:
                params[self.category][f'{source_name[str(source_number)]}'] = {}

        for source_number in source_list:
            if (
                not self.data.get(
                    f'Source {source_number} Enabled', pd.Series([0] * len(self.data))
                ).all()
                == 0
            ):
                params[self.category][f'{source_name[str(source_number)]}'][
                    'enabled'
                ] = True
            else:
                params[self.category][f'{source_name[str(source_number)]}'][
                    'enabled'
                ] = False

        return params

    def get_cracker_params(self, params=None):
        # Extract if the cracker has been used during deposition as the
        # cracker control being enabled and the temperatures of the
        # different zones being above the minimum temperatures
        # defined in the reference values

        if self.category != 'deposition':
            raise ValueError('This method is only available for the deposition event')
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}
        if 'SCracker' not in params[self.category]:
            params[self.category]['SCracker'] = {}

        if 'Sulfur Cracker Zone 1 Current Temperature' in self.data.columns:
            if (
                (self.data['Sulfur Cracker Control Enabled'] == 1).mean() >= TOLERANCE
                and (
                    self.data['Sulfur Cracker Zone 1 Current Temperature']
                    > CRACKER_ZONE_1_MIN_TEMP
                ).all()
                and (
                    self.data['Sulfur Cracker Zone 2 Current Temperature']
                    > CRACKER_ZONE_2_MIN_TEMP
                ).all()
                and (
                    self.data['Sulfur Cracker Zone 3 Current Temperature']
                    > CRACKER_ZONE_3_MIN_TEMP
                ).all()
            ):
                params[self.category]['SCracker']['enabled'] = True
                params[self.category]['SCracker']['zone1_temp'] = self.data[
                    'Sulfur Cracker Zone 1 Current Temperature'
                ].mean()
                params[self.category]['SCracker']['zone2_temp'] = self.data[
                    'Sulfur Cracker Zone 2 Current Temperature'
                ].mean()
                params[self.category]['SCracker']['zone3_temp'] = self.data[
                    'Sulfur Cracker Zone 3 Current Temperature'
                ].mean()
                params[self.category]['SCracker']['pulse_width'] = self.data[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].mean()
                params[self.category]['SCracker']['pulse_freq'] = self.data[
                    'Sulfur Cracker Control Setpoint Feedback'
                ].mean()
            else:
                params[self.category]['SCracker']['enabled'] = False
        else:
            params[self.category]['SCracker']['enabled'] = False
        return params

    def get_pressure_params(self, raw_data, params=None):
        # Extract the some base pressure metric as the lowest positive
        # pressure recorded before deposition (but only if
        # it is below 1-6Torr). If the cracker is enabled, then this metric is not
        # representative of the true base pressure and we set the
        # true_base_pressure_meas to False to indicate that the true base
        # pressure is not measured accurately: If the cracker is not enabled,
        # then the base pressure is measured accurately and we set the
        # true_base_pressure_meas to True

        if self.category != 'deposition':
            raise ValueError('This method is only available for the deposition event')

        if params is None:
            params = {}
        if 'overview' not in params:
            params['overview'] = {}
        if 'deposition' not in params:
            raise ValueError('Missing deposition info, run get_cracker_params first')

        min_pressure_before_depostion = raw_data.loc[
            pd.to_datetime(raw_data['Time Stamp'])
            <= pd.to_datetime(self.data['Time Stamp'].iloc[0]),
            'PC Wide Range Gauge',
        ].min()

        params['overview']['lower_pressure_before_deposition'] = (
            min_pressure_before_depostion
        )
        if min_pressure_before_depostion < MAX_BASE_PRESSURE:
            if not params[self.category]['SCracker']['enabled']:
                params['overview']['true_base_pressure_meas'] = True
            elif params[self.category]['SCracker']['enabled']:
                params['overview']['true_base_pressure_meas'] = False
        else:
            params['overview']['true_base_pressure_meas'] = False

        return params

    def get_simple_deposition_params(self, params=None):
        if self.category != 'deposition':
            raise ValueError('This method is only available for the deposition event')

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        # Extract the platen position during deposition
        if 'Substrate Rotation_Position' in self.data:
            params[self.category]['platen_position'] = self.data[
                'Substrate Rotation_Position'
            ].mean()

        # Extract start and end time of the deposition
        params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
        params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]
        params[self.category]['duration'] = (
            params[self.category]['end_time'] - params[self.category]['start_time']
        )

        # Extract average temperature during deposition
        params[self.category]['avg_temp_1'] = self.data[
            'Substrate Heater Temperature'
        ].mean()
        params[self.category]['avg_temp_2'] = self.data[
            'Substrate Heater Temperature 2'
        ].mean()
        params[self.category]['avg_temp_setpoint'] = self.data[
            'Substrate Heater Temperature Setpoint'
        ].mean()

        # Extract the average true temperature during deposition
        params[self.category]['avg_true_temp'] = calculate_avg_true_temp(
            params[self.category]['avg_temp_1'], params[self.category]['avg_temp_2']
        )

        # Extract average sputter PC Capman pressure during deposition
        params[self.category]['avg_capman_pressure'] = self.data[
            'PC Capman Pressure'
        ].mean()

        # Extract the MF1 Ar, MFC4 PH3 and MFC6 H2S flow during deposition
        # only if the flow is above 1sccm, if not we set the flow to 0
        params[self.category]['avg_ar_flow'] = (
            self.data[self.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD][
                'PC MFC 1 Flow'
            ].mean()
            if not self.data[self.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD][
                'PC MFC 1 Flow'
            ].empty
            else 0
        )
        params[self.category]['avg_ph3_flow'] = (
            self.data[self.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD][
                'PC MFC 4 Flow'
            ].mean()
            if not self.data[self.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD][
                'PC MFC 4 Flow'
            ].empty
            else 0
        )
        params[self.category]['avg_h2s_flow'] = (
            self.data[self.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD][
                'PC MFC 6 Flow'
            ].mean()
            if not self.data[self.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD][
                'PC MFC 6 Flow'
            ].empty
            else 0
        )

        return params

    def get_source_depostion_params(self, source_list, params=None):
        if self.category != 'deposition':
            raise ValueError('This method is only available for the deposition event')

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}
        elements = []
        for source_number in source_list:
            if params[self.category][f'{source_name[str(source_number)]}']['enabled']:
                params = self.get_avg_output_power(params, source_number)
                params = self.get_plasma_type(params, source_number)
                params = self.get_deposition_voltage(params, source_number)
                params, elements = self.get_source_material_and_target(
                    params, source_number, elements
                )
                # Extract source material and target id and add the element to the
                # elements list for the material space extraction
        # Extract the material space as the elements used during deposition
        if params[self.category]['avg_ph3_flow'] > MFC_FLOW_THRESHOLD:
            elements = elements + ['P']
        if (params[self.category]['avg_h2s_flow'] > MFC_FLOW_THRESHOLD) or (
            params[self.category]['SCracker']['enabled']):
            elements = elements + ['S']
        # add the element as an hypen separated string
        params[self.category]['material_space'] = '-'.join(elements)
        return params

    def get_avg_output_power(self, params, source_number):
        params[self.category][f'{source_name[str(source_number)]}'][
            'avg_output_power'
        ] = self.data[f'Source {source_number} Output Setpoint'].mean()
        return params

    def get_plasma_type(self, params, source_number):
        dc_current_col = f'Source {source_number} Current'
        rf_bias_col = f'Source {source_number} DC Bias'
        pulse_enable_col = f'Source {source_number} Pulse Enabled'
        fwd_power_col = f'Source {source_number} Fwd Power'
        rfl_power_col = f'Source {source_number} Rfl Power'

        # We tolerate a certain percentage of the data to be below the threshold
        if dc_current_col in self.data and (
            (self.data[dc_current_col] > CURRENT_THRESHOLD).mean() >= TOLERANCE
            or (
                (self.data[fwd_power_col] - self.data[rfl_power_col])
                > POWER_FWD_REFL_THRESHOLD).mean() >= TOLERANCE
        ):
            params[self.category][f'{source_name[str(source_number)]}']['DC'] = True
            params[self.category][f'{source_name[str(source_number)]}']['RF'] = False
            if pulse_enable_col in self.data:
                params[self.category][f'{source_name[str(source_number)]}'][
                    'pulsed'
                ] = self.data[pulse_enable_col].all() == 1
                if params[self.category][f'{source_name[str(source_number)]}'][
                    'pulsed'
                ]:
                    params[self.category][f'{source_name[str(source_number)]}'][
                        'plasma_type'
                    ] = 'pulsed_DC'
                    params[self.category][f'{source_name[str(source_number)]}'][
                        'pulse_frequency'
                    ] = self.data[f'Source {source_number} Pulse Frequency'].mean()
                    params[self.category][f'{source_name[str(source_number)]}'][
                        'dead_time'
                    ] = self.data[f'Source {source_number} Reverse Time'].mean()
                else:
                    params[self.category][
                        f'{source_name[str(source_number)]}'
                        ]['pulsed'] = False
                    params[self.category][
                        f'{source_name[str(source_number)]}'
                        ]['plasma_type'] = 'DC'
        elif rf_bias_col in self.data and (
            (self.data[rf_bias_col] > BIAS_THRESHOLD).mean() >= TOLERANCE
            or (
                (self.data[fwd_power_col] - self.data[rfl_power_col])
                > POWER_FWD_REFL_THRESHOLD).mean() >= TOLERANCE
            ):
            params[self.category][f'{source_name[str(source_number)]}']['RF'] = True
            params[self.category][
                f'{source_name[str(source_number)]}'
                ]['plasma_type'] = 'RF'
            params[self.category][f'{source_name[str(source_number)]}']['DC'] = False
            params[self.category][
                f'{source_name[str(source_number)]}'
                ]['pulsed'] = False
        else:
            print('Error: Plasma type not recognized')


        return params

    def get_deposition_voltage(self, params, source_number):
        def extract_voltage_stats(data, key_prefix):
            return {
                'start_voltage': data.iloc[
                    : int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(data))
                ].mean(),
                'end_voltage': data.iloc[
                    -int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(data)) :
                ].mean(),
                'avg_voltage': data.mean(),
                'min_voltage': data.min(),
                'max_voltage': data.max(),
                'std_voltage': data.std(),
            }

        source_key = f'{source_name[f"{source_number}"]}'
        category = params[self.category][source_key]

        if category['DC']:
            voltage_data = self.data[f'Source {source_number} Voltage']
        elif category['RF']:
            voltage_data = self.data[f'Source {source_number} DC Bias']
        else:
            return params

        voltage_stats = extract_voltage_stats(voltage_data, source_key)
        for key, value in voltage_stats.items():
            category[key] = value

        return params

    def get_source_material_and_target(self, params, source_number, elements):
        source_element = str(self.data[f'PC Source {source_number} Material'].iloc[0])
        source_element = re.split(r'\s+', source_element)[0]
        params[self.category][f'{source_name[str(source_number)]}']['material'] = (
            element(source_element).symbol
        )
        params[self.category][f'{source_name[str(source_number)]}']['target_id'] = (
            self.data[f'PC Source {source_number} Loaded Target'].iloc[0]
        )
        elements.append(element(source_element).symbol)

        return params, elements

    def get_cracker_pressure_params(self, params=None):
        if self.category != 'cracker_base_pressure':
            raise ValueError

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        # Extract the S induced base pressure as the mean pressure during
        # the cracker being on and no gas being flown
        if not self.data.empty:
            params[self.category]['cracker_pressure_meas'] = True
            params[self.category]['cracker_pressure'] = self.data[
                'PC Wide Range Gauge'
            ].mean()
        else:
            params['cracker_pressure_meas'] = False
        return params

    def get_source_presput_params(self, params=None):
        if self.category != 'source_presput':
            raise ValueError(
                'This method is only available for the source presput event'
            )

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        source_number = self.source
        if f'{source_name[str(source_number)]}' not in params[self.category]:
            params[self.category][f'{source_name[str(source_number)]}'] = {}

        # We check if the source is enabled during deposition
        if params['deposition'][f'{source_name[str(source_number)]}']['enabled']:
            # ----source presputtering parameters-----
            # Extract the presputtering duration
            presput_duration = 0
            for i in range(len(self.bounds)):
                presput_duration += (
                    self.bounds[i][1] - self.bounds[i][0]
                ).total_seconds()
            presput_duration = pd.to_timedelta(presput_duration, unit='s')
            params[self.category][f'{source_name[str(source_number)]}']['duration'] = (
                presput_duration
            )
            # Extract the average output power during presputtering
            params[self.category][f'{source_name[str(source_number)]}'][
                'avg_output_power'
            ] = self.data[f'Source {source_number} Output Setpoint'].mean()
            # Extract the avg capman pressure during presputtering
            params[self.category][f'{source_name[str(source_number)]}'][
                'avg_capman_pressure'
            ] = self.data['PC Capman Pressure'].mean()
            # Extract the gas flows during presputtering
            params[self.category][f'{source_name[str(source_number)]}'][
                'avg_ar_flow'
            ] = self.data['PC MFC 1 Flow'].mean()
        return params

    def get_source_ramp_up_params(self, raw_data, params=None):
        # Here, we interate over the sources to extract many relevant parameters

        if self.category != 'source_ramp_up':
            raise ValueError(
                'This method is only available for the source ramp up event'
            )

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        source_number = self.source
        if f'{source_name[str(source_number)]}' not in params[self.category]:
            params[self.category][f'{source_name[str(source_number)]}'] = {}
        # We check if the source is enabled during deposition
        if params['deposition'][f'{source_name[str(source_number)]}']['enabled']:
            # Extract the plasma ignition power as the power at which
            # the plasma really ignites
            # We first filter only the last [-1] source ramp up event with the
            # event filter function
            current_series = raw_data.get(
                f'Source {source_number} Current', pd.Series([0] * len(raw_data))
            )
            bias_series = raw_data.get(
                f'Source {source_number} DC Bias', pd.Series([0] * len(raw_data))
            )
            fwd_power_series = raw_data.get(
                f'Source {source_number} Fwd Power', pd.Series([0] * len(raw_data))
            )
            rfl_power_series = raw_data.get(
                f'Source {source_number} Rfl Power', pd.Series([0] * len(raw_data))
            )
            # Create a boolean mask for the conditions
            mask = (
                (current_series > CURRENT_THRESHOLD)
                | (bias_series > BIAS_THRESHOLD)
                | ((fwd_power_series - rfl_power_series) > POWER_FWD_REFL_THRESHOLD)
            )
            # Apply the mask to get the moment where the plasma is on during
            # ramp up
            data_ignition_time = self.data.loc[mask]
            # If the plasma turns on during ramp up, data_ignition_time should
            # not be empty
            if not data_ignition_time.empty:
                ignition_time = data_ignition_time['Time Stamp'].iloc[0]
                params[self.category][f'{source_name[str(source_number)]}'][
                    'ignition'
                ] = True
                params[self.category][f'{source_name[str(source_number)]}'][
                    'ignition_time'
                ] = ignition_time
                ignition_data = self.data[self.data['Time Stamp'] == ignition_time]
                params[self.category][f'{source_name[str(source_number)]}'][
                    'ignition_power'
                ] = ignition_data[f'Source {source_number} Output Setpoint'].iloc[0]
                params[self.category][f'{source_name[str(source_number)]}'][
                    'ignition_pressure'
                ] = ignition_data['PC Capman Pressure'].iloc[0]
            else:
                params[self.category][f'{source_name[str(source_number)]}'][
                    'source_ignition'
                ] = False

        return params

    def get_sub_ramp_up_params(self, raw_data, params=None):
        if self.category != 'ramp_up_temp':
            raise ValueError(
                'This method is only available for the substrate ramp up event'
            )

        if 'deposition' not in params:
            raise ValueError('Missing deposition info, run get_rt_bool first')
        if self.category not in params:
            params[self.category] = {}
        if 'SCracker' not in params[self.category]:
            params[self.category]['SCracker'] = {}

        if not params['deposition']['rt']:
            # ------Extract the substrate ramp up parameters------
            # Extract the slope assuming linear ramp up
            # In data_ramp_up_temp only increasing setpoint temperature are
            # considered making easier to extract the slope
            params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
            params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]
            params[self.category]['duration'] = (
                params[self.category]['end_time'] - params[self.category]['start_time']
            )
            temp_diff = (
                self.data['Substrate Heater Temperature Setpoint'].iloc[-1]
                - self.data['Substrate Heater Temperature Setpoint'].iloc[0]
            )
            time_interval_minutes = (
                params[self.category]['duration'].total_seconds() / 60
            )
            params[self.category]['temp_slope'] = temp_diff / time_interval_minutes
            # Extract the average capman pressure during the ramp up
            params[self.category]['avg_capman_pressure'] = self.data[
                'PC Capman Pressure'
            ].mean()
            # Extract the gas flows during the substrate ramp up
            # If the flows are below the noise level threshold,
            # we set the flow to 0
            params[self.category]['avg_ar_flow'] = (
                self.data['PC MFC 1 Flow'].mean()
                if not self.data[self.data['PC MFC 1 Flow'] > 1]['PC MFC 1 Flow'].empty
                else 0
            )
            params[self.category]['avg_ph3_flow'] = (
                self.data['PC MFC 4 Flow'].mean()
                if not self.data[self.data['PC MFC 4 Flow'] > 1]['PC MFC 4 Flow'].empty
                else 0
            )
            params[self.category]['avg_h2s_flow'] = (
                self.data['PC MFC 6 Flow'].mean()
                if not self.data[self.data['PC MFC 6 Flow'] > 1]['PC MFC 6 Flow'].empty
                else 0
            )
            # Extract if the cracker has been used during ramp up
            # The column 'Sulfur Cracker Control Enabled' correspond to the
            # act of opening the cracker pulse valve (1 open, 0 closed)
            if 'Sulfur Cracker Zone 1 Current Temperature' in raw_data.columns:
                if (
                    (self.data['Sulfur Cracker Control Enabled'] == 1)
                    .mean() >= TOLERANCE
                    and (
                        self.data['Sulfur Cracker Zone 1 Current Temperature']
                        > CRACKER_ZONE_1_MIN_TEMP
                    ).all()
                    and (
                        self.data['Sulfur Cracker Zone 2 Current Temperature']
                        > CRACKER_ZONE_2_MIN_TEMP
                    ).all()
                    and (
                        self.data['Sulfur Cracker Zone 3 Current Temperature']
                        > CRACKER_ZONE_3_MIN_TEMP
                    ).all()
                ):
                    params[self.category]['SCracker']['enabled'] = True
                    # If the cracker has been used, extract the cracker parameters
                    params[self.category]['SCracker']['zone1_temp'] = self.data[
                        'Sulfur Cracker Zone 1 Current Temperature'
                    ].mean()
                    params[self.category]['SCracker']['zone2_temp'] = self.data[
                        'Sulfur Cracker Zone 2 Current Temperature'
                    ].mean()
                    params[self.category]['SCracker']['zone3_temp'] = self.data[
                        'Sulfur Cracker Zone 3 Current Temperature'
                    ].mean()
                    params[self.category]['SCracker']['pulse_width'] = self.data[
                        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                    ].mean()
                    params[self.category]['SCracker']['pulse_freq'] = self.data[
                        'Sulfur Cracker Control Setpoint Feedback'
                    ].mean()
                else:
                    params[self.category]['SCracker']['enabled'] = False
            else:
                params[self.category]['SCracker']['enabled'] = False
        return params

    def get_sub_ramp_down_params(self, params=None):
        if self.category != 'sub_ramp_down':
            raise ValueError(
                'This method is only available for the substrate ramp down event'
            )

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if not params['depostion']['rt']:
            # Extract the slope from when the temp in controled,
            # assuming linear ramp up
            # In data_ramp_down_temp only decreasing setpoint temperature are
            # considered making easier to extract the slope
            start_time = self.data['Time Stamp'].iloc[0]
            end_time = self.data['Time Stamp'].iloc[-1]
            time_interval = end_time - start_time
            temp_diff = -(
                self.data['Substrate Heater Temperature Setpoint'].iloc[-1]
                - self.data['Substrate Heater Temperature Setpoint'].iloc[0]
            )
            time_interval_minutes = time_interval.total_seconds() / 60
            params[self.category]['temp_slope'] = temp_diff / time_interval_minutes
            # Now we distinguish between the high temp and low temp ramp down phase
            # Extract the start time of the ramp down as the first time of
            # the high temperature ramp down and the end time as the last time of
            # the low temperature ramp down (which is the last time of the log)
            params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
            params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]
            params[self.category]['duration'] = (
                params[self.category]['end_time'] - params[self.category]['start_time']
            )
        return params

    def get_sub_ramp_down_high_temp_params(self, params=None):
        if self.category != 'ramp_down_high_temp':
            raise ValueError(
                'This method is only available for the high temperature '
                'substrate ramp down event'
            )
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if 'SCracker' not in params[self.category]:
            params[self.category]['SCracker'] = {}

        if 'deposition' not in params:
            raise ValueError('Missing deposition info, run get_rt_bool first')

        if not params['deposition']['rt']:
            params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
            params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]

            # Extract the start and end temperature of the
            # high temperature ramp down
            params[self.category]['start_setpoint_temp'] = self.data[
                'Substrate Heater Temperature Setpoint'
            ].iloc[0]
            params[self.category]['end_setpoint_temp'] = self.data[
                'Substrate Heater Temperature Setpoint'
            ].iloc[-1]

            # Extract the gases used during the high substrate ramp down
            params[self.category]['avg_ar_flow'] = (
                self.data[self.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD][
                    'PC MFC 1 Flow'
                ].mean()
                if not self.data[self.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD][
                    'PC MFC 1 Flow'
                ].empty
                else 0
            )
            params[self.category]['avg_ph3_flow'] = (
                self.data[self.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD][
                    'PC MFC 4 Flow'
                ].mean()
                if not self.data[self.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD][
                    'PC MFC 4 Flow'
                ].empty
                else 0
            )
            params[self.category]['avg_h2s_flow'] = (
                self.data[self.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD][
                    'PC MFC 6 Flow'
                ].mean()
                if not self.data[self.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD][
                    'PC MFC 6 Flow'
                ].empty
                else 0
            )
            # Extract if the cracker has been used during ramp down
            if 'Sulfur Cracker Zone 1 Current Temperature' in self.data.columns:
                if (
                    (self.data['Sulfur Cracker Control Enabled'] == 1).all()
                    and (
                        self.data['Sulfur Cracker Zone 1 Current Temperature']
                        > CRACKER_ZONE_1_MIN_TEMP
                    ).all()
                    and (
                        self.data['Sulfur Cracker Zone 2 Current Temperature']
                        > CRACKER_ZONE_2_MIN_TEMP
                    ).all()
                    and (
                        self.data['Sulfur Cracker Zone 3 Current Temperature']
                        > CRACKER_ZONE_3_MIN_TEMP
                    ).all()
                ):
                    params[self.category]['SCracker']['enabled'] = True
                    # if the crack has been used, extract the cracker parameters
                    params[self.category]['SCracker']['zone1_temp'] = self.data[
                        'Sulfur Cracker Zone 1 Current Temperature'
                    ].mean()
                    params[self.category]['SCracker']['zone2_temp'] = self.data[
                        'Sulfur Cracker Zone 2 Current Temperature'
                    ].mean()
                    params[self.category]['SCracker']['zone3_temp'] = self.data[
                        'Sulfur Cracker Zone 3 Current Temperature'
                    ].mean()
                    params[self.category]['SCracker']['pulse_width'] = self.data[
                        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                    ].mean()
                    params[self.category]['SCracker']['pulse_freq'] = self.data[
                        'Sulfur Cracker Control Setpoint Feedback'
                    ].mean()
                else:
                    params[self.category]['SCracker']['enabled'] = False
            else:
                params[self.category]['SCracker']['enabled'] = False
            # Extract the anion input cutoff temperature as the last temperature of
            # the high temperature ramp down
            params[self.category]['anion_input_cutoff_temp'] = self.data[
                'Substrate Heater Temperature Setpoint'
            ].iloc[-1]
            params[self.category]['anion_input_cutoff_time'] = self.data[
                'Time Stamp'
            ].iloc[-1]
        return params

    def get_sub_ramp_down_low_temp_params(self, params=None):
        if self.category != 'ramp_down_low_temp':
            raise ValueError(
                'This method is only available for',
                'the low temperature substrate ramp down event',
            )
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if 'deposition' not in params:
            raise ValueError('Missing deposition info, run get_rt_bool first')

        if not params['deposition']['rt']:
            params[self.category]['start'] = self.data['Time Stamp'].iloc[0]
            params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]
        return params

    def get_deposition_rate_params(self, params=None):
        list_allowed_categories = ['s_deprate2_film_meas', 'source_deprate2_film_meas']
        if self.category not in list_allowed_categories:
            raise ValueError(
                'This method is only available for the film deposition rate event'
            )

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if self.source is None:
            source_number = 'all'
        elif self.source is not None:
            source_number = self.source

        if source_name[str(source_number)] not in params[self.category]:
            params[self.category][source_name[str(source_number)]] = {}

        if self.source is not None:
            source_number = self.source
            source_element = str(
                self.data[f'PC Source {source_number} Material'].iloc[0]
            )
            source_element = re.split(r'\s+', source_element)[0]
            params[self.category][f'{source_name[str(source_number)]}']['material'] = (
                element(source_element).symbol
            )

        params[self.category][f'{source_name[str(source_number)]}']['dep_rate'] = (
            self.data['Thickness Rate'].mean()
        )
        params[self.category][f'{source_name[str(source_number)]}'][
            'dep_rate_ref_mat'
        ] = self.data['Thickness Active Material'].iloc[0]
        if 'Thickness Material Density' in self.data.columns:
            params[self.category][f'{source_name[str(source_number)]}'][
                'dep_rate_ref_density'
            ] = self.data['Thickness Material Density'].mean()
        if 'Thickness Material Z' in self.data.columns:
            params[self.category][f'{source_name[str(source_number)]}'][
                'dep_rate_ref_z'
            ] = self.data['Thickness Material Z'].mean()

        return params


# ---------FUNCTIONS DEFINITION------------

# ---------HELPERS FUNCTIONS FOR REPORT GENERATION------------


def get_overview(raw_data, params=None):
    if params is None:
        params = {}
    if 'overview' not in params:
        params['overview'] = {}

    # Extract sample name as the first 3 log file string when parsed by '_'
    # params['overview']['sample_name'] =

    # Extract start and end time of the log file
    params['overview']['log_start_time'] = raw_data['Time Stamp'].iloc[0]
    params['overview']['log_end_time'] = raw_data['Time Stamp'].iloc[-1]

    return params

def get_end_of_process(raw_data, params=None):
    # Extract the end of process temperature as the last temperature logged
    # Note: this part can be improved by extracting the temperature at
    # the vent recipe step
    if params is None:
        params = {}
    if 'overview' not in params:
        params['overview'] = {}

    if 'deposition' not in params:
        raise ValueError(
            'Missing deposition info, ' 'run get_simple_deposition_params first'
        )
    params['overview']['end_of_process_temp'] = raw_data[
        'Substrate Heater Temperature'
    ].iloc[-1]

    # Extract the time in chamber after deposition as the time difference
    # between end of logging and end of deposition time
    params['overview']['time_in_chamber_after_deposition'] = (
        params['overview']['log_end_time'] - params['deposition']['end_time']
    )
    return params


def save_report_as_text(params:dict, txt_file_path, logfile_name):
    # Save the derived quantities report as a text file as
    with open(txt_file_path, 'w') as txt_file:
        txt_file.write(f'Derived quantities report for logfile\n{logfile_name}:\n\n')
        txt_file.write(write_params(params))


# Function to convert timestamps to isoformat
def convert_timestamps(obj):
    if isinstance(obj, dict):
        return {k: convert_timestamps(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_timestamps(i) for i in obj]
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, pd.Timedelta):
        return str(obj)
    else:
        return obj


# Function to print the derived quantities in a nested format
def print_params(quantities, indent=''):
    for key, value in quantities.items():
        if isinstance(value, dict):
            print(f'{indent}{key}:')
            print_params(value, indent + '    ')
        else:
            formatted_value = value
            if isinstance(value, pd.Timestamp):
                if key in {'log_start_time', 'log_end_time'}:
                    formatted_value = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted_value = value.strftime('%H:%M:%S')
            elif isinstance(value, pd.Timedelta):
                total_seconds = int(value.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_value = f'{hours:02d}:{minutes:02d}:{seconds:02d}'

            print(f'{indent}{key}: {formatted_value}')


# Function to write the derived quantities in a nested format
def write_params(quantities, indent=''):
    output = []
    for key, value in quantities.items():
        if isinstance(value, dict):
            output.append(f'{indent}{key}:')
            output.append(write_params(value, indent + '    '))
        else:
            formatted_value = value
            if isinstance(value, pd.Timestamp):
                if key in {'log_start_time', 'log_end_time'}:
                    formatted_value = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted_value = value.strftime('%H:%M:%S')
            elif isinstance(value, pd.Timedelta):
                total_seconds = int(value.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                formatted_value = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
            output.append(f'{indent}{key}: {formatted_value}')
    return '\n'.join(output)


# ----------FUNCTION FOR READING THE LOGFILE------------


# Function to read the IDOL combinatorial chamber CSV logfile
def read_logfile(file_path):
    """
    This function reads a logfile and returns a DataFrame with the
    'Time Stamp' column converted to datetime format.
    All the logged values are stored in the DataFrame
    as they are in the logfile.
    """
    df = pd.read_csv(file_path, header=[1], skiprows=[0])
    df['Time Stamp'] = pd.to_datetime(
        df['Time Stamp'], format='%b-%d-%Y %I:%M:%S.%f %p'
    )
    # Ensure all timestamps in the log file and spectrum are tz-naive
    df['Time Stamp'] = df['Time Stamp'].dt.tz_localize(None)
    return df


# ----------FUNCTIONS FOR HANDLING TIMESTAMPS------------


# Function to calculate the average time step
# between consecutive timestamps in a DataFrame
def cal_avg_timestep(df, timestamp_col='Time Stamp'):
    """
    This function calculates the average time step between consecutive
    timestamps in a DataFrame.
    """
    # work on a copy of the DataFrame
    df2 = pd.DataFrame()
    # Parse the timestamps
    df2[timestamp_col] = pd.to_datetime(
        df[timestamp_col], format='%b-%d-%Y %I:%M:%S.%f %p'
    )
    # Calculate the time differences between consecutive timestamps
    time_diffs = df2[timestamp_col].diff().dropna()
    # Calculate the average time difference
    avg_timestep = time_diffs.mean()
    return avg_timestep


# Function to extract continuous domains based on time continuity


# a function that filters a dataframe based on two bounds of time
def event_filter(df, bounds, timestamp_col='Time Stamp'):
    df2 = df.copy()
    df2[timestamp_col] = pd.to_datetime(
        df[timestamp_col], format='%b-%d-%Y %I:%M:%S.%f %p'
    )

    # Ensure bounds are tuples or lists of start and end times
    filtered_df = df2[
        (df2[timestamp_col] >= bounds[0]) & (df2[timestamp_col] <= bounds[1])
    ]

    return filtered_df


# Function to convert all timestamps to tz-naive
def make_timestamps_tz_naive(timestamps):
    """
    This function converts all timestamps in a dictionary
    to tz-naive timestamps.
    """
    timestamps = {
        key: timestamps.tz_localize(None) for key, timestamps in timestamps.items()
    }
    return timestamps


# ----------CORE FUNCTIONS FOR DATA PROCESSING------------


# Function to calculate the true temperature
def calculate_avg_true_temp(temp_1, temp_2):
    return 0.905 * (0.5 * (temp_1 + temp_2)) + 12


# Helper function to check if a column is within a certain range
def within_range(data_col, ref_col_mean, diff_param):
    if ref_col_mean == 0:
        cond = (data_col > (-MFC_FLOW_THRESHOLD)) & (data_col < (+MFC_FLOW_THRESHOLD))
    else:
        cond = (data_col > (1 - 0.01 * diff_param) * ref_col_mean) & (
            data_col < (1 + 0.01 * diff_param) * ref_col_mean
        )
    return cond


# Function to get the source list automatically from the logfile
# (Ex: source_list = [1, 3, 4])
def get_source_list(data):
    source_list = []
    for col in data.columns:
        if col.startswith('PC Source') and col.endswith('Loaded Target'):
            source_number = int(col.split()[2])
            source_list.append(source_number)
    return source_list


# Function to read what source is connected to which power supply and creates column
# names that relate directly to the source instead of the power supply
# Iterate over source numbers and perform column creation
# (Ex: 'Power Supply 1 DC Bias' -> 'Source 4 DC Bias')
# Additiomal we check if, at any point the shutter
# is open and the source is switch at the same time
# to ensure that the algorithm does think that we used a source if
# we switched it on to a power supply by mistake
def connect_source_to_power_supply(data, source_list):
    for source_number in source_list:
        shutter_col = f'PC Source {source_number} Shutter Open'
        if f'PC Source {source_number} Switch-PDC-PWS1' in data.columns:
            switch_columns = {
                f'PC Source {source_number} Switch-PDC-PWS1': 'Power Supply 1',
                f'PC Source {source_number} Switch-RF1-PWS2': 'Power Supply 2',
                f'PC Source {source_number} Switch-RF2-PWS3': 'Power Supply 3',
            }
            for switch_col, power_supply in switch_columns.items():
                condition_met = (data[switch_col] == 1) & (data[shutter_col] == 1)
                if condition_met.any():
                    for col in data.columns:
                        if col.startswith(power_supply):
                            new_col = col.replace(
                                power_supply, f'Source {source_number}'
                            )
                            data[new_col] = data[col]
        elif f'PC Source {source_number} Switch-PDC-PWS1' not in data.columns:
            for power_supply in ['Power Supply 1', 'Power Supply 2', 'Power Supply 3']:
                condition_met = (data[f'{power_supply} Enabled'] == 1) & (
                    data[shutter_col] == 1
                )
                if condition_met.any():
                    for col in data.columns:
                        if col.startswith(power_supply):
                            new_col = col.replace(
                                power_supply, f'Source {source_number}'
                            )
                            data[new_col] = data[col]
        else:
            print('No source found')
            break


# Method to rename all 'Sulfur Cracker Control Setpoint' columns to
#'Sulfur Cracker Control Setpoint Feedback' and all
#'Sulfur Cracker Control Valve PulseWidth Setpoint' columns to
#'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
# This allows to harmonize the column name for samples deposited
# before the 12/08/2024, for which the column name was wrong and
# cracker data is not logged properly
def rename_cracker_columns(data):
    cond_column = ('Sulfur Cracker Control Setpoint' in data.columns) & (
        'Sulfur Cracker Control Valve PulseWidth Setpoint' in data.columns
    )
    cond_column_feedback = (
        'Sulfur Cracker Control Setpoint Feedback' in data.columns
    ) & ('Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in data.columns)

    if cond_column and not cond_column_feedback:
        # If the wrong cracker columns are present exclusively, we rename them
        data.rename(
            columns={
                'Sulfur Cracker Control Setpoint': (
                    'Sulfur Cracker Control Setpoint Feedback'
                ),
                'Sulfur Cracker Control Valve PulseWidth Setpoint': (
                    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ),
            },
            inplace=True,
        )
    return data


# For all the sources, method to read the dataframe for columns that
# give indication#of the status of the source (current,
# dc bias, output setpoint)#and create conditions for the
# plasma being on and being ramped up
# (Ex : plasma being on is defined as the current being above a
# threshold or the dc bias being above a threshold and the
# source being enabled)
# Because we have performed the previous step, we can now
# directly use the source number to create the conditions if we handle
# the case where the column does not exist in the dataframe
def filter_data_plasma_on_ramp_up(data, source_list):
    print('Defining the conditions and filtering the data')
    # Initialize dictionaries to store the ramp up, plasma on
    # conditions and corresponding data for each source
    source_ramp_up = {}
    source_on = {}
    source_on_open = {}

    for source_number in source_list:
        enabled_cond = (
            data.get(f'Source {source_number} Enabled', pd.Series([0] * len(data))) != 0
        )
        # this syntax is used to handle cases where the column does
        # not exist in the dataframe. In that case, it returns a dataframe
        # of 0 (False) values of the same length as the original dataframe
        current_cond = (
            data.get(f'Source {source_number} Current', pd.Series([0] * len(data)))
            > CURRENT_THRESHOLD
        )
        dc_bias_cond = (
            data.get(f'Source {source_number} DC Bias', pd.Series([0] * len(data)))
            > BIAS_THRESHOLD
        )
        power_fwd_refl_cond = (
            data.get(f'Source {source_number} Fwd Power', pd.Series([0] * len(data)))
            - data.get(f'Source {source_number} Rfl Power', pd.Series([0] * len(data)))
        ) > POWER_FWD_REFL_THRESHOLD

        setpoint_diff_cond = (
            data.get(
                f'Source {source_number} Output Setpoint', pd.Series([0] * len(data))
            ).diff()
            > POWER_SETPOINT_DIFF_THRESHOLD
        )
        # In the folowing, we store each dataframe in a dictionary of
        # dataframes, where the key is the source number

        # Initiate source_on[str(source_number)] as a Lf_Event object
        source_on[str(source_number)] = Lf_Event(
            f'Source {source_number} On', source=source_number, category='source_on'
        )
        # Define conditions for the plasma being on
        source_on_cond = enabled_cond & (
            (current_cond | dc_bias_cond) | power_fwd_refl_cond
        )
        source_on[str(source_number)].set_condition(source_on_cond)
        # Filter the data points where the plasma is on
        source_on[str(source_number)].filter_data(data)

        source_on_open[str(source_number)] = Lf_Event(
            f'Source {source_number} On Open',
            source=source_number,
            category='source_on_open',
        )
        # Define conditions for the plasma being on and the shutter being open
        source_on_open_cond = source_on_cond & (
            data[f'PC Source {source_number} Shutter Open'] == 1
        )
        source_on_open[str(source_number)].set_condition(source_on_open_cond)
        # Filter the data points where the plasma is on and the shutter is open
        source_on_open[str(source_number)].filter_data(data)

        # Initiate source_ramp_up[str(source_number)] as a Lf_Event object
        source_ramp_up[str(source_number)] = Lf_Event(
            f'Source {source_number} Ramp Up',
            source=source_number,
            category='source_ramp_up',
        )
        # Define conditions for the plasma ramping up
        source_ramp_up_wo1stpoint_cond = enabled_cond & setpoint_diff_cond

        source_ramp_up_w1stpoint_cond = (
            source_ramp_up_wo1stpoint_cond
            | source_ramp_up_wo1stpoint_cond.shift(-1, fill_value=False)
        )
        source_ramp_up[str(source_number)].set_condition(source_ramp_up_w1stpoint_cond)
        # Filter the data points where the plasma is ramping up
        source_ramp_up[str(source_number)].filter_data(data)
        source_ramp_up[str(source_number)].stitch_source_ramp_up_events()
        # Sometimes, we ramp up the sources in steps (Ex: 0->50->75)
        # In that case, the same event is counted as two events
        # We check if the last output setpoint power value of one event
        # is the same as the
        # first value of the next event and if so, we merge the two events
        # into one
    return source_on, source_on_open, source_ramp_up


# Define conditions for the cracker being on using the temperatures
# of the different zones of the cracker and the control being enabled
def filter_data_cracker_on_open(data):
    cracker_on_open = Lf_Event(
        'Cracker On Open',
        category='cracker_on_open',
    )

    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_on_open_cond = (
            (
                data['Sulfur Cracker Zone 1 Current Temperature']
                > CRACKER_ZONE_1_MIN_TEMP
            )
            & (
                data['Sulfur Cracker Zone 2 Current Temperature']
                > CRACKER_ZONE_2_MIN_TEMP
            )
            & (
                data['Sulfur Cracker Zone 3 Current Temperature']
                > CRACKER_ZONE_3_MIN_TEMP
            )
            & (data['Sulfur Cracker Control Enabled'] == 1)
        )
        cracker_on_open.set_condition(cracker_on_open_cond)
    else:
        cracker_on_open_cond = pd.Series(False, index=data.index)
    cracker_on_open.set_condition(cracker_on_open_cond)
    cracker_on_open.filter_data(data)
    return cracker_on_open


# Define conditions for the temperature control (when the temperature
# setpoint is different from the actual temperature) and filter the data
def filter_data_temp_ctrl(data):
    temp_ctrl = Lf_Event('Temperature Ctrl.', category='temp_ctrl')
    if 'Temperature Control Enabled' in data.columns:
        temp_ctrl_cond = data['Temperature Control Enabled'] == 1
    else:
        temp_ctrl_cond = (
            data['Substrate Heater Temperature Setpoint']
            != data['Substrate Heater Temperature']
        )
    temp_ctrl.set_condition(temp_ctrl_cond)
    temp_ctrl.filter_data(data)
    # There is a bug that sometimes the heater temp and the setpoint desagree
    # even though the temperature control is off. We need to check that the
    # size of the temperature control data is above a certain threshold or
    # the domains are not isolate points (if so, then extract_domains will
    # return an empty list). If the size is below the threshold or the domains
    # are isolated points, we set the data_temp_ctrl to an empty dataframe
    if (len(temp_ctrl.data) < MIN_TEMP_CTRL_SIZE) or (temp_ctrl.bounds == []):
        temp_ctrl.set_data(pd.DataFrame(columns=temp_ctrl.data.columns), data)

    return temp_ctrl


# Define conditions for the different gases being flown based on
# the setpoint and flow of the MFCs being above a threshold defined
# by MFC_FLOW_THRESHOLD
def filter_gas(data):
    ph3 = Lf_Event('PH3 On', category='ph3_on')
    h2s = Lf_Event('H2S On', category='h2s_on')
    ar = Lf_Event('Ar On', category='ar_on')

    ph3_cond = (data['PC MFC 4 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD
    )
    ph3.set_condition(ph3_cond)
    ph3.filter_data(data)

    h2s_cond = (data['PC MFC 6 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD
    )
    h2s.set_condition(h2s_cond)
    h2s.filter_data(data)

    ar_cond = (data['PC MFC 1 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD
    )
    ar.set_condition(ar_cond)
    ar.filter_data(data)

    return ph3, h2s, ar


# We can also define composite conditions for different events by
# combining the base condition (AND: & OR: | NOT: ~)


# Method to filter the data for the deposition as the substrate shutter
# being open and any source being on and open at the same time
def filter_data_deposition(data, source_list, **kwargs):
    source_on = kwargs.get('source_on')

    required_keys = ['source_on']

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    any_source_on = Lf_Event('Any Source On', category='any_source_on')
    any_source_on_open = Lf_Event(
        'Any Source On and Open', category='any_source_on_open'
    )
    #We create a deposition event that is not tied to any source in particular
    deposition = Lf_Event('Deposition', category='deposition', source = None)

    # Define a list of condition containing each source being on and open
    # at the same time
    source_on_open_cond_list = [
        source_on[str(source_number)].cond
        & (data[f'PC Source {source_number} Shutter Open'] == 1)
        for source_number in source_list
    ]
    # Define a list of conditions containing each source being on
    source_on_cond_list = [
        source_on[str(source_number)].cond for source_number in source_list
    ]
    # Combine the source conditions using OR (|) to get any source being on
    # and open and any source being on
    any_source_on_open_cond = reduce(operator.or_, source_on_open_cond_list)
    any_source_on_open.set_condition(any_source_on_open_cond)
    any_source_on_open.filter_data(data)

    any_source_on_cond = reduce(operator.or_, source_on_cond_list)
    any_source_on.set_condition(any_source_on_cond)
    any_source_on.filter_data(data)

    # Define deposition condition as te substrate shutter being open
    # and any source being on and open, as defined just above, and filtering
    # the data points where the deposition is happening
    deposition_cond = (data['PC Substrate Shutter Open'] == 1) & any_source_on_open.cond
    deposition.set_condition(deposition_cond)
    deposition.filter_data(data)

    source_used_list = []
    for source_number in source_list:
        if (
            not deposition.data.get(
                f'Source {source_number} Enabled', pd.Series([0] * len(deposition.data))
            ).all()
            == 0
        ):
            source_used_list.append(source_number)

    return any_source_on, any_source_on_open, deposition, source_used_list


# Method for the conditions for the plasma being presputtered as:
# - the source being on
# - the event happening before the deposition and after the last
# ramp up of the sources
# - the source not ramping up
# - no P or S being flown or cracked
# Note: this part may be improved as we may want to include presputtering
# in P or S gases. We may also include postsputtering
def filter_data_plasma_presput(data, source_list, **kwargs):
    required_keys = [
        'source_on',
        'source_ramp_up',
        'cracker_on_open',
        'ph3',
        'h2s',
        'deposition',
    ]

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    source_on = kwargs.get('source_on')
    source_ramp_up = kwargs.get('source_ramp_up')
    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    h2s = kwargs.get('h2s')
    deposition = kwargs.get('deposition')

    source_presput = {}

    for source_number in source_list:
        if not source_on[str(source_number)].data.empty:
            source_presput_cond = (
                source_on[str(source_number)].cond
                & (data['Time Stamp'] < deposition.bounds[0][0])
                & (
                    data['Time Stamp']
                    > (source_ramp_up[str(source_number)].data['Time Stamp'].iloc[-1])
                )
                & ~source_ramp_up[str(source_number)].cond
                & ~(ph3.cond | h2s.cond | cracker_on_open.cond)
            )

            source_presput[str(source_number)] = Lf_Event(
                f'Source {source_number} Presput',
                source=source_number,
                category='source_presput',
            )
            source_presput[str(source_number)].set_source(source_number)
            source_presput[str(source_number)].set_condition(source_presput_cond)
            source_presput[str(source_number)].filter_data(data)
    return source_presput


# Method to define the condition for measurement of the
# Sulfur Cracker induced base_pressure, as:
# - the cracker is on and open
# - no gas (h2s,ph2, or ar) is flown
# - the time is before the deposition
# - the cracker temperature and parameters
# are within WITHIN_RANGE_PARAM of the deposition conditions (for the cracker, and
# and the pressure)
def filter_data_cracker_pressure(data, **kwargs):
    required_keys = ['cracker_on_open', 'ph3', 'h2s', 'ar', 'deposition']

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    h2s = kwargs.get('h2s')
    ar = kwargs.get('ar')
    deposition = kwargs.get('deposition')

    cracker_base_pressure = Lf_Event(
        'Cracker Pressure Meas', category='cracker_base_pressure'
    )
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_temp_cond = (
            within_range(
                data['Sulfur Cracker Zone 1 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 1 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Zone 2 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 2 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Zone 3 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 3 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
        )

        valve_cond = within_range(
            data['Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'],
            deposition.data[
                'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
            ].mean(),
            WITHIN_RANGE_PARAM,
        ) & within_range(
            data['Sulfur Cracker Control Setpoint Feedback'],
            deposition.data['Sulfur Cracker Control Setpoint Feedback'].mean(),
            WITHIN_RANGE_PARAM,
        )

        if not cracker_on_open.data.empty:
            cracker_base_pressure_cond = (
                cracker_on_open.cond
                & (data['Time Stamp'] < deposition.bounds[0][0])
                & ~h2s.cond
                & ~ph3.cond
                & ~ar.cond
                & cracker_temp_cond
                & valve_cond
                & (data['Sulfur Cracker Control Enabled'] == 1)
            )
        else:
            cracker_base_pressure_cond = pd.Series(False, index=data.index)
    else:
        cracker_base_pressure_cond = pd.Series(False, index=data.index)
    cracker_base_pressure.set_condition(cracker_base_pressure_cond)
    cracker_base_pressure.filter_data(data)

    return cracker_base_pressure


# Condition of the deposition rate measurement is defined as the
# Xtal2 substrate shutter being open from which we exclude the
# data points just after the Xtal2 shutter opens, as the QCM
# needs time to stabilize. The STAB_TIME stabilization time
# is defined in the reference values section
def filter_data_film_dep_rate(data, source_list, **kwargs):
    required_keys = [
        'deposition',
        'source_on_open',
        'any_source_on_open',
        'cracker_on_open',
        'ph3',
        'h2s',
    ]

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    deposition = kwargs.get('deposition')
    source_on_open = kwargs.get('source_on_open')
    any_source_on_open = kwargs.get('any_source_on_open')
    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    h2s = kwargs.get('h2s')

    xtal2_open = Lf_Event('Xtal 2 Shutter Open', category='xtal2_shutter_open')
    deprate2_meas = Lf_Event('Deposition Rate Measurement', category='deprate2_meas')
    deprate2_film_meas = {}
    deprate2_sulfur_meas = Lf_Event('S Dep Rate Meas', category='s_deprate2_film_meas')

    xtal2_open, deprate2_meas = define_xtal2_open_conditions(
        data, xtal2_open, deprate2_meas
    )

    # Define the condition for the Metal-P-S film deposition rate measurement
    # as the condition just above, with the addition of S or P being flown
    # or the cracker being on, and the material used as refereced by the QCM
    # not being Sulfur
    # We assume here that the deposition rate is not measured during deposition
    # We also include that the condition of the plasma are within the
    # WITHIN_RANGE_PARAM of the deposition conditions

    pressure_cond, ph3_dep_cond, h2s_dep_cond, cracker_dep_cond = (
        define_deposition_conditions(data, deposition)
    )

    deprate2_film_meas, deprate2_ternary_meas = define_film_meas_conditions(
        data,
        source_list,
        deprate2_meas=deprate2_meas,
        source_on_open=source_on_open,
        cracker_dep_cond=cracker_dep_cond,
        h2s_dep_cond=h2s_dep_cond,
        ph3_dep_cond=ph3_dep_cond,
        deposition=deposition,
        pressure_cond=pressure_cond,
        deprate2_film_meas=deprate2_film_meas,
    )

    deprate2_sulfur_meas = define_sulfur_meas_conditions(
        data,
        deprate2_meas,
        deprate2_sulfur_meas,
        deposition=deposition,
        any_source_on_open=any_source_on_open,
        cracker_on_open=cracker_on_open,
        ph3=ph3,
        h2s=h2s,
    )

    return (
        deprate2_ternary_meas,
        deprate2_film_meas,
        deprate2_meas,
        xtal2_open,
        deprate2_sulfur_meas,
    )


def define_xtal2_open_conditions(data, xtal2_open, deprate2_meas):
    if 'Xtal 2 Shutter Open' in data.columns:
        xtal2_open_cond = data['Xtal 2 Shutter Open'] == 1
        xtal2_open.set_condition(xtal2_open_cond)
        xtal2_open.filter_data(data)

        # Set a time window to exclude data points after
        # the Xtal shutter opens
        # Identify the indices where the shutter opens (transitions to 1)
        xtal2_open_indices = data.index[data['Xtal 2 Shutter Open'].diff() == 1]
        # Create a boolean mask to exclude points within STAB_TIME seconds
        # after the shutter opens
        mask = pd.Series(True, index=data.index)
        for idx in xtal2_open_indices:
            # Find the time of the shutter opening event
            open_time = data.at[idx, 'Time Stamp']
            # Find points within STAB_TIME seconds after the shutter opening
            within_stab_time = (data['Time Stamp'] > open_time) & (
                data['Time Stamp'] <= open_time + pd.Timedelta(seconds=STAB_TIME)
            )
            # Update the mask to exclude these points
            mask &= ~within_stab_time
        # Apply the mask to filter the data
        deprate2_meas_cond = mask & xtal2_open.cond
    else:
        deprate2_meas_cond = pd.Series(False, index=data.index)
    deprate2_meas.set_condition(deprate2_meas_cond)
    deprate2_meas.filter_data(data)
    return xtal2_open, deprate2_meas


def define_deposition_conditions(data, deposition):
    pressure_cond = within_range(
        data['PC Capman Pressure'],
        deposition.data['PC Capman Pressure'].mean(),
        WITHIN_RANGE_PARAM,
    )

    ph3_dep_cond = within_range(
        data['PC MFC 4 Setpoint'],
        deposition.data['PC MFC 4 Setpoint'].mean(),
        WITHIN_RANGE_PARAM,
    )

    h2s_dep_cond = within_range(
        data['PC MFC 6 Setpoint'],
        deposition.data['PC MFC 6 Setpoint'].mean(),
        WITHIN_RANGE_PARAM,
    )
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_dep_cond = (
            within_range(
                data['Sulfur Cracker Zone 1 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 1 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Zone 2 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 2 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Zone 3 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 3 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'],
                deposition.data[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Control Setpoint Feedback'],
                deposition.data['Sulfur Cracker Control Setpoint Feedback'].mean(),
                WITHIN_RANGE_PARAM,
            )
        )
    else:
        cracker_dep_cond = pd.Series(False, index=data.index)
    return pressure_cond, ph3_dep_cond, h2s_dep_cond, cracker_dep_cond


def define_film_meas_conditions(data, source_list, **kwargs):
    deprate2_meas = kwargs.get('deprate2_meas')
    source_on_open = kwargs.get('source_on_open')
    cracker_dep_cond = kwargs.get('cracker_dep_cond')
    h2s_dep_cond = kwargs.get('h2s_dep_cond')
    ph3_dep_cond = kwargs.get('ph3_dep_cond')
    deposition = kwargs.get('deposition')
    pressure_cond = kwargs.get('pressure_cond')
    deprate2_film_meas = kwargs.get('deprate2_film_meas')

    deprate2_film_meas_cond_list = []
    for source_number in source_list:
        if f'Source {source_number} Output Setpoint' in data.columns:
            power_cond = within_range(
                data[f'Source {source_number} Output Setpoint'],
                deposition.data[f'Source {source_number} Output Setpoint'].mean(),
                WITHIN_RANGE_PARAM,
            )
            deprate2_film_meas_cond = (
                deprate2_meas.cond
                & source_on_open[str(source_number)].cond
                & cracker_dep_cond
                & h2s_dep_cond
                & ph3_dep_cond
                & (data['Thickness Active Material'] != 'Sulfur')
                & power_cond
                & pressure_cond
            )
            deprate2_film_meas_cond_list.append(deprate2_film_meas_cond)

            deprate2_film_meas[str(source_number)] = Lf_Event(
                f'Source {source_number} Film Dep Rate Meas',
                source=source_number,
                category='source_deprate2_film_meas',
            )
            deprate2_film_meas[str(source_number)].set_source(source_number)
            deprate2_film_meas[str(source_number)].set_condition(
                deprate2_film_meas_cond
            )
            deprate2_film_meas[str(source_number)].filter_data(data)
            # We define the condition for the all sources film
            # deposition rate measurement
            # as the combination of al the film dep rate conditions above

    deprate2_ternary_meas_cond = reduce(operator.and_, deprate2_film_meas_cond_list)
    deprate2_ternary_meas = Lf_Event(
        'All Source Film Dep Rate Meas',
        source=None,
        category='source_deprate2_film_meas',
    )
    deprate2_ternary_meas.set_condition(deprate2_ternary_meas_cond)
    deprate2_ternary_meas.filter_data(data)

    return deprate2_film_meas, deprate2_ternary_meas


def define_sulfur_meas_conditions(data, deprate2_meas, deprate2_sulfur_meas, **kwargs):
    deposition = kwargs.get('deposition')
    any_source_on_open = kwargs.get('any_source_on_open')
    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    h2s = kwargs.get('h2s')

    # Define the condition for the onlt Sulfur film deposition rate measurement as:
    #  with the material used as refereced by the QCM
    # being Sulfur
    # We also include the condition of the cracker are
    # within the WITHIN_RANGE_PARAM of the deposition conditions¨
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_temp_cond = (
            within_range(
                data['Sulfur Cracker Zone 1 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 1 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Zone 2 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 2 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
            & within_range(
                data['Sulfur Cracker Zone 3 Current Temperature'],
                deposition.data['Sulfur Cracker Zone 3 Current Temperature'].mean(),
                WITHIN_RANGE_PARAM,
            )
        )

        valve_cond = within_range(
            data['Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'],
            deposition.data[
                'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
            ].mean(),
            WITHIN_RANGE_PARAM,
        ) & within_range(
            data['Sulfur Cracker Control Setpoint Feedback'],
            deposition.data['Sulfur Cracker Control Setpoint Feedback'].mean(),
            WITHIN_RANGE_PARAM,
        )

        pressure_cond = within_range(
            data['PC Capman Pressure'],
            deposition.data['PC Capman Pressure'].mean(),
            WITHIN_RANGE_PARAM,
        )

        deprate2_sulfur_meas_cond = (
            deprate2_meas.cond
            & ~any_source_on_open.cond
            & cracker_on_open.cond
            & ~(ph3.cond | h2s.cond)
            & (data['Thickness Active Material'] == 'Sulfur')
            & ~deposition.cond
            & cracker_temp_cond
            & valve_cond
            & pressure_cond
        )
    else:
        deprate2_sulfur_meas_cond = pd.Series(False, index=data.index)

    deprate2_sulfur_meas.set_condition(deprate2_sulfur_meas_cond)
    deprate2_sulfur_meas.filter_data(data)
    return deprate2_sulfur_meas


# Method to filter the data for the substrate temperature was ramping up as:
# - the temperature control is enabled
# - the event is not a deposition
# - the temperature setpoint is increasing faster than the threshold
# defined in the reference values
def filter_data_temp_ramp_up_down(data, **kwargs):
    required_keys = ['cracker_on_open', 'temp_ctrl', 'ph3', 'h2s', 'deposition']

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    cracker_on_open = kwargs.get('cracker_on_open')
    temp_ctrl = kwargs.get('temp_ctrl')
    ph3 = kwargs.get('ph3')
    h2s = kwargs.get('h2s')
    deposition = kwargs.get('deposition')

    ramp_up_temp = Lf_Event('Sub Temp Ramp Up', category='ramp_up_temp')
    ramp_down_temp = Lf_Event('Sub Temp Ramp Down', category='ramp_down_temp')
    ramp_down_high_temp = Lf_Event(
        'Sub High Temp Ramp Down', category='ramp_down_high_temp'
    )
    ramp_down_low_temp = Lf_Event(
        'Sub Low Temp Ramp Down', category='ramp_down_low_temp'
    )

    if (
        not temp_ctrl.data.empty
        or (
            deposition.data['Substrate Heater Temperature Setpoint'] > RT_TEMP_THRESHOLD
        ).all()
    ):
        ramp_up_temp_cond = (
            temp_ctrl.cond
            & ~deposition.cond
            & (
                data['Substrate Heater Temperature Setpoint'].diff()
                > TEMP_SETPOINT_DIFF_THRESHOLD
            )
        )
        ramp_up_temp.set_condition(ramp_up_temp_cond)
        ramp_up_temp.filter_data(data)

        # Define conditions and filtering the data
        # for the substrate temperature was ramping down in a similar fashion
        ramp_down_temp_cond = (
            temp_ctrl.cond
            & ~deposition.cond
            & (
                data['Substrate Heater Temperature Setpoint'].diff()
                < -TEMP_SETPOINT_DIFF_THRESHOLD
            )
            & (data['Substrate Heater Temperature Setpoint'] > 1)
        )
        ramp_down_temp.set_condition(ramp_down_temp_cond)
        ramp_down_temp.filter_data(data)
        # In the following, we distinguish betweem to phases of the ramp down:
        # 1/ the high temperature phase where we flow H2S, PH3 or the cracker is on
        # to prevent the film loosing P or S
        # 2/ the low temperature phase where we do not flow H2S, PH3 or
        # the cracker is off

        # Define the ramp down high temperature condition as a events after
        # the beginning of the ramp down of the temperature ramp down
        # where we flow H2S, PH3 or the cracker is on
        ramp_down_high_temp_cond = (
            data['Time Stamp'] > ramp_down_temp.data['Time Stamp'].iloc[0]
        ) & (h2s.cond | cracker_on_open.cond | ph3.cond)
        ramp_down_high_temp.set_condition(ramp_down_high_temp_cond)
        ramp_down_high_temp.filter_data(data)
        ramp_down_high_temp.filter_out_small_events(MIN_TEMP_RAMP_DOWN_SIZE)

        # Define the ramp down low temperature condition as a events after
        # the beginning of the ramp down of the temperature ramp down
        # where we do not flow H2S, PH3 or the cracker is off
        ramp_down_low_temp_cond = (
            data['Time Stamp'] > ramp_down_temp.data['Time Stamp'].iloc[0]
        ) & ~(h2s.cond | cracker_on_open.cond | ph3.cond)
        ramp_down_low_temp.set_condition(ramp_down_low_temp_cond)
        ramp_down_low_temp.filter_data(data)

    return ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp


# -------PLOTTING DEFINITIONS------------


def plot_plotly_extimeline(events_to_plot, sample_name):
    """
    args:
        logfile_name: str
            Name of the logfile to be used in the title of the plot
        data: pd.DataFrame
            Dataframe containing the raw data
        source_used_list: list
            List of sources used during the process
        bottom_steps: list
            List of steps to be plotted at the bottom of the plot
        non_source_steps: list
            List of steps to be plotted above the bottom steps
        source_steps: list
            List of source dependent steps to be plotted
            above the non_source_steps
    """

    # Format the steps to be plotted for the plotly timeline
    rows = []
    for step in events_to_plot:
        if isinstance(step, Lf_Event):
            for bounds in step.bounds:
                rows.append({'Event': step.name, 'Start': bounds[0], 'End': bounds[1],
                'Average Temp': step.data['Substrate Heater Temperature'].mean(),
                'Average Pressure': step.data['PC Capman Pressure'].mean()})
                #add more quantities if needed

    df = pd.DataFrame(rows)

    time_margin = pd.Timedelta(minutes=15)
    # Determine the timeline duration
    min_start_time = df['Start'].min() - time_margin
    # Calculate end time overlooking the Ar On event
    max_end_time = df[df['Event'] != 'Ar On']['End'].max() + time_margin
    # Duration in hours
    timeline_duration = (max_end_time - min_start_time).total_seconds() / 3600

    # Calculate dynamic width and height
    num_events = len(df['Event'].unique())
    width = max(900, timeline_duration * 50)  # Minimum width 800px, scale with duration
    height = max(500, num_events * 30)  # Minimum height 600px,scale with num. of events
    # Create the plot with plotly express.timeline
    fig = px.timeline(
        df,
        x_start='Start',
        x_end='End',
        y='Event',
        color='Event',
        color_discrete_map=STEP_COLORS,
        title='Process Timeline',
        hover_data=['Average Temp', 'Average Pressure'],
    )
    fig.update_xaxes(range=[min_start_time, max_end_time])
    # Update the layout to include a border around the plot area
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title=None,
        yaxis=dict(
            tickvals=df['Event'].unique(),
            ticktext=df['Event'].unique(),
            autorange='reversed',  # Ensure tasks are displayed in order
        ),
        template='plotly_white', # Use a white background template
        hovermode='closest',
        dragmode='zoom',
        title=dict(
            text=f'Process Timeline for {sample_name}',  # Title text
            x=0.5,  # Center the title horizontally
            y=0.85,  # Position the title vertically
            xanchor='center',  # Anchor the title at the center horizontally
            yanchor='top',  # Anchor the title at the top vertically
            font=dict(size=16),  # Font size of the title
        ),
        margin=dict(l=50, r=50, t=120, b=50),  # Increased top margin for title
        width=width,  # Dynamic width
        height=height,  # Dynamic height
        showlegend=False,  # Hide the legend
        paper_bgcolor='white',  # Background color of the entire figure
        plot_bgcolor='white',  # Background color of the plotting area
        shapes=[
            dict(
                type='rect',
                x0=0,
                x1=1,
                y0=0,
                y1=1,
                xref='paper',
                yref='paper',
                line=dict(color='black', width=1),
            )
        ],
    )

    return fig


# -------HELPER FUNCTIONS TO MANIPULATE LISTS OF EVENTS--------


def unfold_events(all_lf_events, data):
    all_sub_lf_events = []
    for step in all_lf_events:
        for i in range(step.events):
            new_step = Lf_Event(
                step.sep_name[i],
                source=step.source,
                category=step.category,
                step_number=i,
            )
            new_step.set_source(step.source)
            new_step.set_data(step.sep_data[i], data)
            all_sub_lf_events.append(new_step)

    return all_sub_lf_events


def add_event_to_events(event, all_events):
    """
    args:
        all_events: list
            List of all the events to which the event is to be added
        event: Lf_Event, list of Lf_Event, or dict of Lf_Event
            Event to be added to the list of all events
    """
    if isinstance(event, list):
        for item in event:
            if isinstance(item, Lf_Event):
                all_events.append(item)
            elif isinstance(item, dict):
                for key in item:
                    all_events.append(item[key])
    elif isinstance(event, Lf_Event):
        all_events.append(event)
    elif isinstance(event, dict):
        for key in event:
            all_events.append(event[key])

    else:
        raise ValueError(
            'The event to be added to the list of all events is not of the right type'
        )
    return all_events


# Definition to sort the events by the start time
# PROBLEM WITH THIS FUNCTION
def sort_events_by_start_time(all_events):
    """
    args:
        all_events: list
            List of all the events to be sorted by start time
    """
    # Sort events by their start time using Python's sorted, which is stable
    sorted_list = sorted(all_events, key=lambda event: event.bounds[0][0])
    return sorted_list


def filter_events_by_category(all_events, category):
    """
    args:
        all_events: list
            List of all the events to be filtered by category
        category: str
            Category of the events to be filtered
    """
    return all_events


# Definition to place the ramp_up_temp, deposition, ramp_down_high_temp,
# ramp_down_low_temp event first in the list of all events, in this order
def place_deposition_ramp_up_down_events_first(all_events):
    # Separate events into priority categories and others
    priority_events = []
    other_events = []

    for event in all_events:
        if event.category in CATEGORIES_FIRST:
            priority_events.append(event)
        else:
            other_events.append(event)

    # Group the non-priority events by source if the source is not None
    events_by_source = {}
    no_source_events = []

    for event in other_events:
        if event.source is not None:
            if event.source not in events_by_source:
                events_by_source[event.source] = []
            events_by_source[event.source].append(event)
        else:
            no_source_events.append(event)

    # Flatten the grouped events and append to the result
    sorted_events = priority_events

    for source, events in events_by_source.items():
        sorted_events.extend(events)

    sorted_events.extend(no_source_events)
    return sorted_events


# -------ADDITIONAL FUNCTIONS FOR THE OPTIX SPECTRA------------


# Function to read the OPTIX spectrum CSV file
def read_spectrum(file_path):
    """
    Intended to read OPTIX spectrum
    Reads a CSV file with spectrum data and returns a DataFrame
    with columns 'x', 'y1', 'y2', etc.,
    and a dictionary mapping each 'y' column to its corresponding timestamp.

    You can access the timestamps of each spectrum by looking up the
    timestamp_map dictionary. For example, timestamp_map['y1'] will give
    you the timestamp for the first intensity spectrum,
    timestamp_map['y2'] for the second, and so on

    Parameters:
    file_path (str): Path to the CSV file.

    Returns:
    result_df (DataFrame): A DataFrame with columns 'x', 'y1', 'y2', etc.
    timestamp_map (dict): A dictionary mapping each 'y'
    column to its corresponding timestamp.
    """

    # Step 0: Initiate a dictionary to store the spectrum and timestamp
    spectra = {}

    # Step 1: Read the CSV file, specifying that the header is in the first row
    df = pd.read_csv(file_path, header=None)

    # Step 2: Extract the x wavelength values
    # (from the first row, starting from the third column)
    x_wavelengths = df.iloc[0, 2:].values

    # Step 3: Process the rest of the data (from the second row onwards)
    data = df.iloc[1:].copy()

    # Step 4: Rename the columns to 'Timestamp', 'Triggered', and x wavelength values
    data.columns = ['Timestamp', 'Triggered'] + list(x_wavelengths)
    data.drop('Triggered', axis=1, inplace=True)

    # Step 5: Convert the 'Timestamp' column to datetime
    data['Timestamp'] = pd.to_datetime(data['Timestamp'])

    # Step 6: Reshape the DataFrame to have columns 'x', 'y1', 'y2', etc.
    reshaped_data = data.melt(id_vars='Timestamp', var_name='x', value_name='Intensity')

    # Step 7: Create a new DataFrame with columns 'x', 'y1', 'y2', etc.
    result_df = reshaped_data.pivot(
        index='x', columns='Timestamp', values='Intensity'
    ).reset_index()

    # Rename the columns appropriately
    result_df.columns.name = None
    y_columns = [f'y{i+1}' for i in range(len(result_df.columns) - 1)]
    result_df.columns = ['x'] + y_columns

    # Step 8: Drop the first row if it is filled with NaNs
    if result_df.iloc[0].isna().all():
        result_df = result_df.drop(result_df.index[0])

    # Step 9: Create a timestamp map
    timestamp_map = {
        f'y{i+1}': timestamp
        for i, timestamp in enumerate(reshaped_data['Timestamp'].unique())
    }

    timestamp_map_tz_naive = make_timestamps_tz_naive(timestamp_map)

    spectra['data'] = result_df
    spectra['timestamp_map'] = timestamp_map_tz_naive

    return spectra


def filter_spectrum(spectra, bounds):
    """
    This function filters in the Optix spectrums based on the conditions that they
    have been recorded during the time bounds passed in the 'bounds' list.
    """
    filtered_spectra = {'data': [], 'timestamp_map': {}}

    spectra['timestamp_map'] = make_timestamps_tz_naive(spectra['timestamp_map'])

    for bound in bounds:
        start_time, end_time = bound
        for timestamp_key, timestamp in spectra['timestamp_map'].items():
            if start_time <= timestamp <= end_time:
                filtered_spectra['data'].append(spectra['data'][['x', timestamp_key]])
                filtered_spectra['timestamp_map'][timestamp_key] = timestamp

    if filtered_spectra['data']:
        filtered_spectra['data'] = (
            pd.concat(filtered_spectra['data'], axis=1).T.drop_duplicates().T
        )
    else:
        filtered_spectra['data'] = pd.DataFrame()

    return filtered_spectra


# normalize the data in a column
def normalize_column(df, column_name):
    min_val = df[column_name].min()
    max_val = df[column_name].max()
    return (df[column_name] - min_val) / (max_val - min_val)


# ------------------------CORE METHODS----------------------


def formatting_logfile(data):
    print('Formatting the dataframe for conditional filtering')
    # -----FORMATTING THE DATAFRAME FOR CONDITIONAL FILTERING-------
    # -------RENAME THE CRACKER COLUMNS OF THE DATAFRAME---------
    data = rename_cracker_columns(data)
    # ---------READING THE SOURCE USED--------
    # Get the source list automatically from the logfile
    source_list = get_source_list(data)
    # ---------CONNECTING THE SOURCES TO THE POWER SUPPLIES--------
    # Read what source is connected to which power supply and
    # create column names that relate directly to the source instead
    # of the power supply
    connect_source_to_power_supply(data, source_list)
    # ---------DEFINE DE CONDITIONS FOR DIFFERENT EVENTS-------------
    # Initialize the list of all events
    return data, source_list


def verify_deposition_unicity(events, raw_data):
    for event in events:
        if event.category == 'deposition':
            # if a deposition event time between the bounds is lower
            # than MIN_DEPOSITION_SIZE, we consider that the deposition
            # event is not valid
            if event.events == 0:
                print('Error: No deposition event found')
                break
            elif event.events > 1:
                print(
                    'More than one deposition event detected.',
                    'Removing deposition events smaller than',
                    f'{MIN_DEPOSITION_SIZE} steps',
                )
                print(
                    'Number of deposition events before filtering:', event.events, '\n'
                )
                for i in range(event.events):
                    print(
                        f'Deposition({i})start time: {event.bounds[i][0]}',
                        f'Deposition({i})end time: {event.bounds[i][1]}',
                    )
                event.filter_out_small_events(MIN_DEPOSITION_SIZE)
                print('Number of deposition events after filtering:', event.events)
                for i in range(event.events):
                    print(
                        f'Deposition({i+1})start time: {event.bounds[i][0]}',
                        f'Deposition({i+1})end time: {event.bounds[i][1]}',
                    )
                if event.events != 1:
                    print(
                        'Removal failed. The number of deposition events is not 1.',
                        'Increasing the continuity limit to',
                        DEPOSITION_CONTINUITY_LIMIT,
                    )
                    # We try to increase the continuity limit to
                    # DEPOSITION_CONTINUITY_LIMIT)
                    event.set_data(
                        event.data,
                        raw_data,
                        continuity_limit=DEPOSITION_CONTINUITY_LIMIT,
                    )
                    if event.events == 1:
                        print('A unique deposition event was succesfully filtered')
                    else:
                        raise ValueError(
                            'Error: The number of deposition events is not 1 ',
                            'after increasing the continuity limit and filttering ',
                            'smaller events',
                        )
                        break
    return events


def select_last_event(events, raw_data, ref_event, categories):
    for event in events:
        if event.category in categories:
            try:
                event.select_event(raw_data, -1, ref_event.bounds[0][0])
            except Exception as e:
                print(
                    'Warning: Failed to find any event before ref_event for',
                    f'{event.step_id}. Error: {e}',
                )
    return events


def read_events(data):

    data, source_list = formatting_logfile(data)

    # ---------DEFINE DE CONDITIONS FOR DIFFERENT EVENTS-------------
    # Initialize the list of all events
    events = []

    # ---------1/CONDITIONS FOR THE PLASMA ON OR BEING RAMPED UP--------
    source_on, source_on_open, source_ramp_up = filter_data_plasma_on_ramp_up(
        data, source_list
    )

    add_event_to_events([source_on, source_on_open, source_ramp_up], events)

    # ---------2/CONDITION FOR THE CRACKER BEING ON--------
    cracker_on_open = filter_data_cracker_on_open(data)

    add_event_to_events(cracker_on_open, events)

    # ---------3/CONDITION FOR THE TEMPERATURE CONTROL--------
    temp_ctrl = filter_data_temp_ctrl(data)

    add_event_to_events(temp_ctrl, events)

    # ----- 4/CONDITIONS FOR THE DIFFERENT GASES BEING FLOWN--------
    ph3, h2s, ar = filter_gas(data)

    add_event_to_events([ph3, h2s, ar], events)

    # ---------5/CONDITIONS FOR THE DEPOSITION--------
    any_source_on, any_source_on_open, deposition, source_used_list = (
        filter_data_deposition(data, source_list, source_on=source_on)
    )

    add_event_to_events([any_source_on, any_source_on_open, deposition], events)

    # ---------6/CONDITIONS FOR THE DIFFERENT SOURCES BEING PRESPUTTERED--------
    source_presput = filter_data_plasma_presput(
        data,
        source_list,
        source_on=source_on,
        source_ramp_up=source_ramp_up,
        cracker_on_open=cracker_on_open,
        ph3=ph3,
        h2s=h2s,
        deposition=deposition,
    )

    add_event_to_events(source_presput, events)

    # ---------7/CONDITIONS FOR THE S CRACKER PRESSURE MEAS--------
    # Filter the data for the S Cracker pressure
    cracker_base_pressure = filter_data_cracker_pressure(
        data,
        cracker_on_open=cracker_on_open,
        ph3=ph3,
        h2s=h2s,
        ar=ar,
        deposition=deposition,
    )

    add_event_to_events(cracker_base_pressure, events)

    # ---------8/CONDITIONS FOR THE DEPOSITION RATE MEASUREMENT--------

    (
        deprate2_ternary_meas,
        deprate2_film_meas,
        deprate2_meas,
        xtal2_open,
        deprate2_sulfur_meas,
    ) = filter_data_film_dep_rate(
        data,
        source_list,
        deposition=deposition,
        source_on_open=source_on_open,
        any_source_on_open=any_source_on_open,
        cracker_on_open=cracker_on_open,
        ph3=ph3,
        h2s=h2s,
    )

    add_event_to_events(
        [
            deprate2_meas,
            xtal2_open,
            deprate2_sulfur_meas,
            deprate2_film_meas,
            deprate2_ternary_meas,
        ],
        events,
    )

    # ---9/CONDITIONS FOR THE SUBSTRATE TEMPERATURE RAMPING UP OR DOWN-----
    # Filter the data for the substrate temperature ramping up or down
    ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp = (
        filter_data_temp_ramp_up_down(
            data,
            cracker_on_open=cracker_on_open,
            temp_ctrl=temp_ctrl,
            ph3=ph3,
            h2s=h2s,
            deposition=deposition,
        )
    )
    add_event_to_events(
        [ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp], events
    )

    # Remove the empty events from the events
    events = [event for event in events if event.bounds]

    # Place the ramp_up_temp, deposition, ramp_down_high_temp, ramp_down_low_temp
    # event first in the list of all events, in this particular order
    events = place_deposition_ramp_up_down_events_first(events)

    # Getting the list of all events to pass it to the plotting function
    # in the future
    events_to_plot = copy.deepcopy(events)

    # We verify the unicity of the deposition event, and try to fix it if needed
    events = verify_deposition_unicity(events, data)

    # To make a list sutable for making a report, we remove
    # all the events that do not match the CATEGORIES_MAIN_REPORT

    events_main_report = [
        copy.deepcopy(event)
        for event in events
        if event.category in CATEGORIES_MAIN_REPORT
    ]

    # For all the events of the main report list, we also get the last_event before
    # the deposition, using the select_event function, -1 (last) event together with the
    # deposition first bounds
    events = select_last_event(events, data, deposition, CATEGORIES_LAST_EVENT)

    # Initialize the params dictionary for the main report
    main_params = {}

    # for event in events_for_main_report, we apply the get_ methods for
    # the class Lf_Event to get the params dict
    main_params = get_overview(data)
    for event in events_main_report:
        main_params = event.get_params(data, source_list, params=main_params)
    main_params = get_end_of_process(data, main_params)

    # unfold all the events_main_report events to get sep_events
    sep_events = unfold_events(copy.deepcopy(events_main_report), data)

    # Sort the subevents by the start time
    sep_events = sort_events_by_start_time(sep_events)

    # Initialize the params dictionary for the sub report
    step_params = {}

    # get the individual step params
    for event in sep_events:
        step_params = event.get_nomad_step_params(step_params, source_list)

    return events_to_plot, main_params, step_params

# ---------------MAIN-----------

def main():
    global events_to_plot, main_params, step_params
    samples_dir = r'Z:\P110143-phosphosulfides-Andrea\Data\samples'
    logfiles_extension = 'CSV'

    logfiles = {'name': [], 'folder': []}

    samples_to_remove = [
        'mittma_0002_Cu__H2S_and_PH3_RT_Recording Set 2024.04.17-17.54.07'
    ]

    # In samples_dir, explore all the folders (samples names)
    for folder in os.listdir(samples_dir):
        sample_path = os.path.join(samples_dir, folder, 'log_files')

        # Check if the sample_path exists and is a directory
        if os.path.isdir(sample_path):
            # Iterate over files in the sample_path directory
            for file in os.listdir(sample_path):
                if re.match(r'^\w+\d{4}\w+', file) and file.endswith(
                    f'.{logfiles_extension}'
                ):
                    logfile_name = re.sub(rf'\.{logfiles_extension}$', '', file)
                    if logfile_name not in samples_to_remove:
                        logfiles['name'].append(logfile_name)
                        logfiles['folder'].append(sample_path)

    # # Uncomment to test the script on a single logfile
    # logfiles = {}
    # logfiles['name']= ['mittma_0007_Cu_Recording Set 2024.06.03-09.52.29']
    # logfiles['folder']= [
    #     r'Z:\P110143-phosphosulfides-Andrea\Data\Samples\mittma_0007_Cu\log_files']


    # Loop over all the logfiles in the directory
    for i in range(len(logfiles['name'])):
        # Default Logfile location
        print(f'Processing logfile: {logfiles["name"][i]}')
        logfile_path = (
            f'{logfiles["folder"][i]}/{logfiles["name"][i]}.{logfiles_extension}'
        )

        # ---------DEFAULT EXPORT LOCATIONS-------------
        # Specify the path and filename for the report text file
        txt_file_dir = os.path.join(logfiles['folder'][i])
        txt_file_name = f'{logfiles["name"][i]}_derived_quantities.txt'
        txt_file_path = os.path.join(txt_file_dir, txt_file_name)

        # Specify the plotly graph export location and file name
        plotly_graph_file_dir = os.path.join(logfiles['folder'][i])
        plotly_graph_file_name = f'{logfiles["name"][i]}_plotly_timeline.html'
        plotly_graph_file_path = os.path.join(
            plotly_graph_file_dir, plotly_graph_file_name
        )

        # ---------READ THE DATA-------------

        # Read the log file and spectrum data
        print('Extracting all the events from the logfile')
        data = read_logfile(logfile_path)


        # ----READ ALL THE EVENTS IN THE LOGFILE----
        events_to_plot, main_params, step_params = read_events(data)

        # --------GRAPH THE DIFFERENT STEPS ON A TIME LINE------------

        # Create the figure
        print('Generating the plotly plot')
        plotly_timeline = plot_plotly_extimeline(events_to_plot, logfiles['name'][i])
        # plotly_timeline.show()

        # Save the image as an interactive html file
        plotly_timeline.write_html(plotly_graph_file_path)

        # --------PRINT DERIVED QUANTITIES REPORTS-------------

        print(f'Derived quantities report for logfile\n{logfiles["name"][i]}:\n')
        print_params(main_params)
        print('\n')

        print(f'Step report for logfile\n{logfiles["name"][i]}:\n')
        print_params(step_params)
        print('\n')

        # ---SAVE THE REPORT QUANTITIES IN A TEXT FILE---

        print('Saving the derived quantities report as a text file')
        save_report_as_text(main_params, txt_file_path, logfiles['name'][i])
        print('\n')


if __name__ == '__main__':
    main()


# ------TESTING GROUND--------
