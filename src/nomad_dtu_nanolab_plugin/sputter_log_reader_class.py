"""
Created on Fri Jun  7 10:46:17 2024

@author: eugbe

"""
# %%
# ---------PACKAGES-------------

import operator
import os
from functools import reduce

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from mendeleev import element
import re
import plotly.graph_objects as go
import plotly.express as px

##------EVENT CLASS DEFINITION------

class Lf_Event:
    def __init__(self, name: str, data: pd.DataFrame):
        self.source = None
        self.name = name
        self.raw_data = data
        self.cond = pd.DataFrame()
        self._data = pd.DataFrame()
        self._bounds = []
        self._events = 0
        self._sep_data = [pd.DataFrame()]
        self._sep_name = ['']

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value
        self._bounds = extract_domains(self._data, self.raw_data)
        self._update_events_and_separated_data()

    @property
    def bounds(self):
        return self._bounds

    @bounds.setter
    def bounds(self, value):
        self._bounds = value
        self._update_events_and_separated_data()

    @property
    def events(self):
        return self._events

    @property
    def sep_data(self):
        return self._sep_data

    @property
    def sep_name(self):
        return self._sep_name

    @property
    def sep_bounds(self):
        return self._sep_bounds

    def set_condition(self, condition):
        self.cond = condition

    def set_source(self, source):
        self.source = source

    def set_name(self, name):
        self.name = name

    def set_data(self, data):
        self.data = data

    def set_bounds(self, bounds):
        self.bounds = bounds  # This correctly sets the bounds

    def filter_data(self, data):
        if self.cond is not None:
            self.raw_data = data
            self.data = data[self.cond]
        else:
            print(f'Error: Unable to filter. No condition set for event {self.name}')

    def stitch_source_ramp_up_events(self):
            i = 0
            while i < len(self.bounds) - 1:
                # Find the timestamps of the end of the first event and the start of the next event
                end_timestamp = self.bounds[i][1]
                start_timestamp_next = self.bounds[i + 1][0]

                # Convert timestamps to integer indices
                try:
                    end_index = self.data[self.data['Time Stamp'] == end_timestamp].index[0]
                    start_index_next = self.data[self.data['Time Stamp'] == start_timestamp_next].index[0]
                except IndexError:
                    print(f"Error: 'Time Stamp' value {end_timestamp} or {start_timestamp_next} not found in data.")
                    return

                # Check if the output setpoint power value of the first event is the same as the next event
                if self.data[f'Source {self.source} Output Setpoint'].loc[end_index] == \
                self.data[f'Source {self.source} Output Setpoint'].loc[start_index_next]:
                    # If so, merge the two events
                    self.bounds[i] = (
                        self.bounds[i][0],
                        self.bounds[i + 1][1],
                    )
                    self.bounds.pop(i + 1)
                else:
                    i += 1  # Only increment i if no merge occurred
            self._update_events_and_separated_data()

    def _update_events_and_separated_data(self):
        """Helper method to update events, sep_data, sep_name, and sep_bounds after bounds change."""
        self._events = len(self._bounds)
        self._sep_data = self._generate_sep_data()
        self._sep_name = self._generate_sep_name()
        self._sep_bounds = self._generate_sep_bounds()

    def _generate_sep_data(self):
        return [event_filter(self.data, bound) for bound in self.bounds]

    def _generate_sep_name(self):
        return [f'{self.name}({i})' for i in range(self._events)]

    def _generate_sep_bounds(self):
        return [self.bounds[i] for i in range(self._events)]


# %%
# ---------FUNCTIONS DEFINITION------------


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


# Function to read the IDOL combinatorial chamber CSV logfile
def read_logfile(file_path):
    """
    This function reads a logfile and returns a DataFrame with the
    'Time Stamp' column converted to datetime format.
    All the logged values are stored in the DataFrame
    as they are in the logfile.
    """
    try:
        df = pd.read_csv(file_path, header=[1], skiprows=[0])
        df['Time Stamp'] = pd.to_datetime(
            df['Time Stamp'], format='%b-%d-%Y %I:%M:%S.%f %p'
        )
        # Ensure all timestamps in the log file and spectrum are tz-naive
        df['Time Stamp'] = df['Time Stamp'].dt.tz_localize(None)
        return df
    except Exception:
        return None


