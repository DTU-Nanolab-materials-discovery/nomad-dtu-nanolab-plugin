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

# %%
# ---------FILES LOCATIONS-------------

# Logfile location
logfile_dir = r'O:\Intern\Phosphosulfides\Data\deposition logs'
logfile_name = 'mittma_0015_Cu_Recording Set 2024.08.02-10.52.28'
logfile_extension = 'CSV'
logfile_path = f'{logfile_dir}/{logfile_name}.{logfile_extension}'

# %%
# ---------REFERENCE VALUES-------------

# Set of reference values used in different parts of the script

# VERSION
version = 'v0.0.20'

# Eletrical current threshold above which a dc plasma is considered on
current_threshold = 0.01  # miliamps
# Bias threshold above which a rf plasma is considered on
bias_threshold = 0.01  # volts
# Power setpoint difference threshold above which a
# plasma is considered ramping up
power_setpoint_diff_threshold = 0.01  # watts
# Temperature setpoint difference threshold above which the
# substrate temp is considered ramping up
temp_setpoint_diff_threshold = 0.11  # degrees
# Temperature setpoint of cracker's zones above which the
# the cracker is considered on
cracker_zone1_min_temp = 70  # degrees
cracker_zone2_min_temp = 150  # degrees
cracker_zone3_min_temp = 200  # degrees
# Temperature below which the deposition is considered room temperature
rt_temp_threshold = 30  # degrees
# Time for the qcm to stabilize after the Xtal 2 shutter opens
stab_time = 30  # seconds
# Threshold above which the flow of the mfc is considered on
mfc_flow_threshold = 1  # sccm
# Fraction of the length of the deposition dataframe to consider for the
# beginning and end of the deposition voltage averaging
fraq_rows_avg_voltage = 5  # %
# Number of timesteps to consider for the continuity limit
num_timestep = 3
# Minimum size of a domain in terms of the average timestep
min_domain_size = 3
# Size of the temperature control domains above which we consider that the
# temperature control was on
min_temp_ctrl_size = 10
# Max pressure to read the base pressure
max_base_pressure = 1e-6  # Torr
# variation in percent to consider that the cracker temperature is the same
# as the cracker temperature during deposition to read the cracker induced
# base pressure
cracker_param = 5  # %

# %%
# ---------FUNCTION DEFINITIONS-------------


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
    # work on a copy of the DataFrame
    df3 = pd.DataFrame()
    # Calculate the average time step of df2
    avg_timestep = cal_avg_timestep(df2, timestamp_col)
    # Set the continuity limit as num_timestep the average time step
    continuity_limit = num_timestep * avg_timestep
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
    # interval so only keep big domains
    bounds = [
        bound
        for bound in bounds
        if (bound[1] - bound[0]) > min_domain_size * avg_timestep
    ]
    return bounds


# a function that filters a dataframe based on two bouds of time
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


# %%
# ---------READ THE DATA-------------

# Read the log file and spectrum data
data = read_logfile(logfile_path)

# Ensure all timestamps in the log file and spectrum are tz-naive
data['Time Stamp'] = data['Time Stamp'].dt.tz_localize(None)

# %%
# ---------DEFINE DE CONDITIONS FOR DIFFERENT EVENTS-------------

# Initialize dictionaries to store the ramp up, plasma on, and
# presputtering conditions and corresponding data for each source
source_ramp_up_cond_dict = {}
data_source_ramp_up_dict = {}
bounds_events_source_ramp_up_dict = {}
num_events_source_ramp_up_dict = {}

source_on_cond_dict = {}
data_source_on_dict = {}
bounds_events_source_on_dict = {}
num_events_source_on_dict = {}

source_presput_cond_dict = {}
data_source_presput_dict = {}
bounds_events_source_presput_dict = {}
num_events_source_presput_dict = {}

# ---------READING THE SOURCE USED--------

# Get the source list automatically from the logfile
# (Ex: source_list = [1, 3, 4])
source_list = []
for col in data.columns:
    if col.startswith('PC Source') and col.endswith('Loaded Target'):
        source_number = int(col.split()[2])
        source_list.append(source_number)

# ---------CONNECTING THE SOURCES TO THE POWER SUPPLIES--------

# Read what source is connected to which power supply and creates column
# names that relate directly to the source instead of the power supply
# Iterate over source numbers and perform column creation
# (Ex: 'Power Supply 1 DC Bias' -> 'Source 4 DC Bias')
# Additiomal we check if, at any point the shutter
# is open and the source is switch at the same time
# to ensure that the algorithm does think that we used a source if
# we switched it on to a power supply by mistake
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

# ---------CONDITIONS FOR THE PLASMA ON OR BEING RAMPED UP--------