# Function to print the derived quantities in a nested format
def print_derived_quantities(quantities, indent=''):
    for key, value in quantities.items():
        if isinstance(value, dict):
            print(f'{indent}{key}:')
            print_derived_quantities(value, indent + '  ')
        else:
            if isinstance(value, pd.Timestamp):
                if key == 'log_start_time' or key == 'log_end_time':
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    value = value.strftime('%H:%M:%S')
            elif isinstance(value, pd.Timedelta):
                total_seconds = int(value.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                value = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
            print(f'{indent}{key}: {value}')


# Function to write the derived quantities in a nested format
def write_derived_quantities(quantities, indent=''):
    output = []
    for key, value in quantities.items():
        if isinstance(value, dict):
            output.append(f'{indent}{key}:')
            output.append(write_derived_quantities(value, indent + '  '))
        else:
            if isinstance(value, pd.Timestamp):
                if key == 'log_start_time' or key == 'log_end_time':
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    value = value.strftime('%H:%M:%S')
            elif isinstance(value, pd.Timedelta):
                total_seconds = int(value.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                value = f'{hours:02d}:{minutes:02d}:{seconds:02d}'
            output.append(f'{indent}{key}: {value}')
    return '\n'.join(output)


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
def extract_domains(df, df2, timestamp_col='Time Stamp'):
    """
    This function extracts the bounds of continuous time domains in a
    DataFrame based on the time continuity
    For example, if the time difference between two consecutive
    timestamps of df1 is greater than the avg_timestep of df2,
    then the two timestamps are considered to be in
    different timedomains.
    """
    if df.empty:
        return []
    else:
        # work on a copy of the DataFrame
        df3 = pd.DataFrame()
        # Calculate the average time step of df2
        avg_timestep = cal_avg_timestep(df2, timestamp_col)
        # Set the continuity limit as NUM_TIMESTEP the average time step
        continuity_limit = NUM_TIMESTEP * avg_timestep
        # Parse the timestamps in df
        df3[timestamp_col] = pd.to_datetime(
            df[timestamp_col], format='%b-%d-%Y %I:%M:%S.%f %p'
        )
        # Calculate the time differences between consecutive timestamps
        df3['time_diff'] = df3[timestamp_col].diff()
        # Identify the points where the discontinuity is
        # greater than the continuity limit
        discontinuities = df3['time_diff'] > continuity_limit
        # Extract the bounds of the continuous domains
        bounds = []
        start_idx = 0
        for i in range(1, len(df)):
            if discontinuities.iloc[i]:
                end_idx = i - 1
                bounds.append(
                    (df[timestamp_col].iloc[start_idx], df[timestamp_col].iloc[end_idx])
                )
                start_idx = i
        # Add the last continuous domain
        bounds.append((df[timestamp_col].iloc[start_idx], df[timestamp_col].iloc[-1]))
        # remove all the bounds that are less than a certain time
        # interval to only keep big domains
        bounds = [
            bound
            for bound in bounds
            if (bound[1] - bound[0]) > MIN_DOMAIN_SIZE * avg_timestep
        ]
        return bounds


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
    timestamps
    return {key: timestamps.tz_localize(None) for key, timestamps in timestamps.items()}


# Function to calculate the true temperature
def calculate_avg_true_temp(temp_1, temp_2):
    return 0.905 * (0.5 * (temp_1 + temp_2)) + 12

# Helper function to check if a column is within a certain range
def within_range(data_col, ref_col_mean, diff_param):
    return (
        (data_col > (1 - 0.01 * diff_param) * ref_col_mean) &
        (data_col < (1 + 0.01 * diff_param) * ref_col_mean)
    )


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
                            new_col = col.replace(power_supply, f'Source {source_number}')
                            data[new_col] = data[col]
        elif f'PC Source {source_number} Switch-PDC-PWS1' not in data.columns:
            for power_supply in ['Power Supply 1', 'Power Supply 2', 'Power Supply 3']:
                condition_met = (data[f'{power_supply} Enabled'] == 1) & (
                data[shutter_col] == 1
            )
                if condition_met.any():
                    for col in data.columns:
                        if col.startswith(power_supply):
                            new_col = col.replace(power_supply, f'Source {source_number}')
                            data[new_col] = data[col]
        else:
            print('No source found')
            break

#Method to rename all 'Sulfur Cracker Control Setpoint' columns to
#'Sulfur Cracker Control Setpoint Feedback' and all
#'Sulfur Cracker Control Valve PulseWidth Setpoint' columns to
#'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
#This allows to harmonize the column name for samples deposited
# before the 12/08/2024, for which the column name was wrong and
# cracker data is not logged properly
def rename_cracker_columns(data):
    if ('Sulfur Cracker Control Setpoint'
        in data.columns) & (
        'Sulfur Cracker Control Valve PulseWidth Setpoint'
        in data.columns):
        data.rename(columns={
            'Sulfur Cracker Control Valve Setpoint':
            'Sulfur Cracker Control Valve Setpoint Feedback',
            'Sulfur Cracker Control Valve PulseWidth Setpoint':
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'},inplace=True)
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

    # Initialize dictionaries to store the ramp up, plasma on
    # conditions and corresponding data for each source
    source_ramp_up = {}
    source_on = {}

    for source_number in source_list:
        print(f'Processing Source {source_number}')

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
        setpoint_diff_cond = (
        data.get(
            f'Source {source_number} Output Setpoint', pd.Series([0] * len(data))
        ).diff()
        > POWER_SETPOINT_DIFF_THRESHOLD
        )
        # In the folowing, we store each dataframe in a dictionary of
        # dataframes, where the key is the source number

        #Initiate source_on[f'{source_number}'] as a Lf_Event object
        source_on[f'{source_number}'] = Lf_Event(f'Source {source_number} On',data)
        source_on[f'{source_number}'].set_source(source_number)
        # Define conditions for the plasma being on
        source_on_cond = enabled_cond & (current_cond | dc_bias_cond)
        source_on[f'{source_number}'].set_condition(source_on_cond)
        # Filter the data points where the plasma is on
        source_on[f'{source_number}'].filter_data(data)

        #Initiate source_ramp_up[f'{source_number}'] as a Lf_Event object
        source_ramp_up[f'{source_number}'] = Lf_Event(f'Source {source_number} Ramp Up',data)
        source_ramp_up[f'{source_number}'].set_source(source_number)
        # Define conditions for the plasma ramping up
        source_ramp_up_wo1stpoint_cond = enabled_cond & setpoint_diff_cond

        source_ramp_up_w1stpoint_cond = (source_ramp_up_wo1stpoint_cond |
        source_ramp_up_wo1stpoint_cond.shift(-1, fill_value=False)
        )
        source_ramp_up[f'{source_number}'].set_condition(source_ramp_up_w1stpoint_cond)
        # Filter the data points where the plasma is ramping up
        source_ramp_up[f'{source_number}'].filter_data(data)
        print(source_ramp_up[f'{source_number}'].events)
        source_ramp_up[f'{source_number}'].stitch_source_ramp_up_events()
        print(source_ramp_up[f'{source_number}'].events)
        # Sometimes, we ramp up the sources in steps (Ex: 0->50->75)
        # In that case, the same event is counted as two events
        # We check if the last output setpoint power value of one event
        # is the same as the
        # first value of the next event and if so, we merge the two events
        # into one
    return source_on, source_ramp_up

# Define conditions for the cracker being on using the temperatures
# of the different zones of the cracker and the control being enabled
def filter_data_cracker_on_open(data):

    cracker_on_open = Lf_Event('Cracker On Open',data)

    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_on_open_cond = (
        (data['Sulfur Cracker Zone 1 Current Temperature'] > CRACKER_ZONE_1_MIN_TEMP)
        & (data['Sulfur Cracker Zone 2 Current Temperature'] > CRACKER_ZONE_2_MIN_TEMP)
        & (data['Sulfur Cracker Zone 3 Current Temperature'] > CRACKER_ZONE_3_MIN_TEMP)
        & (data['Sulfur Cracker Control Enabled'] == 1))
        cracker_on_open.set_condition(cracker_on_open_cond)
    else:
        cracker_on_open_cond = pd.Series(False, index=data.index)
    cracker_on_open.set_condition(cracker_on_open_cond)
    cracker_on_open.filter_data(data)
    return cracker_on_open


# Define conditions for the temperature control (when the temperature
# setpoint is different from the actual temperature) and filter the data
def filter_data_temp_ctrl(data):

    temp_ctrl = Lf_Event('Temperature Ctrl.',data)

    if 'Temperature Control Enabled' in data.columns:
        temp_ctrl_cond = data['Temperature Control Enabled'] == 1
    else:
        temp_ctrl_cond= (
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
    if (len(temp_ctrl.data) < MIN_TEMP_CTRL_SIZE) or (
    temp_ctrl.bounds == []):
        temp_ctrl.set_data(pd.DataFrame(columns=temp_ctrl.data.columns))

    return temp_ctrl


# Define conditions for the different gases being flown based on
# the setpoint and flow of the MFCs being above a threshold defined
# by MFC_FLOW_THRESHOLD
def filter_gas(data):
    ph3 = Lf_Event('PH3 On',data)
    h2s = Lf_Event('H2S On',data)
    ar = Lf_Event('Ar On',data)

    ph3_cond = (data['PC MFC 4 Setpoint'] > MFC_FLOW_THRESHOLD) & (
    data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD)
    ph3.set_condition(ph3_cond)
    ph3.filter_data(data)

    h2s_cond = (data['PC MFC 6 Setpoint'] > MFC_FLOW_THRESHOLD) & (
    data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD)
    h2s.set_condition(h2s_cond)
    h2s.filter_data(data)

    ar_cond = (data['PC MFC 1 Setpoint'] > MFC_FLOW_THRESHOLD) & (
    data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD)
    ar.set_condition(ar_cond)
    ar.filter_data(data)

    return ph3,h2s,ar

# We can also define composite conditions for different events by
# combining the base condition (AND: & OR: | NOT: ~)

#Method to filter the data for the deposition as the substrate shutter
# being open and any source being on and open at the same time
def filter_data_deposition(data, source_list, source_on):

    any_source_on = Lf_Event('Any Source On',data)
    any_source_on_open = Lf_Event('Any Source On and Open',data)
    deposition = Lf_Event('Deposition',data)

    # Define a list of condition containing each source being on and open
    # at the same time
    source_on_open_cond_list = [
    source_on[f'{source_number}'].cond
    & (data[f'PC Source {source_number} Shutter Open'] == 1)
    for source_number in source_list
    ]
    # Define a list of conditions containing each source being on
    source_on_cond_list = [
    source_on[f'{source_number}'].cond for source_number in source_list
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
def filter_data_plasma_presput(data, source_list,
                            source_on, source_ramp_up,
                            cracker_on_open, ph3, h2s, deposition):
    source_presput = {}

    for source_number in source_list:
        if not source_on[f'{source_number}'].data.empty:
            source_presput_cond= (
            source_on[f'{source_number}'].cond
            & (data['Time Stamp'] < deposition.bounds[0][0])
            & (
            data['Time Stamp']
            > (
                source_ramp_up[f'{source_number}'].data[
                    'Time Stamp'
                ].iloc[-1]
                )
            )
            & ~source_ramp_up[f'{source_number}'].cond
            & ~(ph3.cond | h2s.cond | cracker_on_open.cond)
        )

            source_presput[f'{source_number}'] = Lf_Event(f'Source {source_number} Presput',data)
            source_presput[f'{source_number}'].set_source(source_number)
            source_presput[f'{source_number}'].set_condition(source_presput_cond)
            source_presput[f'{source_number}'].filter_data(data)
    return source_presput

# Method to define the condition for measurement of the
# Sulfur Cracker induced base_pressure, as:
# - the cracker is on and open
# - no gas (h2s,ph2, or ar) is flown
# - the time is before the deposition
# - the cracker temperature and parameters
# are within CRACKER_DIFF_PARAM of the deposition conditions (for the cracker, and
# and the pressure)
def filter_data_cracker_pressure(data, cracker_on_open,
                                ph3, h2s, ar, deposition):
    cracker_base_pressure = Lf_Event('Cracker Pressure Meas',data)
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_temp_cond = (
        within_range(data['Sulfur Cracker Zone 1 Current Temperature'],
            deposition.data[
            'Sulfur Cracker Zone 1 Current Temperature'
            ].mean(),
            CRACKER_DIFF_PARAM)
        & within_range(data['Sulfur Cracker Zone 2 Current Temperature'],
            deposition.data[
            'Sulfur Cracker Zone 2 Current Temperature'
            ].mean(),
            CRACKER_DIFF_PARAM)
        & within_range(data['Sulfur Cracker Zone 3 Current Temperature'],
            deposition.data[
            'Sulfur Cracker Zone 3 Current Temperature'
            ].mean(),
            CRACKER_DIFF_PARAM)
    )

        valve_cond = (
            within_range(data['Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'],
                deposition.data[
                'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].mean(),
                CRACKER_DIFF_PARAM)
            & within_range(data['Sulfur Cracker Control Valve Setpoint Feedback'],
                deposition.data[
                'Sulfur Cracker Control Valve Setpoint Feedback'
                ].mean(),
                CRACKER_DIFF_PARAM)
        )

        if not cracker_on_open.data.empty:
            cracker_base_pressure_cond= (
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
def filter_data_film_dep_rate(data, deposition, source_list, cracker_on_open, ph3, h2s, any_source_on_open):
    xtal2_open = Lf_Event('Xtal 2 Shutter Open',data)

    deprate2_meas = Lf_Event('Deposition Rate Measurement',data)

    deprate2_film_meas = {}

    deprate2_sulfur_meas = Lf_Event('S Dep Rate Meas',data)

    if 'Xtal 2 Shutter Open' in data.columns:
        xtal2_open_cond=data['Xtal 2 Shutter Open'] == 1
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
        deprate2_meas_cond= mask & xtal2_open.cond
    else:
        deprate2_meas_cond = pd.Series(False, index=data.index)
    deprate2_meas.set_condition(deprate2_meas_cond)
    deprate2_meas.filter_data(data)

    # Define the condition for the Metal-P-S film deposition rate measurement
    # as the condition just above, with the addition of S or P being flown
    # or the cracker being on, and the material used as refereced by the QCM
    # not being Sulfur
    #We assume here that the deposition rate is not measured during deposition
    #We also include that the condition of the plasma are within the
    #CRACKER_DIFF_PARAM of the deposition conditions

    for source_number in source_list:
        if f'Source {source_number} Output Setpoint' in data.columns:
            power_cond = (
                within_range(data[f'Source {source_number} Output Setpoint'],
                            deposition.data[f'Source {source_number} Output Setpoint']
                            .mean(),
                            CRACKER_DIFF_PARAM)
            )

            pressure_cond = (
                within_range(data['PC Capman Pressure'],
                    deposition.data['PC Capman Pressure'].mean(),
                    CRACKER_DIFF_PARAM)
                )

            deprate2_film_meas_cond = (
            deprate2_meas_cond
            & any_source_on_open.cond
            & (cracker_on_open.cond | h2s.cond)
            & ph3.cond
            & (data['Thickness Active Material']!= 'Sulfur')
            & ~deposition.cond
            & power_cond
            & pressure_cond
            )
            deprate2_film_meas[f'{source_number}'] = Lf_Event(f'Source {source_number} MePS Dep Rate Meas',data)
            deprate2_film_meas[f'{source_number}'].set_source(source_number)
            deprate2_film_meas[f'{source_number}'].set_condition(deprate2_film_meas_cond)
            deprate2_film_meas[f'{source_number}'].filter_data(data)

    # Define the condition for the onlt Sulfur film deposition rate measurement as:
    #  with the material used as refereced by the QCM
    # being Sulfur
    #We also include the condition of the cracker are
    #within the CRACKER_DIFF_PARAM of the deposition conditions¨
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        cracker_temp_cond = (
        within_range(data['Sulfur Cracker Zone 1 Current Temperature'],
            deposition.data[
            'Sulfur Cracker Zone 1 Current Temperature'
            ].mean(),
            CRACKER_DIFF_PARAM)
        & within_range(data['Sulfur Cracker Zone 2 Current Temperature'],
            deposition.data[
            'Sulfur Cracker Zone 2 Current Temperature'
            ].mean(),
            CRACKER_DIFF_PARAM)
        & within_range(data['Sulfur Cracker Zone 3 Current Temperature'],
            deposition.data[
            'Sulfur Cracker Zone 3 Current Temperature'
            ].mean(),
            CRACKER_DIFF_PARAM)
    )

        valve_cond = (
            within_range(data['Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'],
                deposition.data[
                'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].mean(),
                CRACKER_DIFF_PARAM)
            & within_range(data['Sulfur Cracker Control Valve Setpoint Feedback'],
                deposition.data[
                'Sulfur Cracker Control Valve Setpoint Feedback'
                ].mean(),
                CRACKER_DIFF_PARAM)
            )

        pressure_cond = (
            within_range(data['PC Capman Pressure'],
                deposition.data[
                'PC Capman Pressure'
                ].mean(),
                CRACKER_DIFF_PARAM)
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

    return deprate2_film_meas, deprate2_meas, xtal2_open, deprate2_sulfur_meas

# Method to filter the data for the substrate temperature was ramping up as:
# - the temperature control is enabled
# - the event is not a deposition
# - the temperature setpoint is increasing faster than the threshold
# defined in the reference values
def filter_data_temp_ramp_up_down(data,
                            cracker_on_open,temp_ctrl,
                            ph3, h2s, deposition):

    ramp_up_temp = Lf_Event('Sub Temp Ramp Up',data)
    ramp_down_temp = Lf_Event('Sub Temp Ramp Down',data)
    ramp_down_high_temp = Lf_Event('Sub High Temp Ramp Down',data)
    ramp_down_low_temp = Lf_Event('Sub Low Temp Ramp Down',data)

    if not temp_ctrl.data.empty or (
    deposition.data['Substrate Heater Temperature Setpoint'] > RT_TEMP_THRESHOLD
    ).all():

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
        (data['Time Stamp'] > ramp_down_temp.data['Time Stamp'].iloc[0])
        & (h2s.cond | cracker_on_open.cond)
        & ph3.cond
        )
        ramp_down_high_temp.set_condition(ramp_down_high_temp_cond)
        ramp_down_high_temp.filter_data(data)

    # Define the ramp down low temperature condition as a events after
    # the beginning of the ramp down of the temperature ramp down
    # where we do not flow H2S, PH3 or the cracker is off
        ramp_down_low_temp_cond = (
        data['Time Stamp'] > ramp_down_temp.data['Time Stamp'].iloc[0]
        ) & ~(h2s.cond  | cracker_on_open.cond  | ph3.cond )
        ramp_down_low_temp.set_condition(ramp_down_low_temp_cond)
        ramp_down_low_temp.filter_data(data)

    return ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp

def init_derived_quant(source_list):
    # Initialize a  nested dictionary to store derived quantities
    # for ramp up, plasma on, presputtering and deposition events, we nest
    # other dictionaries for the different sources or the cracker status
    derived_quant = {
    'deposition': {'cracker': {}},
    'source_ramp_up': {},
    'source_presput': {},
    'sub_ramp_up': {'cracker': {}},
    'sub_ramp_down': {'cracker': {}}
    }

    for source_number in source_list:
        derived_quant['deposition'][f'{source_number}'] = {}
        derived_quant['source_ramp_up'][f'{source_number}'] = {}
        derived_quant['source_presput'][f'{source_number}'] = {}

    return derived_quant

# Extact sample name as the first 3 log file string when parsed by '_'
def extract_overview(derived_quant,logfile_path, data):

    # Extract sample name as the first 3 log file string when parsed by '_'
    derived_quant['sample_name'] = '_'.join(logfile_name.split('_')[:3])

    # Extract start and end time of the log file
    derived_quant['log_start_time'] = data['Time Stamp'].iloc[0]
    derived_quant['log_end_time'] = data['Time Stamp'].iloc[-1]

    return derived_quant

def extract_rt_bool(derived_quant, temp_ctrl, deposition):
    # Extract if the deposition was done at room temperature as :
    # - the temperature control is disabled or
    # - the temperature control is enabled but the temperature setpoint
    # is below the RT threshold defined in the reference values
    if (
    temp_ctrl.data.empty
    or (
        deposition.data['Substrate Heater Temperature Setpoint'] < RT_TEMP_THRESHOLD
    ).all()
        ):
        derived_quant['deposition']['rt'] = True
    elif (
    deposition.data['Substrate Heater Temperature Setpoint'] > RT_TEMP_THRESHOLD
        ).all():
        derived_quant['deposition']['rt'] = False
    return derived_quant

def extract_source_used_deposition(derived_quant, source_list, deposition, source_presput):
    # Extract the source used for deposition
    # For all sources, we check if the source is enabled during deposition
    # and if it is, we set the source as the source enabled for deposition
    # which implies that the source was also ramped up and presputtered
    for source_number in source_list:
        if (
        not deposition.data.get(
            f'Source {source_number} Enabled', pd.Series([0] * len(deposition.data))
            ).all()
            == 0
            ):
            derived_quant['deposition'][f'{source_number}']['enabled'] = True
            derived_quant['source_ramp_up'][f'{source_number}']['enabled'] = True
            if not source_presput[f'{source_number}'].data.empty:
                derived_quant['source_presput'][f'{source_number}']['enabled'] = True
            else:
                derived_quant['source_presput'][f'{source_number}']['enabled'] = False
        else:
            derived_quant['deposition'][f'{source_number}']['enabled'] = False
            derived_quant['source_ramp_up'][f'{source_number}']['enabled'] = False
            derived_quant['source_presput'][f'{source_number}']['enabled'] = False
    return derived_quant

def extract_cracker_params(derived_quant, data, deposition, cracker_base_pressure):
    # Extract if the cracker has been used during deposition as the
    # cracker control being enabled and the temperatures of the
    # different zones being above the minimum temperatures
    # defined in the reference values
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        if (
        (deposition.data['Sulfur Cracker Control Enabled'] == 1).all()
        and (
            deposition.data['Sulfur Cracker Zone 1 Current Temperature']
            > CRACKER_ZONE_1_MIN_TEMP
        ).all()
        and (
            deposition.data['Sulfur Cracker Zone 2 Current Temperature']
            > CRACKER_ZONE_2_MIN_TEMP
        ).all()
        and (
            deposition.data['Sulfur Cracker Zone 3 Current Temperature']
            > CRACKER_ZONE_3_MIN_TEMP
        ).all()
    ):
            derived_quant['deposition']['cracker']['enabled'] = True
    else:
        derived_quant['deposition']['cracker']['enabled'] = False

    # Extract the cracker parameters if the cracker has been used
    if derived_quant['deposition']['cracker']['enabled']:
        derived_quant['deposition']['cracker']['zone1_temp'] = deposition.data[
            'Sulfur Cracker Zone 1 Current Temperature'
        ].mean()
        derived_quant['deposition']['cracker']['zone2_temp'] = deposition.data[
            'Sulfur Cracker Zone 2 Current Temperature'
        ].mean()
        derived_quant['deposition']['cracker']['zone3_temp'] = deposition.data[
            'Sulfur Cracker Zone 3 Current Temperature'
        ].mean()
        derived_quant['deposition']['cracker']['pulse_width'] = deposition.data[
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
        ].mean()
        derived_quant['deposition']['cracker']['pulse_freq'] = deposition.data[
            'Sulfur Cracker Control Valve Setpoint Feedback'
        ].mean()
        # Extract the S induced base pressure as the mean pressure during
        # the cracker being on and no gas being flown
        if not cracker_base_pressure.data.empty:
            derived_quant['cracker_pressure_meas'] = True
            derived_quant['cracker_pressure'] = cracker_base_pressure.data[
            'PC Wide Range Gauge'].mean()
        else:
            derived_quant['cracker_pressure_meas'] = False
    return derived_quant

def extract_pressure_params(derived_quant, data, deposition):
    # Extract the some base pressure metric as the lowest positive
    # pressure recorded before deposition (but only if
    # it is below 1-6Torr). If the cracker is enabled, then this metric is not
    # representative of the true base pressure and we set the
    # true_base_pressure_meas to False to indicate that the true base
    # pressure is not measured accurately: If the cracker is not enabled,
    # then the base pressure is measured accurately and we set the
    # true_base_pressure_meas to True
    min_pressure_before_depostion = data.loc[
        pd.to_datetime(data['Time Stamp'])
        <= pd.to_datetime(deposition.data['Time Stamp'].iloc[0]),
        'PC Wide Range Gauge',
        ].min()

    derived_quant['lower_pressure_before_deposition'] = min_pressure_before_depostion
    if min_pressure_before_depostion < MAX_BASE_PRESSURE:
        if not derived_quant['deposition']['cracker']['enabled']:
            derived_quant['true_base_pressure_meas'] = True
        elif derived_quant['deposition']['cracker']['enabled']:
            derived_quant['true_base_pressure_meas'] = False
    else:
        derived_quant['true_base_pressure_meas'] = False

    return derived_quant

def extract_simple_deposition_params(derived_quant,deposition):
    # Extract the platin position during deposition
    if 'Substrate Rotation_Position' in deposition.data:
        derived_quant['deposition']['platin_position'] = deposition.data[
        'Substrate Rotation_Position'
        ].mean()
    # Extract the number of deposition events
    derived_quant['deposition']['num_events'] = deposition.events

    # Extract start and end time of the deposition
    derived_quant['deposition']['start_time'] = deposition.data['Time Stamp'].iloc[0]
    derived_quant['deposition']['end_time'] = deposition.data['Time Stamp'].iloc[-1]
    derived_quant['deposition']['duration'] = (
    derived_quant['deposition']['end_time'] - derived_quant['deposition']['start_time']
    )

    # Extract average temperature during deposition
    derived_quant['deposition']['avg_temp_1'] = deposition.data[
    'Substrate Heater Temperature'
    ].mean()
    derived_quant['deposition']['avg_temp_2'] = deposition.data[
    'Substrate Heater Temperature 2'
    ].mean()
    derived_quant['deposition']['avg_temp_setpoint'] = deposition.data[
    'Substrate Heater Temperature Setpoint'
    ].mean()

    # Extract the average true temperature during deposition
    derived_quant['deposition']['avg_true_temp'] = calculate_avg_true_temp(
    derived_quant['deposition']['avg_temp_1'], derived_quant['deposition']['avg_temp_2']
    )

    # Extract average sputter PC Capman pressure during deposition
    derived_quant['deposition']['avg_capman_pressure'] = deposition.data[
    'PC Capman Pressure'
    ].mean()

    # Extract the MF1 Ar, MFC4 PH3 and MFC6 H2S flow during deposition
    # only if the flow is above 1sccm, if not we set the flow to 0
    derived_quant['deposition']['avg_ar_flow'] = (
    deposition.data[deposition.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD][
        'PC MFC 1 Flow'
    ].mean()
    if not deposition.data[deposition.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD][
        'PC MFC 1 Flow'
    ].empty
    else 0
    )
    derived_quant['deposition']['avg_ph3_flow'] = (
    deposition.data[deposition.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD][
        'PC MFC 4 Flow'
    ].mean()
    if not deposition.data[deposition.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD][
        'PC MFC 4 Flow'
    ].empty
    else 0
    )
    derived_quant['deposition']['avg_h2s_flow'] = (
    deposition.data[deposition.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD][
        'PC MFC 6 Flow'
    ].mean()
    if not deposition.data[deposition.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD][
        'PC MFC 6 Flow'
        ].empty
        else 0
    )

    return derived_quant

def extract_source_presput_params(derived_quant, source_list, source_presput):
# Here, we interate over the sources to extract many relevant parameters
    for source_number in source_list:
        # We check if the source is enabled during deposition
        if derived_quant['deposition'][f'{source_number}']['enabled']:
            # ----source presputtering parameters-----
            if derived_quant['source_presput'][f'{source_number}']['enabled']:
                # Extract the presputtering duration
                # First, we extract the bounds of the continuous domains
                presput_time = pd.Timedelta(0)
                # Secondly, or all the presputtering events, we calculate the
                # duration and add it to the total presputtering time
                for i in range(source_presput[f'{source_number}'].events):
                    presput_time += (
                        source_presput[f'{source_number}'].bounds[i][1]
                        - source_presput[f'{source_number}'].bounds[i][0]
                    )
                derived_quant['source_presput'][f'{source_number}']['duration'] = (
                    presput_time
                )
                # Extract the average output power during presputtering
                derived_quant['source_presput'][f'{source_number}'][
                    'avg_output_power'
                ] = source_presput[f'{source_number}'].data[
                    f'Source {source_number} Output Setpoint'
                ].mean()
                # Extract the avg capman pressure during presputtering
                derived_quant['source_presput'][f'{source_number}'][
                    'avg_capman_pressure'
                ] = source_presput[f'{source_number}'].data[
                    'PC Capman Pressure'
                ].mean()
                # Extract the gas flows during presputtering
                derived_quant['source_presput'][f'{source_number}']['avg_ar_flow'] = (
                    source_presput[
                        f'{source_number}'
                    ].data['PC MFC 1 Flow'].mean()
                )
    return derived_quant

def extract_source_ramp_up_params(derived_quant, source_list, source_ramp_up, data):
    # Here, we interate over the sources to extract many relevant parameters
    for source_number in source_list:
        # We check if the source is enabled during deposition
        if derived_quant['deposition'][f'{source_number}']['enabled']:
            # Extract the number of ramp up events
            derived_quant['source_ramp_up'][f'{source_number}']['num_events'] = (
                source_ramp_up[f'{source_number}'].events
            )
            # Extract the plasma ignition power as the power at which
            # the plasma really ignites
            # We first filter only the last [-1] source ramp up event with the
            # event filter function
            last_ramp_up_bounds = list(
                source_ramp_up[f'{source_number}'].bounds[-1]
            )
            # Then we adjust the bounds to include the all the
            # times until deposition
            last_ramp_up_bounds[1] = derived_quant['deposition']['start_time']
            data_last_ramp_up_event = event_filter(data, last_ramp_up_bounds)
            current_series = data.get(
                f'Source {source_number} Current', pd.Series([0] * len(data))
            )
            bias_series = data.get(
                f'Source {source_number} DC Bias', pd.Series([0] * len(data))
            )
            # Create a boolean mask for the conditions
            mask = (current_series > CURRENT_THRESHOLD) | (bias_series > BIAS_THRESHOLD)
            # Apply the mask to get the moment where the plasma is on during
            # ramp up
            data_ignition_time = data.loc[mask]
            # If the plasma turns on during ramp up, data_ignition_time should
            # not be empty
            if not data_ignition_time.empty:
                ignition_time = data_ignition_time['Time Stamp'].iloc[0]
                derived_quant['source_ramp_up'][f'{source_number}'][
                    'source_ignition'
                ] = True
                derived_quant['source_ramp_up'][f'{source_number}'][
                    'source_ignition_time'
                ] = ignition_time
                ignition_data = data[data['Time Stamp'] == ignition_time]
                derived_quant['source_ramp_up'][f'{source_number}'][
                    'source_ignition_power'
                ] = ignition_data[f'Source {source_number} Output Setpoint'].iloc[0]
                derived_quant['source_ramp_up'][f'{source_number}'][
                    'source_ignition_pressure'
                ] = ignition_data['PC Capman Pressure'].iloc[0]
            else:
                derived_quant['source_ramp_up'][f'{source_number}'][
                    'source_ignition'
                ] = False

    return derived_quant

def extract_source_deposition_params(derived_quant, source_list, deposition, deprate2_film_meas):
    # Here, we interate over the sources to extract many relevant parameters
    for source_number in source_list:
        # We check if the source is enabled during deposition
        if derived_quant['deposition'][f'{source_number}']['enabled']:
            # initialize the elements list for the material space extraction
            elements = []

            # Extract average ouput power during deposition
            derived_quant['deposition'][f'{source_number}']['avg_output_power'] = (
            deposition.data[f'Source {source_number} Output Setpoint'].mean()
        )
            # Extract the plasma type by checking what power supply was used¨
            # during deposition, which can be done by checking if relevant
            # columns are present in the dataframe for each source
            enable_col = f'Source {source_number} Enabled'
            dc_current_col = f'Source {source_number} Current'
            rf_bias_col = f'Source {source_number} DC Bias'
            pulse_enable_col = f'Source {source_number} Pulse Enabled'
            if dc_current_col in deposition.data:
                if deposition.data[dc_current_col].all() > CURRENT_THRESHOLD:
                    (derived_quant['deposition'][f'{source_number}']['dc']) = True
                    (derived_quant['deposition'][f'{source_number}']['rf']) = False
                    if (
                    pulse_enable_col in deposition.data
                    and (deposition.data[pulse_enable_col].all()) == 1
                ):
                        (
                        derived_quant['deposition'][f'{source_number}']['pulsed']
                    ) = True
                        derived_quant['deposition']
                        [f'{source_number}']['pulse_frequency'] = deposition.data[
                        f'Source {source_number} Pulse Frequency'
                    ].mean()
                    # Extract the dc pulse frequency and reverse time
                        derived_quant['deposition'][f'{source_number}'][
                        'dead_time'
                    ] = deposition.data[f'Source {source_number} Reverse Time'].mean()
                    elif (
                    pulse_enable_col in deposition.data
                    and (deposition.data[pulse_enable_col].all()) == 0
                ):
                        (
                        derived_quant['deposition'][f'{source_number}']['pulsed']
                    ) = False
            elif rf_bias_col in deposition.data:
                if deposition.data[rf_bias_col].all() > BIAS_THRESHOLD:
                    (derived_quant['deposition'][f'{source_number}']['rf']) = True
                    (derived_quant['deposition'][f'{source_number}']['dc']) = False
            # Extract the deposition voltage for each source
            # by distinguishing the rf and dc cases
            if derived_quant['deposition'][f'{source_number}']['dc']:
                derived_quant['deposition'][f'{source_number}']['start_voltage'] = (
                int(
                    deposition.data[f'Source {source_number} Voltage']
                    .iloc[: (int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(deposition.data)))]
                    .mean()
                )
            )
                derived_quant['deposition'][f'{source_number}']['end_voltage'] = (
                deposition.data[f'Source {source_number} Voltage']
                .iloc[-(int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(deposition.data))) :]
                .mean()
            )
                derived_quant['deposition'][f'{source_number}']['avg_voltage'] = (
                deposition.data[f'Source {source_number} Voltage'].mean()
            )
            elif derived_quant['deposition'][f'{source_number}']['rf']:
                derived_quant['deposition'][f'{source_number}']['start_voltage'] = (
                deposition.data[f'Source {source_number} DC Bias']
                .iloc[: (int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(deposition.data)))]
                .mean()
            )
                derived_quant['deposition'][f'{source_number}']['end_voltage'] = (
                deposition.data[f'Source {source_number} DC Bias']
                .iloc[-(int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(deposition.data))) :]
                .mean()
            )
                derived_quant['deposition'][f'{source_number}']['avg_voltage'] = (
                deposition.data[f'Source {source_number} DC Bias'].mean()
            )
            # Extract the deposition rate of the Metal-P-S film
            if not deprate2_film_meas[f'{source_number}'].data.empty:
                derived_quant['deposition'][f'{source_number}']['deposition_rate'] = (
                deprate2_film_meas[f'{source_number}'].data[
                'Thickness Rate'
            ].mean())
                derived_quant['deposition'][f'{source_number}']['deposition_rate_mat'] = (
                deprate2_film_meas[f'{source_number}'].data[
                'Thickness Active Material'
            ].iloc[0])

        # Extract source material and target id and add the element to the
        # elements list for the material space extraction
            source_element = str(
            deposition.data[f'PC Source {source_number} Material'].iloc[0]
        )
            derived_quant['deposition'][f'{source_number}']['material'] = element(
            source_element
        ).symbol
            derived_quant['deposition'][f'{source_number}']['target_id'] = (
            deposition.data[f'PC Source {source_number} Loaded Target'].iloc[0]
        )
            elements = elements + [element(source_element).symbol]

    # Extract the material space as the elements used during deposition
    if derived_quant['deposition']['avg_ph3_flow'] > MFC_FLOW_THRESHOLD:
        elements = elements + ['P']
    if (derived_quant['deposition']['avg_h2s_flow'] > MFC_FLOW_THRESHOLD) or (
    derived_quant['deposition']['cracker']['enabled']
    ):
        elements = elements + ['S']
    # add the element as an hypen separated string
    derived_quant['material_space'] = '-'.join(elements)



    return derived_quant

def extract_end_of_process(derived_quant,data):
    # Extract the end of process temperature as the last temperature logged
    # Note: this part can be improved by extracting the temperature at
    # the vent recipe step
    derived_quant['end_of_process_temp'] = data['Substrate Heater Temperature'].iloc[-1]

    # Extract the time in chamber after deposition as the time difference
    # between end of logging and end of deposition time
    derived_quant['time_in_chamber_after_deposition'] = (
    derived_quant['log_end_time'] - derived_quant['deposition']['end_time']
    )
    return derived_quant

def extract_sub_ramp_up_params(derived_quant, ramp_up_temp, data):
    if not derived_quant['deposition']['rt']:
        # ------Extract the substrate ramp up parameters------
        # Extract the number of ramp up events¨
        derived_quant['sub_ramp_up']['num_events'] = ramp_up_temp.events

        # Extract the slope assuming linear ramp up
        # In data_ramp_up_temp only increasing setpoint temperature are
        # considered making easier to extract the slope
        derived_quant['sub_ramp_up']['start_time'] = ramp_up_temp.data[
            'Time Stamp'
        ].iloc[0]
        derived_quant['sub_ramp_up']['end_time'] = ramp_up_temp.data[
            'Time Stamp'
        ].iloc[-1]
        derived_quant['sub_ramp_up']['duration'] = (
            derived_quant['sub_ramp_up']['end_time']
            - derived_quant['sub_ramp_up']['start_time']
        )
        temp_diff = (
            ramp_up_temp.data['Substrate Heater Temperature Setpoint'].iloc[-1]
            - ramp_up_temp.data['Substrate Heater Temperature Setpoint'].iloc[0]
        )
        time_interval_minutes = (
            derived_quant['sub_ramp_up']['duration'].total_seconds() / 60
        )
        derived_quant['sub_ramp_up']['temp_slope'] = temp_diff / time_interval_minutes
        # Extract the time plateau as the time difference between the
        # start of the deposition and the end of the ramp up (i.e. the time at
        # constant high temperature before the deposition)
        derived_quant['sub_ramp_up']['time_plateau'] = (
            derived_quant['deposition']['start_time']
            - derived_quant['sub_ramp_up']['end_time']
        )
        # Extract the average capman pressure during the ramp up
        derived_quant['sub_ramp_up']['avg_capman_pressure'] = ramp_up_temp.data[
            'PC Capman Pressure'
        ].mean()
        # Extract the gas flows during the substrate ramp up
        # If the flows are below the noise level threshold,
        # we set the flow to 0
        derived_quant['sub_ramp_up']['avg_ar_flow'] = (
            ramp_up_temp.data['PC MFC 1 Flow'].mean()
            if not ramp_up_temp.data[ramp_up_temp.data['PC MFC 1 Flow'] > 1][
                'PC MFC 1 Flow'
            ].empty
            else 0
        )
        derived_quant['sub_ramp_up']['avg_ph3_flow'] = (
            ramp_up_temp.data['PC MFC 4 Flow'].mean()
            if not ramp_up_temp.data[ramp_up_temp.data['PC MFC 4 Flow'] > 1][
                'PC MFC 4 Flow'
            ].empty
            else 0
        )
        derived_quant['sub_ramp_up']['avg_h2s_flow'] = (
            ramp_up_temp.data['PC MFC 6 Flow'].mean()
            if not ramp_up_temp.data[ramp_up_temp.data['PC MFC 6 Flow'] > 1][
                'PC MFC 6 Flow'
            ].empty
            else 0
        )
        # Extract if the cracker has been used during ramp up
        # The column 'Sulfur Cracker Control Enabled' correspond to the
        # act of opening the cracker pulse valve (1 open, 0 closed)
        if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
            if (
                (ramp_up_temp.data['Sulfur Cracker Control Enabled'] == 1).all()
                and (
                    ramp_up_temp.data['Sulfur Cracker Zone 1 Current Temperature']
                    > CRACKER_ZONE_1_MIN_TEMP
                ).all()
                and (
                    ramp_up_temp.data['Sulfur Cracker Zone 2 Current Temperature']
                    > CRACKER_ZONE_2_MIN_TEMP
                ).all()
                and (
                    ramp_up_temp.data['Sulfur Cracker Zone 3 Current Temperature']
                    > CRACKER_ZONE_3_MIN_TEMP
                ).all()
            ):
                derived_quant['sub_ramp_up']['cracker']['enabled'] = True
                # If the cracker has been used, extract the cracker parameters
                derived_quant['sub_ramp_up']['cracker']['zone1_temp'] = (
                    ramp_up_temp.data[
                        'Sulfur Cracker Zone 1 Current Temperature'
                    ].mean()
                )
                derived_quant['sub_ramp_up']['cracker']['zone2_temp'] = (
                    ramp_up_temp.data[
                        'Sulfur Cracker Zone 2 Current Temperature'
                    ].mean()
                )
                derived_quant['sub_ramp_up']['cracker']['zone3_temp'] = (
                    ramp_up_temp.data[
                        'Sulfur Cracker Zone 3 Current Temperature'
                    ].mean()
                )
                derived_quant['sub_ramp_up']['cracker']['pulse_width'] = (
                    ramp_up_temp.data[
                        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                    ].mean()
                )
                derived_quant['sub_ramp_up']['cracker']['pulse_freq'] = (
                    ramp_up_temp.data['Sulfur Cracker Control Valve Setpoint Feedback'].mean()
                )
            else:
                derived_quant['sub_ramp_up']['cracker']['enabled'] = False
        else:
            derived_quant['sub_ramp_up']['cracker']['enabled'] = False
    return derived_quant

def extract_sub_ramp_down_params(derived_quant, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp):
    if not derived_quant['deposition']['rt']:
        # ------Extract the substrate ramp down parameters------
        # Extract the number of ramp down events
        derived_quant['sub_ramp_down']['events'] = ramp_down_temp.events
        derived_quant['sub_ramp_down']['events_high_temp'] = ramp_down_high_temp.events
        derived_quant['sub_ramp_down']['events_low_temp'] = ramp_down_low_temp.events

        # Extract the slope from when the temp in controled,
        # assuming linear ramp up
        # In data_ramp_down_temp only decreasing setpoint temperature are
        # considered making easier to extract the slope
        start_time = ramp_down_temp.data['Time Stamp'].iloc[0]
        end_time = ramp_down_temp.data['Time Stamp'].iloc[-1]
        time_interval = end_time - start_time
        temp_diff = -(
            ramp_down_temp.data['Substrate Heater Temperature Setpoint'].iloc[-1]
            - ramp_down_temp.data['Substrate Heater Temperature Setpoint'].iloc[0]
        )
        time_interval_minutes = time_interval.total_seconds() / 60
        derived_quant['sub_ramp_down']['temp_slope'] = temp_diff / time_interval_minutes
        # Now we distinguish between the high temp and low temp ramp down phase
        # Extract the start time of the ramp down as the first time of
        # the high temperature ramp down and the end time as the last time of
        # the low temperature ramp down (which is the last time of the log)
        derived_quant['sub_ramp_down']['start_time'] = ramp_down_high_temp.data[
            'Time Stamp'
        ].iloc[0]
        if not ramp_down_low_temp.data.empty:
            derived_quant['sub_ramp_down']['end_time'] = ramp_down_low_temp.data[
                'Time Stamp'
            ].iloc[-1]
        else:
            derived_quant['sub_ramp_down']['end_time'] = ramp_down_high_temp.data[
                'Time Stamp'
            ].iloc[-1]
        derived_quant['sub_ramp_down']['duration'] = (
            derived_quant['sub_ramp_down']['end_time']
            - derived_quant['sub_ramp_down']['start_time']
        )
        # Extract the time plateau as the time difference between the
        # end of the deposition and the start of the ramp down
        derived_quant['sub_ramp_up']['time_plateau'] = (
            derived_quant['sub_ramp_down']['start_time']
            - derived_quant['deposition']['end_time']
        )
        # Extract the gases used during the high substrate ramp down
        derived_quant['sub_ramp_down']['avg_ar_flow'] = (
            ramp_down_high_temp.data[
                ramp_down_high_temp.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD
            ]['PC MFC 1 Flow'].mean()
            if not ramp_down_high_temp.data[
                ramp_down_high_temp.data['PC MFC 1 Flow'] > MFC_FLOW_THRESHOLD
            ]['PC MFC 1 Flow'].empty
            else 0
        )
        derived_quant['sub_ramp_down']['avg_ph3_flow'] = (
            ramp_down_high_temp.data[
                ramp_down_high_temp.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD
            ]['PC MFC 4 Flow'].mean()
            if not ramp_down_high_temp.data[
                ramp_down_high_temp.data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD
            ]['PC MFC 4 Flow'].empty
            else 0
        )
        derived_quant['sub_ramp_down']['avg_h2s_flow'] = (
            ramp_down_high_temp.data[
                ramp_down_high_temp.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD
            ]['PC MFC 6 Flow'].mean()
            if not ramp_down_high_temp.data[
                ramp_down_high_temp.data['PC MFC 6 Flow'] > MFC_FLOW_THRESHOLD
            ]['PC MFC 6 Flow'].empty
            else 0
        )
        # Extract if the cracker has been used during ramp down
        if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
            if (
                (ramp_down_high_temp.data['Sulfur Cracker Control Enabled'] == 1).all()
                and (
                    ramp_down_high_temp.data['Sulfur Cracker Zone 1 Current Temperature']
                    > CRACKER_ZONE_1_MIN_TEMP
                ).all()
                and (
                    ramp_down_high_temp.data['Sulfur Cracker Zone 2 Current Temperature']
                    > CRACKER_ZONE_2_MIN_TEMP
                ).all()
                and (
                    ramp_down_high_temp.data['Sulfur Cracker Zone 3 Current Temperature']
                    > CRACKER_ZONE_3_MIN_TEMP
                ).all()
            ):
                derived_quant['sub_ramp_down']['cracker']['enabled'] = True
                # if the crack has been used, extract the cracker parameters
                derived_quant['sub_ramp_down']['cracker']['zone1_temp'] = (
                    ramp_down_high_temp.data[
                        'Sulfur Cracker Zone 1 Current Temperature'
                    ].mean()
                )
                derived_quant['sub_ramp_down']['cracker']['zone2_temp'] = (
                    ramp_down_high_temp.data[
                        'Sulfur Cracker Zone 2 Current Temperature'
                    ].mean()
                )
                derived_quant['sub_ramp_down']['cracker']['zone3_temp'] = (
                    ramp_down_high_temp.data[
                        'Sulfur Cracker Zone 3 Current Temperature'
                    ].mean()
                )
                derived_quant['sub_ramp_down']['cracker']['pulse_width'] = (
                    ramp_down_high_temp.data[
                        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                    ].mean()
                )
                derived_quant['sub_ramp_down']['cracker']['pulse_freq'] = (
                    ramp_down_high_temp.data['Sulfur Cracker Control Valve Setpoint Feedback'].mean()
                )
            else:
                derived_quant['sub_ramp_down']['cracker']['enabled'] = False
        else:
            derived_quant['sub_ramp_down']['cracker']['enabled'] = False
        # Extract the anion input cutoff temperature as the last temperature of
        # the high temperature ramp down
        derived_quant['sub_ramp_down']['anion_input_cutoff_temp'] = (
            ramp_down_high_temp.data['Substrate Heater Temperature Setpoint'].iloc[-1]
        )
        derived_quant['sub_ramp_down']['anion_input_cutoff_time'] = (
            ramp_down_high_temp.data['Time Stamp'].iloc[-1]
        )
    return derived_quant

def plot_matplotlib_timeline(logfile_name, data, source_used_list,
                bottom_steps, other_steps, step_colors):
    '''
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
        step_colors: dict
            Dictionary containing the colors to be used for each step
            in the plot
    '''

    # Remove the steps in bottom_steps that have empty bounds
    bottom_steps = [step for step in bottom_steps if step.bounds]

    #The non_source_steps are Lf_Event objects
    non_source_steps = [step for step in other_steps if type(step) == Lf_Event]

    #Remove the non_source_steps that have empty bounds
    non_source_steps = [step for step in non_source_steps if step.bounds]

    # Number of steps at the bottom of the graph
    number_step_bottom = len(bottom_steps)

    # Combine bottom_steps and non_source_steps
    all_non_source_steps = bottom_steps + non_source_steps

    #The source steps are dictorionaries with the source number as key
    source_steps = [step for step in other_steps if type(step) == dict]

    #Remove the source_steps that have empty bounds
    for source_number in source_used_list:
        source_steps = [step for step in source_steps if (
            step.get(f'{source_number}')) and step[f'{source_number}'].bounds]

    steps_plot = {
    'name': [],
    'bounds': []
    }
    # Extract the variable names and bounds
    for step in all_non_source_steps:
        steps_plot['name'].append(step.name)
        steps_plot['bounds'].append(step.bounds)

    for source_number in source_used_list:
        for step in source_steps:
            if step[f'{source_number}'].bounds:
                steps_plot['name'].append(step[f'{source_number}'].name)
                steps_plot['bounds'].append(step[f'{source_number}'].bounds)

    # Print a message to the console
    print('Generating the matplotlib plot')

    #initialize the figure
    timeline = plt.figure(figsize=(8, 3))

    # Create a figure and axis
    ax = timeline.add_subplot(111)

    # Set up the axis limits and labels
    ax.set_xlim(data['Time Stamp'].iloc[0], data['Time Stamp'].iloc[-1])
    ax.set_xlabel('Time', fontsize=12)

    # Set time ticks format
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

    # Title of the plot
    ax.set_title(f'Process Timeline for sample:\n{logfile_name}', #y=-0.5,
    fontsize=12, pad=20)


    # Defining to counters to keep track of the current step
    # and when to start stacking events on top of each other
    i,j = 0, 0
    while i < len(steps_plot['name']):
        label_added = False  # Flag to track if the label has been added
        #let k iterate over the number of events in the step
        for k in range(len(steps_plot['bounds'][i])):
            # Get the bounds
            start_time = steps_plot['bounds'][i][k][0]
            end_time = steps_plot['bounds'][i][k][1]
            # Plot the step as a horizontal line
            ax.axvspan(
            start_time,
            end_time,
            # Set the y position of the step to match the vertical
            # extent of the graphs (0<y<2)
            ymin=j/(len(steps_plot['name'])-number_step_bottom+1),
            ymax=(j+1)/(len(steps_plot['name'])-number_step_bottom+1),
            color=step_colors[steps_plot['name'][i]],
            label=steps_plot['name'][i] if not label_added else "",  # Add label only if not already added
            )
            label_added = True  # Set the flag to True after adding the label
        i += 1
        #Only increment the counter responsible for stacking the events on top of each
        # other after the step number NUMBER_STEPS_BOTTOM has been reached
        if i > number_step_bottom-1:
            j += 1

    # Get the handles and labels from the current legend
    handles, labels = ax.get_legend_handles_labels()

    # Reverse the order of handles and labels
    handles.reverse()
    labels.reverse()

    # Create the legend with the reversed order outside the graph
    ax.legend(handles, labels, loc='upper left', bbox_to_anchor=(1, 1.3))

    #  Remove the y axis ticks and labels
    ax.set_yticks([])
    ax.set_ylabel('')

    return timeline

def save_report_as_text(derived_quant, logfile_dir, logfile_name):

# Save the derived quantities report as a text file as
    with open(txt_file_path, 'w') as txt_file:
        txt_file.write(
        f'Derived quantities report for logfile\n{logfile_name}:\n\n'
    )
        txt_file.write(write_derived_quantities(derived_quant))

def steps_to_nomad(steps_list,source_list):
    '''
    Function to convert the list of steps to the NOMAD format, which is a list of
    dictionaries with the following keys
    - name: str
        Name of the step
    - data: pd.DataFrame
        Dataframe containing the data of the step
    - bounds: tuple
        Tuple containing the start and end time of the step
    args:
        steps_list: list of steps to be converted to the NOMAD compatible format
        source_list: list of sources in the raw data during the process
    The function also sorts the steps by the start time
    The consequence is that the definintion only expect non overlapping steps
    '''
    #Initialize the list to store the nomad steps
    nomad_steps_list = []
    for step in steps_list:
        #If the step is not source dependent, then the name is a string
        if type(step['name']) == str:
            #We iterate over the number of events in the step
            for i in range(step['events']):
                filtered_step = {}
                #Filter the data to only include the data within the bounds
                filtered_step['data'] = event_filter(step['data'], step['bounds'][i])
                #We name the step as the name of the step with the event number
                filtered_step['name'] = f'{step[f'name']}({i})'
                #We add the bounds of the step
                filtered_step['bounds'] = step['bounds'][i]
                #We append the filtered step to the nomad steps list
                nomad_steps_list.append(filtered_step)
        #If the step is source dependent, then the name is a dictionary
        elif type(step['name']) == dict:
            #see comments above
            for source_number in source_list:
                for i in range (step['events'][f'{source_number}']):
                    filtered_step = {}
                    filtered_step['data'] = event_filter(step[f'{source_number}'].data, step['bounds'][f'{source_number}'][i])
                    filtered_step['name'] = f'{step[f'name'][f'{source_number}']}({i})'
                    filtered_step['bounds'] = step['bounds'][f'{source_number}'][i]
                    nomad_steps_list.append(filtered_step)
    #We order the steps by the start time
    sorted_nomad_steps_list = sorted(nomad_steps_list, key=lambda x: x['bounds'][0])

    return sorted_nomad_steps_list


def plot_plotly_extimeline(logfile_name, data, source_used_list, steps_to_plot,
                            step_colors):
    '''
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
        step_colors: dict
            Dictionary containing the colors to be used for each step
            in the plot
    '''

    # Printing that the plot is being generated
    print('Generating the plotly plot')

    #Format the steps to be plotted for the plotly timeline
    rows = []
    for step in steps_to_plot:
        if type(step) == Lf_Event:
            for bounds in step.bounds:
                rows.append({
                    'Event': step.name,
                    'Start': bounds[0],
                    'End': bounds[1]
                })
        elif type(step) == dict:
            for source_number in source_used_list:
                for bounds in step[f'{source_number}'].bounds:
                    rows.append({
                        'Event': step[f'{source_number}'].name,
                        'Start': bounds[0],
                        'End': bounds[1]
                    })

    df = pd.DataFrame(rows)

    # Determine the timeline duration
    min_start_time = df['Start'].min()
    max_end_time = df['End'].max()
    timeline_duration = (max_end_time - min_start_time).total_seconds() / 3600  # Duration in hours

    # Calculate dynamic width and height
    num_events = len(df['Event'].unique())
    width = max(900, timeline_duration * 50)  # Minimum width 800px, scale with duration
    height = max(500, num_events * 30)  # Minimum height 600px, scale with number of events
    # Create the plot with plotly express.timeline
    fig = px.timeline(df, x_start='Start', x_end='End', y='Event', color='Event',
                      color_discrete_map=step_colors,
                      title='Process Timeline')
    # Update the layout to include a border around the plot area
    fig.update_layout(
        xaxis_title='Time',
        yaxis_title=None,
        yaxis=dict(
            tickvals=df['Event'].unique(),
            ticktext=df['Event'].unique(),
            autorange='reversed'  # Ensure tasks are displayed in order
        ),
        template='plotly_white',  # Use a white background template
        title=dict(
            text=f'Process Timeline',  # Title text
            x=0.5,  # Center the title horizontally
            y=0.85,  # Position the title vertically
            xanchor='center',  # Anchor the title at the center horizontally
            yanchor='top',  # Anchor the title at the top vertically
            font=dict(size=16)  # Font size of the title
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
                line=dict(
                    color='black',
                    width=1
                )
            )
        ]
    )

    return fig

def unfold_events(all_lf_events,data):
    all_sub_lf_events = []
    for step in all_lf_events:
        if 'Time Stamp' in step.data.columns:
            if step.events > 1:
                for i in range(step.events):
                    new_step = Lf_Event(step.sep_name[i],data)
                    new_step.set_data(step.sep_data[i])
                    all_sub_lf_events.append(new_step)
            else:
                all_sub_lf_events.append(step)
    return all_sub_lf_events



# %%
#---------------MAIN-----------

# ---------REFERENCE VALUES-------------

# Set of reference values used in different parts of the script

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
NUM_TIMESTEP = 3
# Minimum size of a domain in terms of the average timestep
MIN_DOMAIN_SIZE = 3
# Size of the temperature control domains above which we consider that the
# temperature control was on
MIN_TEMP_CTRL_SIZE = 10
# Max pressure to read the base pressure
MAX_BASE_PRESSURE = 1e-6  # Torr
# variation in percent to consider that the cracker temperature is the same
# as the cracker temperature during deposition to read the cracker induced
# base pressure
CRACKER_DIFF_PARAM = 10  # %
# Default dpi for the figures
FIG_EXPORT_DPI = 300  # dpi
# Define a dictionary for step colors in the timeline plot
STEP_COLORS = {
    'Deposition': 'blue',
    'Sub Temp Ramp Up': 'green',
    'Sub High Temp Ramp Down': 'red',
    'Sub Low Temp Ramp Down': 'pink',
    'Source 4 Ramp Up': 'purple',
    'Source 4 On': '#EE82EE',  # Violet
    'Source 4 Presput': 'magenta',
    'Source 4 MePS Dep Rate Meas':'#DA70D6',  # Orchid
    'Source 3 Ramp Up': 'blue',
    'Source 3 On': '#1E90FF',  # Dodger Blue
    'Source 3 Presput': '#87CEFA',  # Light Sky Blue
    'Source 3 MePS Dep Rate Meas':'#4682B4',  # Steel Blue
    'Source 1 Ramp Up': '#006400',  # Dark Green
    'Source 1 On ': 'green',
    'Source 1 Presput': '#90EE90',  # Light Green
    'Source 1 MePS Dep Rate Meas':'#32CD32',  # Lime Green
    'Cracker On Open': 'yellow',
    'H2S On': 'orange',
    'PH3 On': 'cyan',
    'Ar On': 'black',
    'S Dep Rate Meas': '#B22222',# Firebrick
    'Cracker Pressure Meas': 'brown'
}

# ---------GET THE NAMES OF ALL THE LOGFILES IN THE DIRECTORY-------------

logfile_dir = r'O:\Intern\Phosphosulfides\Data\deposition logs'
logfile_extension = 'CSV'

#Read all the logfiles in the directory
# Read all the logfiles in the directory, removing only the .CSV extension
logfile_names = [
    re.sub(rf'\.{logfile_extension}$', '', file)
    for file in os.listdir(logfile_dir)
    if re.match(r'^\w+\d{4}\w+', file) and file.endswith(f'.{logfile_extension}')
]
#Remove mittma_0002_Cu__H2S_and_PH3_RT_Recording Set 2024.04.17-17.54.07
# from the logfile_names
logfile_names.remove('mittma_0002_Cu__H2S_and_PH3_RT_Recording Set 2024.04.17-17.54.07')

# %%
# Loop over all the logfiles in the directory
# logfile_names= ['mittma_0005_Cu_RecordingSet 2024.05.24-12.21.19']


for logfile_name in logfile_names:
    # Default Logfile location
    print(f'Processing logfile: {logfile_name}')
    logfile_path = f'{logfile_dir}/{logfile_name}.{logfile_extension}'

    # ---------DEFAULT EXPORT LOCATIONS-------------
    # Specify the path and filename for the report text file
    txt_file_dir = os.path.join(logfile_dir, 'derived_quantities_txt_files')
    txt_file_name = f'{logfile_name}_derived_quantities.txt'
    txt_file_path = os.path.join(txt_file_dir, txt_file_name)

    # Specify the path and filename for the matplotlib graph
    matplotlib_graph_file_dir = os.path.join(logfile_dir, 'matplotlib_process_timeline_graphs')
    matplotlib_graph_file_name = f'{logfile_name}_matplotlib_timeline.png'
    matplotlib_graph_file_path = os.path.join(matplotlib_graph_file_dir, matplotlib_graph_file_name)

    #Same for the plotly graph
    plotly_graph_file_dir = os.path.join(logfile_dir, 'plotly_process_timeline_graphs')
    plotly_graph_file_name = f'{logfile_name}_plotly_timeline.png'
    plotly_graph_file_path = os.path.join(plotly_graph_file_dir, plotly_graph_file_name)

    # ---------READ THE DATA-------------

    # Read the log file and spectrum data

    print(f'Reading the logfile')
    data = read_logfile(logfile_path)



    #---------FORMATTING THE DATAFRAME FOR CONDITIONAL FILTERING------------

    print(f'Formatting the dataframe for conditional filtering')

   # ---------RENAME THE CRACKER COLUMNS OF THE DATAFRAME------------
    data=rename_cracker_columns(data)

    # ---------READING THE SOURCE USED--------

    # Get the source list automatically from the logfile
    source_list = get_source_list(data)

    # ---------CONNECTING THE SOURCES TO THE POWER SUPPLIES--------

    # Read what source is connected to which power supply and
    # create column names that relate directly to the source instead
    # of the power supply

    connect_source_to_power_supply(data, source_list)

    # ---------DEFINE DE CONDITIONS FOR DIFFERENT EVENTS-------------

    #Initialize the list of all events
    all_lf_events = []

    # ---------1/CONDITIONS FOR THE PLASMA ON OR BEING RAMPED UP--------

    source_on, source_ramp_up = filter_data_plasma_on_ramp_up(
        data, source_list)

    for source_number in source_list:
        if source_on[f'{source_number}']:
            all_lf_events.extend([source_on[f'{source_number}'],
                                 source_ramp_up[f'{source_number}']])

    # ---------2/CONDITION FOR THE CRACKER BEING ON--------

    cracker_on_open = filter_data_cracker_on_open(data)

    all_lf_events.append(cracker_on_open)

    # ---------3/CONDITION FOR THE TEMPERATURE CONTROL--------

    temp_ctrl = filter_data_temp_ctrl(data)

    all_lf_events.append(temp_ctrl)

    # ----- 4/CONDITIONS FOR THE DIFFERENT GASES BEING FLOWN--------

    ph3, h2s, ar = filter_gas(data)

    all_lf_events.extend([ph3, h2s, ar])

    # ---------5/CONDITIONS FOR THE DEPOSITION--------

    any_source_on, any_source_on_open, deposition, source_used_list = (
    filter_data_deposition(data, source_list, source_on)
    )

    all_lf_events.extend([any_source_on, any_source_on_open, deposition])

    # ---------6/CONDITIONS FOR THE DIFFERENT SOURCES BEING PRESPUTTERED--------

    source_presput = filter_data_plasma_presput(data, source_list,
                            source_on, source_ramp_up,
                            cracker_on_open, ph3, h2s, deposition)

    for source_number in source_used_list:
        all_lf_events.append(source_presput[f'{source_number}'])

    # ---------7/CONDITIONS FOR THE S CRACKER PRESSURE MEAS--------

    #Filter the data for the S Cracker pressure
    cracker_base_pressure = filter_data_cracker_pressure(
    data, cracker_on_open, ph3, h2s, ar, deposition)

    all_lf_events.append(cracker_base_pressure)


    # ---------8/CONDITIONS FOR THE DEPOSITION RATE MEASUREMENT--------

    deprate2_film_meas, deprate2_meas, xtal2_open, deprate2_sulfur_meas = (
    filter_data_film_dep_rate(data, deposition, source_list,
                            cracker_on_open, ph3, h2s, any_source_on_open))

    all_lf_events.extend([deprate2_meas, xtal2_open, deprate2_sulfur_meas])
    for source_number in source_used_list:
        all_lf_events.append(deprate2_film_meas[f'{source_number}'])
    # ---9/CONDITIONS FOR THE SUBSTRATE TEMPERATURE RAMPING UP OR DOWN-----

    # Filter the data for the substrate temperature ramping up or down
    ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp = (
    filter_data_temp_ramp_up_down(data,cracker_on_open,temp_ctrl,
                            ph3, h2s, deposition))

    all_lf_events.extend([ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp])

    #Remove the empty events from the all_lf_events
    all_lf_events = [event for event in all_lf_events if event.bounds]

    #Unfold the all_lf_events to make a list of all subevents
    all_sub_lf_events = unfold_events(all_lf_events,data)

    # ---EXTRACT DERIVED QUANTITIES IN A DICIONARY TO INPUT IN NOMAD----

    # Initialize the nested dictionary to store derived quantities
    derived_quant = init_derived_quant(source_list)

    # Call the method to extract sample information
    derived_quant = extract_overview(derived_quant, logfile_name, data)

    # ---DEPOSITION PARAMETERS-----

    #Extract if the deposition is at room temperature
    derived_quant = extract_rt_bool(derived_quant, temp_ctrl, deposition)
    #Extract what sources are used during deposition
    derived_quant = extract_source_used_deposition(
    derived_quant, source_list, deposition, source_presput)
    #Extract the parameters of the S cracker during deposition
    derived_quant = extract_cracker_params(derived_quant, data, deposition, cracker_base_pressure)

    #Extract some pressure parameters during deposition
    derived_quant = extract_pressure_params(derived_quant, data, deposition)


    #Extract simple (non cource dependent) deposition parameters
    derived_quant = extract_simple_deposition_params(derived_quant,deposition)

    #Extract the presputtering parameters for the sources
    derived_quant = extract_source_presput_params(derived_quant, source_list, source_presput)
    #Extract the ramp up parameters for the sources
    derived_quant = extract_source_ramp_up_params(derived_quant, source_list, source_ramp_up, data)

    #Extract the source dependent deposition parameters
    dervied_quant = extract_source_deposition_params(derived_quant, source_list, deposition, deprate2_film_meas)

    #Extract so called end of process parameters
    dervied_quant = extract_end_of_process(derived_quant,data)

    #Extract the substrate ramp up parameters
    derived_quant = extract_sub_ramp_up_params(derived_quant, ramp_up_temp, data)

    #Extract the substrate ramp down parameters
    derived_quant = extract_sub_ramp_down_params(derived_quant, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp)


    # --------PRINT DERIVED QUANTITIES REPORT-------------

    # print(f'Derived quantities report for logfile\n{logfile_name}:\n')
    # print_derived_quantities(derived_quant)


    # ---SAVE THE REPORT QUANTITIES IN A TEXT FILE---

    save_report_as_text(derived_quant, logfile_dir, logfile_name)


    # --------GRAPH THE DIFFERENT STEPS ON A TIME LINE------------

    # Here we use the different bounds of the different events to plot them
    # as thick horizontal lines on a time line, with the different events names

    # Define the steps appearing at the bottom of the graph
    bottom_steps = [
    ramp_up_temp, deposition, ramp_down_high_temp, ramp_down_low_temp
    ]

    other_steps = [
    cracker_on_open, h2s, ph3, ar,
    deprate2_sulfur_meas, cracker_base_pressure,
    source_ramp_up, source_on, source_presput, deprate2_film_meas]

    #Using matplotlib

    # Create the figure and axis

    matplotlib_timeline = plot_matplotlib_timeline(logfile_name, data, source_used_list, bottom_steps,
                            other_steps, STEP_COLORS)
    # Save the graph as a png file

    # Save the graph as a png file

    matplotlib_timeline.savefig(matplotlib_graph_file_path, dpi=FIG_EXPORT_DPI, bbox_inches='tight')

    #Using plotly

    # steps_to_plot = [ramp_up_temp, deposition, ramp_down_high_temp, ramp_down_low_temp,
    #     cracker_on_open, h2s, ph3, ar,
    #     deprate2_sulfur_meas, cracker_base_pressure,
    #     source_ramp_up, source_on, source_presput, deprate2_film_meas]

    steps_to_plot = all_lf_events

    # Create the figure
    plotly_timeline = plot_plotly_extimeline(logfile_name, data, source_used_list, steps_to_plot,
                            STEP_COLORS)
    # Save the graph as a png file

    #show the plot
    # plotly_timeline.show()

    # plotly_timeline.write_image(plotly_graph_file_path, width=800, height=300, scale=1)


#------TESTING GROUND--------