# For all the sources, we read the dataframe for columns that
# give indication#of the status of the source (current,
# dc bias, output setpoint)#and create conditions for the
# plasma being on and being ramped up
# (Ex : plasma being on is defined as the current being above a
# threshold or the dc bias being above a threshold and the
# source being enabled)
# Because we have performed the previous step, we can now
# directly use the source number to create the conditions if we handle
# the case where the column does not exist in the dataframe
for source_number in source_list:
    enabled = (
        data.get(f'Source {source_number} Enabled', pd.Series([0] * len(data))) != 0
    )
    # this syntax is used to handle cases where the column does
    # not exist in the dataframe. In that case, it returns a dataframe
    # of 0 (False) values of the same length as the original dataframe
    current = (
        data.get(f'Source {source_number} Current', pd.Series([0] * len(data)))
        > current_threshold
    )
    dc_bias = (
        data.get(f'Source {source_number} DC Bias', pd.Series([0] * len(data)))
        > bias_threshold
    )
    setpoint_diff = (
        data.get(
            f'Source {source_number} Output Setpoint', pd.Series([0] * len(data))
        ).diff()
        > power_setpoint_diff_threshold
    )
    # Define conditions for the plasma being on
    source_on_cond = enabled & (current | dc_bias)
    # Define conditions for the plasma ramping up
    source_ramp_up_cond = enabled & setpoint_diff
    # In the folowing, we store each dataframe in a dictionary of
    # dataframes, where the key is the source number
    # Define conditions for specific plasma being on
    source_on_cond_dict[f'source{source_number}'] = source_on_cond
    # Filter the data points where the plasma is on
    data_source_on_dict[f'source{source_number}'] = data[source_on_cond]
    # Find the number of events where the plasma is on
    if not data_source_on_dict[f'source{source_number}'].empty:
        bounds_events_source_on_dict[f'source{source_number}'] = extract_domains(
            data_source_on_dict[f'source{source_number}'], data
        )
        num_events_source_on_dict[f'source{source_number}'] = len(
            bounds_events_source_on_dict[f'source{source_number}']
        )
    else:
        bounds_events_source_on_dict[f'source{source_number}'] = []
        num_events_source_on_dict[f'source{source_number}'] = 0
    # Define conditions for the plasma ramping up
    source_ramp_up_wo1stpoint_cond = enabled & setpoint_diff
    source_ramp_up_cond = (
        source_ramp_up_wo1stpoint_cond
        | source_ramp_up_wo1stpoint_cond.shift(-1, fill_value=False)
    )
    # Filter the data points where the plasma is ramping up
    data_source_ramp_up_dict[f'source{source_number}'] = data[source_ramp_up_cond]
    # Find the number of events where the plasma is ramping up
    if not data_source_ramp_up_dict[f'source{source_number}'].empty:
        bounds_events_source_ramp_up_dict[f'source{source_number}'] = extract_domains(
            data_source_ramp_up_dict[f'source{source_number}'], data
        )
        # Sometimes, we ramp up the sources in steps (Ex: 0->50->75)
        # In that case, the same event is counted as two events
        # We check if the last output setpoint power value of one event
        # is the same as the
        # first value of the next event and if so, we merge the two events
        # into one
        i = 0
        while i < len(bounds_events_source_ramp_up_dict[f'source{source_number}']) - 1:
            # find the timestamps of the end of the first event
            # and the start of the next event
            end_timestamp = bounds_events_source_ramp_up_dict[f'source{source_number}'][
                i
            ][1]
            start_timestamp_next = bounds_events_source_ramp_up_dict[
                f'source{source_number}'
            ][i + 1][0]
            # convert timestamps to integer indices
            end_index = data_source_ramp_up_dict[f'source{source_number}'][
                data_source_ramp_up_dict[f'source{source_number}']['Time Stamp']
                == end_timestamp
            ].index[0]
            start_index_next = data_source_ramp_up_dict[f'source{source_number}'][
                data_source_ramp_up_dict[f'source{source_number}']['Time Stamp']
                == start_timestamp_next
            ].index[0]
            # Ceck if the output setpoint power value of the first event
            # is the same as the output setpoint power value of the next
            # event
            if (
                data_source_ramp_up_dict[f'source{source_number}'][
                    f'Source {source_number} Output Setpoint'
                ].loc[end_index]
                == data_source_ramp_up_dict[f'source{source_number}'][
                    f'Source {source_number} Output Setpoint'
                ].loc[start_index_next]
            ):
                # If so, merge the two events
                bounds_events_source_ramp_up_dict[f'source{source_number}'][i] = (
                    bounds_events_source_ramp_up_dict[f'source{source_number}'][i][0],
                    bounds_events_source_ramp_up_dict[f'source{source_number}'][i + 1][
                        1
                    ],
                )
                bounds_events_source_ramp_up_dict[f'source{source_number}'].pop(i + 1)
            else:
                i += 1  # Only increment i if no merge occurred

        num_events_source_ramp_up_dict[f'source{source_number}'] = len(
            bounds_events_source_ramp_up_dict[f'source{source_number}']
        )
    else:
        bounds_events_source_ramp_up_dict[f'source{source_number}'] = []
        num_events_source_ramp_up_dict[f'source{source_number}'] = 0

# ---------CONDITION FOR THE CRACKER BEING ON--------

# Define conditions for the cracker being on using the temperatures
# of the different zones of the cracker and the control being enabled
if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
    cracker_on_cond = (
        (data['Sulfur Cracker Zone 1 Current Temperature'] > cracker_zone1_min_temp)
        & (data['Sulfur Cracker Zone 2 Current Temperature'] > cracker_zone2_min_temp)
        & (data['Sulfur Cracker Zone 3 Current Temperature'] > cracker_zone3_min_temp)
        & (data['Sulfur Cracker Control Enabled'] == 1)
    )
else:
    cracker_on_cond = pd.Series(False, index=data.index)
data_cracker_on = data[cracker_on_cond]

# ---------CONDITION FOR THE TEMPERATURE CONTROL--------

# Define conditions for the temperature control (when the temperature
# setpoint is different from the actual temperature) and filter the data
if 'Temperature Control Enabled' in data.columns:
    temp_ctrl_cond = data['Temperature Control Enabled'] == 1
else:
    temp_ctrl_cond = (
        data['Substrate Heater Temperature Setpoint']
        != data['Substrate Heater Temperature']
    )
data_temp_ctrl = data[temp_ctrl_cond]
# There is a bug that sometimes the heater temp and the setpoint desagree
# even though the temperature control is off. We need to check that the
# size of the temperature control data is above a certain threshold or
# the domains are not isolate points (if so, then extract_domains will
# return an empty list). If the size is below the threshold or the domains
# are isolated points, we set the data_temp_ctrl to an empty dataframe
if (len(data_temp_ctrl) < min_temp_ctrl_size) or (
    extract_domains(data_temp_ctrl, data) == []
):
    data_temp_ctrl = pd.DataFrame()

# -----CONDITIONS FOR THE DIFFERENT GASES BEING FLOWN--------


# Define conditions for the different gases being flown based on
# the setpoint and flow of the MFCs being above a threshold defined
# by mfc_flow_threshold
ph3_cond = (data['PC MFC 4 Setpoint'] > mfc_flow_threshold) & (
    data['PC MFC 4 Flow'] > mfc_flow_threshold
)

h2s_cond = (data['PC MFC 6 Setpoint'] > mfc_flow_threshold) & (
    data['PC MFC 6 Flow'] > mfc_flow_threshold
)

ar_cond = (data['PC MFC 1 Setpoint'] > mfc_flow_threshold) & (
    data['PC MFC 1 Flow'] > mfc_flow_threshold
)

# ---------COMPOSITE CONDITIONS FOR DIFFERENT EVENTS--------

# Define composite conditions for different events by
# combining the base condition (AND: & OR: | NOT: ~)

# Define conditions for any plasma on or any source shutter open
# Initialize two list of conditions to track the status of each source
# either just being on, or being on and the open


# ---------CONDITIONS FOR THE DEPOSITION--------

# Define a list of condition containing each source being on and open
# at the same time
source_on_open_cond_list = [
    source_on_cond_dict[f'source{source_number}']
    & (data[f'PC Source {source_number} Shutter Open'] == 1)
    for source_number in source_list
]
# Define a list of conditions containing each source being on
source_on_cond_list = [
    source_on_cond_dict[f'source{source_number}'] for source_number in source_list
]
# Combine the source conditions using OR (|) to get any source being on
# and open and any source being on
any_source_on_open_cond = reduce(operator.or_, source_on_open_cond_list)
any_source_on_cond = reduce(operator.or_, source_on_cond_list)

# Define deposition condition as te substrate shutter being open
# and any source being on and open, as defined just above, and filtering
# the data points where the deposition is happening
deposition_cond = (data['PC Substrate Shutter Open'] == 1) & any_source_on_open_cond
data_deposition = data[deposition_cond]
bounds_events_deposition = extract_domains(data_deposition, data)
num_events_deposition = len(bounds_events_deposition)

# ---------CONDITIONS FOR THE DIFFERENT SOURCES BEING PRESPUTTERED--------

# Define conditions for the plasma being presputtered as:
# - the source being on
# - the event happening before the deposition and after the last
# ramp up of the sources
# - the source not ramping up
# - no P or S being flown or cracked
# Note: this part may be improved as we may want to include presputtering
# in P or S gases. We may also include postsputtering


for source_number in source_list:
    enabled = (
        data.get(f'Source {source_number} Enabled', pd.Series([0] * len(data))) != 0
    )
    current = (
        data.get(f'Source {source_number} Current', pd.Series([0] * len(data)))
        > current_threshold
    )
    dc_bias = (
        data.get(f'Source {source_number} DC Bias', pd.Series([0] * len(data)))
        > bias_threshold
    )
    setpoint_diff = (
        data.get(
            f'Source {source_number} Output Setpoint', pd.Series([0] * len(data))
        ).diff()
        > power_setpoint_diff_threshold
    )
    source_on_cond = enabled & (current | dc_bias)
    source_ramp_up_cond = enabled & setpoint_diff
    if not data_source_on_dict[f'source{source_number}'].empty:
        source_presput_cond_dict[f'source{source_number}'] = (
            source_on_cond
            & (data['Time Stamp'] < data_deposition['Time Stamp'].iloc[0])
            & (
                data['Time Stamp']
                > (
                    data_source_ramp_up_dict[f'source{source_number}'][
                        'Time Stamp'
                    ].iloc[-1]
                )
            )
            & ~source_ramp_up_cond
            & ~(ph3_cond | h2s_cond | cracker_on_cond)
        )
        data_source_presput_dict[f'source{source_number}'] = data[
            source_presput_cond_dict[f'source{source_number}']
        ]
        if not data_source_presput_dict[f'source{source_number}'].empty:
            bounds_events_source_presput_dict[f'source{source_number}'] = (
                extract_domains(
                    data_source_presput_dict[f'source{source_number}'], data
                )
            )
            num_events_source_presput_dict[f'source{source_number}'] = len(
                bounds_events_source_presput_dict[f'source{source_number}']
            )
        else:
            bounds_events_source_presput_dict[f'source{source_number}'] = []
            num_events_source_presput_dict[f'source{source_number}'] = 0

# ---------CONDITIONS FOR THE S CRACKER PRESSURE--------

# Condition for measurement of the Sulfur Cracker induced base_pressure, as:
# - the cracker is on and open
# - no gas (h2s,ph2, or ar) is flown
# - the time is before the deposition
# - the cracker temperature and parameters
# are within cracker_param of the deposition conditions

if not data_cracker_on.empty:
    cracker_base_pressure_cond = (
        cracker_on_cond
        & (data['Time Stamp'] < data_deposition['Time Stamp'].iloc[0])
        & ~h2s_cond
        & ~ph3_cond
        & ~ar_cond
        & (
            data['Sulfur Cracker Zone 1 Current Temperature']
            > (1 - 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Zone 1 Current Temperature'].mean()
        )
        & (
            data['Sulfur Cracker Zone 1 Current Temperature']
            < (1 + 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Zone 1 Current Temperature'].mean()
        )
        & (
            data['Sulfur Cracker Zone 2 Current Temperature']
            > (1 - 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Zone 2 Current Temperature'].mean()
        )
        & (
            data['Sulfur Cracker Zone 2 Current Temperature']
            < (1 + 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Zone 2 Current Temperature'].mean()
        )
        & (
            data['Sulfur Cracker Zone 3 Current Temperature']
            > (1 - 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Zone 3 Current Temperature'].mean()
        )
        & (
            data['Sulfur Cracker Zone 3 Current Temperature']
            < (1 + 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Zone 3 Current Temperature'].mean()
        )
        & (
            data['Sulfur Cracker Control Valve PulseWidth Setpoint']
            < (1 + 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Control Valve PulseWidth Setpoint'].mean()
        )
        & (
            data['Sulfur Cracker Control Valve Setpoint']
            < (1 + 0.01 * cracker_param)
            * data_deposition['Sulfur Cracker Control Valve Setpoint'].mean()
        )
        & (data['Sulfur Cracker Control Enabled'] == 1)
    )
    data_cracker_base_pressure = data[cracker_base_pressure_cond]
    if not data_cracker_base_pressure.empty:
        bounds_events_cracker_base_pressure = extract_domains(
            data_cracker_base_pressure, data
        )
        num_events_cracker_base_pressure = len(bounds_events_cracker_base_pressure)
    else:
        bounds_events_cracker_base_pressure = []
        num_events_cracker_base_pressure = 0


# ---------CONDITIONS FOR THE DEPOSITION RATE MEASUREMENT--------

# Condition of the deposition rate measurement is defined as the
# Xtal2 substrate shutter being open from which we exclude the
# data points just after the Xtal2 shutter opens, as the QCM
# needs time to stabilize. The stab_time stabilization time
# is defined in the reference values section
if 'Xtal 2 Shutter Open' in data.columns:
    data_xtal2_open_cond = data['Xtal 2 Shutter Open'] == 1
    # Set a time window to exclude data points after
    # the Xtal shutter opens
    # Identify the indices where the shutter opens (transitions to 1)
    xtal2_open_indices = data.index[data['Xtal 2 Shutter Open'].diff() == 1]
    # Create a boolean mask to exclude points within stab_time seconds
    # after the shutter opens
    mask = pd.Series(True, index=data.index)
    for idx in xtal2_open_indices:
        # Find the time of the shutter opening event
        open_time = data.at[idx, 'Time Stamp']
        # Find points within stab_time seconds after the shutter opening
        within_stab_time = (data['Time Stamp'] > open_time) & (
            data['Time Stamp'] <= open_time + pd.Timedelta(seconds=stab_time)
        )
        # Update the mask to exclude these points
        mask &= ~within_stab_time
    # Apply the mask to filter the data
    data_deprate2_meas_cond = mask & data_xtal2_open_cond
else:
    data_deprate2_meas_cond = pd.Series(False, index=data.index)

# Define the condition for the Metal-P-S film deposition rate measurement
# as the condition just above, with the addition of S or P being flown
# or the cracker being on and the material used as refereced by the QCM
# not being Sulfur
data_deprate2_film_meas_cond = (
    data_deprate2_meas_cond
    & any_source_on_open_cond
    & (cracker_on_cond | h2s_cond)
    & ph3_cond
    & data['Thickness Active Material']
    != 'Sulfur'
)
data_deprate2_meas = data[data_deprate2_meas_cond]
data_deprate2_film_meas = data[data_deprate2_film_meas_cond]

# ---CONDITIONS FOR THE SUBSTRATE TEMPERATURE RAMPING UP OR DOWN-----

if (
    not data_temp_ctrl.empty
    or (
        data_deposition['Substrate Heater Temperature Setpoint'] > rt_temp_threshold
    ).all()
):
    # Define conditions and filtering the data
    # for the substrate temperature was ramping up as:
    # - the temperature control is enabled
    # - the event is not a deposition
    # - the temperature setpoint is increasing faster than the threshold
    # defined in the reference values
    ramp_up_temp_ctrl_cond = (
        temp_ctrl_cond
        & ~deposition_cond
        & (
            data['Substrate Heater Temperature Setpoint'].diff()
            > temp_setpoint_diff_threshold
        )
    )
    data_ramp_up_temp_ctrl = data[ramp_up_temp_ctrl_cond]
    # Define conditions and filtereing the data
    # for the substrate temperature was ramping down in a similar fashion
    ramp_down_temp_ctrl_cond = (
        temp_ctrl_cond
        & ~deposition_cond
        & (
            data['Substrate Heater Temperature Setpoint'].diff()
            < -temp_setpoint_diff_threshold
        )
        & (data['Substrate Heater Temperature Setpoint'] > 1)
    )
    data_ramp_down_temp_ctrl = data[ramp_down_temp_ctrl_cond]
    # In the following, we distinguish betweem to phases of the ramp down:
    # 1/ the high temperature phase where we flow H2S, PH3 or the cracker is on
    # to prevent the film loosing P or S
    # 2/ the low temperature phase where we do not flow H2S, PH3 or
    # the cracker is off

    # Define the ramp down high temperature condition as a events after
    # the beginning of the ramp down of the temperature ramp down
    # where we flow H2S, PH3 or the cracker is on
    ramp_down_high_temp_cond = (
        (data['Time Stamp'] > data_ramp_down_temp_ctrl['Time Stamp'].iloc[0])
        & (h2s_cond | cracker_on_cond)
        & ph3_cond
    )
    data_ramp_down_high_temp = data[ramp_down_high_temp_cond]
    # Define the ramp down low temperature condition as a events after
    # the beginning of the ramp down of the temperature ramp down
    # where we do not flow H2S, PH3 or the cracker is off
    ramp_down_low_temp_cond = (
        data['Time Stamp'] > data_ramp_down_temp_ctrl['Time Stamp'].iloc[0]
    ) & ~(h2s_cond | cracker_on_cond | ph3_cond)
    data_ramp_down_low_temp = data[ramp_down_low_temp_cond]


# %%
# ---EXTRACT DERIVED QUANTITIES IN A DICIONARY TO INPUT IN NOMAD----


# ----INITIALIZE THE NESTED DICTIONARY TO STORE DERIVED QUANTITIES-----

# Initialize a  nested dictionary to store derived quantities
# for ramp up, plasma on, presputtering and deposition events, we nest
# other dictionaries for the different sources or the cracker status
derived_quant = {}

derived_quant['deposition'] = {}
derived_quant['source_ramp_up'] = {}
derived_quant['source_presput'] = {}
derived_quant['sub_ramp_up'] = {}
derived_quant['sub_ramp_up']['cracker'] = {}
derived_quant['sub_ramp_down'] = {}
derived_quant['sub_ramp_down']['cracker'] = {}
derived_quant['deposition']['cracker'] = {}

for source_number in source_list:
    derived_quant['deposition'][f'source{source_number}'] = {}
    derived_quant['source_ramp_up'][f'source{source_number}'] = {}
    derived_quant['source_presput'][f'source{source_number}'] = {}

# initialize the elements list for the material space extraction
elements = []

# Note: The following section name are partly based on NOMAD DTUSputtering
# class section names

# ---OVERVIEW-----

# Extact sample name as the first 3 log file string when parsed by '_'
derived_quant['sample_name'] = '_'.join(logfile_name.split('_')[:3])

# Extract start and end time of the log file
derived_quant['log_start_time'] = data['Time Stamp'].iloc[0]
derived_quant['log_end_time'] = data['Time Stamp'].iloc[-1]

# ---ADJUSTED INTRUMENT PARAMETERS-----

# Extract the platin position during deposition
if 'Substrate Rotation_Position' in data_deposition:
    derived_quant['deposition']['platin_position'] = data_deposition[
        'Substrate Rotation_Position'
    ].mean()

# ---DEPOSITION PARAMETERS-----

# Extract if the deposition was done at room temperature as :
# - the temperature control is disabled or
# - the temperature control is enabled but the temperature setpoint
# is below the RT threshold defined in the reference values
if (
    data_temp_ctrl.empty
    or (
        data_deposition['Substrate Heater Temperature Setpoint'] < rt_temp_threshold
    ).all()
):
    derived_quant['deposition']['rt'] = True
elif (
    data_deposition['Substrate Heater Temperature Setpoint'] > rt_temp_threshold
).all():
    derived_quant['deposition']['rt'] = False

# Extract the source used for deposition
# For all sources, we check if the source is enabled during deposition
# and if it is, we set the source as the source enabled for deposition
# which implies that the source was also ramped up and presputtered
for source_number in source_list:
    if (
        not data_deposition.get(
            f'Source {source_number} Enabled', pd.Series([0] * len(data_deposition))
        ).all()
        == 0
    ):
        derived_quant['deposition'][f'source{source_number}']['enabled'] = True
        derived_quant['source_ramp_up'][f'source{source_number}']['enabled'] = True
        if not data_source_presput_dict[f'source{source_number}'].empty:
            derived_quant['source_presput'][f'source{source_number}']['enabled'] = True
        else:
            derived_quant['source_presput'][f'source{source_number}']['enabled'] = False
    else:
        derived_quant['deposition'][f'source{source_number}']['enabled'] = False
        derived_quant['source_ramp_up'][f'source{source_number}']['enabled'] = False
        derived_quant['source_presput'][f'source{source_number}']['enabled'] = False

# Extract if the cracker has been used during deposition as the
# cracker control being enabled and the temperatures of the
# different zones being above the minimum temperatures
# defined in the reference values
if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
    if (
        (data_deposition['Sulfur Cracker Control Enabled'] == 1).all()
        and (
            data_deposition['Sulfur Cracker Zone 1 Current Temperature']
            > cracker_zone1_min_temp
        ).all()
        and (
            data_deposition['Sulfur Cracker Zone 2 Current Temperature']
            > cracker_zone2_min_temp
        ).all()
        and (
            data_deposition['Sulfur Cracker Zone 3 Current Temperature']
            > cracker_zone3_min_temp
        ).all()
    ):
        derived_quant['deposition']['cracker']['enabled'] = True
else:
    derived_quant['deposition']['cracker']['enabled'] = False

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
    <= pd.to_datetime(data_deposition['Time Stamp'].iloc[0]),
    'PC Wide Range Gauge',
].min()

derived_quant['lower_pressure_before_deposition'] = min_pressure_before_depostion
if min_pressure_before_depostion < max_base_pressure:
    if not derived_quant['deposition']['cracker']['enabled']:
        derived_quant['true_base_pressure_meas'] = True
    elif derived_quant['deposition']['cracker']['enabled']:
        derived_quant['true_base_pressure_meas'] = False
else:
    derived_quant['true_base_pressure_meas'] = False

# Extract the S induced base pressure as the mean pressure during
# the cracker being on and no gas being flown
if not data_cracker_base_pressure.empty:
    derived_quant['cracker_pressure_meas'] = True
    derived_quant['cracker_pressure'] = data_cracker_base_pressure[
        'PC Wide Range Gauge'
    ].mean()
else:
    derived_quant['cracker_pressure_meas'] = False

# Extract the cracker parameters if the cracker has been used
if derived_quant['deposition']['cracker']['enabled']:
    derived_quant['deposition']['cracker']['zone1_temp'] = data_deposition[
        'Sulfur Cracker Zone 1 Current Temperature'
    ].mean()
    derived_quant['deposition']['cracker']['zone2_temp'] = data_deposition[
        'Sulfur Cracker Zone 2 Current Temperature'
    ].mean()
    derived_quant['deposition']['cracker']['zone3_temp'] = data_deposition[
        'Sulfur Cracker Zone 3 Current Temperature'
    ].mean()
    derived_quant['deposition']['cracker']['pulse_width'] = data_deposition[
        'Sulfur Cracker Control Valve PulseWidth Setpoint'
    ].mean()
    derived_quant['deposition']['cracker']['pulse_freq'] = data_deposition[
        'Sulfur Cracker Control Valve Setpoint'
    ].mean()

# Extract the number of deposition events
derived_quant['deposition']['num_events'] = num_events_deposition

# Extract start and end time of the deposition
derived_quant['deposition']['start_time'] = data_deposition['Time Stamp'].iloc[0]
derived_quant['deposition']['end_time'] = data_deposition['Time Stamp'].iloc[-1]
derived_quant['deposition']['duration'] = (
    derived_quant['deposition']['end_time'] - derived_quant['deposition']['start_time']
)

# Extract average temperature during deposition
derived_quant['deposition']['avg_temp_1'] = data_deposition[
    'Substrate Heater Temperature'
].mean()
derived_quant['deposition']['avg_temp_2'] = data_deposition[
    'Substrate Heater Temperature 2'
].mean()
derived_quant['deposition']['avg_temp_setpoint'] = data_deposition[
    'Substrate Heater Temperature Setpoint'
].mean()

# Extract the average true temperature during deposition
derived_quant['deposition']['avg_true_temp'] = calculate_avg_true_temp(
    derived_quant['deposition']['avg_temp_1'], derived_quant['deposition']['avg_temp_2']
)

# Extract average sputter PC Capman pressure during deposition
derived_quant['deposition']['avg_capman_pressure'] = data_deposition[
    'PC Capman Pressure'
].mean()


# Extract the MF1 Ar, MFC4 PH3 and MFC6 H2S flow during deposition
# only if the flow is above 1sccm, if not we set the flow to 0
derived_quant['deposition']['avg_ar_flow'] = (
    data_deposition[data_deposition['PC MFC 1 Flow'] > mfc_flow_threshold][
        'PC MFC 1 Flow'
    ].mean()
    if not data_deposition[data_deposition['PC MFC 1 Flow'] > mfc_flow_threshold][
        'PC MFC 1 Flow'
    ].empty
    else 0
)
derived_quant['deposition']['avg_ph3_flow'] = (
    data_deposition[data_deposition['PC MFC 4 Flow'] > mfc_flow_threshold][
        'PC MFC 4 Flow'
    ].mean()
    if not data_deposition[data_deposition['PC MFC 4 Flow'] > mfc_flow_threshold][
        'PC MFC 4 Flow'
    ].empty
    else 0
)
derived_quant['deposition']['avg_h2s_flow'] = (
    data_deposition[data_deposition['PC MFC 6 Flow'] > mfc_flow_threshold][
        'PC MFC 6 Flow'
    ].mean()
    if not data_deposition[data_deposition['PC MFC 6 Flow'] > mfc_flow_threshold][
        'PC MFC 6 Flow'
    ].empty
    else 0
)

# ----- Source dependent parameters-----

# Here, we interate over the sources to extract many relevant parameters
for source_number in source_list:
    # We check if the source is enabled during deposition
    if derived_quant['deposition'][f'source{source_number}']['enabled']:
        # ----source presputtering parameters-----
        if derived_quant['source_presput'][f'source{source_number}']['enabled']:
            # Extract the presputtering duration
            # First, we extract the bounds of the continuous domains
            presput_time = pd.Timedelta(0)
            # Secondly, or all the presputtering events, we calculate the
            # duration and add it to the total presputtering time
            for i in range(num_events_source_presput_dict[f'source{source_number}']):
                presput_time += (
                    bounds_events_source_presput_dict[f'source{source_number}'][i][1]
                    - bounds_events_source_presput_dict[f'source{source_number}'][i][0]
                )
            derived_quant['source_presput'][f'source{source_number}']['duration'] = (
                presput_time
            )
            # Extract the average output power during presputtering
            derived_quant['source_presput'][f'source{source_number}'][
                'avg_output_power'
            ] = data_source_presput_dict[f'source{source_number}'][
                f'Source {source_number} Output Setpoint'
            ].mean()
            # Extract the avg capman pressure during presputtering
            derived_quant['source_presput'][f'source{source_number}'][
                'avg_capman_pressure'
            ] = data_source_presput_dict[f'source{source_number}'][
                'PC Capman Pressure'
            ].mean()
            # Extract the gas flows during presputtering
            derived_quant['source_presput'][f'source{source_number}']['avg_ar_flow'] = (
                data_source_presput_dict[
                    f'source{source_number}'
                ]['PC MFC 1 Flow'].mean()
            )

        # -------source ramp up parameters-----

        # Extract the number of ramp up events
        derived_quant['source_ramp_up'][f'source{source_number}']['num_events'] = (
            num_events_source_ramp_up_dict[f'source{source_number}']
        )
        # Extract the plasma ignition power as the power at which
        # the plasma really ignites
        # We first filter only the last [-1] source ramp up event with the
        # event filter function
        last_ramp_up_bounds = list(
            bounds_events_source_ramp_up_dict[f'source{source_number}'][-1]
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
        mask = (current_series > current_threshold) | (bias_series > bias_threshold)
        # Apply the mask to get the moment where the plasma is on during
        # ramp up
        data_ignition_time = data.loc[mask]
        # If the plasma turns on during ramp up, data_ignition_time should
        # not be empty
        if not data_ignition_time.empty:
            ignition_time = data_ignition_time['Time Stamp'].iloc[0]
            derived_quant['source_ramp_up'][f'source{source_number}'][
                'source_ignition'
            ] = True
            derived_quant['source_ramp_up'][f'source{source_number}'][
                'source_ignition_time'
            ] = ignition_time
            ignition_data = data[data['Time Stamp'] == ignition_time]
            derived_quant['source_ramp_up'][f'source{source_number}'][
                'source_ignition_power'
            ] = ignition_data[f'Source {source_number} Output Setpoint'].iloc[0]
            derived_quant['source_ramp_up'][f'source{source_number}'][
                'source_ignition_pressure'
            ] = ignition_data['PC Capman Pressure'].iloc[0]
        else:
            derived_quant['source_ramp_up'][f'source{source_number}'][
                'source_ignition'
            ] = False

        # -------source deposition parameters-----

        # Extract average ouput power during deposition
        derived_quant['deposition'][f'source{source_number}']['avg_output_power'] = (
            data_deposition[f'Source {source_number} Output Setpoint'].mean()
        )
        # Extract the plasma type by checking what power supply was used¨
        # during deposition, which can be done by checking if relevant
        # columns are present in the dataframe for each source
        enable_col = f'Source {source_number} Enabled'
        dc_current_col = f'Source {source_number} Current'
        rf_bias_col = f'Source {source_number} DC Bias'
        pulse_enable_col = f'Source {source_number} Pulse Enabled'
        if dc_current_col in data_deposition:
            if data_deposition[dc_current_col].all() > current_threshold:
                (derived_quant['deposition'][f'source{source_number}']['dc']) = True
                (derived_quant['deposition'][f'source{source_number}']['rf']) = False
                if (
                    pulse_enable_col in data_deposition
                    and (data_deposition[pulse_enable_col].all()) == 1
                ):
                    (
                        derived_quant['deposition'][f'source{source_number}']['pulsed']
                    ) = True
                    derived_quant['deposition']
                    [f'source{source_number}']['pulse_frequency'] = data_deposition[
                        f'Source {source_number} Pulse Frequency'
                    ].mean()
                    # Extract the dc pulse frequency and reverse time
                    derived_quant['deposition'][f'source{source_number}'][
                        'dead_time'
                    ] = data_deposition[f'Source {source_number} Reverse Time'].mean()
                elif (
                    pulse_enable_col in data_deposition
                    and (data_deposition[pulse_enable_col].all()) == 0
                ):
                    (
                        derived_quant['deposition'][f'source{source_number}']['pulsed']
                    ) = False
        elif rf_bias_col in data_deposition:
            if data_deposition[rf_bias_col].all() > bias_threshold:
                (derived_quant['deposition'][f'source{source_number}']['rf']) = True
                (derived_quant['deposition'][f'source{source_number}']['dc']) = False
        # Extract the deposition voltage for each source
        # by distinguishing the rf and dc cases
        if derived_quant['deposition'][f'source{source_number}']['dc']:
            derived_quant['deposition'][f'source{source_number}']['start_voltage'] = (
                int(
                    data_deposition[f'Source {source_number} Voltage']
                    .iloc[: (int(fraq_rows_avg_voltage * 0.01 * len(data_deposition)))]
                    .mean()
                )
            )
            derived_quant['deposition'][f'source{source_number}']['end_voltage'] = (
                data_deposition[f'Source {source_number} Voltage']
                .iloc[-(int(fraq_rows_avg_voltage * 0.01 * len(data_deposition))) :]
                .mean()
            )
            derived_quant['deposition'][f'source{source_number}']['avg_voltage'] = (
                data_deposition[f'Source {source_number} Voltage'].mean()
            )
        elif derived_quant['deposition'][f'source{source_number}']['rf']:
            derived_quant['deposition'][f'source{source_number}']['start_voltage'] = (
                data_deposition[f'Source {source_number} DC Bias']
                .iloc[: (int(fraq_rows_avg_voltage * 0.01 * len(data_deposition)))]
                .mean()
            )
            derived_quant['deposition'][f'source{source_number}']['end_voltage'] = (
                data_deposition[f'Source {source_number} DC Bias']
                .iloc[-(int(fraq_rows_avg_voltage * 0.01 * len(data_deposition))) :]
                .mean()
            )
            derived_quant['deposition'][f'source{source_number}']['avg_voltage'] = (
                data_deposition[f'Source {source_number} DC Bias'].mean()
            )
        # Extract source material and target id and add the element to the
        # elements list for the material space extraction
        source_element = str(
            data_deposition[f'PC Source {source_number} Material'].iloc[0]
        )
        derived_quant['deposition'][f'source{source_number}']['material'] = element(
            source_element
        ).symbol
        derived_quant['deposition'][f'source{source_number}']['target_id'] = (
            data_deposition[f'PC Source {source_number} Loaded Target'].iloc[0]
        )
        elements = elements + [element(source_element).symbol]

# Extract the material space as the elements used during deposition
if derived_quant['deposition']['avg_ph3_flow'] > mfc_flow_threshold:
    elements = elements + ['P']
if (derived_quant['deposition']['avg_h2s_flow'] > mfc_flow_threshold) or (
    derived_quant['deposition']['cracker']['enabled']
):
    elements = elements + ['S']
    # add the element as an hypen separated string
derived_quant['material_space'] = '-'.join(elements)

# Extract the deposition rate of the Metal-P-S film
if not data_deprate2_film_meas.empty:
    derived_quant['deposition']['deposition_rate'] = data_deprate2_film_meas[
        'Thickness Rate'
    ].mean()
    derived_quant['deposition']['deposition_rate_mat'] = data_deprate2_film_meas[
        'Thickness Active Material'
    ].iloc[0]

# -----end of process

# Extract the end of process temperature as the last temperature logged
# Note: this part can be improved by extracting the temperature at
# the vent recipe step
derived_quant['end_of_process_temp'] = data['Substrate Heater Temperature'].iloc[-1]

# Extract the time in chamber after deposition as the time difference
# between end of logging and end of deposition time
derived_quant['time_in_chamber_after_deposition'] = (
    derived_quant['log_end_time'] - derived_quant['deposition']['end_time']
)

if not derived_quant['deposition']['rt']:
    # ------Extract the substrate ramp up parameters------
    # Extract the number of ramp up events¨
    derived_quant['sub_ramp_up']['num_events'] = len(
        extract_domains(data_ramp_up_temp_ctrl, data)
    )
    # Extract the slope assuming linear ramp up
    # In data_ramp_up_temp_ctrl only increasing setpoint temperature are
    # considered making easier to extract the slope
    derived_quant['sub_ramp_up']['start_time'] = data_ramp_up_temp_ctrl[
        'Time Stamp'
    ].iloc[0]
    derived_quant['sub_ramp_up']['end_time'] = data_ramp_up_temp_ctrl[
        'Time Stamp'
    ].iloc[-1]
    derived_quant['sub_ramp_up']['duration'] = (
        derived_quant['sub_ramp_up']['end_time']
        - derived_quant['sub_ramp_up']['start_time']
    )
    temp_diff = (
        data_ramp_up_temp_ctrl['Substrate Heater Temperature Setpoint'].iloc[-1]
        - data_ramp_up_temp_ctrl['Substrate Heater Temperature Setpoint'].iloc[0]
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
    derived_quant['sub_ramp_up']['avg_capman_pressure'] = data_ramp_up_temp_ctrl[
        'PC Capman Pressure'
    ].mean()
    # Extract the gas flows during the substrate ramp up
    # If the flows are below the noise level threshold,
    # we set the flow to 0
    derived_quant['sub_ramp_up']['avg_ar_flow'] = (
        data_ramp_up_temp_ctrl[data_ramp_up_temp_ctrl['PC MFC 1 Flow'] > 1][
            'PC MFC 1 Flow'
        ].mean()
        if not data_ramp_up_temp_ctrl[data_ramp_up_temp_ctrl['PC MFC 1 Flow'] > 1][
            'PC MFC 1 Flow'
        ].empty
        else 0
    )
    derived_quant['sub_ramp_up']['avg_ph3_flow'] = (
        data_ramp_up_temp_ctrl[data_ramp_up_temp_ctrl['PC MFC 4 Flow'] > 1][
            'PC MFC 4 Flow'
        ].mean()
        if not data_ramp_up_temp_ctrl[data_ramp_up_temp_ctrl['PC MFC 4 Flow'] > 1][
            'PC MFC 4 Flow'
        ].empty
        else 0
    )
    derived_quant['sub_ramp_up']['avg_h2s_flow'] = (
        data_ramp_up_temp_ctrl[data_ramp_up_temp_ctrl['PC MFC 6 Flow'] > 1][
            'PC MFC 6 Flow'
        ].mean()
        if not data_ramp_up_temp_ctrl[data_ramp_up_temp_ctrl['PC MFC 6 Flow'] > 1][
            'PC MFC 6 Flow'
        ].empty
        else 0
    )
    # Extract if the cracker has been used during ramp up
    # The column 'Sulfur Cracker Control Enabled' correspond to the
    # act of opening the cracker pulse valve (1 open, 0 closed)
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        if (
            (data_ramp_up_temp_ctrl['Sulfur Cracker Control Enabled'] == 1).all()
            and (
                data_ramp_up_temp_ctrl['Sulfur Cracker Zone 1 Current Temperature']
                > cracker_zone1_min_temp
            ).all()
            and (
                data_ramp_up_temp_ctrl['Sulfur Cracker Zone 2 Current Temperature']
                > cracker_zone2_min_temp
            ).all()
            and (
                data_ramp_up_temp_ctrl['Sulfur Cracker Zone 3 Current Temperature']
                > cracker_zone3_min_temp
            ).all()
        ):
            derived_quant['sub_ramp_up']['cracker']['enabled'] = True
            # If the cracker has been used, extract the cracker parameters
            derived_quant['sub_ramp_up']['cracker']['zone1_temp'] = (
                data_ramp_up_temp_ctrl[
                    'Sulfur Cracker Zone 1 Current Temperature'
                ].mean()
            )
            derived_quant['sub_ramp_up']['cracker']['zone2_temp'] = (
                data_ramp_up_temp_ctrl[
                    'Sulfur Cracker Zone 2 Current Temperature'
                ].mean()
            )
            derived_quant['sub_ramp_up']['cracker']['zone3_temp'] = (
                data_ramp_up_temp_ctrl[
                    'Sulfur Cracker Zone 3 Current Temperature'
                ].mean()
            )
            derived_quant['sub_ramp_up']['cracker']['pulse_width'] = (
                data_ramp_up_temp_ctrl[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint'
                ].mean()
            )
            derived_quant['sub_ramp_up']['cracker']['pulse_freq'] = (
                data_ramp_up_temp_ctrl['Sulfur Cracker Control Valve Setpoint'].mean()
            )
        else:
            derived_quant['sub_ramp_up']['cracker']['enabled'] = False
    else:
        derived_quant['sub_ramp_up']['cracker']['enabled'] = False
    # ------Extract the substrate ramp down parameters------
    # Extract the number of ramp down events
    derived_quant['sub_ramp_down']['num_events'] = len(
        extract_domains(data_ramp_down_temp_ctrl, data)
    )
    derived_quant['sub_ramp_down']['num_events_high_temp'] = (
        len(extract_domains(data_ramp_down_high_temp, data))
        if not data_ramp_down_high_temp.empty
        else 0
    )
    derived_quant['sub_ramp_down']['num_events_low_temp'] = (
        len(extract_domains(data_ramp_down_low_temp, data))
        if not data_ramp_down_low_temp.empty
        else 0
    )
    # Extract the slope from when the temp in controled,
    # assuming linear ramp up
    # In data_ramp_down_temp_ctrl only decreasing setpoint temperature are
    # considered making easier to extract the slope
    start_time = data_ramp_down_temp_ctrl['Time Stamp'].iloc[0]
    end_time = data_ramp_down_temp_ctrl['Time Stamp'].iloc[-1]
    time_interval = end_time - start_time
    temp_diff = -(
        data_ramp_down_temp_ctrl['Substrate Heater Temperature Setpoint'].iloc[-1]
        - data_ramp_down_temp_ctrl['Substrate Heater Temperature Setpoint'].iloc[0]
    )
    time_interval_minutes = time_interval.total_seconds() / 60
    derived_quant['sub_ramp_down']['temp_slope'] = temp_diff / time_interval_minutes
    # Now we distinguish between the high temp and low temp ramp down phase
    # Extract the start time of the ramp down as the first time of
    # the high temperature ramp down and the end time as the last time of
    # the low temperature ramp down (which is the last time of the log)
    derived_quant['sub_ramp_down']['start_time'] = data_ramp_down_high_temp[
        'Time Stamp'
    ].iloc[0]
    if not data_ramp_down_low_temp.empty:
        derived_quant['sub_ramp_down']['end_time'] = data_ramp_down_low_temp[
            'Time Stamp'
        ].iloc[-1]
    else:
        derived_quant['sub_ramp_down']['end_time'] = data_ramp_down_high_temp[
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
        data_ramp_down_high_temp[
            data_ramp_down_high_temp['PC MFC 1 Flow'] > mfc_flow_threshold
        ]['PC MFC 1 Flow'].mean()
        if not data_ramp_down_high_temp[
            data_ramp_down_high_temp['PC MFC 1 Flow'] > mfc_flow_threshold
        ]['PC MFC 1 Flow'].empty
        else 0
    )
    derived_quant['sub_ramp_down']['avg_ph3_flow'] = (
        data_ramp_down_high_temp[
            data_ramp_down_high_temp['PC MFC 4 Flow'] > mfc_flow_threshold
        ]['PC MFC 4 Flow'].mean()
        if not data_ramp_down_high_temp[
            data_ramp_down_high_temp['PC MFC 4 Flow'] > mfc_flow_threshold
        ]['PC MFC 4 Flow'].empty
        else 0
    )
    derived_quant['sub_ramp_down']['avg_h2s_flow'] = (
        data_ramp_down_high_temp[
            data_ramp_down_high_temp['PC MFC 6 Flow'] > mfc_flow_threshold
        ]['PC MFC 6 Flow'].mean()
        if not data_ramp_down_high_temp[
            data_ramp_down_high_temp['PC MFC 6 Flow'] > mfc_flow_threshold
        ]['PC MFC 6 Flow'].empty
        else 0
    )
    # Extract if the cracker has been used during ramp down
    if 'Sulfur Cracker Zone 1 Current Temperature' in data.columns:
        if (
            (data_ramp_down_high_temp['Sulfur Cracker Control Enabled'] == 1).all()
            and (
                data_ramp_down_high_temp['Sulfur Cracker Zone 1 Current Temperature']
                > cracker_zone1_min_temp
            ).all()
            and (
                data_ramp_down_high_temp['Sulfur Cracker Zone 2 Current Temperature']
                > cracker_zone2_min_temp
            ).all()
            and (
                data_ramp_down_high_temp['Sulfur Cracker Zone 3 Current Temperature']
                > cracker_zone3_min_temp
            ).all()
        ):
            derived_quant['sub_ramp_down']['cracker']['enabled'] = True
            # if the crack has been used, extract the cracker parameters
            derived_quant['sub_ramp_down']['cracker']['zone1_temp'] = (
                data_ramp_down_high_temp[
                    'Sulfur Cracker Zone 1 Current Temperature'
                ].mean()
            )
            derived_quant['sub_ramp_down']['cracker']['zone2_temp'] = (
                data_ramp_down_high_temp[
                    'Sulfur Cracker Zone 2 Current Temperature'
                ].mean()
            )
            derived_quant['sub_ramp_down']['cracker']['zone3_temp'] = (
                data_ramp_down_high_temp[
                    'Sulfur Cracker Zone 3 Current Temperature'
                ].mean()
            )
            derived_quant['sub_ramp_down']['cracker']['pulse_width'] = (
                data_ramp_down_high_temp[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint'
                ].mean()
            )
            derived_quant['sub_ramp_down']['cracker']['pulse_freq'] = (
                data_ramp_down_high_temp['Sulfur Cracker Control Valve Setpoint'].mean()
            )
        else:
            derived_quant['sub_ramp_down']['cracker']['enabled'] = False
    else:
        derived_quant['sub_ramp_down']['cracker']['enabled'] = False
    # Extract the anion input cutoff temperature as the last temperature of
    # the high temperature ramp down
    derived_quant['sub_ramp_down']['anion_input_cutoff_temp'] = (
        data_ramp_down_high_temp['Substrate Heater Temperature Setpoint'].iloc[-1]
    )
    derived_quant['sub_ramp_down']['anion_input_cutoff_time'] = (
        data_ramp_down_high_temp['Time Stamp'].iloc[-1]
    )


# %%
# --------GRAPH THE DIFFERENT STEPS ON A TIME LINE------------

# Here we use the different bounds of the different events to plot them
# as thick horizontal lines on a time line, with the different events names


# Create the figure and axis
timeline = plt.figure(figsize=(8, 3))
ax = timeline.add_subplot(111)

# Set up the axis limits and labels
ax.set_xlim(data['Time Stamp'].iloc[0], data['Time Stamp'].iloc[-1])
ax.set_xlabel('Time', fontsize=12)

# Set time ticks format
ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

# Title of the plot
ax.set_title('Process Timeline', fontsize=12, pad=20)

# Setting the alpha value
default_alpha = 1

# Height of each step on the timeline
j = 0

# Define a dictionary for step colors
step_colors = {
    'Deposition': 'blue',
    'Ramp Up': 'green',
    'Ramp Down': 'red',
    'Source 4 Ramp Up': 'purple',
    'Source 4 Pre-Sputter': 'orange',
    'Source 4 On': 'brown',
}

# Plot the deposition step
deposition_start = derived_quant['deposition']['start_time']
deposition_end = derived_quant['deposition']['end_time']
ax.axvspan(
    deposition_start,
    deposition_end,
    ymin=0,
    ymax=0.2,
    color=step_colors['Deposition'],
    alpha=default_alpha,
    label='Deposition',
)
j += 1

# Plot the ramp up step
ramp_up_start = derived_quant['sub_ramp_up']['start_time']
ramp_up_end = derived_quant['sub_ramp_up']['end_time']
ax.axvspan(
    ramp_up_start,
    ramp_up_end,
    ymin=0,
    ymax=0.2,
    color=step_colors['Ramp Up'],
    alpha=default_alpha,
    label='Ramp Up',
)
j += 1

# Plot the ramp down step
ramp_down_start = derived_quant['sub_ramp_down']['start_time']
ramp_down_end = derived_quant['sub_ramp_down']['end_time']
ax.axvspan(
    ramp_down_start,
    ramp_down_end,
    ymin=0,
    ymax=0.2,
    color=step_colors['Ramp Down'],
    label='Ramp Down',
)
j += 1

# Plot the sources ramp up step
for source_number in source_list:
    if derived_quant['deposition'][f'source{source_number}']['enabled']:
        for k in range(num_events_source_ramp_up_dict[f'source{source_number}']):
            source_ramp_up_start = bounds_events_source_ramp_up_dict[
                f'source{source_number}'
            ][k][0]
            source_ramp_up_end = bounds_events_source_ramp_up_dict[
                f'source{source_number}'
            ][k][1]
            ax.axvspan(
                source_ramp_up_start,
                source_ramp_up_end,
                ymin=0.4 + (0.15 * k),
                ymax=0.45,
                color=step_colors[f'Source {source_number} Ramp Up'],
                alpha=default_alpha,
                label=f'Source {source_number} Ramp Up',
            )
            j += 1
        for k in range(num_events_source_presput_dict[f'source{source_number}']):
            source_presput_start = bounds_events_source_presput_dict[
                f'source{source_number}'
            ][k][0]
            source_presput_end = bounds_events_source_presput_dict[
                f'source{source_number}'
            ][k][1]
            ax.axvspan(
                source_presput_start,
                source_presput_end,
                ymin=0.45 + (0.15 * k),
                ymax=0.50,
                color=step_colors[f'Source {source_number} Pre-Sputter'],
                alpha=default_alpha,
                label=f'Source {source_number} Pre-Sputter',
            )
        j += 1
        for k in range(num_events_source_on_dict[f'source{source_number}']):
            source_on_start = bounds_events_source_on_dict[f'source{source_number}'][k][
                0
            ]
            source_on_end = bounds_events_source_on_dict[f'source{source_number}'][k][1]
            ax.axvspan(
                source_on_start,
                source_on_end,
                ymin=0.5 + (0.15 * k),
                ymax=0.55,
                color=step_colors[f'Source {source_number} On'],
                alpha=default_alpha,
                label=f'Source {source_number} On',
            )
        j += 1

# Add labels and legend
ax.set_ylabel('Step')
ax.legend(loc='upper right')


# Adjust y-axis limits to fit all steps

# Improve layout and show the plot
plt.tight_layout()
plt.show()

# %%
# --------PRINT DERIVED QUANTITIES REPORT-------------

print(f'Derived quantities report for logfile\n{logfile_name}:\n')
print_derived_quantities(derived_quant)

# %%
# ---SAVE THE REPORT QUANTITIES IN A TEXT FILE---
# Specify the path and filename for the text file
txt_file_dir = logfile_dir + r'\derived_quantities_txt_files'
txt_file_name = logfile_name + '_derived_quantities.txt'
txt_file_path = os.path.join(txt_file_dir, txt_file_name)

# Save the derived quantities report as a text file as
with open(txt_file_path, 'w') as txt_file:
    txt_file.write(
        f'{version}\nDerived quantities report for logfile\n{logfile_name}:\n\n'
    )
    txt_file.write(write_derived_quantities(derived_quant))

# %%
