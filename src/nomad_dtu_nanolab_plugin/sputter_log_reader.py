"""
Created on Fri Jun  7 10:46:17 2024

@author: eugbe

"""
# ---------PACKAGES-------------

# Core
import copy
import operator
import os
import re
from functools import reduce

# Chamber visualization
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np

# Data manipulation
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from matplotlib import patches
from matplotlib.transforms import Affine2D
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots

# ---------MAIN FUNCTION PARAMETERS------------

# Set the execution flags
PRINT_MAIN_PARAMS = False
PRINT_STEP_PARAMS = False
PRINT_FIGURES = False
TEST_SPECIFIC_LOGFILE = True
REMOVE_SAMPLES = True
SAVE_STEP_PARAMS = False
RENAME_CRACKER_COL = True

LOGFILES_EXTENSION = 'CSV'
SPECTRA_EXTENSION = 'csv'

SAMPLES_TO_REMOVE = [
    # 'mittma_0025_Cu_Recording Set 2024.11.05-10.13.29',
    # 'mittma_0026_Cu_Recording Set 2024.11.06-09.44.32',
    # 'mittma_0027_Cu_Recording Set 2024.11.19-11.33.19',
]

SAMPLES_TO_TEST = [
    # 'eugbe_0020_Zr_Recording Set 2025.02.05-09.07.05',
    # 'eugbe_0021_Zr_Recording Set 2025.02.07-10.03.37',
    # 'mittma_0029_Cu_Recording Set 2024.12.02-10.49.07',
    'eugbe_0026_Ag_Recording Set 2025.03.07-10.09.23',
]

# -----USEFUL DICTIONARIES AND LISTS-----

# column names dictionary. Feel free to add more columns to this dictionary for easier
# access to the data
COL = {
    'time': 'Time Stamp',
    'time_stamp': 'Time Stamp',
    'pressure_wrg': 'PC Wide Range Gauge',
    'pressure': 'PC Capman Pressure',
    'pressure_sp': 'PC Capman Pressure Setpoint',
    'ps1_en': 'Power Supply 1 Enable',
    'ps1_ed': 'Power Supply 1 Enabled',
    'ps1_out_sp': 'Power Supply 1 Output Setpoint',
    'ps1_volt_sp': 'Power Supply 1 Voltage Setpoint',
    'ps1_curr_sp': 'Power Supply 1 Current Setpoint',
    'ps1_power': 'Power Supply 1 Power',
    'ps1_volt': 'Power Supply 1 Voltage',
    'ps1_curr': 'Power Supply 1 Current',
    'ps1_pulse_en': 'Power Supply 1 Pulse Enable',
    'ps1_pulse_freq_sp': 'Power Supply 1 Pulse Frequency Setpoint',
    'ps1_pulse_freq': 'Power Supply 1 Pulse Frequency',
    'ps1_rev_time_sp': 'Power Supply 1 Reverse Time Setpoint',
    'ps1_rev_time': 'Power Supply 1 Reverse Time',
    'ps2_en': 'Power Supply 2 Enable',
    'ps2_ed': 'Power Supply 2 Enabled',
    'ps2_out_sp': 'Power Supply 2 Output Setpoint',
    'ps2_fwd_pwr': 'Power Supply 2 Fwd Power',
    'ps2_rfl_pwr': 'Power Supply 2 Rfl Power',
    'ps2_dc_bias': 'Power Supply 2 DC Bias',
    'ps2_load_cap_pos': 'Power Supply 2 Load Cap Position',
    'ps2_tune_cap_pos': 'Power Supply 2 Tune Cap Position',
    'ps3_en': 'Power Supply 3 Enable',
    'ps3_ed': 'Power Supply 3 Enabled',
    'ps3_out_sp': 'Power Supply 3 Output Setpoint',
    'ps3_fwd_pwr': 'Power Supply 3 Fwd Power',
    'ps3_rfl_pwr': 'Power Supply 3 Rfl Power',
    'ps3_dc_bias': 'Power Supply 3 DC Bias',
    'ps3_load_cap_pos': 'Power Supply 3 Load Cap Position',
    'ps3_tune_cap_pos': 'Power Supply 3 Tune Cap Position',
    'mfc1_flow': 'PC MFC 1 Flow',
    'mfc1_sp': 'PC MFC 1 Setpoint',
    'ar_flow': 'PC MFC 1 Flow',
    'ar_sp': 'PC MFC 1 Setpoint',
    'mfc2_flow': 'PC MFC 2 Flow',
    'mfc2_sp': 'PC MFC 2 Setpoint',
    'n2_flow': 'PC MFC 2 Flow',
    'n2_sp': 'PC MFC 2 Setpoint',
    'mfc3_flow': 'PC MFC 3 Flow',
    'mfc3_sp': 'PC MFC 3 Setpoint',
    'o2_flow': 'PC MFC 3 Flow',
    'o2_sp': 'PC MFC 3 Setpoint',
    'mfc4_flow': 'PC MFC 4 Flow',
    'mfc4_sp': 'PC MFC 4 Setpoint',
    'ph3_flow': 'PC MFC 4 Flow',
    'ph3_sp': 'PC MFC 4 Setpoint',
    'mfc5_flow': 'PC MFC 5 Flow',
    'mfc5_sp': 'PC MFC 5 Setpoint',
    'nh3_flow': 'PC MFC 5 Flow',
    'nh3_sp': 'PC MFC 5 Setpoint',
    'mfc6_flow': 'PC MFC 6 Flow',
    'mfc6_sp': 'PC MFC 6 Setpoint',
    'h2s_flow': 'PC MFC 6 Flow',
    'h2s_sp': 'PC MFC 6 Setpoint',
    'sub_shutter_open': 'PC Substrate Shutter Open',
    'proc_phase': 'Process Phase',
    'proc_time_tracker': 'Process Time Tracker',
    'thk_rate': 'Thickness Rate',
    'deprate': 'Thickness Rate',
    'thk': 'Thickness',
    'thk_tooling': 'Thickness Tooling',
    'thk_active_mat': 'Thickness Active Material',
    'thk_mat_density': 'Thickness Material Density',
    'thk_mat_z': 'Thickness Material Z',
    'thk_q': 'Thickness Q',
    'thk_err': 'Thickness Error',
    'sub_temp_ctrl_en': 'Substrate Heater Temperature Control Enable',
    'sub_temp_sp': 'Substrate Heater Temperature Setpoint',
    'sub_temp': 'Substrate Heater Temperature',
    'sub_temp2': 'Substrate Heater Temperature 2',
    'sub_curr': 'Substrate Heater Current',
    'sul_crk_zone1_temp': 'Sulfur Cracker Zone 1 Current Temperature',
    'crk_z1_temp': 'Sulfur Cracker Zone 1 Current Temperature',
    'sul_crk_zone1_en': 'Sulfur Cracker Zone 1 Enabled',
    'crk_z1_en': 'Sulfur Cracker Zone 1 Enabled',
    'sul_crk_zone1_sp': 'Sulfur Cracker Zone 1 Temperature Setpoint',
    'crk_z1_sp': 'Sulfur Cracker Zone 1 Temperature Setpoint',
    'sul_crk_zone2_temp': 'Sulfur Cracker Zone 2 Current Temperature',
    'crk_z2_temp': 'Sulfur Cracker Zone 2 Current Temperature',
    'sul_crk_zone2_en': 'Sulfur Cracker Zone 2 Enabled',
    'crk_z2_en': 'Sulfur Cracker Zone 2 Enabled',
    'sul_crk_zone2_sp': 'Sulfur Cracker Zone 2 Temperature Setpoint',
    'crk_z2_sp': 'Sulfur Cracker Zone 2 Temperature Setpoint',
    'sul_crk_zone3_temp': 'Sulfur Cracker Zone 3 Current Temperature',
    'crk_z3_temp': 'Sulfur Cracker Zone 3 Current Temperature',
    'sul_crk_zone3_en': 'Sulfur Cracker Zone 3 Enabled',
    'crk_z3_en': 'Sulfur Cracker Zone 3 Enabled',
    'sul_crk_zone3_sp': 'Sulfur Cracker Zone 3 Temperature Setpoint',
    'crk_z3_sp': 'Sulfur Cracker Zone 3 Temperature Setpoint',
    'sul_crk_lambda': 'Sulfur Cracker Control Sensor Value',
    'crk_lambda': 'Sulfur Cracker Control Sensor Value',
    'sul_crk_ctrl_en': 'Sulfur Cracker Control Enabled',
    'crk_ctrl_en': 'Sulfur Cracker Control Enabled',
    'sul_crk_ctrl_mode': 'Sulfur Cracker Control Mode',
    'crk_ctrl_mode': 'Sulfur Cracker Control Mode',
    'sul_crk_ctrl_sensor': 'Sulfur Cracker Control Sensor Value',
    'crk_ctrl_sensor': 'Sulfur Cracker Control Sensor Value',
    'sul_crk_ctrl_sp': 'Sulfur Cracker Control Setpoint',
    'crk_ctrl_sp': 'Sulfur Cracker Control Setpoint',
    'sul_crk_ctrl_fb': 'Sulfur Cracker Control Setpoint Feedback',
    'crk_freq': 'Sulfur Cracker Control Setpoint Feedback',
    'sul_crk_valve_freq_sp': 'Sulfur Cracker Control Valve InitFrequency Setpoint',
    'crk_valve_freq_sp': 'Sulfur Cracker Control Valve InitFrequency Setpoint',
    'sul_crk_valve_pw_sp': 'Sulfur Cracker Control Valve PulseWidth Setpoint',
    'crk_valve_pw_sp': 'Sulfur Cracker Control Valve PulseWidth Setpoint',
    'sul_crk_valve_pw_fb': 'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback',
    'crk_valve_pw_fb': 'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback',
    'sul_crk_valve_sp': 'Sulfur Cracker Control Valve Setpoint',
    'crk_valve_sp': 'Sulfur Cracker Control Valve Setpoint',
    'sul_crk_valve_val': 'Sulfur Cracker Control Valve Value',
    's1_load': 'PC Source 1 Loaded Target',
    's1_mat': 'PC Source 1 Material',
    's1_shutter': 'PC Source 1 Shutter Open',
    's1_pdc_ps1': 'PC Source 1 Switch-PDC-PWS1',
    's1_rf1_ps2': 'PC Source 1 Switch-RF1-PWS2',
    's1_rf2_ps3': 'PC Source 1 Switch-RF2-PWS3',
    's1_usage': 'PC Source 1 Usage',
    's1_usage_calc': 'PC Source 1 Usage Calculation',
    's3_load': 'PC Source 3 Loaded Target',
    's3_mat': 'PC Source 3 Material',
    's3_shutter': 'PC Source 3 Shutter Open',
    's3_pdc_ps1': 'PC Source 3 Switch-PDC-PWS1',
    's3_rf1_ps2': 'PC Source 3 Switch-RF1-PWS2',
    's3_rf2_ps3': 'PC Source 3 Switch-RF2-PWS3',
    's3_usage': 'PC Source 3 Usage',
    's3_usage_calc': 'PC Source 3 Usage Calculation',
    's4_load': 'PC Source 4 Loaded Target',
    's4_mat': 'PC Source 4 Material',
    's4_shutter': 'PC Source 4 Shutter Open',
    's4_pdc_ps1': 'PC Source 4 Switch-PDC-PWS1',
    's4_rf1_ps2': 'PC Source 4 Switch-RF1-PWS2',
    's4_rf2_ps3': 'PC Source 4 Switch-RF2-PWS3',
    's4_usage': 'PC Source 4 Usage',
    's4_usage_calc': 'PC Source 4 Usage Calculation',
    'sub_rot_pos': 'Substrate Rotation_Position',
    'sub_rot_pos_sp': 'Substrate Rotation_PositionSetpoint',
    'xtal1_shutter': 'Xtal 1 Shutter Open',
    'xtal2_shutter': 'Xtal 2 Shutter Open',
    'xtal1_open': 'Xtal 1 Shutter Open',
    'xtal2_open': 'Xtal 2 Shutter Open',
    'ps7_en': 'Power Supply 7 Enable',
    'ps7_ed': 'Power Supply 7 Enabled',
    'ps7_out_sp': 'Power Supply 7 Output Setpoint',
    'ps7_fwd_pwr': 'Power Supply 7 Fwd Power',
    'ps7_rfl_pwr': 'Power Supply 7 Rfl Power',
    'ps7_dc_bias': 'Power Supply 7  Bias',
    'ps7_load_cap_pos': 'Power Supply 7 Load Cap Position',
    'ps7_tune_cap_pos': 'Power Supply 7 Tune Cap Position',
}
for source_number in ['1', '3', '4']:
    COL[f's{source_number}_en'] = f'Source {source_number} Enable'
    COL[f's{source_number}_ed'] = f'Source {source_number} Enabled'
    COL[f's{source_number}_out_sp'] = f'Source {source_number} Output Setpoint'
    COL[f's{source_number}_volt_sp'] = f'Source {source_number} Voltage Setpoint'
    COL[f's{source_number}_curr_sp'] = f'Source {source_number} Current Setpoint'
    COL[f's{source_number}_power'] = f'Source {source_number} Power'
    COL[f's{source_number}_volt'] = f'Source {source_number} Voltage'
    COL[f's{source_number}_curr'] = f'Source {source_number} Current'
    COL[f's{source_number}_pulse_en'] = f'Source {source_number} Pulse Enable'
    COL[f's{source_number}_pulse_freq_sp'] = (
        f'Source {source_number} Pulse Frequency Setpoint'
    )
    COL[f's{source_number}_pulse_freq'] = f'Source {source_number} Pulse Frequency'
    COL[f's{source_number}_rev_time_sp'] = (
        f'Source {source_number} Reverse Time Setpoint'
    )
    COL[f's{source_number}_rev_time'] = f'Source {source_number} Reverse Time'
    COL[f's{source_number}_fwd_pwr'] = f'Source {source_number} Fwd Power'
    COL[f's{source_number}_rfl_pwr'] = f'Source {source_number} Rfl Power'
    COL[f's{source_number}_dc_bias'] = f'Source {source_number} DC Bias'
    COL[f's{source_number}_load_cap_pos'] = f'Source {source_number} Load Cap Position'
    COL[f's{source_number}_tune_cap_pos'] = f'Source {source_number} Tune Cap Position'

# Elements name to symbol dict
ELEMENTS = {
    '': 'X',
    'Hydrogen': 'H',
    'Helium': 'He',
    'Lithium': 'Li',
    'Beryllium': 'Be',
    'Boron': 'B',
    'Carbon': 'C',
    'Nitrogen': 'N',
    'Oxygen': 'O',
    'Fluorine': 'F',
    'Neon': 'Ne',
    'Sodium': 'Na',
    'Magnesium': 'Mg',
    'Aluminium': 'Al',
    'Silicon': 'Si',
    'Phosphorus': 'P',
    'Sulfur': 'S',
    'Chlorine': 'Cl',
    'Argon': 'Ar',
    'Potassium': 'K',
    'Calcium': 'Ca',
    'Scandium': 'Sc',
    'Titanium': 'Ti',
    'Vanadium': 'V',
    'Chromium': 'Cr',
    'Manganese': 'Mn',
    'Iron': 'Fe',
    'Cobalt': 'Co',
    'Nickel': 'Ni',
    'Copper': 'Cu',
    'Zinc': 'Zn',
    'Gallium': 'Ga',
    'Germanium': 'Ge',
    'Arsenic': 'As',
    'Selenium': 'Se',
    'Bromine': 'Br',
    'Krypton': 'Kr',
    'Rubidium': 'Rb',
    'Strontium': 'Sr',
    'Yttrium': 'Y',
    'Zirconium': 'Zr',
    'Niobium': 'Nb',
    'Molybdenum': 'Mo',
    'Technetium': 'Tc',
    'Ruthenium': 'Ru',
    'Rhodium': 'Rh',
    'Palladium': 'Pd',
    'Silver': 'Ag',
    'Cadmium': 'Cd',
    'Indium': 'In',
    'Tin': 'Sn',
    'Antimony': 'Sb',
    'Tellurium': 'Te',
    'Iodine': 'I',
    'Xenon': 'Xe',
    'Caesium': 'Cs',
    'Barium': 'Ba',
    'Lanthanum': 'La',
    'Cerium': 'Ce',
    'Praseodymium': 'Pr',
    'Neodymium': 'Nd',
    'Promethium': 'Pm',
    'Samarium': 'Sm',
    'Europium': 'Eu',
    'Gadolinium': 'Gd',
    'Terbium': 'Tb',
    'Dysprosium': 'Dy',
    'Holmium': 'Ho',
    'Erbium': 'Er',
    'Thulium': 'Tm',
    'Ytterbium': 'Yb',
    'Lutetium': 'Lu',
    'Hafnium': 'Hf',
    'Tantalum': 'Ta',
    'Tungsten': 'W',
    'Rhenium': 'Re',
    'Osmium': 'Os',
    'Iridium': 'Ir',
    'Platinum': 'Pt',
    'Gold': 'Au',
    'Mercury': 'Hg',
    'Thallium': 'Tl',
    'Lead': 'Pb',
    'Bismuth': 'Bi',
    'Polonium': 'Po',
    'Astatine': 'At',
    'Radon': 'Rn',
    'Francium': 'Fr',
    'Radium': 'Ra',
    'Actinium': 'Ac',
    'Thorium': 'Th',
    'Protactinium': 'Pa',
    'Uranium': 'U',
    'Neptunium': 'Np',
    'Plutonium': 'Pu',
    'Americium': 'Am',
    'Curium': 'Cm',
    'Berkelium': 'Bk',
    'Californium': 'Cf',
    'Einsteinium': 'Es',
    'Fermium': 'Fm',
    'Mendelevium': 'Md',
    'Nobelium': 'No',
    'Lawrencium': 'Lr',
    'Rutherfordium': 'Rf',
    'Dubnium': 'Db',
    'Seaborgium': 'Sg',
    'Bohrium': 'Bh',
    'Hassium': 'Hs',
    'Meitnerium': 'Mt',
    'Darmastadtium': 'Ds',
    'Roentgenium': 'Rg',
    'Copernicium': 'Cn',
    'Nihonium': 'Nh',
    'Flerovium': 'Fl',
    'Moscovium': 'Mc',
    'Livermorium': 'Lv',
    'Tennessine': 'Ts',
    'Oganesson': 'Og',
}
IONS = {
    '': '',
    'sulphide': 'S',
    'sulfide': 'S',
    'antimonide': 'Sb',
    'phosphide': 'P',
    'arsenide': 'As',
    'telluride': 'Te',
    'oxide': 'O',
    'fluoride': 'F',
    'chloride': 'Cl',
    'bromide': 'Br',
    'iodide': 'I',
    'selenide': 'Se',
    'nitride': 'N',
    'carbide': 'C',
    'hydride': 'H',
}
# volumne fraction in the respective gas mixture (the complementary gas is Ar)
GAS_FRACTION = {
    'ar': 1,
    'n2': 1,
    'o2': 0.2,
    'ph3': 0.1,
    'nh3': 0.1,
    'h2s': 0.1,
}

# ----SPUTTER LOG READER METHODS----

# ---------REFERENCE VALUES-------------

# Set of reference values used in different parts of the script
# Proportion of values needed to be above the threshold to consider the
# plasma rf or dc
TOLERANCE = 0.85
# Propotion of values needed to be above the threshold to consider the
# plasma to be one particular type or the other
POWER_TYPE_TOLERANCE = 0.1
# fraction of the zeros in the dc bias data above which extra smoothing is triggered
DC_BIAS_SMOOTHING_THRESHOLD = 0.1
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
CAPMAN_PRESSURE_THRESHOLD = 0
# Threshold above which the flow of the mfc is considered on
MFC_FLOW_THRESHOLD = 1  # sccm
# Fr
# action of the length of the deposition dataframe to consider for the
# beginning and end of the deposition voltage averaging
FRAQ_ROWS_AVG_VOLTAGE = 5  # %
# Number of timesteps to consider for the continuity limit
CONTINUITY_LIMIT = 10
# Special continuity limit for deposition events
DEPOSITION_CONTINUITY_LIMIT = 1000
# Minimum size of a domain in terms of numbers of average timestep
MIN_DOMAIN_SIZE = 10
# Minimum size of a deposition in terms of numbers of average timestep
MIN_DEPOSITION_SIZE = 200
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
POWER_FWD_RFL_THRESHOLD = 10  # watts
# ---REPORT VALUES---

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
# Categories of events to be considered in the step report
CATEGORIES_STEPS = [
    'deposition',
    'ramp_up_temp',
    'ramp_down_high_temp',
    'source_presput',
    'source_ramp_up',
]
# ------OTHER VALUES------

# Categories of events to select the last event before the deposition, if possible
CATEGORIES_LAST_EVENT = ['source_deprate2_film_meas', 'ramp_up_temp', 'source_ramp_up']
# Categories of events to put in the bottom of the timeline plot
CATEGORIES_FIRST = {
    'deposition',
    'ramp_up_temp',
    'ramp_down_high_temp',
    'ramp_down_low_temp',
}
SOURCE_NAME = {
    '0': 's_cracker',
    '1': 'taurus',
    '3': 'magkeeper3',
    '4': 'magkeeper4',
    'all': 'all',
}

SOURCE_LABEL = {
    's_cracker': 'S Cracker',
    'taurus': 'Taurus',
    'magkeeper3': 'Magkeeper3',
    'magkeeper4': 'Magkeeper4',
    'all': 'all',
}
GAS_NUMBER = {
    'ar': 1,
    'n2': 2,
    'o2': 3,
    'ph3': 4,
    'nh3': 5,
    'h2s': 6,
}

# ----PLOT VALUES-----


BASE_HEIGHT = 250
WIDTH = 700
HEIGHT = 450
VERTICAL_SPACING = 0
ROLLING_NUM = 50
ROLLING_FRAC_MAX = 0.2

BOOL_THRESHOLD = 0.5
LINE_BREAK_LIMIT = 15

EXPORT_SCALE = 20
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

OVERVIEW_PLOT_RESAMPLING_TIME = 30  # seconds
BIAS_PLOT_RESAMPLING_TIME = 10  # seconds
OVERVIEW_PLOT_COLOR_MAP = {True: 'green', False: 'red'}
OVERVIEW_PLOT_MARKER_MAP = {True: 'x', False: 'circle'}

# Choosing what to plot in the overview plot
OVERVIEW_PLOT = [
    'PC Capman Pressure',
    'Substrate Heater Temperature',
    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback',
    'Sulfur Cracker Control Setpoint Feedback',
    'Sulfur Cracker Zone 1 Current Temperature',
    'Thickness Rate',
]
for gas in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
    OVERVIEW_PLOT.append(f'PC MFC {GAS_NUMBER[gas]} Flow')

for source_number in ['1', '3', '4']:
    OVERVIEW_PLOT.append(f'Source {source_number} DC Bias')
    OVERVIEW_PLOT.append(f'Source {source_number} Voltage')
    OVERVIEW_PLOT.append(f'Source {source_number} Output Setpoint')

# Set y-axis titles
DICT_RENAME = {
    'Sulfur Cracker Control Sensor Value': 'Cracker Sensor Value',
    'Sulfur Cracker Control Enabled': 'Cracker Open',
    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback': 'Cracker Pulse Width',
    'Sulfur Cracker Control Setpoint Feedback': 'Cracker Frequency',
    'PC MFC 1 Flow': 'Ar Flow',
    'PC MFC 2 Flow': 'N2 Flow',
    'PC MFC 3 Flow': 'O2 Flow',
    'PC MFC 4 Flow': 'PH3 Flow',
    'PC MFC 5 Flow': 'NH3 Flow',
    'PC MFC 6 Flow': 'H2S Flow',
}
DPI = 300
PLOTLY_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',
        # 'width': 10*WIDTH,
        # 'height': 10*HEIGHT,
        'scale': 10,
    }
}

##------EVENT CLASS DEFINITION------


class Lf_Event:
    def __init__(
        self, name: str, source=None, category=None, step_number=None, step_id=None
    ):
        # human readable name of the event
        self.name = name
        # category of the event (Ex: deposition, ramp_up_temp, etc)
        self.category = category
        # source associated with the event (Ex: source_presput)
        # None if the event is not associated with no or more than one
        # source (Ex: deposition)
        self.source = source
        # the avg_timestep is the average time difference between two
        # consecutive timestamps in the raw_logfile. It is used as a reference
        # time to determine the continuity of the time domains
        self.avg_timestep = None
        # we also enable storring of the original raw data, whenever it is passed
        self.raw_data = pd.DataFrame()
        # the condition is a boolean pd.Series that indicates which rows of the
        # raw_data are part of the particular event
        self.cond = pd.DataFrame()
        # the data is a pd.DataFrame that contains the rows of the raw_data that
        # meet the condition defined above
        self.data = pd.DataFrame()
        # the bounds are the start and end timestamps of the continuous time
        # there can be multiple bounds if the event is not continuous. If so
        # there will be separate events (sep_) for each continuous domain
        self.bounds = []
        # the number of time continuous domains in the event, essentially len(bounds)
        self.events = 0
        # if several events are within the object (time discontinuity),
        # the step number will indicate what is index of the subevent
        self.step_number = step_number
        # and sep_data will store the data of each subevent
        self.sep_data = [pd.DataFrame()]
        # the name of each subevent. Autmatically generated based on the name
        # of the event, the source and the index of the subevent
        # (Ex: Source 1 Ramp Up(0), Source 1 Ramp Up(1), etc)
        self.sep_name = ['']
        # the bounds of each subevent
        self.sep_bounds = []
        # we also store the raw spectra data from the optix, and trigger the
        # filtering of the spectra data when the raw_spectra is set,
        # same of sep_evenets
        self.raw_spectra = pd.DataFrame()
        self.filtered_spectra = pd.DataFrame()
        self.sep_spectra = [pd.DataFrame()]

        # here we create a unique identifier for the event
        # based on the name, category, source and step number
        if step_id is None:
            self.step_id = self.generate_step_id()

    def generate_step_id(self):
        if self.category is not None:
            step_id = self.category
        else:
            step_id = self.name
        if self.category != 'deposition':
            if self.source is not None:
                step_id += f'_s{self.source}'
            if self.step_number is not None:
                step_id += f'_n{self.step_number}'
        return step_id

    # method to populate the data attribute of the event, using the raw_data,
    # and the CONTINUITY_LIMIT (threshold for time continuity)
    def set_data(self, data, raw_data, continuity_limit=CONTINUITY_LIMIT):
        self.data = data
        # Whenever the data is set, we also calculate the average timestep...
        self.avg_timestep = cal_avg_timestep(raw_data)
        # ... the bounds...
        self.bounds = self.extract_domains(continuity_limit)
        # ... and run the update_events_and_separated_data method, which will
        # update the events, sep_data, sep_name and sep_bounds attributes
        self.update_events_and_separated_data()

    # method to set the bounds of the event
    def set_bounds(self, bounds):
        self.bounds = bounds
        # whenever the bounds are set, we also run the update_events_and_separated_data
        self.update_events_and_separated_data()
        # whenever the bounds are set, we also filter the spectra data if applicable
        if not self.raw_spectra:
            self.filtered_spectra = filter_spectrum(self.raw_spectra, self.bounds)

    # helper method to update events, sep_data, sep_name, and sep_bounds after
    # bounds changes
    def update_events_and_separated_data(self):
        self.events = len(self.bounds)
        self.sep_data = [event_filter(self.data, bound) for bound in self.bounds]
        self.sep_name = [f'{self.name}({i})' for i in range(self.events)]
        self.sep_bounds = [self.bounds[i] for i in range(self.events)]
        if not self.raw_spectra.empty:
            self.sep_spectra = [
                filter_spectrum(self.raw_spectra, self.bounds[i])
                for i in range(self.events)
            ]

    # very important method to extract the bounds of the continuous time domains
    def extract_domains(
        self, continuity_limit=CONTINUITY_LIMIT, timestamp_col='Time Stamp'
    ):
        """
        This function extracts the bounds of continuous time domains in a
        DataFrame based on the time continuity
        For example, if the time difference between two consecutive
        timestamps of df1 is greater than the continuity limit,
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

    # method to filter the data of the event based on a conditionnal boolean pd.Series
    def filter_data(self, raw_data, cond=None):
        if cond is not None:
            self.cond = cond
        if not self.cond.empty:
            self.raw_data = raw_data
            self.avg_timestep = cal_avg_timestep(raw_data)
            filtered_data = raw_data[self.cond]
            self.set_data(filtered_data, raw_data)
        else:
            print(f'Error: Unable to filter. No condition set for event {self.name}')

    def set_condition(self, condition):
        self.cond = condition

    def set_source(self, source):
        self.source = source

    def set_spectra(self, raw_spectra):
        self.raw_spectra = raw_spectra
        if not self.bounds:
            self.filtered_spectra = filter_spectrum(raw_spectra, self.bounds)

    # simple method to exlude events that are too small
    def filter_out_small_events(self, min_domain_size):
        data_list = []
        for i in range(self.events):
            if len(self.sep_data[i]) > min_domain_size:
                data_list.append(self.sep_data[i])
        # Concatenate the list of DataFrames
        if data_list:
            data = pd.concat(data_list, ignore_index=True)
            self.set_data(data, data)

    # method to only select events that come before a certain reference time
    # with the option of selecting any event before the reference time
    def select_event(self, raw_data, event_loc: int, ref_time=None):
        event_list = []
        if ref_time is None:
            ref_time = self.data['Time Stamp'].iloc[-1]
        for i in range(self.events):
            if self.bounds[i][1] < ref_time:
                event_list.append(self.sep_data[i])
            elif self.bounds[i][1] > ref_time and self.bounds[i][0] < ref_time:
                # If the event is not entirely before the reference time, we
                # filter the data to only keep the data before the reference time
                event_list.append(
                    self.sep_data[i][self.sep_data[i]['Time Stamp'] < ref_time]
                )
        if event_loc < len(event_list):
            self.set_data(event_list[event_loc], raw_data)
        else:
            raise IndexError('event_loc is out of the range of the event_list')

    # specific method to stitch the source ramp up events together,
    # in the case a source is ramped up in several steps.
    # it essentially merges the events if the last output setpoint power
    # of first event is the same as the second event first output setpoint power
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

    # DTUsteps parameters extraction methods

    # method to extract the parameters of step events, in a format that can be
    # used to populate the Nomad DTUsteps of DTUSputtering
    def get_nomad_step_params(self, params=None, source_list=None):
        # Set a default value for the source list
        if source_list is None:
            source_list = [self.source]
        # Initialize the params dictionary if it is not provided
        if params is None:
            params = {}
        # Write the event step_id as the key of the dictionary

        params[self.step_id] = {}

        # Get basic step parameters in the dictionary

        params[self.step_id]['name'] = self.name
        params[self.step_id]['lab_id'] = self.step_id
        params[self.step_id]['category'] = self.category
        # Extract the start and end time, and duration of the event
        params[self.step_id]['start_time'] = self.data['Time Stamp'].iloc[0]
        params[self.step_id]['end_time'] = self.data['Time Stamp'].iloc[-1]
        params[self.step_id]['duration'] = (
            params[self.step_id]['end_time'] - params[self.step_id]['start_time']
        )
        params[self.step_id]['creates_new_thin_film'] = self.category == 'deposition'

        # Get the step environment parameters
        params = self.get_step_environment_params(params)
        # Get the sources parameters
        params = self.get_step_sources_params(params, source_list)
        # get the sputter_parameters

        return params

    # method to extract the so called environment parameters (gases, sources, etc)
    # of single steps
    def get_step_environment_params(self, params):
        # Extract the gas flow parameters

        # initialize the dictionaries
        params[self.step_id]['environment'] = {}
        params[self.step_id]['environment']['gas_flow'] = {}
        params[self.step_id]['environment']['pressure'] = {}
        params[self.step_id]['environment']['heater'] = {}

        # Get the strat time of the step
        start_time = self.data['Time Stamp'].iloc[0]

        for gas_name in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
            # initialize the gas_flow dictionary
            gas_flow = {}

            gas_flow['gas'] = {}
            gas_flow['flow_rate'] = {}

            gas_flow['gas_name'] = gas_name
            # In the following entry, we set the value of the gas flow rate
            gas_flow['flow_rate']['value'] = self.data[
                f'PC MFC {GAS_NUMBER[gas_name]} Flow'
            ].tolist()
            # In the following entry, we set the time values
            gas_flow['flow_rate']['time'] = (
                (self.data['Time Stamp'] - start_time).dt.total_seconds().tolist()
            )
            gas_flow['flow_rate']['measurement_type'] = 'Mass Flow Controller'
            gas_flow['gas']['name'] = gas_name

            params[self.step_id]['environment']['gas_flow'][gas_name] = gas_flow

        # Extract the pressure parameters
        if (self.data['PC Capman Pressure'] < CAPMAN_PRESSURE_THRESHOLD).all():
            pressure_col = 'PC Wide Range Gauge'
        elif (self.data['PC Wide Range Gauge'] > CAPMAN_PRESSURE_THRESHOLD).all():
            pressure_col = 'PC Capman Pressure'
        else:
            pressure_col = None

        if pressure_col is not None:
            # Extract the pressure parameters
            params[self.step_id]['environment']['pressure']['time'] = (
                (self.data['Time Stamp'] - start_time).dt.total_seconds().tolist()
            )
            params[self.step_id]['environment']['pressure']['value'] = self.data[
                pressure_col
            ].tolist()

        # Extract the platen bias parameters
        if 'Power Supply 7 Output Setpoint' in self.data.columns:
            params = self.get_platen_bias_params(params)

        # Extract the substrate heater parameters
        params = self.get_substrate_heater_params(params)

        return params

    def get_platen_bias_params(self, params):
        # Initialize the source dictionary if it does not exist
        if 'platen_bias' not in params[self.step_id]['environment']:
            params[self.step_id]['environment']['platen_bias'] = {}
            params[self.step_id]['environment']['platen_bias']['power_supply'] = {}
            params[self.step_id]['environment']['platen_bias']['shutter_open'] = {}

        # Extract the source source id
        params[self.step_id]['environment']['platen_bias']['name'] = 'platen_bias'

        # extract the state of the source shutter
        params[self.step_id]['environment']['platen_bias']['shutter_open']['value'] = [
            bool(x) for x in self.data['PC Substrate Shutter Open'].tolist()
        ]
        params[self.step_id]['environment']['platen_bias']['shutter_open']['time'] = (
            (self.data['Time Stamp'] - self.data['Time Stamp'].iloc[0])
            .dt.total_seconds()
            .tolist()
        )
        # we check if the shutter is open during more than the TOLERANCE
        params[self.step_id]['environment']['platen_bias']['shutter_open'][
            'mode_value'  # most common value
        ] = bool(self.data['PC Substrate Shutter Open'].value_counts().idxmax())

        # extract the power supply parameters
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'power_type'
        ] = 'RF'

        # get the time series in seconds from the start of the step
        time_series = (
            (self.data['Time Stamp'] - self.data['Time Stamp'].iloc[0])
            .dt.total_seconds()
            .tolist()
        )

        # the platen power supply is the seven
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'avg_power_sp'
        ] = self.data['Power Supply 7 Output Setpoint'].mean()
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'power_sp'
        ] = {}
        params[self.step_id]['environment']['platen_bias']['power_supply']['power_sp'][
            'value'
        ] = self.data['Power Supply 7 Output Setpoint'].tolist()
        params[self.step_id]['environment']['platen_bias']['power_supply']['power_sp'][
            'time'
        ] = time_series

        # Extract the source dc bias setpoint
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'avg_dc_bias'
        ] = self.data['Power Supply 7 DC Bias'].mean()
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'dc_bias'
        ] = {}
        params[self.step_id]['environment']['platen_bias']['power_supply']['dc_bias'][
            'value'
        ] = self.data['Power Supply 7 DC Bias'].tolist()
        params[self.step_id]['environment']['platen_bias']['power_supply']['dc_bias'][
            'time'
        ] = time_series

        # Extract the fwd power
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'avg_fwd_power'
        ] = self.data['Power Supply 7 Fwd Power'].mean()
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'fwd_power'
        ] = {}
        params[self.step_id]['environment']['platen_bias']['power_supply']['fwd_power'][
            'value'
        ] = self.data['Power Supply 7 Fwd Power'].tolist()
        params[self.step_id]['environment']['platen_bias']['power_supply']['fwd_power'][
            'time'
        ] = time_series

        # Extract the rfl power
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'avg_rfl_power'
        ] = self.data['Power Supply 7 Rfl Power'].mean()
        params[self.step_id]['environment']['platen_bias']['power_supply'][
            'rfl_power'
        ] = {}
        params[self.step_id]['environment']['platen_bias']['power_supply']['rfl_power'][
            'value'
        ] = self.data['Power Supply 7 Rfl Power'].tolist()
        params[self.step_id]['environment']['platen_bias']['power_supply']['rfl_power'][
            'time'
        ] = time_series

        return params

    def get_substrate_heater_params(self, params):
        # Initialize the source dictionary if it does not exist
        if 'substrate_heater' not in params[self.step_id]['environment']:
            params[self.step_id]['environment']['heater'] = {}
            params[self.step_id]['environment']['heater']['temp_1'] = {}
            params[self.step_id]['environment']['heater']['temp_2'] = {}
            params[self.step_id]['environment']['heater']['temp_sp'] = {}

        # extract the substrate heater avg temperature 1 and 2 and the setpoint
        params[self.step_id]['environment']['heater']['avg_temp_1'] = self.data[
            'Substrate Heater Temperature'
        ].mean()

        params[self.step_id]['environment']['heater']['avg_temp_2'] = self.data[
            'Substrate Heater Temperature 2'
        ].mean()

        params[self.step_id]['environment']['heater']['avg_temp_sp'] = self.data[
            'Substrate Heater Temperature Setpoint'
        ].mean()

        # get the time series in seconds from the start of the step
        time_series = (
            (self.data['Time Stamp'] - self.data['Time Stamp'].iloc[0])
            .dt.total_seconds()
            .tolist()
        )

        # Extract the substrate heater temperature 1

        params[self.step_id]['environment']['heater']['temp_1']['value'] = self.data[
            'Substrate Heater Temperature'
        ].tolist()
        params[self.step_id]['environment']['heater']['temp_1']['time'] = time_series

        # Extract the substrate heater temperature 2

        params[self.step_id]['environment']['heater']['temp_2']['value'] = self.data[
            'Substrate Heater Temperature 2'
        ].tolist()
        params[self.step_id]['environment']['heater']['temp_2']['time'] = time_series

        # Extract the substrate heater temperature setpoint

        params[self.step_id]['environment']['heater']['temp_sp']['value'] = self.data[
            'Substrate Heater Temperature Setpoint'
        ].tolist()
        params[self.step_id]['environment']['heater']['temp_sp']['time'] = time_series

        return params

    # method to extract the so called sources parameters of single steps
    def get_step_sources_params(self, params, source_list):
        # helper method to deduce the plasma type of the source during deposition

        # initialize the sources dictionary
        if 'sources' not in params[self.step_id]:
            params[self.step_id]['sources'] = {}

        for source_number in source_list:
            source_name = f'{SOURCE_NAME[str(source_number)]}'

            # get the power type of the source (incidentally, it also tells us if the
            # source was used e.g. if power_type is not None)
            power_type = self.get_power_type(source_number)
            if (f'Source {source_number} Output Setpoint' in self.data.columns) and (
                power_type is not None
            ):
                params = self.get_sputter_sources_step_params(
                    source_name, params, power_type, source_number
                )

        # check is the cracker zone 1 above the threshold
        if 'Sulfur Cracker Zone 1 Current Temperature' in self.data.columns:
            if (
                self.data['Sulfur Cracker Zone 1 Current Temperature'].mean()
                > CRACKER_ZONE_1_MIN_TEMP
            ):
                params = self.get_s_cracker_step_params(params)

            # params = self.get_reactive_gas_step_params(params)

        return params

    # def get_reactive_gas_step_params(self, params):
    #     return params

    def get_s_cracker_step_params(self, params):
        # Initialize the source dictionary if it does not exist
        if 's_cracker' not in params[self.step_id]['sources']:
            params[self.step_id]['sources']['s_cracker'] = {}
            params[self.step_id]['sources']['s_cracker']['zone1_temp'] = {}
            params[self.step_id]['sources']['s_cracker']['zone1_temp_sp'] = {}
            params[self.step_id]['sources']['s_cracker']['zone2_temp'] = {}
            params[self.step_id]['sources']['s_cracker']['zone3_temp'] = {}
            params[self.step_id]['sources']['s_cracker']['valve_on_time'] = {}
            params[self.step_id]['sources']['s_cracker']['valve_frequency'] = {}
            params[self.step_id]['sources']['s_cracker']['valve_pulsing'] = {}

        # check if the cracker is recorded by the log
        if 'Sulfur Cracker Zone 1 Current Temperature' not in self.data.columns:
            params[self.step_id]['sources']['s_cracker']['cracker_record'] = False
        else:
            params[self.step_id]['sources']['s_cracker']['cracker_record'] = True

        # get the time series in seconds from the start of the step
        time_series = (
            (self.data['Time Stamp'] - self.data['Time Stamp'].iloc[0])
            .dt.total_seconds()
            .tolist()
        )

        for zone_number in ['1', '2', '3']:
            # Extract the cracker zone temperature
            params[self.step_id]['sources']['s_cracker'][
                f'avg_zone{zone_number}_temp'
            ] = self.data[
                f'Sulfur Cracker Zone {zone_number} Current Temperature'
            ].mean()
            params[self.step_id]['sources']['s_cracker'][f'zone{zone_number}_temp'][
                'value'
            ] = self.data[
                f'Sulfur Cracker Zone {zone_number} Current Temperature'
            ].tolist()
            params[self.step_id]['sources']['s_cracker'][f'zone{zone_number}_temp'][
                'time'
            ] = time_series

        # Extract the cracker valve on time if possible
        cond_column_feedback = (
            'Sulfur Cracker Control Setpoint Feedback' in self.data.columns
        ) & (
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
            in self.data.columns
        )
        if cond_column_feedback:
            params[self.step_id]['sources']['s_cracker']['avg_valve_on_time'] = (
                self.data[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].mean()
            )
            params[self.step_id]['sources']['s_cracker']['valve_on_time']['value'] = (
                self.data[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].tolist()
            )
            params[self.step_id]['sources']['s_cracker']['valve_on_time']['time'] = (
                time_series
            )

        # Extract the cracker valve frequency
        cond_column_feedback = (
            'Sulfur Cracker Control Setpoint Feedback' in self.data.columns
        ) & (
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
            in self.data.columns
        )
        if cond_column_feedback:
            params[self.step_id]['sources']['s_cracker']['avg_valve_frequency'] = (
                self.data['Sulfur Cracker Control Setpoint Feedback'].mean()
            )
            params[self.step_id]['sources']['s_cracker']['valve_frequency']['value'] = (
                self.data['Sulfur Cracker Control Setpoint Feedback'].tolist()
            )
            params[self.step_id]['sources']['s_cracker']['valve_frequency']['time'] = (
                time_series
            )

        # extract if the cracker valve is pulsing (enabled) as a boolean series
        params[self.step_id]['sources']['s_cracker']['valve_pulsing']['value'] = [
            bool(x) for x in self.data['Sulfur Cracker Control Enabled'].tolist()
        ]
        params[self.step_id]['sources']['s_cracker']['valve_pulsing']['time'] = (
            time_series
        )

        # extract the mode value of the valve pulsing
        params[self.step_id]['sources']['s_cracker']['valve_pulsing']['mode_value'] = (
            bool(self.data['Sulfur Cracker Control Enabled'].value_counts().idxmax())
        )

        return params

    def get_sputter_sources_step_params(
        self, source_name, params, power_type, source_number
    ):
        # Initialize the source dictionary if it does not exist
        if source_name not in params[self.step_id]['sources']:
            params[self.step_id]['sources'][source_name] = {}
            params[self.step_id]['sources'][source_name]['power_supply'] = {}
            params[self.step_id]['sources'][source_name]['material'] = {}
            params[self.step_id]['sources'][source_name]['source_shutter_open'] = {}

        # Extract the source source id
        params[self.step_id]['sources'][source_name]['name'] = source_name
        params[self.step_id]['sources'][source_name]['target_id'] = self.data[
            f'PC Source {source_number} Loaded Target'
        ].iloc[0]

        # extract the state of the source shutter
        params[self.step_id]['sources'][source_name]['source_shutter_open']['value'] = [
            bool(x)
            for x in self.data[f'PC Source {source_number} Shutter Open'].tolist()
        ]
        params[self.step_id]['sources'][source_name]['source_shutter_open']['time'] = (
            (self.data['Time Stamp'] - self.data['Time Stamp'].iloc[0])
            .dt.total_seconds()
            .tolist()
        )
        # we check if the shutter is open during more than the TOLERANCE
        params[self.step_id]['sources'][source_name]['source_shutter_open'][
            'mode_value'  # most common value
        ] = bool(
            self.data[f'PC Source {source_number} Shutter Open'].value_counts().idxmax()
        )

        # extract the power supply parameters
        params[self.step_id]['sources'][source_name]['power_supply']['power_type'] = (
            power_type
        )

        # get the time series in seconds from the start of the step
        time_series = (
            (self.data['Time Stamp'] - self.data['Time Stamp'].iloc[0])
            .dt.total_seconds()
            .tolist()
        )

        # Extract the source power setpoint
        params[self.step_id]['sources'][source_name]['power_supply']['avg_power_sp'] = (
            self.data[f'Source {source_number} Output Setpoint'].mean()
        )
        params[self.step_id]['sources'][source_name]['power_supply']['power_sp'] = {}
        params[self.step_id]['sources'][source_name]['power_supply']['power_sp'][
            'value'
        ] = self.data[f'Source {source_number} Output Setpoint'].tolist()
        params[self.step_id]['sources'][source_name]['power_supply']['power_sp'][
            'time'
        ] = time_series

        if f'Source {source_number} Current' in self.data.columns:
            params[self.step_id]['sources'][source_name]['power_supply'][
                'avg_current'
            ] = self.data[f'Source {source_number} Current'].mean()
            params[self.step_id]['sources'][source_name]['power_supply']['current'] = {}
            params[self.step_id]['sources'][source_name]['power_supply']['current'][
                'value'
            ] = self.data[f'Source {source_number} Current'].tolist()
            params[self.step_id]['sources'][source_name]['power_supply']['current'][
                'time'
            ] = time_series

        # the quantities common to dc and plused
        # dc power supplies (avg and as time series)
        if power_type in ['DC', 'pulsed_DC']:
            params = self.get_dc_power_supply_params(
                source_name, source_number, power_type, time_series, params
            )

        elif power_type == 'RF':
            params = self.get_rf_power_supply_params(
                source_name, source_number, time_series, params
            )

        return params

    def get_rf_power_supply_params(
        self, source_name, source_number, time_series, params
    ):
        # Extract the source dc bias setpoint
        params[self.step_id]['sources'][source_name]['power_supply']['avg_dc_bias'] = (
            self.data[f'Source {source_number} DC Bias'].mean()
        )
        params[self.step_id]['sources'][source_name]['power_supply']['dc_bias'] = {}
        params[self.step_id]['sources'][source_name]['power_supply']['dc_bias'][
            'value'
        ] = self.data[f'Source {source_number} DC Bias'].tolist()
        params[self.step_id]['sources'][source_name]['power_supply']['dc_bias'][
            'time'
        ] = time_series

        # Extract the fwd power
        params[self.step_id]['sources'][source_name]['power_supply'][
            'avg_fwd_power'
        ] = self.data[f'Source {source_number} Fwd Power'].mean()
        params[self.step_id]['sources'][source_name]['power_supply']['fwd_power'] = {}
        params[self.step_id]['sources'][source_name]['power_supply']['fwd_power'][
            'value'
        ] = self.data[f'Source {source_number} Fwd Power'].tolist()
        params[self.step_id]['sources'][source_name]['power_supply']['fwd_power'][
            'time'
        ] = time_series

        # Extract the rfl power
        params[self.step_id]['sources'][source_name]['power_supply'][
            'avg_rfl_power'
        ] = self.data[f'Source {source_number} Rfl Power'].mean()
        params[self.step_id]['sources'][source_name]['power_supply']['rfl_power'] = {}
        params[self.step_id]['sources'][source_name]['power_supply']['rfl_power'][
            'value'
        ] = self.data[f'Source {source_number} Rfl Power'].tolist()
        params[self.step_id]['sources'][source_name]['power_supply']['rfl_power'][
            'time'
        ] = time_series

        return params

    def get_dc_power_supply_params(
        self, source_name, source_number, power_type, time_series, params
    ):
        params[self.step_id]['sources'][source_name]['power_supply']['avg_voltage'] = (
            self.data[f'Source {source_number} Voltage'].mean()
        )
        params[self.step_id]['sources'][source_name]['power_supply']['voltage'] = {}
        params[self.step_id]['sources'][source_name]['power_supply']['voltage'][
            'value'
        ] = self.data[f'Source {source_number} Voltage'].tolist()
        params[self.step_id]['sources'][source_name]['power_supply']['voltage'][
            'time'
        ] = time_series

        params[self.step_id]['sources'][source_name]['power_supply']['avg_current'] = (
            self.data[f'Source {source_number} Current'].mean()
        )
        params[self.step_id]['sources'][source_name]['power_supply']['current'] = {}
        params[self.step_id]['sources'][source_name]['power_supply']['current'][
            'value'
        ] = self.data[f'Source {source_number} Current'].tolist()
        params[self.step_id]['sources'][source_name]['power_supply']['current'][
            'time'
        ] = time_series

        # Extract the pulse frequency and dead time if applicable
        # (avg and as time series)
        if power_type == 'pulsed_DC':
            params[self.step_id]['sources'][source_name]['power_supply'][
                'avg_pulse_frequency'
            ] = self.data[f'Source {source_number} Pulse Frequency'].mean()
            params[self.step_id]['sources'][source_name]['power_supply'][
                'pulse_frequency'
            ] = {}
            params[self.step_id]['sources'][source_name]['power_supply'][
                'pulse_frequency'
            ]['value'] = self.data[f'Source {source_number} Pulse Frequency'].tolist()
            params[self.step_id]['sources'][source_name]['power_supply'][
                'pulse_frequency'
            ]['time'] = time_series

            params[self.step_id]['sources'][source_name]['power_supply'][
                'avg_dead_time'
            ] = self.data[f'Source {source_number} Reverse Time'].mean()
            params[self.step_id]['sources'][source_name]['power_supply'][
                'dead_time'
            ] = {}
            params[self.step_id]['sources'][source_name]['power_supply']['dead_time'][
                'value'
            ] = self.data[f'Source {source_number} Reverse Time'].tolist()
            params[self.step_id]['sources'][source_name]['power_supply']['dead_time'][
                'time'
            ] = time_series

        return params

    def get_power_type(self, source_number):
        dc_current_col = f'Source {source_number} Current'
        rf_bias_col = f'Source {source_number} DC Bias'
        pulse_enable_col = f'Source {source_number} Pulse Enable'
        fwd_power_col = f'Source {source_number} Fwd Power'
        rfl_power_col = f'Source {source_number} Rfl Power'

        power_type = None

        # We tolerate a certain percentage of the data to be below the threshold
        if dc_current_col in self.data and (
            (self.data[dc_current_col] > CURRENT_THRESHOLD).mean() >= TOLERANCE
        ):
            if pulse_enable_col in self.data and (
                self.data[pulse_enable_col].mean() >= POWER_TYPE_TOLERANCE
            ):
                power_type = 'pulsed_DC'
            else:
                power_type = 'DC'
        elif rf_bias_col in self.data and (
            (self.data[rf_bias_col] > BIAS_THRESHOLD).mean() >= POWER_TYPE_TOLERANCE
            or (
                (self.data[fwd_power_col] - self.data[rfl_power_col])
                > POWER_FWD_RFL_THRESHOLD
            ).mean()
            >= POWER_TYPE_TOLERANCE
        ):
            power_type = 'RF'
        return power_type


class Deposition_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='deposition', **kwargs)
        self.step_id = self.generate_step_id()

    # master parameters extraction method for the deposition event
    def get_params(
        self, raw_data=None, source_list=None, params=None, interrupt_deposition=False
    ):
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        # Extract if the deposition has beem interrupted based the interrupt_deposition
        # flag
        params[self.category]['interrupted'] = interrupt_deposition

        params = self.get_rt_bool(params=params)
        params = self.get_source_used_deposition(source_list, params=params)
        params = self.get_cracker_params(params=params)
        params = self.get_pressure_params(raw_data, params=params)
        params = self.get_simple_deposition_params(params=params)
        params = self.get_source_depostion_params(source_list, params=params)
        params = self.get_platen_bias_params(params=params)
        return params

    # method to deduce if the deposition was done at room temperature or not
    def get_rt_bool(self, params=None):
        # Extract if the deposition was done at room temperature as :
        # - the temperature control is disabled or
        # - the temperature control is enabled but the temperature setpoint
        # is below the RT threshold defined in the reference values

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if (
            self.data['Substrate Heater Temperature Setpoint'] < RT_TEMP_THRESHOLD
        ).mean() >= TOLERANCE:
            params[self.category]['rt'] = True
        elif (
            self.data['Substrate Heater Temperature Setpoint'] > RT_TEMP_THRESHOLD
        ).mean() >= TOLERANCE:
            params[self.category]['rt'] = False
        return params

    # method to extrac the sources used for deposition
    def get_source_used_deposition(self, source_list, params=None):
        # Extract the source used for deposition
        # For all sources, we check if the source is enabled during deposition
        # and if it is, we set the source as the source enabled for deposition
        # which implies that the source was also ramped up and presputtered

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}
        for source_number in source_list:
            if f'{SOURCE_NAME[str(source_number)]}' not in params[self.category]:
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'] = {}

        for source_number in source_list:
            if (
                not self.data.get(
                    f'Source {source_number} Enabled', pd.Series([0] * len(self.data))
                ).all()
                == 0
            ):
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'enabled'
                ] = True
            else:
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'enabled'
                ] = False

        return params

    # method to extract the s_cracker parameters
    def get_cracker_params(self, params=None):
        # Extract if the cracker has been used during deposition as the
        # cracker control being enabled and the temperatures of the
        # different zones being above the minimum temperatures
        # defined in the reference values

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}
        if 's_cracker' not in params[self.category]:
            params[self.category]['s_cracker'] = {}

        if 'Sulfur Cracker Zone 1 Current Temperature' not in self.data.columns:
            params[self.category]['s_cracker']['enabled'] = False
            return params

        if not self.is_cracker_enabled():
            params[self.category]['s_cracker']['enabled'] = False
            return params

        params[self.category]['s_cracker']['enabled'] = True
        params[self.category]['s_cracker']['zone1_temp'] = self.data[
            'Sulfur Cracker Zone 1 Current Temperature'
        ].mean()
        params[self.category]['s_cracker']['zone1_temp_sp'] = self.data[
            'Sulfur Cracker Zone 1 Temperature Setpoint'
        ].mean()
        params[self.category]['s_cracker']['zone2_temp'] = self.data[
            'Sulfur Cracker Zone 2 Current Temperature'
        ].mean()
        params[self.category]['s_cracker']['zone3_temp'] = self.data[
            'Sulfur Cracker Zone 3 Current Temperature'
        ].mean()

        cond_column_feedback = (
            'Sulfur Cracker Control Setpoint Feedback' in self.data.columns
        ) & (
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
            in self.data.columns
        )
        if cond_column_feedback:
            params[self.category]['s_cracker']['pulse_width'] = self.data[
                'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
            ].mean()
            params[self.category]['s_cracker']['pulse_freq'] = self.data[
                'Sulfur Cracker Control Setpoint Feedback'
            ].mean()

        return params

    def is_cracker_enabled(self):
        return (
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
        )

    # method to extract important pressure parameters
    def get_pressure_params(self, raw_data, params=None):
        # Extract the some base pressure metric as the lowest positive
        # pressure recorded before deposition (but only if
        # it is below 1-6Torr). If the cracker is enabled, then this metric is not
        # representative of the true base pressure and we set the
        # true_base_pressure_meas to False to indicate that the true base
        # pressure is not measured accurately: If the cracker is not enabled,
        # then the base pressure is measured accurately and we set the
        # true_base_pressure_meas to True

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
            if not params[self.category]['s_cracker']['enabled']:
                params['overview']['true_base_pressure_meas'] = True
            elif params[self.category]['s_cracker']['enabled']:
                params['overview']['true_base_pressure_meas'] = False
        else:
            params['overview']['true_base_pressure_meas'] = False

        if params['overview']['true_base_pressure_meas']:
            params['overview']['base_pressure'] = min_pressure_before_depostion

        return params

    # method to extract simple deposition parameters, that are not source specific
    def get_simple_deposition_params(self, params=None):
        # helper method to calculate the partial pressure of a gas
        def add_partial_pressures(gas, params):
            params[self.category][f'avg_{gas}_partial_pressure'] = (
                params[self.category]['avg_capman_pressure']
                * GAS_FRACTION[gas]
                * params[self.category][f'avg_{gas}_flow']
                / (
                    params[self.category]['avg_ar_flow']
                    + params[self.category]['avg_n2_flow']
                    + params[self.category]['avg_o2_flow']
                    + params[self.category]['avg_ph3_flow']
                    + params[self.category]['avg_nh3_flow']
                    + params[self.category]['avg_h2s_flow']
                )
            )
            return params

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

        for gas in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
            mean_flow = self.data[f'PC MFC {GAS_NUMBER[gas]} Flow'].mean()
            if mean_flow > MFC_FLOW_THRESHOLD:
                params[self.category][f'avg_{gas}_flow'] = mean_flow
            else:
                params[self.category][f'avg_{gas}_flow'] = 0

        # calculate the partial pressure of the gases
        for gas in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
            params = add_partial_pressures(gas, params)

        # calculate the ratio between the PH3 and H2S flow
        if (
            params[self.category]['avg_h2s_flow'] > MFC_FLOW_THRESHOLD
            and params[self.category]['avg_ph3_flow'] > MFC_FLOW_THRESHOLD
        ):
            params[self.category]['ph3_h2s_ratio'] = (
                params[self.category]['avg_ph3_flow']
                / params[self.category]['avg_h2s_flow']
            )
        # TODO, add the ratio for other reactive gases ?

        return params

    # method to extract the source specific parameters of the deposition event.
    # this method uses different sub-methods to extract the parameters of the
    # sources used during deposition
    def get_source_depostion_params(self, source_list, params=None):
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}
        elements = []
        for source_number in source_list:
            if params[self.category][f'{SOURCE_NAME[str(source_number)]}']['enabled']:
                params = self.get_avg_output_power(params, source_number)
                params = self.get_plasma_type(params, source_number)
                params = self.get_deposition_voltage(params, source_number)
                params, elements = self.get_source_material_and_target(
                    params, source_number, elements
                )
                # Extract source material and target id and add the element to the
                # elements list for the material space extraction
        # Extract the material space as the elements used during deposition
        if (
            'P' not in elements
            and params[self.category]['avg_ph3_flow'] > MFC_FLOW_THRESHOLD
        ):
            elements += ['P']
        if 'S' not in elements and (
            (params[self.category]['avg_h2s_flow'] > MFC_FLOW_THRESHOLD)
            or (params[self.category]['s_cracker']['enabled'])
        ):
            elements += ['S']
        if (
            'N' not in elements
            and params[self.category]['avg_n2_flow'] > MFC_FLOW_THRESHOLD
            or params[self.category]['avg_nh3_flow'] > MFC_FLOW_THRESHOLD
        ):
            elements += ['N']
        if (
            'O' not in elements
            and params[self.category]['avg_o2_flow'] > MFC_FLOW_THRESHOLD
        ):
            elements += ['O']
        # add the element as an hypen separated string
        params[self.category]['material_space'] = '-'.join(elements)
        return params

    # method to deduce the average output power of the source during deposition
    def get_avg_output_power(self, params, source_number):
        params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
            'avg_output_power'
        ] = self.data[f'Source {source_number} Output Setpoint'].mean()
        return params

    # method to deduce the plasma type of the source during deposition
    def get_plasma_type(self, params, source_number):
        dc_current_col = f'Source {source_number} Current'
        rf_bias_col = f'Source {source_number} DC Bias'
        pulse_enable_col = f'Source {source_number} Pulse Enable'
        fwd_power_col = f'Source {source_number} Fwd Power'
        rfl_power_col = f'Source {source_number} Rfl Power'

        # We tolerate a certain percentage of the data to be below the threshold
        if dc_current_col in self.data and (
            (self.data[dc_current_col] > CURRENT_THRESHOLD).mean() >= TOLERANCE
        ):
            params[self.category][f'{SOURCE_NAME[str(source_number)]}']['DC'] = True
            params[self.category][f'{SOURCE_NAME[str(source_number)]}']['RF'] = False
            if pulse_enable_col in self.data and (
                (self.data[pulse_enable_col] == 1).mean() >= TOLERANCE
            ):
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'pulsed'
                ] = True

                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'plasma_type'
                ] = 'pulsed_DC'

                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'pulse_frequency'
                ] = self.data[f'Source {source_number} Pulse Frequency'].mean()
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'dead_time'
                ] = self.data[f'Source {source_number} Reverse Time'].mean()
            else:
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'pulsed'
                ] = False
                params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                    'plasma_type'
                ] = 'DC'
        elif rf_bias_col in self.data and (
            (self.data[rf_bias_col] > BIAS_THRESHOLD).mean() >= TOLERANCE
            or (
                (self.data[fwd_power_col] - self.data[rfl_power_col])
                > POWER_FWD_RFL_THRESHOLD
            ).mean()
            >= TOLERANCE
        ):
            params[self.category][f'{SOURCE_NAME[str(source_number)]}']['RF'] = True
            params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
                'plasma_type'
            ] = 'RF'
            params[self.category][f'{SOURCE_NAME[str(source_number)]}']['DC'] = False
            params[self.category][f'{SOURCE_NAME[str(source_number)]}']['pulsed'] = (
                False
            )
        else:
            print('Error: Plasma type not recognized')
        return params

    # method to deduce the deposition voltage of the source during deposition
    def get_deposition_voltage(self, params, source_number):
        def extract_voltage_stats(data, key_prefix):
            start_voltage = data.iloc[
                : int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(data))
            ].mean()
            end_voltage = data.iloc[
                -int(FRAQ_ROWS_AVG_VOLTAGE * 0.01 * len(data)) :
            ].mean()
            return {
                'start_voltage': start_voltage,
                'end_voltage': end_voltage,
                'avg_voltage': data.mean(),
                'min_voltage': data.min(),
                'max_voltage': data.max(),
                'std_voltage': data.std(),
                'range_voltage': data.max() - data.min(),
                'start_minus_end_voltage': start_voltage - end_voltage,
            }

        source_key = f'{SOURCE_NAME[f"{source_number}"]}'
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

    # method to deduce the source material and target of the source during deposition
    def get_source_material_and_target(self, params, source_number, elements):
        params[self.category][f'{SOURCE_NAME[str(source_number)]}']['target_name'] = (
            f'{SOURCE_NAME[str(source_number)]}'
        )

        source_material = self.data[f'PC Source {source_number} Material'].iloc[0]
        elements, material = elements_from_string(source_material, elements)

        params[self.category][f'{SOURCE_NAME[str(source_number)]}'][
            'target_material'
        ] = material
        params[self.category][f'{SOURCE_NAME[str(source_number)]}']['target_id'] = (
            self.data[f'PC Source {source_number} Loaded Target'].iloc[0]
        )
        #the acumulated power is the last power recorded after the deposition
        params[self.category][f'{SOURCE_NAME[str(source_number)]}']['target_usage'] = (
            self.data[f'PC Source {source_number} Usage'].iloc[-1]
        )
        return params, elements

    def get_platen_bias_params(self, params=None):
        # Extract the platen bias during deposition
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        params[self.category]['platen_bias'] = {}

        if 'Power Supply 7 Output Setpoint' in self.data:
            if (
                self.data['Power Supply 7 DC Bias'] > BIAS_THRESHOLD
            ).mean() >= TOLERANCE:
                params[self.category]['platen_bias']['enabled'] = True
            else:
                params[self.category]['platen_bias']['enabled'] = False
        else:
            params[self.category]['platen_bias']['enabled'] = False

        if params[self.category]['platen_bias']['enabled']:
            params[self.category]['platen_bias']['platen_power'] = self.data[
                'Power Supply 7 Output Setpoint'
            ].mean()
            params[self.category]['platen_bias']['avg_platen_bias'] = self.data[
                'Power Supply 7 DC Bias'
            ].mean()

        return params


class SCracker_Pressure_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='cracker_base_pressure', **kwargs)
        self.step_id = self.generate_step_id()

    # method to extract the pressure induced by the cracker
    def get_params(self, raw_data=None, source_list=None, params=None):
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


class Source_Presput_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='source_presput', **kwargs)

        self.step_id = self.generate_step_id()

    # method to extract source dependent presputtering parameters
    def get_params(self, raw_data=None, source_list=None, params=None):
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        target_name = f'{SOURCE_NAME[str(self.source)]}'

        source_number = self.source
        if target_name not in params[self.category]:
            params[self.category][target_name] = {}

        # We check if the source is enabled during deposition
        if params['deposition'][target_name]['enabled']:
            # ----source presputtering parameters-----
            params[self.category][target_name]['target_name'] = target_name
            # Extract the presputtering duration
            presput_duration = 0
            for i in range(len(self.bounds)):
                presput_duration += (
                    self.bounds[i][1] - self.bounds[i][0]
                ).total_seconds()
            presput_duration = pd.to_timedelta(presput_duration, unit='s')
            params[self.category][target_name]['duration'] = presput_duration
            # Extract the average output power during presputtering
            params[self.category][target_name]['avg_output_power'] = self.data[
                f'Source {source_number} Output Setpoint'
            ].mean()
            # Extract the avg capman pressure during presputtering
            params[self.category][target_name]['avg_capman_pressure'] = self.data[
                'PC Capman Pressure'
            ].mean()
            # Extract the gas flows during presputtering
            if self.data['PC MFC 1 Flow'].mean() > MFC_FLOW_THRESHOLD:
                params[self.category][target_name]['avg_ar_flow'] = self.data[
                    'PC MFC 1 Flow'
                ].mean()
            else:
                params[self.category][target_name]['avg_ar_flow'] = 0
        return params


class Source_Ramp_Up_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)
        super().__init__(*args, category='source_ramp_up', **kwargs)
        self.step_id = self.generate_step_id()

    # method to extract the source ramp up and ignition parameters
    def get_params(self, raw_data=None, source_list=None, params=None):
        # Here, we interate over the sources to extract many relevant parameters

        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        source_number = self.source
        target_name = f'{SOURCE_NAME[str(source_number)]}'
        if target_name not in params[self.category]:
            params[self.category][target_name] = {}
        # We check if the source is enabled during deposition
        if params['deposition'][target_name]['enabled']:
            params[self.category][target_name]['target_name'] = target_name
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
                | ((fwd_power_series - rfl_power_series) > POWER_FWD_RFL_THRESHOLD)
            )
            # Apply the mask to get the moment where the plasma is on during
            # ramp up
            data_ignition_time = self.data.loc[mask]
            # If the plasma turns on during ramp up, data_ignition_time should
            # not be empty
            if not data_ignition_time.empty:
                ignition_time = data_ignition_time['Time Stamp'].iloc[0]
                params[self.category][target_name]['ignition'] = True
                params[self.category][target_name]['ignition_time'] = ignition_time
                ignition_data = self.data[self.data['Time Stamp'] == ignition_time]
                params[self.category][target_name]['ignition_power'] = ignition_data[
                    f'Source {source_number} Output Setpoint'
                ].iloc[0]
                params[self.category][target_name]['ignition_pressure'] = ignition_data[
                    'PC Capman Pressure'
                ].iloc[0]
            else:
                params[self.category][target_name]['source_ignition'] = False

        return params


class Sub_Ramp_Up_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)
        super().__init__(*args, category='ramp_up_temp', **kwargs)
        self.step_id = self.generate_step_id()

    # method to extract the substrate ramp up parameters
    def get_params(self, raw_data=None, source_list=None, params=None):
        if 'deposition' not in params:
            raise ValueError('Missing deposition info, run get_rt_bool first')
        if self.category not in params:
            params[self.category] = {}
        if 's_cracker' not in params[self.category]:
            params[self.category]['s_cracker'] = {}

        if not params['deposition']['rt']:
            # ------Extract the substrate ramp up parameters------
            # Extract the slope assuming linear ramp up
            # In data_ramp_up_temp only increasing setpoint temperature are
            # considered making easier to extract the slope
            params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
            params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]
            params[self.category]['start_temp'] = self.data[
                'Substrate Heater Temperature Setpoint'
            ].iloc[0]
            params[self.category]['end_temp'] = self.data[
                'Substrate Heater Temperature Setpoint'
            ].iloc[-1]
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

            for gas in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
                mean_flow = self.data[f'PC MFC {GAS_NUMBER[gas]} Flow'].mean()
                if mean_flow > MFC_FLOW_THRESHOLD:
                    params[self.category][f'avg_{gas}_flow'] = mean_flow
                else:
                    params[self.category][f'avg_{gas}_flow'] = 0

            # Extract if the cracker has been used during ramp up
            # The column 'Sulfur Cracker Control Enabled' correspond to the
            # act of opening the cracker pulse valve (1 open, 0 closed)
            if 'Sulfur Cracker Zone 1 Current Temperature' in raw_data.columns:
                if (
                    (self.data['Sulfur Cracker Control Enabled'] == 1).mean()
                    >= TOLERANCE
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
                    params[self.category]['s_cracker']['enabled'] = True
                    # If the cracker has been used, extract the cracker parameters
                    params[self.category]['s_cracker']['zone1_temp'] = self.data[
                        'Sulfur Cracker Zone 1 Current Temperature'
                    ].mean()
                    params[self.category]['s_cracker']['zone1_temp_sp'] = self.data[
                        'Sulfur Cracker Zone 1 Temperature Setpoint'
                    ].mean()
                    params[self.category]['s_cracker']['zone2_temp'] = self.data[
                        'Sulfur Cracker Zone 2 Current Temperature'
                    ].mean()
                    params[self.category]['s_cracker']['zone3_temp'] = self.data[
                        'Sulfur Cracker Zone 3 Current Temperature'
                    ].mean()
                    cond_column_feedback = (
                        'Sulfur Cracker Control Setpoint Feedback' in self.data.columns
                    ) & (
                        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                        in self.data.columns
                    )
                    if cond_column_feedback:
                        params[self.category]['s_cracker']['pulse_width'] = self.data[
                            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                        ].mean()
                        params[self.category]['s_cracker']['pulse_freq'] = self.data[
                            'Sulfur Cracker Control Setpoint Feedback'
                        ].mean()
                else:
                    params[self.category]['s_cracker']['enabled'] = False
            else:
                params[self.category]['s_cracker']['enabled'] = False
        return params


class Sub_Ramp_Down_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='sub_ramp_down', **kwargs)

        self.step_id = self.generate_step_id()

    # method to extract the substatre temperature ramp down parameters,
    def get_params(self, raw_data=None, source_list=None, params=None):
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

            params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
            params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]
            params[self.category]['duration'] = (
                params[self.category]['end_time'] - params[self.category]['start_time']
            )
        return params


class Sub_Ramp_Down_High_Temp_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='ramp_down_high_temp', **kwargs)
        self.step_id = self.generate_step_id()

    # method to extract the high temperature ramp down parameters (meaning when
    # the substrate temperature is above the temperature where anions tend to
    # escape the film)
    def get_params(self, raw_data=None, source_list=None, params=None):
        if params is None:
            params = {}
        if self.category not in params:
            params[self.category] = {}

        if 's_cracker' not in params[self.category]:
            params[self.category]['s_cracker'] = {}

        if 'deposition' not in params:
            raise ValueError('Missing deposition info, run get_rt_bool first')

        if params['deposition']['rt']:
            return params

        params[self.category]['start_time'] = self.data['Time Stamp'].iloc[0]
        params[self.category]['end_time'] = self.data['Time Stamp'].iloc[-1]

        # start and end temperature of the high temperature ramp down
        params[self.category]['start_temp'] = self.data[
            'Substrate Heater Temperature'
        ].iloc[0]
        params[self.category]['end_temp'] = self.data[
            'Substrate Heater Temperature'
        ].iloc[-1]

        # get the avg capman pressure during the high temperature ramp down
        params[self.category]['avg_capman_pressure'] = self.data[
            'PC Capman Pressure'
        ].mean()
        params[self.category]['duration'] = (
            params[self.category]['end_time'] - params[self.category]['start_time']
        )
        # Extract the start and end temperature of the
        # high temperature ramp down
        params[self.category]['start_setpoint_temp'] = self.data[
            'Substrate Heater Temperature'
        ].iloc[0]
        params[self.category]['end_setpoint_temp'] = self.data[
            'Substrate Heater Temperature'
        ].iloc[-1]
        # slope assuming linear ramp down
        temp_slope = (
            params[self.category]['end_setpoint_temp']
            - params[self.category]['start_setpoint_temp']
        ) / params[self.category]['duration'].total_seconds()
        params[self.category]['temp_slope'] = temp_slope

        # Extract the gases used during the high substrate ramp down
        for gas in ['ar', 'n2', 'o2', 'ph3', 'nh3', 'h2s']:
            mean_flow = self.data[f'PC MFC {GAS_NUMBER[gas]} Flow'].mean()
            if mean_flow > MFC_FLOW_THRESHOLD:
                params[self.category][f'avg_{gas}_flow'] = mean_flow
            else:
                params[self.category][f'avg_{gas}_flow'] = 0

        params[self.category]['anion_input_cutoff_temp'] = self.data[
            'Substrate Heater Temperature Setpoint'
        ].iloc[-1]
        params[self.category]['anion_input_cutoff_time'] = self.data['Time Stamp'].iloc[
            -1
        ]

        # Extract if the cracker has been used during ramp down
        params[self.category]['s_cracker'] = self._get_cracker_params()

        # if 'Sulfur Cracker Zone 1 Current Temperature' in self.data.columns:
        #     if (
        #         (self.data['Sulfur Cracker Control Enabled'] == 1).all()
        #         and (
        #             self.data['Sulfur Cracker Zone 1 Current Temperature']
        #             > CRACKER_ZONE_1_MIN_TEMP
        #         ).all()
        #         and (
        #             self.data['Sulfur Cracker Zone 2 Current Temperature']
        #             > CRACKER_ZONE_2_MIN_TEMP
        #         ).all()
        #         and (
        #             self.data['Sulfur Cracker Zone 3 Current Temperature']
        #             > CRACKER_ZONE_3_MIN_TEMP
        #         ).all()
        #     ):
        #         params[self.category]['s_cracker']['enabled'] = True
        #         # if the crack has been used, extract the cracker parameters
        #         params[self.category]['s_cracker']['zone1_temp'] = self.data[
        #             'Sulfur Cracker Zone 1 Current Temperature'
        #         ].mean()
        #         params[self.category]['s_cracker']['zone2_temp'] = self.data[
        #             'Sulfur Cracker Zone 2 Current Temperature'
        #         ].mean()
        #         params[self.category]['s_cracker']['zone3_temp'] = self.data[
        #             'Sulfur Cracker Zone 3 Current Temperature'
        #         ].mean()
        #         cond_column_feedback = (
        #             'Sulfur Cracker Control Setpoint Feedback' in self.data.columns
        #         ) & (
        #             'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
        #             in self.data.columns
        #         )
        #         if cond_column_feedback:
        #             params[self.category]['s_cracker']['pulse_width'] = self.data[
        #                 'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
        #             ].mean()
        #             params[self.category]['s_cracker']['pulse_freq'] = self.data[
        #                 'Sulfur Cracker Control Setpoint Feedback'
        #             ].mean()
        #     else:
        #         params[self.category]['s_cracker']['enabled'] = False
        # else:
        #     params[self.category]['s_cracker']['enabled'] = False
        # Extract the anion input cutoff temperature as the last temperature of
        # the high temperature ramp down

        return params

    def _get_cracker_params(self):
        cracker_params = {'enabled': False}

        if 'Sulfur Cracker Zone 1 Current Temperature' not in self.data.columns:
            return cracker_params

        enabled = (
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
        )

        if enabled:
            cracker_params['enabled'] = True
            cracker_params['zone1_temp'] = self.data[
                'Sulfur Cracker Zone 1 Current Temperature'
            ].mean()
            cracker_params['zone1_temp_sp'] = self.data[
                'Sulfur Cracker Zone 1 Temperature Setpoint'
            ].mean()
            cracker_params['zone2_temp'] = self.data[
                'Sulfur Cracker Zone 2 Current Temperature'
            ].mean()
            cracker_params['zone3_temp'] = self.data[
                'Sulfur Cracker Zone 3 Current Temperature'
            ].mean()

            if ('Sulfur Cracker Control Setpoint Feedback' in self.data.columns) and (
                'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                in self.data.columns
            ):
                cracker_params['pulse_width'] = self.data[
                    'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback'
                ].mean()
                cracker_params['pulse_freq'] = self.data[
                    'Sulfur Cracker Control Setpoint Feedback'
                ].mean()

        return cracker_params


class Sub_Ramp_Down_Low_Temp_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='ramp_down_low_temp', **kwargs)
        self.step_id = self.generate_step_id()

    # method to extract the low temperature ramp down parameters (meaning when
    # the substrate temperature is below the temperature where anions tend to
    # escape the film)
    def get_params(self, raw_data=None, source_list=None, params=None):
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


class DepRate_Meas_Event(Lf_Event):
    def __init__(self, *args, **kwargs):
        kwargs.pop('category', None)

        super().__init__(*args, category='source_deprate2_film_meas', **kwargs)
        self.step_id = self.generate_step_id()

    # method to extract the film deposition rate parameters
    def get_params(self, raw_data=None, source_list=None, params=None):
        list_allowed_categories = ['source_deprate2_film_meas']
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

        target_name = SOURCE_NAME[str(source_number)]

        if target_name not in params[self.category]:
            params[self.category][target_name] = {}

        params[self.category][target_name]['target_name'] = target_name

        if self.source is not None and self.source != 0:
            source_number = self.source
            source_element = str(
                self.data[f'PC Source {source_number} Material'].iloc[0]
            )
            source_element = re.split(r'\s+', source_element)[0]
            params[self.category][target_name]['target_material'] = ELEMENTS[
                source_element
            ]
        if self.source == 0:
            source_number = 0
            source_element = 'S'
            params[self.category][target_name]['target_material'] = source_element

        params[self.category][target_name]['dep_rate'] = self.data[
            'Thickness Rate'
        ].mean()
        params[self.category][target_name]['dep_rate_ref_mat'] = self.data[
            'Thickness Active Material'
        ].iloc[0]
        if 'Thickness Material Density' in self.data.columns:
            params[self.category][target_name]['dep_rate_ref_density'] = self.data[
                'Thickness Material Density'
            ].mean()
        if 'Thickness Material Z' in self.data.columns:
            params[self.category][target_name]['dep_rate_ref_z'] = self.data[
                'Thickness Material Z'
            ].mean()

        return params


# ---------FUNCTIONS DEFINITION------------

# ---------HELPERS FUNCTIONS FOR REPORT GENERATION------------


def elements_from_string(source_material, elements=[]):
    source_element_name_list = re.split(r'\s+', source_material)
    material = ''
    for element_name in source_element_name_list:
        if element_name in ELEMENTS:
            element = ELEMENTS[element_name]
            material += element
            if element not in elements:
                elements.append(element)
        elif element_name in IONS:
            element = IONS[element_name]
            material += element
            if element not in elements:
                elements.append(element)
    return elements, material


# def get_material_list(source_mat):
#     material_list = []
#     material_stoichiometry = []
#     i = 0
#     if source_mat in ELEMENTS:
#         source_mat = ELEMENTS[source_mat]
#     elif source_mat in IONS:
#         source_mat = IONS[source_mat]
#     while i < len(source_mat):
#         if source_mat[i].isupper():
#             element = source_mat[i]
#             i += 1
#             # Check if the next character is lowercase (for elements like "Si")
#             if i < len(source_mat) and source_mat[i].islower():
#                 element += source_mat[i]
#                 i += 1
#             material_list.append(element)
#             # Read the stoichiometry number
#             stoichiometry = ''
#             while i < len(source_mat) and source_mat[i].isdigit():
#                 stoichiometry += source_mat[i]
#                 i += 1
#             material_stoichiometry.append(int(stoichiometry) if stoichiometry else 1)
#         else:
#             i += 1
#     return material_list, material_stoichiometry


def get_overview(raw_data, params=None):
    if params is None:
        params = {}
    if 'overview' not in params:
        params['overview'] = {}

    # Extract start and end time of the log file
    params['overview']['log_start_time'] = raw_data['Time Stamp'].iloc[0]
    params['overview']['log_end_time'] = raw_data['Time Stamp'].iloc[-1]

    cond_column_feedback = (
        'Sulfur Cracker Control Setpoint Feedback' in raw_data.columns
    ) & (
        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in raw_data.columns
    )

    params['overview']['right_scracker_column'] = cond_column_feedback

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
            'Missing deposition info, run get_simple_deposition_params first'
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


# method to save the derived quantities report as a text file
def save_report_as_text(params: dict, txt_file_path, logfile_name=None):
    # Save the derived quantities report as a text file as
    with open(txt_file_path, 'w') as txt_file:
        if logfile_name is not None:
            txt_file.write(
                f'Derived quantities report for logfile\n{logfile_name}:\n\n'
            )
        txt_file.write(write_params(params))


# method to flatten a nested dictionary
def flatten_dict(d, parent_key='', sep=';'):
    """
    Flatten a nested dictionary.

    Args:
        d (dict): The dictionary to flatten.
        parent_key (str): The base key string for nested keys.
        sep (str): The separator between parent and child keys.

    Returns:
        dict: The flattened dictionary.
    """
    items = []
    for k, v in d.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))

    return dict(items)


def fix_single_dict_level(dict_var, sep='__'):
    # Calculate the max depth of the dict
    max_depth = 0
    for key in dict_var.keys():
        current_depth = len(key.split('__'))
        max_depth = max(current_depth, max_depth)

    new_dict = {}

    # Iterate over the original dictionary to construct the new dictionary
    for key in list(
        dict_var.keys()
    ):  # Make a list to avoid modifying the dict during iteration
        if len(key.split('__')) == max_depth - 1:
            key_split = key.split('__')
            key_split[1] = f'{key_split[1]}{sep}general'
            new_key = '__'.join(key_split)
            new_dict[new_key] = dict_var[key]
            del dict_var[key]  # Safely remove the key from the original dict

    # Merge new keys into the original dictionary
    dict_var.update(new_dict)

    return dict_var


def consolidate_data_to_csv(all_params, samples_dir, sep='__', process_NaN=False):
    # Flatten the dictionary with the specified separator
    flatten_all_params = flatten_dict(all_params, sep=sep)

    # fix the level of the dict
    flatten_all_params = fix_single_dict_level(flatten_all_params)

    # Convert the flattened dictionary to a DataFrame
    df = pd.DataFrame([flatten_all_params])

    # Split the column names using the separator and ensure consistent levels
    split_columns = [tuple(col.split(sep)) for col in df.columns]

    # Set the standardized MultiIndex for the DataFrame columns
    df.columns = pd.MultiIndex.from_tuples(split_columns)

    # Fill NaN values in the MultiIndex headers
    if process_NaN:
        df.columns = pd.MultiIndex.from_tuples(
            [tuple('' if pd.isna(x) else x for x in col) for col in df.columns]
        )

    # Save the DataFrame to a CSV file
    output_path = os.path.join(samples_dir, 'all_params.csv')
    df.to_csv(output_path, index=False, na_rep='')

    print(f'Data successfully saved to {output_path}')


def open_csv_as_multiindex(csv_path, replace_nan=False):
    """
    Reopen a CSV file as a MultiIndex DataFrame.

    Args:
        csv_path (str): The path to the CSV file.

    Returns:
        pd.DataFrame: The MultiIndex DataFrame.
    """
    # Read the CSV file with the appropriate header levels
    df = pd.read_csv(csv_path, header=[0, 1, 2, 3], na_filter=False)

    # The columns are already MultiIndex, so no need to split them again
    df.columns = pd.MultiIndex.from_tuples(df.columns)

    # set the index names to ['sample','event','source','parameter']
    df.columns.names = ['sample', 'event', 'source', 'parameter']

    if replace_nan:
        # Replace the string 'nan' with an empty string in MultiIndex column names
        df.columns = df.columns.set_levels(
            [level.str.replace('nan', '') for level in df.columns.levels]
        )

    return df


# method to get a parameter from a MultiIndex DataFrame
# path being a list of strings pointing to the parameter
def get_df_param(df, path: list):
    for key in path:
        df = df.xs(key, axis=1, level=1)
    # set the data row index to path[-1]
    df.index = pd.Index(df.index, name=path[-1])
    return df


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
            elif isinstance(value, pd.Series):
                formatted_value = 'Cannot display pd.DataFrame'
            print(f'{indent}{key}: {formatted_value}')


def build_file_paths(logfiles, i):
    file_dir = os.path.join(logfiles['folder'][i])

    # Specify the main report export location and file name
    txt_file_name = f'{logfiles["name"][i]}_derived_quantities.txt'
    txt_file_path = os.path.join(file_dir, txt_file_name)

    # Specify the step report export location and file name
    step_file_name = f'{logfiles["name"][i]}_derived_quantities_step.txt'
    step_file_path = os.path.join(file_dir, step_file_name)

    # Specify the plotly graph export location and file name for timelines
    timeline_file_name = f'{logfiles["name"][i]}_plotly_timeline.html'
    timeline_file_path = os.path.join(file_dir, timeline_file_name)

    # Specify the plotly graph export location and file name for bias/power plots
    bias_file_name = f'{logfiles["name"][i]}_plotly_bias.html'
    bias_file_path = os.path.join(file_dir, bias_file_name)

    # Specify the plotly graph export location and file name
    # for the overview plot
    overview_file_name = f'{logfiles["name"][i]}_plotly_overview.html'
    overview_file_path = os.path.join(file_dir, overview_file_name)

    # specify the optix cascade plot export location and file name
    optix_cascade_file_name = f'{logfiles["name"][i]}_optix_cascade.html'
    optix_file_path = os.path.join(file_dir, optix_cascade_file_name)

    # Specify the chamber config plot export location and file name
    chamber_config_file_name = f'{logfiles["name"][i]}_chamber_config.png'
    chamber_config_file_path = os.path.join(file_dir, chamber_config_file_name)

    return (
        txt_file_path,
        step_file_path,
        timeline_file_path,
        bias_file_path,
        overview_file_path,
        optix_file_path,
        chamber_config_file_path,
    )


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
            elif isinstance(value, pd.Series):
                formatted_value = '[...](pd.DataFrame)'
            elif isinstance(value, list):
                formatted_value = '[...](list)'
            output.append(f'{indent}{key}: {formatted_value}')
    return '\n'.join(output)


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
    # if temp_1 is a pint quantity, convert it to a float
    return 0.905 * (0.5 * (temp_1 + temp_2)) + 12


# Helper function to check if a column is within a certain range
def within_range(data_col, ref_col_mean, diff_param, mode='percent'):
    if ref_col_mean == 0:
        cond = (data_col > (-MFC_FLOW_THRESHOLD)) & (data_col < (+MFC_FLOW_THRESHOLD))
    elif mode == 'percent':
        cond = (data_col > (1 - 0.01 * diff_param) * ref_col_mean) & (
            data_col < (1 + 0.01 * diff_param) * ref_col_mean
        )
    elif mode == 'absolute':
        cond = (data_col > (ref_col_mean - diff_param)) & (
            data_col < (ref_col_mean + diff_param)
        )
    return cond


def format_time_stamp(time, ref_object=None, timestamp_col='Time Stamp'):
    len_hh_mm = 2
    len_hh_mm_ss = 3

    if not isinstance(time, pd.Timestamp):
        # Check if the input string contains only the time part
        if isinstance(time, str):
            parts = time.split(':')
            if len(parts) == len_hh_mm:  # If format is HH:MM, assume seconds as :00
                time += ':00'
            elif len(parts) == 1 or len(parts) > len_hh_mm_ss:
                raise ValueError(
                    f"Invalid time format: {time}. Exp. 'HH:MM' or 'HH:MM:SS'."
                )

            if ref_object is not None:
                if isinstance(ref_object, pd.DataFrame):
                    # Handle case where df is empty to avoid IndexError
                    if ref_object.empty:
                        raise ValueError(
                            'DataFrame is empty, cannot infer date for time conversion.'
                        )

                        # Assume the date of the first row of df[timestamp_col]
                        # if only time is provided
                    if len(time.split()) == 1:
                        first_date = pd.to_datetime(
                            ref_object[timestamp_col].iloc[0]
                        ).strftime('%Y-%m-%d')
                        time = f'{first_date} {time}'
                elif isinstance(ref_object, dict):
                    # Assume the date of the first key of the dictionary
                    # if only time is provided
                    if len(time.split()) == 1:
                        first_key = list(ref_object['timestamp_map'].keys())[0]
                        first_date = pd.to_datetime(
                            ref_object['timestamp_map'][first_key]
                        ).strftime('%Y-%m-%d')
                        time = f'{first_date} {time}'
        try:
            # Create the Timestamp
            timestamp = pd.to_datetime(time, format='%Y-%m-%d %H:%M:%S')
        except Exception as e:
            raise ValueError(f'Invalid timestamp format: {time}. Error: {e}')
    else:
        timestamp = time

    return timestamp


# Helper function to check if a column is within a time range
def within_time_range(df, start_time, end_time, timestamp_col='Time Stamp'):
    # Check if the dataframe has the specified column
    if timestamp_col not in df.columns:
        raise ValueError(f"'{timestamp_col}' column not found in DataFrame.")

    # Ensure the timestamp column is in datetime format
    if not pd.api.types.is_datetime64_any_dtype(df[timestamp_col]):
        df[timestamp_col] = pd.to_datetime(df[timestamp_col])

    # Format start_time and end_time
    start_time = format_time_stamp(start_time, ref_object=df)
    end_time = format_time_stamp(end_time, ref_object=df)

    # Ensure both timestamps and DataFrame column are timezone-naive
    if start_time.tzinfo is not None:
        start_time = start_time.tz_convert(None)
    if end_time.tzinfo is not None:
        end_time = end_time.tz_convert(None)
    if pd.api.types.is_datetime64tz_dtype(df[timestamp_col]):
        df[timestamp_col] = df[timestamp_col].dt.tz_convert(None)

    # Return the boolean mask for rows within the time range
    time_cond = (df[timestamp_col] >= start_time) & (df[timestamp_col] <= end_time)
    return time_cond


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
def connect_source_to_power_supply(data: pd.DataFrame, source_list):
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
def rename_cracker_columns(data, rename_cracker_col=False):
    cond_column = ('Sulfur Cracker Control Setpoint' in data.columns) & (
        'Sulfur Cracker Control Valve PulseWidth Setpoint' in data.columns
    )
    cond_column_feedback = (
        'Sulfur Cracker Control Setpoint Feedback' in data.columns
    ) & ('Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in data.columns)

    if rename_cracker_col:
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
    # print('Defining the conditions and filtering the data')
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
        power_fwd_rfl_cond = (
            data.get(f'Source {source_number} Fwd Power', pd.Series([0] * len(data)))
            - data.get(f'Source {source_number} Rfl Power', pd.Series([0] * len(data)))
        ) > POWER_FWD_RFL_THRESHOLD

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
            (current_cond | dc_bias_cond) | power_fwd_rfl_cond
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
        source_ramp_up[str(source_number)] = Source_Ramp_Up_Event(
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
    nh3 = Lf_Event('NH3 On', category='nh3_on')
    h2s = Lf_Event('H2S On', category='h2s_on')
    ar = Lf_Event('Ar On', category='ar_on')
    n2 = Lf_Event('N2 On', category='n2_on')
    o2 = Lf_Event('O2 On', category='o2_on')

    ph3_cond = (data['PC MFC 4 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 4 Flow'] > MFC_FLOW_THRESHOLD
    )
    ph3.set_condition(ph3_cond)
    ph3.filter_data(data)

    nh3_cond = (data['PC MFC 5 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 5 Flow'] > MFC_FLOW_THRESHOLD
    )
    nh3.set_condition(nh3_cond)
    nh3.filter_data(data)

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

    n2_cond = (data['PC MFC 2 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 2 Flow'] > MFC_FLOW_THRESHOLD
    )
    n2.set_condition(n2_cond)
    n2.filter_data(data)

    o2_cond = (data['PC MFC 3 Setpoint'] > MFC_FLOW_THRESHOLD) & (
        data['PC MFC 3 Flow'] > MFC_FLOW_THRESHOLD
    )
    o2.set_condition(o2_cond)
    o2.filter_data(data)

    return ph3, nh3, h2s, ar, n2, o2


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
    # We create a deposition event that is not tied to any source in particular
    deposition = Deposition_Event('Deposition', category='deposition', source=None)

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
        'nh3',
        'h2s',
        'n2',
        'o2',
        'deposition',
    ]

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    source_on = kwargs.get('source_on')
    source_ramp_up = kwargs.get('source_ramp_up')
    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    nh3 = kwargs.get('nh3')
    h2s = kwargs.get('h2s')
    n2 = kwargs.get('n2')
    o2 = kwargs.get('o2')

    deposition = kwargs.get('deposition')

    source_presput = {}

    for source_number in source_list:
        if not source_on[str(source_number)].data.empty:
            try:
                source_presput_cond = (
                    source_on[str(source_number)].cond
                    & (data['Time Stamp'] < deposition.bounds[0][0])
                    & (
                        data['Time Stamp']
                        > (
                            source_ramp_up[str(source_number)]
                            .data['Time Stamp']
                            .iloc[-1]
                        )
                    )
                    & ~source_ramp_up[str(source_number)].cond
                    & ~(
                        ph3.cond
                        | nh3.cond
                        | h2s.cond
                        | n2.cond
                        | o2.cond
                        | cracker_on_open.cond
                    )
                )
            except IndexError:
                print(
                    'The time constraint on the presputtering',
                    'has been partially relaxed',
                    'presput may be located after the last source ramp up',
                )
                try:
                    source_presput_cond = (
                        source_on[str(source_number)].cond
                        & (data['Time Stamp'] < deposition.bounds[0][0])
                        & ~source_ramp_up[str(source_number)].cond
                        & ~(
                            ph3.cond
                            | nh3.cond
                            | h2s.cond
                            | n2.cond
                            | o2.cond
                            | cracker_on_open.cond
                        )
                    )
                except IndexError:
                    print(
                        'The time constraint on the presputtering was fully relaxed',
                        'presput may be located after the deposition',
                    )
                    source_presput_cond = (
                        source_on[str(source_number)].cond
                        & ~source_ramp_up[str(source_number)].cond
                        & ~(
                            ph3.cond
                            | nh3.cond
                            | h2s.cond
                            | n2.cond
                            | o2.cond
                            | cracker_on_open.cond
                        )
                    )

            source_presput[str(source_number)] = Source_Presput_Event(
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
    required_keys = [
        'cracker_on_open',
        'ph3',
        'nh3',
        'h2s',
        'ar',
        'n2',
        'o2',
        'deposition',
    ]

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    nh3 = kwargs.get('nh3')
    h2s = kwargs.get('h2s')
    ar = kwargs.get('ar')
    n2 = kwargs.get('n2')
    o2 = kwargs.get('o2')

    deposition = kwargs.get('deposition')

    cracker_base_pressure = SCracker_Pressure_Event(
        'Cracker Pressure Meas', category='cracker_base_pressure', source=0
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

        cond_column_feedback = (
            'Sulfur Cracker Control Setpoint Feedback' in data.columns
        ) & (
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in data.columns
        )

        if cond_column_feedback:
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
        else:
            # If the cracker columns are not present, we effectively ignore them
            valve_cond = pd.Series(True, index=data.index)

        if not cracker_on_open.data.empty:
            cracker_base_pressure_cond = (
                cracker_on_open.cond
                & (data['Time Stamp'] < deposition.bounds[0][0])
                & ~h2s.cond
                & ~nh3.cond
                & ~ph3.cond
                & ~ar.cond
                & ~n2.cond
                & ~o2.cond
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
        'nh3',
        'h2s',
        'n2',
        'o2',
    ]

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    deposition = kwargs.get('deposition')
    source_on_open = kwargs.get('source_on_open')
    any_source_on_open = kwargs.get('any_source_on_open')
    cracker_on_open = kwargs.get('cracker_on_open')
    ph3 = kwargs.get('ph3')
    nh3 = kwargs.get('nh3')
    h2s = kwargs.get('h2s')
    n2 = kwargs.get('n2')
    o2 = kwargs.get('o2')

    xtal2_open = Lf_Event('Xtal 2 Shutter Open', category='xtal2_shutter_open')
    deprate2_meas = Lf_Event('Deposition Rate Measurement', category='deprate2_meas')
    deprate2_film_meas = {}
    deprate2_sulfur_meas = DepRate_Meas_Event(
        'S Dep Rate Meas', category='source_deprate2_film_meas', source=0
    )

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

    (
        pressure_cond,
        ph3_dep_cond,
        nh3_dep_cond,
        h2s_dep_cond,
        n2_dep_cond,
        o2_dep_cond,
        cracker_dep_cond,
    ) = define_deposition_conditions(data, deposition)

    deprate2_film_meas, deprate2_ternary_meas = define_film_meas_conditions(
        data,
        source_list,
        deprate2_meas=deprate2_meas,
        source_on_open=source_on_open,
        cracker_dep_cond=cracker_dep_cond,
        h2s_dep_cond=h2s_dep_cond,
        nh3_dep_cond=nh3_dep_cond,
        ph3_dep_cond=ph3_dep_cond,
        n2_dep_cond=n2_dep_cond,
        o2_dep_cond=o2_dep_cond,
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
        nh3=nh3,
        h2s=h2s,
        n2=n2,
        o2=o2,
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

    nh3_dep_cond = within_range(
        data['PC MFC 5 Setpoint'],
        deposition.data['PC MFC 5 Setpoint'].mean(),
        WITHIN_RANGE_PARAM,
    )

    h2s_dep_cond = within_range(
        data['PC MFC 6 Setpoint'],
        deposition.data['PC MFC 6 Setpoint'].mean(),
        WITHIN_RANGE_PARAM,
    )

    n2_dep_cond = within_range(
        data['PC MFC 2 Setpoint'],
        deposition.data['PC MFC 2 Setpoint'].mean(),
        WITHIN_RANGE_PARAM,
    )

    o2_dep_cond = within_range(
        data['PC MFC 3 Setpoint'],
        deposition.data['PC MFC 3 Setpoint'].mean(),
        WITHIN_RANGE_PARAM,
    )

    cond_column_feedback = (
        'Sulfur Cracker Control Setpoint Feedback' in data.columns
    ) & ('Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in data.columns)

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
        )
        if cond_column_feedback:
            # If the cracker columns are present, we use them to add
            # the condition
            cracker_dep_cond = (
                cracker_dep_cond
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
    return (
        pressure_cond,
        ph3_dep_cond,
        nh3_dep_cond,
        h2s_dep_cond,
        n2_dep_cond,
        o2_dep_cond,
        cracker_dep_cond,
    )


def define_film_meas_conditions(data, source_list, **kwargs):
    deprate2_meas = kwargs.get('deprate2_meas')
    source_on_open = kwargs.get('source_on_open')
    cracker_dep_cond = kwargs.get('cracker_dep_cond')
    h2s_dep_cond = kwargs.get('h2s_dep_cond')
    nh3_dep_cond = kwargs.get('nh3_dep_cond')
    ph3_dep_cond = kwargs.get('ph3_dep_cond')
    n2_dep_cond = kwargs.get('n2_dep_cond')
    o2_dep_cond = kwargs.get('o2_dep_cond')
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
                & nh3_dep_cond
                & ph3_dep_cond
                & n2_dep_cond
                & o2_dep_cond
                & (data['Thickness Active Material'] != 'Sulfur')
                & power_cond
                & pressure_cond
            )
            deprate2_film_meas_cond_list.append(deprate2_film_meas_cond)

            deprate2_film_meas[str(source_number)] = DepRate_Meas_Event(
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
    if deprate2_film_meas_cond_list:
        deprate2_ternary_meas_cond = reduce(operator.and_, deprate2_film_meas_cond_list)
    else:
        deprate2_ternary_meas_cond = pd.Series(False, index=data.index)

    deprate2_ternary_meas = DepRate_Meas_Event(
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
    nh3 = kwargs.get('nh3')
    h2s = kwargs.get('h2s')
    n2 = kwargs.get('n2')
    o2 = kwargs.get('o2')

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
        cond_column_feedback = (
            'Sulfur Cracker Control Setpoint Feedback' in data.columns
        ) & (
            'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in data.columns
        )

        if cond_column_feedback:
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
        else:
            # If the cracker columns are not present, we effectively ignore them
            valve_cond = pd.Series(True, index=data.index)

        pressure_cond = within_range(
            data['PC Capman Pressure'],
            deposition.data['PC Capman Pressure'].mean(),
            WITHIN_RANGE_PARAM,
        )

        deprate2_sulfur_meas_cond = (
            deprate2_meas.cond
            & ~any_source_on_open.cond
            & cracker_on_open.cond
            & ~(ph3.cond | nh3.cond | h2s.cond | n2.cond | o2.cond)
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
    required_keys = [
        'cracker_on_open',
        'temp_ctrl',
        'ph3',
        'nh3',
        'h2s',
        'n2',
        'o2',
        'deposition',
    ]

    for key in required_keys:
        if key not in kwargs:
            raise ValueError(f'Missing required argument: {key}')

    cracker_on_open = kwargs.get('cracker_on_open')
    temp_ctrl = kwargs.get('temp_ctrl')
    ph3 = kwargs.get('ph3')
    nh3 = kwargs.get('nh3')
    h2s = kwargs.get('h2s')
    n2 = kwargs.get('n2')
    o2 = kwargs.get('o2')
    deposition = kwargs.get('deposition')

    ramp_up_temp = Sub_Ramp_Up_Event('Sub Temp Ramp Up', category='ramp_up_temp')
    ramp_down_temp = Sub_Ramp_Down_Event(
        'Sub Temp Ramp Down', category='ramp_down_temp'
    )
    ramp_down_high_temp = Sub_Ramp_Down_High_Temp_Event(
        'Sub High Temp Ramp Down', category='ramp_down_high_temp'
    )
    ramp_down_low_temp = Sub_Ramp_Down_Low_Temp_Event(
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
        try:
            ramp_down_high_temp_cond = (
                data['Time Stamp'] > ramp_down_temp.data['Time Stamp'].iloc[0]
            ) & (
                h2s.cond
                | nh3.cond
                | ph3.cond
                | n2.cond
                | o2.cond
                | cracker_on_open.cond
            )
        except Exception:
            ramp_down_high_temp_cond = pd.Series(False, index=data.index)
        ramp_down_high_temp.set_condition(ramp_down_high_temp_cond)
        ramp_down_high_temp.filter_data(data)
        ramp_down_high_temp.filter_out_small_events(MIN_TEMP_RAMP_DOWN_SIZE)

        # Define the ramp down low temperature condition as a events after
        # the beginning of the ramp down of the temperature ramp down
        # where we do not flow H2S, PH3 or the cracker is off
        try:
            ramp_down_low_temp_cond = (
                data['Time Stamp'] > ramp_down_temp.data['Time Stamp'].iloc[0]
            ) & ~(
                h2s.cond
                | nh3.cond
                | ph3.cond
                | n2.cond
                | o2.cond
                | cracker_on_open.cond
            )
        except Exception:
            ramp_down_low_temp_cond = pd.Series(False, index=data.index)
        ramp_down_low_temp.set_condition(ramp_down_low_temp_cond)
        ramp_down_low_temp.filter_data(data)

    return ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp


def filter_data_platen_bias_on(data):
    platen_bias_on = Lf_Event('Platen Bias On', category='platen_bias_on')
    if 'Power Supply 7 Enabled' in data.columns:
        platen_bias_on_cond = (data['Power Supply 7 Enabled'] == 1) & (
            data['Power Supply 7 DC Bias'] > BIAS_THRESHOLD
        )
    else:
        platen_bias_on_cond = pd.Series(False, index=data.index)
    platen_bias_on.set_condition(platen_bias_on_cond)
    platen_bias_on.filter_data(data)

    return platen_bias_on


# -------PLOTTING DEFINITIONS------------


def generate_optix_cascade_plot(spectra, **kwargs):
    """
    Generate a 3D cascade plot with optional coloring based on
    experimental data.

    Parameters:
    - spectra (dict): Contains 'data' (DataFrame with x and
         intensity columns) and 'timestamp_map' (dict of timestamps).
    - kwargs (dict): Additional keyword arguments:
      - 'color_df': DataFrame with a 'Timestamp' column and data columns
            for custom coloring.
      - 'color_column': Name of the column in color_df to use for coloring.
      - 'time_col': The column name representing time in color_df.
      - 'wv_range': The wavelength range for filtering the data (e.g., (200, 800)).
      - 'time_range': Time range for filtering the data (optional).
      - 'color_scale': The color scale to use for the plot (e.g., 'Jet').

    Returns:
    - plotly.graph_objects.Figure: The resulting 3D cascade plot.
    """

    # Extract values from kwargs with defaults
    color_df = kwargs.get('color_df', None)
    color_column = kwargs.get('color_column', None)
    time_col = kwargs.get('time_col', 'Time Stamp')
    color_scale = kwargs.get('color_scale', 'Jet')
    wv_range = kwargs.get('wv_range', (200, 800))
    time_range = kwargs.get('time_range', None)
    plot_title = kwargs.get('plot_title', '3D Cascade Plot')

    # initialize variables
    min_color = None
    max_color = None

    # filter the data based on the time range
    if time_range is not None:
        spectra = filter_spectrum(spectra.copy(), time_range)

    # Extract the x-axis and intensity columns
    data = spectra['data']
    timestamp_map = spectra['timestamp_map']

    x_values = data['x']

    # Convert timestamps to numeric elapsed time
    timestamps = list(timestamp_map.values())
    base_time = min(timestamps)
    time_offsets = {
        col: (timestamp - base_time).total_seconds()
        for col, timestamp in timestamp_map.items()
    }

    # Initialize color mapping
    cols = [col for col in data.columns if col != 'x']
    colors = []

    # Process color_df for custom coloring if provided
    if color_df is not None and color_column is not None:
        # Ensure the color_df has a 'Timestamp' column
        if time_col not in color_df.columns:
            raise ValueError(f'color_df must contain a {time_col} column.')

        # Set 'Time Stamp' as the index if not already
        if not np.issubdtype(color_df[time_col].dtype, np.datetime64):
            raise ValueError(
                f'The {time_col} column in color_df must be of datetime type.'
            )

        if color_df.index.name != time_col:
            color_df = color_df.set_index(time_col)

        # Ensure the selected column exists
        if color_column not in color_df.columns:
            raise ValueError(f"Column '{color_column}' not found in color_df.")

        # --- Ensure tz-naive for all timestamps ---
        color_df.index = color_df.index.tz_localize(None)
        # Match timestamps in timestamp_map to the closest time in color_df
        for col in cols:
            spectrum_time = timestamp_map[col]
            closest_idx = np.abs((color_df.index - spectrum_time).to_numpy()).argmin()
            color_value = color_df.iloc[closest_idx][color_column]
            colors.append(color_value)

        # Normalize the values for the colormap
        min_color = min(colors)
        max_color = max(colors)
        normalized_colors = [
            (value - min_color) / (max_color - min_color) for value in colors
        ]
        colors = sample_colorscale(color_scale, normalized_colors)
    elif color_scale is None or color_scale == 'None':
        # Default to a single blue color for all lines if no color scale is provided
        colors = ['#1f77b4'] * len(cols)  # All lines default to blue
    else:
        # Default to time-based coloring
        max_offset = max(time_offsets.values())
        min_offset = min(time_offsets.values())
        colors = sample_colorscale(
            color_scale,
            [
                (time_offsets[col] - min_offset) / (max_offset - min_offset)
                for col in cols
            ],
        )

    # Filter the data based on the provided wavelength range (if applicable)
    if wv_range is not None:
        data_wv_filtered = data[(data['x'] >= wv_range[0]) & (data['x'] <= wv_range[1])]

        # Calculate the min/max intensity based on the filtered wavelength data
        cols = [col for col in data_wv_filtered.columns if col != 'x']
        min_intensity = data_wv_filtered[cols].min().min()  # Min intensity
        max_intensity = data_wv_filtered[cols].max().max()  # Max intensity

    fig = create_3d_plot(
        cols=cols,
        colors=colors,
        x_values=x_values,
        data=data,
        time_offsets=time_offsets,
        timestamp_map=timestamp_map,
        color_df=color_df,
        color_column=color_column,
        min_color=min_color,
        max_color=max_color,
        color_scale=color_scale,
        wv_range=wv_range,
        min_intensity=min_intensity,
        max_intensity=max_intensity,
        plot_title=plot_title,
    )

    return fig


def create_3d_plot(**kwargs):
    # Extract values from kwargs with defaults
    cols = kwargs.get('cols', None)
    colors = kwargs.get('colors', None)
    x_values = kwargs.get('x_values', None)
    data = kwargs.get('data', None)
    time_offsets = kwargs.get('time_offsets', None)
    timestamp_map = kwargs.get('timestamp_map', None)
    color_df = kwargs.get('color_df', None)
    color_column = kwargs.get('color_column', None)
    min_color = kwargs.get('min_color', None)
    max_color = kwargs.get('max_color', None)
    color_scale = kwargs.get('color_scale', None)
    wv_range = kwargs.get('wv_range', None)
    min_intensity = kwargs.get('min_intensity', None)
    max_intensity = kwargs.get('max_intensity', None)
    plot_title = kwargs.get('plot_title', None)

    # Create the 3D plot
    fig = go.Figure()

    for col, color in zip(cols, colors):
        x_axis_values = x_values  # Left-right direction
        z_axis_values = data[col]  # Intensity towards the top
        y_axis_values = [time_offsets[col]] * len(x_axis_values)
        timestamp = timestamp_map[col]

        fig.add_trace(
            go.Scatter3d(
                x=x_axis_values,  # Left-right direction
                y=y_axis_values,  # Depth direction (numeric time)
                z=z_axis_values,  # Intensity towards the top
                mode='lines',
                name=f'Trace {col}',
                line=dict(color=color),
                hovertemplate=(
                    f'X: %{{x}}<br>'
                    f'Intensity: %{{z}}<br>'
                    f'Time: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}<extra></extra>'
                ),
            )
        )

    # Add a dummy scatter trace for the color bar
    if color_df is not None and color_column is not None:
        fig.add_trace(
            go.Scatter3d(
                x=[None],
                y=[None],
                z=[None],  # Dummy data
                mode='markers',
                marker=dict(
                    size=0,  # Invisible markers
                    color=np.linspace(min_color, max_color, 100),  # Range of values
                    colorscale=color_scale,  # Use the same colorscale
                    colorbar=dict(
                        title=color_column,  # Color bar title
                        titleside='right',
                        tickvals=np.linspace(min_color, max_color, 5),
                        tickformat='.2e',
                    ),
                ),
                hoverinfo='none',
            )
        )

    fig.update_layout(
        title=plot_title,
        scene=dict(
            xaxis=dict(
                title='Wavelength (nm)',
                range=[wv_range[0], wv_range[1]],  # You can adjust the range here
                showspikes=True,
                showticklabels=True,
            ),
            yaxis=dict(
                title='Time (s)',
                range=[min(time_offsets.values()), max(time_offsets.values())],
                showspikes=True,
                showticklabels=True,
            ),
            zaxis=dict(
                title='Intensity',
                range=[min_intensity, max_intensity],  # Set the range of intensity
                showspikes=True,
                showticklabels=True,
            ),
        ),
        showlegend=False,  # Hide legend
        # margin=dict(l=0, r=0, t=0, b=0),  # Remove margins
    )

    # make it larger in the  wavelegnth direction
    fig.update_layout(scene=dict(aspectmode='manual', aspectratio=dict(x=2, y=1, z=1)))

    return fig


def plot_logfile_chamber(main_params, logfile_name=''):
    # Reading guns
    guns = []
    for gun_param in ['taurus', 'magkeeper3', 'magkeeper4', 's_cracker']:
        if (
            gun_param in main_params['deposition']
            and (main_params['deposition'][gun_param]['enabled'])
        ):
            if 'target_material' in main_params['deposition'][gun_param]:
                material = main_params['deposition'][gun_param]['target_material']
            elif gun_param == 's_cracker':
                material = 'S'
            gun = Gun(gun_param, material)
            guns.append(gun)

    # Assuming dummy samples for now
    samples = [
        Sample('BR', [20, 35], 0, [40, 40]),
        Sample('BL', [-20, 35], 0, [40, 40]),
        Sample('FR', [20, -5], 0, [40, 40]),
        Sample('FL', [-20, -5], 0, [40, 40]),
        Sample('G', [0, -38], 90, [26, 76]),
    ]

    platen_rot = main_params['deposition']['platen_position']

    # Plotting
    plotly_fig = plot_plotly_chamber_config(
        samples,
        guns,
        platen_rot,
        plot_title='DEPOSITION CONFIG :',
    )

    plotly_fig_mounting_angle = plot_plotly_chamber_config(
        samples,
        guns,
        90,
        in_chamber=False,
        plot_title='MOUNTING CONFIG :',
    )

    # Return bot Plotly figures
    return plotly_fig, plotly_fig_mounting_angle


def quick_plot(df, Y, **kwargs):
    """
    Quick plot function to plot the data in the dataframe.

    Args:
        df (pd.DataFrame): The dataframe containing the data to plot.
        Y (list or str): The column name(s) for the y-axis.
        **kwargs: Additional keyword arguments for plot customization:
            - X (str): Column name for the x-axis. Default is 'Time Stamp'.
            - mode (str): Plotting mode, either 'default', 'stack', or 'dual_y'.
                Default is 'default'.
            - plot_type (str): Type of plot, either 'line' or 'scatter'.
                Default is 'scatter'.
            - Y2 (list or str): Column name(s) for the right y-axis (Y2).
                Default is an empty list.
            - width (int): Width of the plot. Default is WIDTH.
            - height (int): Height of the plot. Default is HEIGHT.
            - plot_title (str): Title of the plot. Default is 'Quick Plot'.

    Returns:
        plotly.graph_objects.Figure: The Plotly figure object.
    """
    if isinstance(Y, str):
        Y = [Y]

    plot_params = setup_plot_params(df, Y, **kwargs)
    mode = plot_params['mode']

    Y2 = kwargs.get('Y2', None)
    if Y2 is not None:
        mode = 'dual_y'

    if mode == 'default':
        fig = create_default_plot(plot_params)
    elif mode == 'stack':
        fig, num_plot = create_stack_plot(plot_params)
    elif mode == 'dual_y':
        fig = create_dual_y_plot(plot_params)

    # Update layout for better visualization
    fig.update_layout(template='plotly_white')
    fig.update_layout(
        legend=dict(
            bgcolor='rgba(0,0,0,0)',  # Transparent legend background
        )
    )

    # Add vertical lines to separate the plots
    if mode == 'stack':
        add_vertical_lines(fig, num_plot)
    else:
        fig.update_layout(
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
            ]
        )

    return fig


def get_axis_title(column, default_title='Values'):
    """
    Helper function to get the axis title from DICT_RENAME
    or use the column name.

    Args:
        column (str): The column name.
        default_title (str): The default title to use if the column
        name is not found in DICT_RENAME.

    Returns:
        str: The axis title.
    """
    return DICT_RENAME.get(column, column) if isinstance(column, str) else default_title


def setup_plot_params(df, Y, **kwargs):
    """
    Helper function to setup plot parameters.

    Args:
        df (pd.DataFrame): The dataframe containing the data to plot.
        Y (list or str): The column name(s) for the y-axis.
        **kwargs: Additional keyword arguments for plot customization:
            - X (str): Column name for the x-axis. Default is 'Time Stamp'.
            - mode (str): Plotting mode, either 'default', 'stack',
                or 'dual_y'. Default is 'default'.
            - plot_type (str): Type of plot, either 'line' or 'scatter'.
                Default is 'scatter'.
            - Y2 (list or str): Column name(s) for the right y-axis (Y2).
                Default is an empty list.
            - width (int): Width of the plot. Default is WIDTH.
            - height (int): Height of the plot. Default is HEIGHT.
            - plot_title (str): Title of the plot. Default is 'Quick Plot'.

    Returns:
        dict: A dictionary containing the plot parameters.
    """
    X = kwargs.get('X', 'Time Stamp')
    mode = kwargs.get('mode', 'default')
    plot_type = kwargs.get('plot_type', 'scatter')
    Y2 = kwargs.get('Y2', [])
    width = kwargs.get('width', WIDTH)
    height = kwargs.get('height', HEIGHT)
    plot_title = kwargs.get('plot_title', 'Quick Plot')
    df_names = kwargs.get('df_names', None)

    # Ensure Y and Y2 are lists
    if isinstance(Y, str):
        Y = [Y]
    if isinstance(Y2, str):
        Y2 = [Y2]

    if isinstance(df, list):
        if df_names is None:
            raise ValueError(
                'df_names must be provided when df is a list of dataframes'
            )

        # checkk if the first column of each dataframe is the same
        if not all(df[0].columns[0] == df_i.columns[0] for df_i in df):
            raise ValueError('The first column of each dataframe must be the same')

        # If the data is a list of dataframes,
        # we first rename the columns to avoid conflicts
        renamed_dfs = []
        for i, df_i in enumerate(df):
            # Create a copy to avoid modifying the original
            df_copy = df_i.copy()
            df_copy.columns = [
                f'{df_names[i]}_{col}' if col != X else col for col in df_copy.columns
            ]
            renamed_dfs.append(df_copy)

        # Concatenate them into a single dataframe
        df_cont = pd.concat(
            [df_i.set_index(df_i.columns[0]) for df_i in renamed_dfs], axis=1
        ).reset_index()

        # Create new lists of X, Y, and Y2 columns with the new column names
        Y_return = [f'{df_names[i]}_{col}' for i in range(len(df)) for col in Y]
        Y2_return = [f'{df_names[i]}_{col}' for i in range(len(df)) for col in Y2]

        df_return = df_cont
    else:
        df_return = df
        Y_return = Y
        Y2_return = Y2

    y_axis_title = get_axis_title(Y[0]) if len(Y) == 1 else 'Values'
    y2_axis_title = get_axis_title(Y2[0]) if len(Y2) == 1 else 'Values'

    return {
        'df': df_return,
        'X': X,
        'Y': Y_return,
        'Y2': Y2_return,
        'plot_type': plot_type,
        'plot_title': plot_title,
        'y_axis_title': y_axis_title,
        'y2_axis_title': y2_axis_title,
        'width': width,
        'height': height,
        'mode': mode,
    }


def add_vertical_lines(fig, num_plot):
    """
    Helper function to add vertical lines to separate the plots.

    Args:
        fig (plotly.graph_objects.Figure): The Plotly figure object.
        num_plot (int): The number of plots.

    Returns:
        None
    """
    shapes = [
        dict(
            type='rect',
            x0=0,
            x1=1,
            y0=i * (1 / num_plot),
            y1=(i + 1) * (1 / num_plot),
            xref='paper',
            yref='paper',
            line=dict(color='black', width=1),
        )
        for i in range(num_plot)
    ]
    fig.update_layout(shapes=shapes)


def create_default_plot(plot_params):
    """
    Create a default plot.

    Args:
        df (pd.DataFrame): The dataframe containing the data to plot.
        plot_params (dict): A dictionary containing the plot parameters.

    Returns:
        plotly.graph_objects.Figure: The Plotly figure object.
    """
    df = plot_params['df']
    X = plot_params['X']
    Y = plot_params['Y']
    plot_type = plot_params['plot_type']
    plot_title = plot_params['plot_title']
    y_axis_title = plot_params['y_axis_title']
    width = plot_params['width']
    height = plot_params['height']

    if plot_type == 'line':
        fig = px.line(df, x=X, y=Y, title=plot_title)
    elif plot_type == 'scatter':
        fig = px.scatter(df, x=X, y=Y, title=plot_title)

    fig.update_layout(
        yaxis_title=y_axis_title, legend_title_text='', width=width, height=height
    )
    return fig


def create_stack_plot(plot_params):
    """
    Create a stacked plot.

    Args:
        df (pd.DataFrame): The dataframe containing the data to plot.
        plot_params (dict): A dictionary containing the plot parameters.

    Returns:
        tuple: A tuple containing the Plotly figure object
        and the number of plots.
    """
    df = plot_params['df']
    X = plot_params['X']
    Y = plot_params['Y']
    plot_type = plot_params['plot_type']
    plot_title = plot_params['plot_title']
    width = plot_params['width']
    height = plot_params['height']

    fig = make_subplots(
        rows=len(Y), cols=1, shared_xaxes=True, vertical_spacing=VERTICAL_SPACING
    )

    for i, y_col in enumerate(Y):
        # Setup y-axis titles with line breaks
        y_axis_title = DICT_RENAME.get(y_col, y_col)
        if len(y_axis_title) > LINE_BREAK_LIMIT:  # Add line break for long titles
            y_axis_title = '<br>'.join(y_axis_title.split(' '))

        trace = go.Scatter(
            x=df[X],
            y=df[y_col],
            mode='lines' if plot_type == 'line' else 'markers',
            name=y_axis_title,
        )
        fig.add_trace(trace, row=i + 1, col=1)
        fig.update_yaxes(
            title_text=y_axis_title,
            title_standoff=40,  # Adjust spacing for wrapped titles
            row=i + 1,
            col=1,
        )

    num_plot = len(Y)
    fig.update_xaxes(title_text='Time', row=num_plot, col=1)
    fig.update_layout(
        title_text=plot_title,
        height=height * 0.3 * num_plot,
        width=width,
        showlegend=False,  # Hide the legend
    )
    return fig, num_plot


def create_dual_y_plot(plot_params):
    """
    Create a default plot.

    Args:
        df (pd.DataFrame): The dataframe containing the data to plot.
        plot_params (dict): A dictionary containing the plot parameters.

    Returns:
        plotly.graph_objects.Figure: The Plotly figure object.
    """
    df = plot_params['df']
    X = plot_params['X']
    Y = plot_params['Y']
    Y2 = plot_params['Y2']
    plot_type = plot_params['plot_type']
    plot_title = plot_params['plot_title']
    y_axis_title = plot_params['y_axis_title']
    y2_axis_title = plot_params['y2_axis_title']
    width = plot_params['width']
    height = plot_params['height']

    fig = go.Figure()

    for y_col in Y:
        trace = go.Scatter(
            x=df[X],
            y=df[y_col],
            mode='lines' if plot_type == 'line' else 'markers',
            name=f'{y_col} (Left)',
        )
        fig.add_trace(trace)

    for y2_col in Y2:
        trace = go.Scatter(
            x=df[X],
            y=df[y2_col],
            mode='lines' if plot_type == 'line' else 'markers',
            name=f'{y2_col} (Right)',
            yaxis='y2',
        )
        fig.add_trace(trace)

    fig.update_layout(
        yaxis=dict(title=y_axis_title),
        yaxis2=dict(title=y2_axis_title, overlaying='y', side='right', showgrid=False),
        title=plot_title,
        legend_title_text='',
        width=width,
        height=height,
    )
    return fig


def update_scatter_colors(fig, df, column, **kwargs):
    """
    Update the colors and markers of specific or all traces in the Plotly figure
    based on the specified column, and optionally remove legends for updated traces.

    Args:
        fig (go.Figure): The Plotly figure object to update.
        df (pd.DataFrame): The original dataframe used for plotting.
        column (str): The column used for determining marker properties.
    **kwargs: Additional keyword arguments for customization:
        color_map (dict, optional): A dictionary mapping values to colors.
        marker_map (dict, optional): A dictionary mapping values to marker types.
        trace_index (int, optional): The index of the specific
            trace to update. Default is None, meaning all traces.
        hide_legend (bool, optional): Whether to hide legends for the updated traces.
    """
    # Extract values from kwargs with defaults
    color_map = kwargs.get('color_map', None)
    marker_map = kwargs.get('marker_map', None)
    trace_index = kwargs.get('trace_index', None)
    hide_legend = kwargs.get('hide_legend', True)  # Default to hiding legend

    if color_map is None and marker_map is None:
        raise ValueError('At least one of color_map or marker_map must be provided.')

    # Determine which traces to update
    traces_to_update = (
        [trace_index] if trace_index is not None else range(len(fig.data))
    )

    for i in traces_to_update:
        trace = fig.data[i]

        # Get the x-values of the current trace
        x_vals = trace.x

        # Ensure x-values are numeric or timestamp-like
        if isinstance(x_vals[0], str):
            x_vals = pd.to_datetime(x_vals)

        # Filter the DataFrame based on the x-values of the trace
        filtered_df = df[df['Time Stamp'].isin(x_vals)]

        # Apply color and marker updates
        if not filtered_df.empty and column in filtered_df.columns:
            if color_map:
                # Map colors based on the color column
                colors = filtered_df[column].map(color_map).fillna('gray')
                trace.marker.color = colors.tolist()
            if marker_map:
                # Map marker symbols based on the column
                markers = filtered_df[column].map(marker_map).fillna('circle')
                trace.marker.symbol = markers.tolist()

            # Optionally hide the legend for this trace
            if hide_legend:
                trace.showlegend = False

    # Add custom legend entries if needed
    legend_entries = []

    # Add a legend entry for the column label (in text mode, no marker)
    legend_entries.append(
        go.Scatter(
            x=[None],  # No data points for legend entry
            y=[None],
            mode='text',
            text=[f'{column}'],  # Column name
            showlegend=True,
            name=f'{column}',  # Legend label
        )
    )

    # Add legend entries for the color map
    if color_map:
        for key, color in color_map.items():
            legend_entries.append(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode='markers',
                    marker=dict(color=color, size=10),
                    name=f'{key} (Color)',
                )
            )

    # Add legend entries for the marker map
    if marker_map:
        for key, marker in marker_map.items():
            legend_entries.append(
                go.Scatter(
                    x=[None],
                    y=[None],
                    mode='markers',
                    marker=dict(symbol=marker, size=10),
                    name=f'{key} (Marker)',
                )
            )

    fig.add_traces(legend_entries)

    # Ensure the legend is visible for the entire figure
    fig.update_layout(showlegend=True)


def generate_timeline(
    events_to_plot,
    sample_name=None,
    plot_title='Process Timeline',
    width=WIDTH,
    height=HEIGHT,
):
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

    # Check if the events_to_plot is a single event or a list of events
    if isinstance(events_to_plot, Lf_Event):
        events_to_plot = [events_to_plot]

    # Format the steps to be plotted for the plotly timeline
    rows = []
    for step in events_to_plot:
        if isinstance(step, Lf_Event):
            for bounds in step.bounds:
                rows.append(
                    {
                        'Event': step.name,
                        'Start': bounds[0],
                        'End': bounds[1],
                        'Average Temp': step.data[
                            'Substrate Heater Temperature'
                        ].mean(),
                        'Average Pressure': step.data['PC Capman Pressure'].mean(),
                    }
                )
                # add more quantities if needed

    df = pd.DataFrame(rows)

    # Set the time extend of the plot
    time_margin = pd.Timedelta(minutes=15)
    # Determine the timeline duration
    min_start_time = df['Start'].min() - time_margin
    # Calculate end time overlooking the Ar On event
    max_end_time = df[df['Event'] != 'Ar On']['End'].max() + time_margin

    # Define the title of the plot
    if sample_name is not None:
        plot_title += f':\n{sample_name}'

    # Create the plot with plotly express.timeline
    fig = px.timeline(
        df,
        x_start='Start',
        x_end='End',
        y='Event',
        color='Event',
        color_discrete_map=STEP_COLORS,
        title=plot_title,
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
        template='plotly_white',  # Use a white background template
        hovermode='closest',
        dragmode='zoom',
        title=plot_title,
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


def generate_bias_plot(
    events_to_plot,
    logfile_name,
    rolling_num=ROLLING_NUM,
    rolling_frac_max=ROLLING_FRAC_MAX,
):
    Y_plot = []
    patterns = [
        r'Source \d+ DC Bias',
        r'Source \d+ Voltage',
    ]

    deposition = event_list_to_dict(events_to_plot)['deposition']

    data = deposition.data.copy()

    # data_resampled = (
    #    data.set_index('Time Stamp')  # Temporarily set 'Time Stamp' as index
    #    .resample(f'{BIAS_PLOT_RESAMPLING_TIME}s')  # Resample data
    #    .mean(numeric_only=True)  # Apply aggregation (mean in this case)
    #    .reset_index()  # Reset index to turn 'Time Stamp' back into a column
    # )

    # data = data_resampled.copy()

    for col in data.columns:
        if any(re.search(pattern, col) for pattern in patterns):
            # Add the original column to the list of columns to plot
            Y_plot.append(col)

            # Add the smoothed column to the list of columns to plot
            data[f'{col} Smoothed {rolling_num}pt'] = (
                data[col].rolling(rolling_num, center=True).mean()
            )
            Y_plot.append(f'{col} Smoothed {rolling_num}pt')

            # check if more than 10percent of the dc bias data is zero
            if data[col].eq(0).sum() / len(data) > DC_BIAS_SMOOTHING_THRESHOLD:
                # if '_Sb_' in logfile_name:
                rolling_num_max = int(rolling_num * rolling_frac_max)
                # add the max instead of the mean after rolling
                data[f'{col} Max {rolling_num_max}pt'] = (
                    data[col]
                    .rolling(int(rolling_num * rolling_frac_max), center=True)
                    .max()
                )
                Y_plot.append(f'{col} Max {rolling_num_max}pt')
                # smooth the max curve
                data[f'{col} Max {rolling_num_max}pt Smoothed {rolling_num}pt'] = (
                    data[f'{col} Max {rolling_num_max}pt']
                    .rolling(rolling_num, center=True)
                    .mean()
                )
                Y_plot.append(f'{col} Max {rolling_num_max}pt Smoothed {rolling_num}pt')
                # iterate over the columns to plot and change zeros for NaN
                data[f'{col} No Zero'] = data[col].replace(0, np.nan)
                Y_plot.append(f'{col} No Zero')
                # smooth the no zero curve
                data[f'{col} No Zero Smoothed {rolling_num}pt'] = (
                    data[f'{col} No Zero']
                    .rolling(rolling_num, min_periods=1, center=True)
                    .mean()
                )
                Y_plot.append(f'{col} No Zero Smoothed {rolling_num}pt')

    bias_plot = quick_plot(
        data,
        Y_plot,
        mode='default',
        plot_type='line',
        width=WIDTH,
        plot_title=(f'DC Bias Plot during deposition: {logfile_name}'),
    )

    # set the Y axis title as 'DC Bias (V)'
    bias_plot.update_layout(yaxis_title='DC Bias (V)')

    return bias_plot


def generate_overview_plot(data, logfile_name, events):
    Y_plot = OVERVIEW_PLOT

    # Check if the columns are in the data
    Y_plot = [col for col in Y_plot if col in data.columns]

    if 'Thickness Rate' in OVERVIEW_PLOT:
        if 'Xtal 2 Shutter Open' in data.columns:
            data['Thickness Rate (0 if closed)'] = (
                data['Thickness Rate'] * data['Xtal 2 Shutter Open']
            )
            Y_plot.append('Thickness Rate (0 if closed)')
            Y_plot.remove('Thickness Rate')

    if (
        'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback' in OVERVIEW_PLOT
        and 'Sulfur Cracker Control Setpoint Feedback' in OVERVIEW_PLOT
    ):
        if 'Sulfur Cracker Control Enabled' in data.columns:
            data['Sulfur Cracker Pulse Width (0 if closed)'] = (
                data['Sulfur Cracker Control Valve PulseWidth Setpoint Feedback']
                * data['Sulfur Cracker Control Enabled']
            )
            Y_plot.append('Sulfur Cracker Pulse Width (0 if closed)')
            Y_plot.remove('Sulfur Cracker Control Valve PulseWidth Setpoint Feedback')

            data['Sulfur Cracker Frequency (0 if closed)'] = (
                data['Sulfur Cracker Control Setpoint Feedback']
                * data['Sulfur Cracker Control Enabled']
            )
            Y_plot.append('Sulfur Cracker Frequency (0 if closed)')
            Y_plot.remove('Sulfur Cracker Control Setpoint Feedback')

    # remove all the Y_col for which the data is constant throughout the data
    new_Y_plot = []
    for col in Y_plot:
        if not data[col].nunique() == 1:
            new_Y_plot.append(col)
    Y_plot = new_Y_plot

    # sort the Y_plot list to put everything that starts with 'Sulfur' at the end
    Y_plot.sort(key=lambda x: x.startswith('Sulfur'))

    # Get the deposition event
    deposition = event_list_to_dict(events)['deposition']
    # set the deposition condition col as the second column of deposition.cond
    data['deposition_cond'] = deposition.cond

    if 'cracker_on_open' in event_list_to_dict(events):
        cracker_on_open = event_list_to_dict(events)['cracker_on_open']
        data['cracker_open_cond'] = cracker_on_open.cond

    # Convert boolean conditions to integers (0 and 1) before resampling
    data['deposition_cond'] = data['deposition_cond'].astype(int)
    if 'cracker_on_open' in event_list_to_dict(events):
        data['cracker_open_cond'] = data['cracker_open_cond'].astype(int)

    data_resampled = (
        data.set_index('Time Stamp')  # Temporarily set 'Time Stamp' as index
        .resample(f'{OVERVIEW_PLOT_RESAMPLING_TIME}s')  # Resample data
        .mean(numeric_only=True)  # Apply aggregation (mean in this case)
        .reset_index()  # Reset index to turn 'Time Stamp' back into a column
    )

    # Ensure the column is treated as numeric (float)
    # before comparison and conversion to boolean
    data_resampled['deposition_cond'] = pd.to_numeric(
        data_resampled['deposition_cond'], errors='coerce'
    )

    # Apply the comparison and convert to boolean
    data_resampled['deposition_cond'] = (
        data_resampled['deposition_cond'] > BOOL_THRESHOLD
    ).astype(bool)

    if 'cracker_on_open' in event_list_to_dict(events):
        data_resampled['cracker_open_cond'] = pd.to_numeric(
            data_resampled['cracker_open_cond'], errors='coerce'
        )
        data_resampled['cracker_open_cond'] = (
            data_resampled['cracker_open_cond'] > BOOL_THRESHOLD
        ).astype(bool)
        data = data.copy()
        data = data_resampled

    # Convert 'deposition_cond' based on mean values
    data['deposition_cond'] = (data['deposition_cond'] > BOOL_THRESHOLD).astype(bool)
    if 'cracker_on_open' in event_list_to_dict(events):
        data['cracker_open_cond'] = (data['cracker_open_cond'] > BOOL_THRESHOLD).astype(
            bool
        )

    # place a vertical line marker at the beginning and at the end of the deposition
    dep_start, dep_end = deposition.bounds[0][0], deposition.bounds[0][1]

    overview_plot = quick_plot(
        data_resampled,
        Y_plot,
        plot_type='scatter',
        plot_title=(
            f'Overview Plot: {logfile_name} \n'
            f'({OVERVIEW_PLOT_RESAMPLING_TIME}s-downsampled)'
        ),
        mode='stack',
        heigth=0.5 * HEIGHT,
        width=WIDTH,
    )

    # Add vertical lines at dep_start and dep_end
    overview_plot.add_shape(
        type='line',
        x0=dep_start,
        y0=0,
        x1=dep_start,
        y1=1,
        xref='x',
        yref='paper',
        line=dict(color='Red', width=2, dash='dashdot'),
    )

    overview_plot.add_shape(
        type='line',
        x0=dep_end,
        y0=0,
        x1=dep_end,
        y1=1,
        xref='x',
        yref='paper',
        line=dict(color='Red', width=2, dash='dashdot'),
    )
    # add to the legend that the markers mark the deposition step

    # Update layout to include the shapes
    overview_plot.update_layout(
        shapes=overview_plot.layout.shapes + tuple(overview_plot.layout.shapes)
    )

    # Add annotations to the legend
    overview_plot.add_annotation(
        x=dep_start,
        y=-0.028,
        xref='x',
        yref='paper',
        text='Deposition<br>Start',
        showarrow=False,
        font=dict(color='Red'),
    )

    overview_plot.add_annotation(
        x=dep_end,
        y=-0.028,
        xref='x',
        yref='paper',
        text='Deposition<br>End',
        showarrow=False,
        font=dict(color='red'),
    )

    # update_scatter_colors(
    #    overview_plot,
    #    data,
    #    'deposition_cond',
    #    color_map=OVERVIEW_PLOT_COLOR_MAP,
    # )

    # if 'cracker_on_open' in event_list_to_dict(events):
    #    update_scatter_colors(
    #        overview_plot,
    #        data,
    #        'cracker_open_cond',
    #        marker_map=OVERVIEW_PLOT_MARKER_MAP,
    #    )

    return overview_plot


def generate_optix_plot(
    spectra,
    events_to_plot,
    logfile_name,
):
    deposition = event_list_to_dict(events_to_plot)['deposition']
    dep_spectra = filter_spectrum(spectra, deposition.bounds)

    # make the cascade plot of the spectra during the deposition
    optix_plot = generate_optix_cascade_plot(
        dep_spectra,
        plot_title=f'Optix Plot: {logfile_name}',
        color_scale='None',
    )

    return optix_plot


# def generate_better_overview_plot(data, logfile_name, events):

#     Y_cracker = [
#         'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback',
#         'Sulfur Cracker Control Setpoint Feedback',
#     ]
#     # Check if the columns are in the data
#     Y_cracker = [col for col in Y_cracker if col in data.columns]

#     cracker_fig = quick_plot(
#         data,
#         Y_cracker,
#         plot_type='line',
#         plot_title=f'Cracker Plot: {logfile_name}',
#         mode='dual_y',
#         heigth=0.5 * HEIGHT,
#         width=WIDTH,
#     )

#     Y_flows = []
#     for gas in ['ar', 'ph3', 'h2s']:
#         Y_flows.append(f'PC MFC {GAS_NUMBER[gas]} Flow')
#     # Check if the columns are in the data
#     Y_flows = [col for col in Y_flows if col in data.columns]

#     flow_fig = quick_plot(
#         data,
#         Y_flows,
#         plot_type='line',
#         plot_title=f'Flow Plot: {logfile_name}',
#         mode='default',
#         heigth=0.5 * HEIGHT,
#         width=WIDTH,
#     )

#     Y_sources = []
#     for source_number in ['1', '3', '4']:
#         Y_sources.append(f'Source {source_number} DC Bias')
#         Y_sources.append(f'Source {source_number} Voltage')
#         Y_sources.append(f'Source {source_number} Output Setpoint')
#     # Check if the columns are in the data
#     Y_sources = [col for col in Y_sources if col in data.columns]

#     source_fig = quick_plot(
#         data,
#         Y_sources,
#         plot_type='line',
#         plot_title=f'Source Plot: {logfile_name}',
#         mode='default',
#         heigth=0.5 * HEIGHT,
#         width=WIDTH,
#     )

#     Y_temp = [
#         'Substrate Heater Temperature',
#         'Substrate Heater Temperature 2',
#         'Substrate Heater Temperature Setpoint',
#     ]
#     # Check if the columns are in the data

#     temp_fig = quick_plot(
#         data,
#         Y_temp,
#         plot_type='line',
#         plot_title=f'Temperature Plot: {logfile_name}',
#         mode='default',
#         heigth=0.5 * HEIGHT,
#         width=WIDTH,
#     )
#     # combine the figures into a single figure with a common x axis

#     return fig


def generate_plots(log_data, events_to_plot, main_params, sample_name=''):
    # initialize a dict of plots
    plots = {}

    # Generate the timeline plot
    plotly_timeline = generate_timeline(events_to_plot, sample_name)
    plots['timeline'] = plotly_timeline

    # Generate the overview plot
    overview_plot = generate_overview_plot(log_data, sample_name, events_to_plot)
    plots['overview_plot'] = overview_plot

    bias_plot = generate_bias_plot(
        events_to_plot,
        sample_name,
        # rolling_num=ROLLING_NUM,
        # rolling_frac_max=ROLLING_FRAC_MAX,
    )
    plots['bias_plot'] = bias_plot

    # _, chamber_plotly_plot = plot_logfile_chamber(main_params, sample_name)
    # plots.append(chamber_plotly_plot)

    return plots


# HELPER FUNCTIONS TO MANIPULATE LISTS OF EVENTS--------


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


def event_list_to_dict(all_events):
    if isinstance(all_events, Lf_Event):
        all_events = [all_events]

    event_dict = {}

    for event in all_events:
        event_dict[event.step_id] = event

    return event_dict


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


# master function to read any file
def read_file(file_path):
    # open the file and read the first line
    with open(file_path) as file:
        first_line = file.readline()
        # check if the line has 'Triggered' in it
        if 'Triggered' in first_line:
            # if it does, read the file as a spectrum
            print('Reading as spectrum')
            return read_spectrum(file_path)
        elif 'Time' in first_line or 'Regulation' in first_line:
            # if it does not, read the file as an RGA file
            print('Reading as RGA')
            return read_rga(file_path)
        elif 'Recording Name' in first_line:
            # if it does not, read the file as a log file
            print('Reading as log file')
            return read_logfile(file_path)


def follow_peak(spectra, peak_pos=[656.1, 341.76, 311.9, 750.4]):
    """
    Track the intensity of specified peaks in the spectra data over time.

    Parameters:
    -----------
    spectra: dict
        A dictionary containing spectral data, with keys:
        - 'data': A dictionary of spectra
            (keys are timestamps, values are intensity arrays)
        - 'x': A list or array of wavelength values
            corresponding to the intensity arrays
        - 'timestamp_map': A dictionary mapping spectral keys to timestamps
    peak_pos: list of float
        Wavelengths of the peaks to track.

    Returns:
    --------
    pd.DataFrame:
        A DataFrame where each timestamp has intensity values for:
        - Peak position columns
        - Corresponding peak name columns (if position is in `PEAK_NAME`)
    """
    PEAK_NAME = {
        656.1: 'H',
        341.76: 'PH',
        311.9: 'S2',
        750.4: 'Ar',
    }

    # Ensure peak_pos is iterable
    peak_pos = [peak_pos] if isinstance(peak_pos, int | float) else peak_pos
    peak_names = {pos: PEAK_NAME.get(pos, None) for pos in peak_pos}

    # Prepare results
    results = []

    for key, time in spectra['timestamp_map'].items():
        row = {'Time Stamp': time}
        for pos, name in peak_names.items():
            # Find the closest wavelength index
            idx = (spectra['data']['x'] - pos).abs().idxmin()
            intensity = spectra['data'][key][idx]
            # Add intensity for position column
            row[f'{pos}'] = intensity
            # Add intensity for peak name column if exists
            if name:
                row[name] = intensity
        results.append(row)

    # Convert results to DataFrame
    peak_intensity = pd.DataFrame(results)

    # Combine rows with the same timestamp
    peak_intensity = peak_intensity.groupby('Time Stamp').first().reset_index()

    return peak_intensity


# Function to read the IDOL combinatorial chamber CSV logfile
def read_logfile(file_path):
    """
    This function reads a logfile and returns a DataFrame with the
    'Time Stamp' column converted to datetime format.
    All the logged values are stored in the DataFrame
    as they are in the logfile.
    """
    for i in range(5):
        df = pd.read_csv(file_path, header=[i+1], skiprows=[i], low_memory=False)

        # Check if the 'Time Stamp' column exists in the DataFrame
        if 'Time Stamp' in df.columns:
            break
    else:
        raise ValueError(
            "No 'Time Stamp' column found in the first 5 rows of the file."
        )

    df['Time Stamp'] = pd.to_datetime(
        df['Time Stamp'], format='%b-%d-%Y %I:%M:%S.%f %p'
    )
    # Ensure all timestamps in the log file and spectrum are tz-naive
    df['Time Stamp'] = df['Time Stamp'].dt.tz_localize(None)
    return df


def read_rga(file_path):
    rga_file = pd.read_csv(
        file_path,
        sep=',',
        header=0,
    )

    # Eplicitly parse the Time column
    rga_file['Time'] = pd.to_datetime(rga_file['Time'], format='%m/%d/%Y %I:%M:%S %p')

    # Rename the 'Time' column to 'Time Stamp'
    rga_file.rename(columns={'Time': 'Time Stamp'}, inplace=True)

    # for all columns except 'Time Stamp' and 'Time', if the column name
    # starts with a space, remove the space
    rga_file.columns = rga_file.columns.str.strip()

    # make time column tz naive
    rga_file['Time Stamp'] = rga_file['Time Stamp'].dt.tz_localize(None)

    return rga_file


def merge_logfile_rga(
    df1,
    df2,
    tolerance=None,
    direction='nearest',
):
    """
    Merge two DataFrames on Time Stamp columns, aligning their timestamps.

    Parameters:
        df1 (pd.DataFrame): First DataFrame with 'Time Stamp' column.
        df2 (pd.DataFrame): Second DataFrame with 'Time Stamp' column.
        tolerance (str or pd.Timedelta, optional): Maximum allowed time difference for
        alignment (e.g., '1s').
        direction (str): Direction for alignment - 'backward', 'forward', or 'nearest'
        (default: 'nearest').

    Returns:
        pd.DataFrame: Merged DataFrame with aligned timestamps and NaN for missing
        values.
    """
    # if df2 columns are found in df1, return df1 already
    if all(col in df1.columns for col in df2.columns):
        return df1

    # Ensure the Time Stamp columns are sorted
    df1 = df1.sort_values('Time Stamp')
    df2 = df2.sort_values('Time Stamp')

    # calculate the average time between the timestamps in each dataframe
    avg_time_diff_df1 = df1['Time Stamp'].diff().mean()
    avg_time_diff_df2 = df2['Time Stamp'].diff().mean()

    # calculate the tolerance based on the df with the smallest
    # average time difference
    tolerance = max(avg_time_diff_df1, avg_time_diff_df2)

    # Perform asof merge
    merged_df = pd.merge_asof(
        df1,
        df2,
        on='Time Stamp',
        direction=direction,
        tolerance=pd.Timedelta(tolerance) if tolerance else None,
    )

    return merged_df


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
    y_columns = [f'y{i + 1}' for i in range(len(result_df.columns) - 1)]
    result_df.columns = ['x'] + y_columns

    # Step 8: Drop the first row if it is filled with NaNs
    if result_df.iloc[0].isna().all():
        result_df = result_df.drop(result_df.index[0])

    # Step 9: Create a timestamp map
    timestamp_map = {
        f'y{i + 1}': timestamp
        for i, timestamp in enumerate(reshaped_data['Timestamp'].unique())
    }

    timestamp_map_tz_naive = make_timestamps_tz_naive(timestamp_map)

    spectra['data'] = result_df
    spectra['timestamp_map'] = timestamp_map_tz_naive

    return spectra


def filter_spectrum(spectra, bounds, calc_mean=False):
    """
    This function filters in the Optix spectrums based on the conditions that they
    have been recorded during the time bounds passed in the 'bounds' list.
    """
    filtered_spectra = {'data': [], 'timestamp_map': {}}

    spectra['timestamp_map'] = make_timestamps_tz_naive(spectra['timestamp_map'])

    if isinstance(bounds, Lf_Event):
        bounds = bounds.bounds

    if not isinstance(bounds[0], tuple):
        bounds = [bounds]

    for bound in bounds:
        start_time, end_time = bound
        # Format start_time and end_time in case they are input strings instead
        # of event.bounds
        start_time = format_time_stamp(start_time, ref_object=spectra)
        end_time = format_time_stamp(end_time, ref_object=spectra)

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

    if calc_mean:
        filtered_spectra = calc_mean_norm_spectrum(filtered_spectra)

    return filtered_spectra


# normalize the data in a column
def normalize_column(df, column_name):
    min_val = df[column_name].min()
    max_val = df[column_name].max()
    return (df[column_name] - min_val) / (max_val - min_val)


def calc_mean_norm_spectrum(spectra):
    if 'mean' in spectra['data'].columns:
        return spectra
    spectra['data']['mean'] = spectra['data'].iloc[:, 1:].mean(axis=1)
    spectra['data']['mean_norm'] = normalize_column(spectra['data'], 'mean')
    return spectra


# ------------------------CORE METHODS----------------------


def format_logfile(data):
    # print('Formatting the dataframe for conditional filtering')
    # -----FORMATTING THE DATAFRAME FOR CONDITIONAL FILTERING-------
    # -------RENAME THE CRACKER COLUMNS OF THE DATAFRAME---------
    data = rename_cracker_columns(data, rename_cracker_col=RENAME_CRACKER_COL)
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
    interrupt_deposition = False
    for event in events:
        if event.category == 'deposition':
            # if a deposition event time between the bounds is lower
            # than MIN_DEPOSITION_SIZE, we consider that the deposition
            # event is not valid
            if event.events == 1:
                interrupt_deposition = False
            elif event.events == 0:
                print('Error: No deposition event found')
                break
            elif event.events > 1:
                print(
                    'More than one deposition event detected.',
                    'Removing deposition events smaller than',
                    f'{MIN_DEPOSITION_SIZE} steps',
                )
                print('Number of deposition events before filtering:', event.events)
                for i in range(event.events):
                    print(
                        f'Deposition({i}) start time: {event.bounds[i][0]}',
                        f'Deposition({i}) end time: {event.bounds[i][1]}',
                    )
                event.filter_out_small_events(MIN_DEPOSITION_SIZE)
                print('Number of deposition events after filtering:', event.events)
                for i in range(event.events):
                    print(
                        f'Deposition({i + 1}) start time: {event.bounds[i][0]}',
                        f'Deposition({i + 1}) end time: {event.bounds[i][1]}',
                    )
                if event.events == 1:
                    print('A unique deposition event was succesfully filtered')
                    interrupt_deposition = False
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
                        interrupt_deposition = True
                    else:
                        raise ValueError(
                            'Error: The number of deposition events is not 1 ',
                            'after increasing the continuity limit and filttering ',
                            'smaller events',
                        )
                        break

    return events, interrupt_deposition


def select_last_event(events, raw_data, ref_event, categories):
    for event in events:
        if event.category in categories:
            try:
                event.select_event(raw_data, -1, ref_event.bounds[0][0])
            except Exception as e:
                print(
                    'Warning: ',
                    f'Failed to find any event before {ref_event.bounds[0][0]}',
                    f'for {event.step_id}. Error: {e}',
                )
    return events


def extract_category_from_list(events: list, category: str):
    list_of_events = []
    for event in events:
        if event.category == category:
            list_of_events.append(event)
    return list_of_events


def read_events(data):
    data, source_list = format_logfile(data)

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
    ph3, nh3, h2s, ar, n2, o2 = filter_gas(data)

    add_event_to_events([ph3, nh3, h2s, ar, n2, o2], events)

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
        nh3=nh3,
        h2s=h2s,
        n2=n2,
        o2=o2,
        deposition=deposition,
    )

    add_event_to_events(source_presput, events)

    # ---------7/CONDITIONS FOR THE S CRACKER PRESSURE MEAS--------
    # Filter the data for the S Cracker pressure
    cracker_base_pressure = filter_data_cracker_pressure(
        data,
        cracker_on_open=cracker_on_open,
        ph3=ph3,
        nh3=nh3,
        h2s=h2s,
        ar=ar,
        n2=n2,
        o2=o2,
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
        nh3=nh3,
        h2s=h2s,
        n2=n2,
        o2=o2,
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
            nh3=nh3,
            h2s=h2s,
            ar=ar,
            n2=n2,
            o2=o2,
            deposition=deposition,
        )
    )
    add_event_to_events(
        [ramp_up_temp, ramp_down_temp, ramp_down_high_temp, ramp_down_low_temp], events
    )

    # ----10/CONDITIONS FOR THE PLATEN BIAS BEING ON----------
    # Filter the data for the platen bias being on
    platen_bias_on = filter_data_platen_bias_on(data)

    add_event_to_events(platen_bias_on, events)

    # -----FURTHER PROCESSING OF THE EVENTS-----
    # Remove the empty events from the events
    events = [event for event in events if event.bounds]

    # here we make sure that if the rest of the code fails, we still have the events
    # to return
    try:
        # Place the ramp_up_temp, deposition, ramp_down_high_temp, ramp_down_low_temp
        # event first in the list of all events, in this particular order
        events = place_deposition_ramp_up_down_events_first(events)

        # Getting the list of all events to pass it to the plotting function
        # in the future
        events_to_plot = copy.deepcopy(events)

        # We verify the unicity of the deposition event, and try to fix it if needed
        events, interrupt_deposition = verify_deposition_unicity(events, data)

        # To make a list sutable for making a report, we remove
        # all the events that do not match the CATEGORIES_MAIN_REPORT

        events_main_report = [
            copy.deepcopy(event)
            for event in events
            if event.category in CATEGORIES_MAIN_REPORT
        ]

        # For all the events of the main report list, we also get the last_event before
        # the deposition, using the select_event function, -1 (last) event
        # together with the deposition first bounds
        events = select_last_event(events, data, deposition, CATEGORIES_LAST_EVENT)

        # Initialize the params dictionary for the main report
        main_params = {}

        # for event in events_for_main_report, we apply the get_ methods for
        # the class Lf_Event to get the params dict
        main_params = get_overview(data)
        for event in events_main_report:
            if event.category == 'deposition':
                main_params = event.get_params(
                    raw_data=data,
                    source_list=source_list,
                    params=main_params,
                    interrupt_deposition=interrupt_deposition,
                )
            else:
                main_params = event.get_params(
                    raw_data=data,
                    source_list=source_list,
                    params=main_params,
                )
        main_params = get_end_of_process(data, main_params)

        # We only get the events that are in the CATEGORIES_STEPS
        events_steps = [
            copy.deepcopy(event)
            for event in events
            if event.category in CATEGORIES_STEPS
        ]

        # unfold all the events_main_report events to get sep_events
        sep_events = unfold_events(copy.deepcopy(events_steps), data)

        # Sort the subevents by the start time
        sep_events = sort_events_by_start_time(sep_events)

        # Initialize the params dictionary for the sub report
        step_params = {}

        # get the individual step params
        for event in sep_events:
            step_params = event.get_nomad_step_params(step_params, source_list)

    except Exception as e:
        print('Error: ', e)
        print('The events are returned without further processing')
        return events, {}, {}

    # generate a list of plots to return
    # plots = generate_plots(data, events_to_plot, main_params)

    return (
        events_to_plot,
        main_params,
        step_params,
    )


# ----NOMAD HELPER FUNCTION-----


# Helper method to get the nested value, if it exists
def get_nested_value(dictionary, key_path):
    """
    Safely get a nested value from a dictionary.

    :param dictionary: The dictionary to traverse.
    :param key_path: A list of keys representing the path
        to the desired value.
    :return: The value at the end of the key path, or None if not found.
    """
    for key in key_path:
        if isinstance(dictionary, dict):
            dictionary = dictionary.get(key)
        else:
            return None
    return dictionary


def map_params_to_nomad(params, gun_list):
    # Definiting the input, ouput and unit
    param_nomad_map = [
        [
            ['deposition', 'avg_temp_1'],
            ['deposition_parameters', 'deposition_temperature'],
            'degC',
        ],
        [
            ['deposition', 'avg_temp_2'],
            ['deposition_parameters', 'deposition_temperature_2'],
            'degC',
        ],
        [
            ['deposition', 'avg_temp_setpoint'],
            ['deposition_parameters', 'deposition_temperature_setpoint'],
            'degC',
        ],
        [
            ['deposition', 'avg_true_temp'],
            ['deposition_parameters', 'deposition_true_temperature'],
            'degC',
        ],
        [
            ['deposition', 'duration'],
            ['deposition_parameters', 'deposition_time'],
            None,  # duration has no unit since it is a TimeDelta object
        ],
        [
            ['deposition', 'avg_capman_pressure'],
            ['deposition_parameters', 'sputter_pressure'],
            'mtorr',
        ],
        [
            ['deposition', 'material_space'],
            ['deposition_parameters', 'material_space'],
            None,
        ],
        [
            ['deposition', 'avg_ar_flow'],
            ['deposition_parameters', 'ar_flow'],
            'cm^3/minute',
        ],
        [
            ['deposition', 'avg_h2s_flow'],
            ['deposition_parameters', 'h2s_in_ar_flow'],
            'cm^3/minute',
        ],
        [
            ['deposition', 'avg_h2s_partial_pressure'],
            ['deposition_parameters', 'h2s_partial_pressure'],
            'mtorr',
        ],
        [
            ['deposition', 'avg_nh3_flow'],
            ['deposition_parameters', 'nh3_in_ar_flow'],
            'cm^3/minute',
        ],
        [
            ['deposition', 'avg_nh3_partial_pressure'],
            ['deposition_parameters', 'nh3_partial_pressure'],
            'mtorr',
        ],
        [
            ['deposition', 'avg_ph3_flow'],
            ['deposition_parameters', 'ph3_in_ar_flow'],
            'cm^3/minute',
        ],
        [
            ['deposition', 'avg_ph3_partial_pressure'],
            ['deposition_parameters', 'ph3_partial_pressure'],
            'mtorr',
        ],
        [
            ['deposition', 'avg_n2_flow'],
            ['deposition_parameters', 'n2_flow'],
            'cm^3/minute',
        ],
        [
            ['deposition', 'avg_n2_partial_pressure'],
            ['deposition_parameters', 'n2_partial_pressure'],
            'mtorr',
        ],
        [
            ['deposition', 'avg_o2_flow'],
            ['deposition_parameters', 'o2_in_ar_flow'],
            'cm^3/minute',
        ],
        [
            ['deposition', 'avg_o2_partial_pressure'],
            ['deposition_parameters', 'o2_partial_pressure'],
            'mtorr',
        ],
        # End of process parameters
        [
            ['overview', 'end_of_process_temp'],
            ['end_of_process', 'heater_temp'],
            'degC',
        ],
        [
            ['overview', 'time_in_chamber_after_deposition'],
            ['end_of_process', 'time_in_chamber_after_deposition'],
            'second',
        ],
    ]
    if 'ph3_h2s_ratio' in params['deposition']:
        param_nomad_map.append(
            [
                ['deposition', 'ph3_h2s_ratio'],
                ['deposition_parameters', 'ph3_h2s_ratio'],
                None,
            ]
        )
    if params['overview']['true_base_pressure_meas']:
        param_nomad_map.append(
            [
                ['overview', 'base_pressure'],
                ['base_pressure'],
                'torr',
            ]
        )
    if params['deposition'].get('s_cracker', {}).get('enabled', False):
        # s_cracker parameters
        param_nomad_map.extend(
            [
                [
                    ['deposition', 's_cracker', 'zone1_temp'],
                    ['deposition_parameters', 's_cracker', 'zone1_temperature'],
                    'degC',
                ],
                [
                    ['deposition', 's_cracker', 'zone1_temp_sp'],
                    [
                        'deposition_parameters',
                        's_cracker',
                        'zone1_temperature_setpoint',
                    ],
                    'degC',
                ],
                [
                    ['deposition', 's_cracker', 'zone2_temp'],
                    ['deposition_parameters', 's_cracker', 'zone2_temperature'],
                    'degC',
                ],
                [
                    ['deposition', 's_cracker', 'zone3_temp'],
                    ['deposition_parameters', 's_cracker', 'zone3_temperature'],
                    'degC',
                ],
                [
                    ['deposition', 's_cracker', 'pulse_width'],
                    ['deposition_parameters', 's_cracker', 'valve_on_time'],
                    'millisecond',
                ],
                [
                    ['deposition', 's_cracker', 'pulse_freq'],
                    ['deposition_parameters', 's_cracker', 'valve_frequency'],
                    'mHz',
                ],
            ]
        )
    # Gun parameters
    for gun in gun_list:
        if params['deposition'].get(gun, {}).get('enabled', False):
            param_nomad_map.extend(
                [
                    [
                        ['deposition', gun, 'target_name'],
                        ['deposition_parameters', gun, 'target_name'],
                        None,
                    ],
                    [
                        ['deposition', gun, 'target_material'],
                        ['deposition_parameters', gun, 'target_material'],
                        None,
                    ],
                    [
                        ['deposition', gun, 'target_id'],
                        ['deposition_parameters', gun, 'target_id', 'lab_id'],
                        None,
                    ],
                    [
                        ['deposition', gun, 'target_usage'],
                        ['deposition_parameters', gun, 'target_usage'],
                        'kWh',#TODO test that
                    ],
                    [
                        ['deposition', gun, 'avg_output_power'],
                        ['deposition_parameters', gun, 'applied_power'],
                        'W',
                    ],
                    [
                        ['deposition', gun, 'plasma_type'],
                        ['deposition_parameters', gun, 'power_type'],
                        None,
                    ],
                    [
                        ['deposition', gun, 'avg_voltage'],
                        ['deposition_parameters', gun, 'average_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'start_voltage'],
                        ['deposition_parameters', gun, 'start_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'end_voltage'],
                        ['deposition_parameters', gun, 'end_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'start_minus_end_voltage'],
                        ['deposition_parameters', gun, 'start_end_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'max_voltage'],
                        ['deposition_parameters', gun, 'max_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'min_voltage'],
                        ['deposition_parameters', gun, 'min_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'range_voltage'],
                        ['deposition_parameters', gun, 'range_voltage'],
                        'V',
                    ],
                    [
                        ['deposition', gun, 'std_voltage'],
                        ['deposition_parameters', gun, 'std_voltage'],
                        'V',
                    ],
                ]
            )
            if not params['deposition']['rt']:
                # ramp up temperature
                param_nomad_map.extend(
                    [
                        [
                            ['ramp_up_temp', 'start_temp'],
                            ['temperature_ramp_up', 'start_temperature_setpoint'],
                            'degC',
                        ],
                        [
                            ['ramp_up_temp', 'end_temp'],
                            ['temperature_ramp_up', 'end_temperature_setpoint'],
                            'degC',
                        ],
                        [
                            ['ramp_up_temp', 'duration'],
                            ['temperature_ramp_up', 'duration'],
                            None,
                        ],
                        [
                            ['ramp_up_temp', 'temp_slope'],
                            ['temperature_ramp_up', 'temperature_slope'],
                            'degC/minute',
                        ],
                        [
                            ['ramp_up_temp', 'avg_capman_pressure'],
                            ['temperature_ramp_up', 'avg_capman_pressure'],
                            'mtorr',
                        ],
                        [
                            ['ramp_up_temp', 'avg_ar_flow'],
                            ['temperature_ramp_up', 'avg_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_up_temp', 'avg_ph3_flow'],
                            ['temperature_ramp_up', 'avg_ph3_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_up_temp', 'avg_nh3_flow'],
                            ['temperature_ramp_up', 'avg_nh3_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_up_temp', 'avg_h2s_flow'],
                            ['temperature_ramp_up', 'avg_h2s_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_up_temp', 'avg_n2_flow'],
                            ['temperature_ramp_up', 'avg_n2_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_up_temp', 'avg_o2_flow'],
                            ['temperature_ramp_up', 'avg_o2_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_up_temp', 's_cracker', 'enabled'],
                            ['temperature_ramp_up', 'cracker_enabled'],
                            None,
                        ],
                        # ramp down temperature
                        [
                            ['ramp_down_high_temp', 'start_temp'],
                            ['temperature_ramp_down', 'start_temperature'],
                            'degC',
                        ],
                        [
                            ['ramp_down_high_temp', 'end_temp'],
                            ['temperature_ramp_down', 'end_temperature'],
                            'degC',
                        ],
                        [
                            ['ramp_down_high_temp', 'duration'],
                            ['temperature_ramp_down', 'duration'],
                            None,
                        ],
                        [
                            ['ramp_down_high_temp', 'temp_slope'],
                            ['temperature_ramp_down', 'temperature_slope'],
                            'degC/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_capman_pressure'],
                            ['temperature_ramp_down', 'avg_capman_pressure'],
                            'mtorr',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_ar_flow'],
                            ['temperature_ramp_down', 'avg_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_ph3_flow'],
                            ['temperature_ramp_down', 'avg_ph3_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_nh3_flow'],
                            ['temperature_ramp_down', 'avg_nh3_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_h2s_flow'],
                            ['temperature_ramp_down', 'avg_h2s_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_n2_flow'],
                            ['temperature_ramp_down', 'avg_n2_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 'avg_o2_flow'],
                            ['temperature_ramp_down', 'avg_o2_in_ar_flow'],
                            'cm^3/minute',
                        ],
                        [
                            ['ramp_down_high_temp', 's_cracker', 'enabled'],
                            ['temperature_ramp_down', 'cracker_enabled'],
                            None,
                        ],
                        [
                            ['ramp_down_high_temp', 'anion_input_cutoff_temp'],
                            ['temperature_ramp_down', 'anion_input_cutoff_temperature'],
                            'degC',
                        ],
                    ]
                )

    return param_nomad_map


def map_source_up_params_to_nomad(target_name):
    source_up_param_nomad_map = [
        [
            ['source_ramp_up', target_name, 'target_name'],
            ['target_name'],
            None,
        ],
        [
            ['source_ramp_up', target_name, 'ignition_power'],
            ['plasma_ignition_power'],
            'W',
        ],
        [
            ['source_ramp_up', target_name, 'ignition_pressure'],
            ['plasma_ignition_pressure'],
            'mtorr',
        ],
    ]

    return source_up_param_nomad_map


def map_source_presput_params_to_nomad(target_name):
    source_presput_param_nomad_map = [
        [
            ['source_presput', target_name, 'target_name'],
            ['target_name'],
            None,
        ],
        [
            ['source_presput', target_name, 'duration'],
            ['presput_time'],
            None,
        ],
        [
            ['source_presput', target_name, 'avg_output_power'],
            ['presput_power'],
            'W',
        ],
        [
            ['source_presput', target_name, 'avg_capman_pressure'],
            ['presput_pressure'],
            'mtorr',
        ],
        [
            ['source_presput', target_name, 'avg_ar_flow'],
            ['presput_ar_flow'],
            'cm^3/minute',
        ],
    ]

    return source_presput_param_nomad_map


def map_source_deprate_params_to_nomad(target_name):
    source_deprate_param_nomad_map = [
        [
            ['source_deprate2_film_meas', target_name, 'target_name'],
            ['target_name'],
            None,
        ],
        [
            ['source_deprate2_film_meas', target_name, 'dep_rate'],
            ['source_deprate'],
            'Å/s',
        ],
        [
            ['source_deprate2_film_meas', target_name, 'dep_rate_ref_mat'],
            ['source_deprate_ref_mat'],
            None,
        ],
    ]

    return source_deprate_param_nomad_map


def map_step_params_to_nomad(key):
    step_param_nomad_map = [
        [[key, 'name'], ['name'], None],
        # start_time has no unit since it is a TimeStamp object
        [[key, 'start_time'], ['start_time'], None],
        # duration has no unit since it is a TimeDelta object
        [[key, 'duration'], ['duration'], None],
    ]

    # Defining the input, output and unit
    return step_param_nomad_map


def map_environment_params_to_nomad(key):
    """
    Heater section missing arguments
    In nomad
    (nomad-material-processing/src/nomad_material_processing/vapor_deposition/general.py)

    class SubstrateHeater(ArchiveSection):
        pass
    """
    environment_param_nomad_map = [
        [[key, 'environment', 'pressure', 'value'], ['pressure', 'value'], 'mtorr'],
        [[key, 'environment', 'pressure', 'time'], ['pressure', 'time'], 'second'],
    ]

    return environment_param_nomad_map


def map_gas_flow_params_to_nomad(key, gas_name):
    gas_flow_param_nomad_map = [
        [[key, 'environment', 'gas_flow', gas_name, 'gas', 'name'], ['gas_name'], None],
        [
            [key, 'environment', 'gas_flow', gas_name, 'gas', 'name'],
            ['gas', 'name'],
            None,
        ],
        [
            [key, 'environment', 'gas_flow', gas_name, 'flow_rate', 'value'],
            ['flow_rate', 'value'],
            'cm^3/minute',
        ],
        [
            [key, 'environment', 'gas_flow', gas_name, 'flow_rate', 'time'],
            ['flow_rate', 'time'],
            'second',
        ],
        [
            [key, 'environment', 'gas_flow', gas_name, 'flow_rate', 'measurement_type'],
            ['flow_rate', 'measurement_type'],
            None,
        ],
    ]

    return gas_flow_param_nomad_map


def map_platen_bias_params_to_nomad(key, step_params):
    platen_bias_param_nomad_map = []  # Initialize with default value

    if 'platen_bias' in step_params[key]['environment']:
        platen_bias_param_nomad_map = [
            [
                [key, 'environment', 'platen_bias', 'shutter_open', 'value'],
                ['source_shutter_open', 'value'],
                'V',
            ],
            [
                [key, 'environment', 'platen_bias', 'shutter_open', 'time'],
                ['source_shutter_open', 'time'],
                'second',
            ],
            [
                [key, 'environment', 'platen_bias', 'shutter_open', 'mode_value'],
                ['source_shutter_open', 'mode_value'],
                None,
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'power_type'],
                ['vapor_source', 'power_type'],
                None,
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'avg_power_sp'],
                ['vapor_source', 'avg_power_sp'],
                'W',
            ],
            [
                [
                    key,
                    'environment',
                    'platen_bias',
                    'power_supply',
                    'power_sp',
                    'value',
                ],
                ['vapor_source', 'power_sp', 'value'],
                'W',
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'power_sp', 'time'],
                ['vapor_source', 'power_sp', 'time'],
                'second',
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'avg_dc_bias'],
                ['vapor_source', 'avg_dc_bias'],
                'V',
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'dc_bias', 'value'],
                ['vapor_source', 'dc_bias', 'value'],
                'V',
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'dc_bias', 'time'],
                ['vapor_source', 'dc_bias', 'time'],
                'second',
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'avg_fwd_power'],
                ['vapor_source', 'avg_fwd_power'],
                'W',
            ],
            [
                [
                    key,
                    'environment',
                    'platen_bias',
                    'power_supply',
                    'fwd_power',
                    'value',
                ],
                ['vapor_source', 'fwd_power', 'value'],
                'W',
            ],
            [
                [
                    key,
                    'environment',
                    'platen_bias',
                    'power_supply',
                    'fwd_power',
                    'time',
                ],
                ['vapor_source', 'fwd_power', 'time'],
                'second',
            ],
            [
                [key, 'environment', 'platen_bias', 'power_supply', 'avg_rfl_power'],
                ['vapor_source', 'avg_rfl_power'],
                'W',
            ],
            [
                [
                    key,
                    'environment',
                    'platen_bias',
                    'power_supply',
                    'rfl_power',
                    'value',
                ],
                ['vapor_source', 'rfl_power', 'value'],
                'W',
            ],
            [
                [
                    key,
                    'environment',
                    'platen_bias',
                    'power_supply',
                    'rfl_power',
                    'time',
                ],
                ['vapor_source', 'rfl_power', 'time'],
                'second',
            ],
        ]

    return platen_bias_param_nomad_map


def map_heater_params_to_nomad(key):
    heater_param_nomad_map = [
        [
            [key, 'environment', 'heater', 'avg_temp_1'],
            ['avg_temperature_1'],
            'degC',
        ],
        [
            [key, 'environment', 'heater', 'avg_temp_2'],
            ['avg_temperature_2'],
            'degC',
        ],
        [
            [key, 'environment', 'heater', 'avg_temp_sp'],
            ['avg_temperature_setpoint'],
            'degC',
        ],
        [
            [key, 'environment', 'heater', 'temp_1', 'value'],
            ['temperature_1', 'value'],
            'degC',
        ],
        [
            [key, 'environment', 'heater', 'temp_1', 'time'],
            ['temperature_1', 'time'],
            'second',
        ],
        [
            [key, 'environment', 'heater', 'temp_2', 'value'],
            ['temperature_2', 'value'],
            'degC',
        ],
        [
            [key, 'environment', 'heater', 'temp_2', 'time'],
            ['temperature_2', 'time'],
            'second',
        ],
        [
            [key, 'environment', 'heater', 'temp_sp', 'value'],
            ['temperature_setpoint', 'value'],
            'degC',
        ],
        [
            [key, 'environment', 'heater', 'temp_sp', 'time'],
            ['temperature_setpoint', 'time'],
            'second',
        ],
    ]

    return heater_param_nomad_map


def map_s_cracker_params_to_nomad(key):
    s_cracker_param_nomad_map = [
        [
            [key, 'sources', 's_cracker', 'valve_pulsing', 'value'],
            ['valve_open', 'value'],
            None,
        ],
        [
            [key, 'sources', 's_cracker', 'valve_pulsing', 'time'],
            ['valve_open', 'time'],
            'second',
        ],
        [
            [key, 'sources', 's_cracker', 'valve_pulsing', 'mode_value'],
            ['valve_open', 'mode_value'],
            None,
        ],
    ]
    for zone_number in ['1', '2', '3']:
        s_cracker_param_nomad_map.extend(
            [
                [
                    [key, 'sources', 's_cracker', f'avg_zone{zone_number}_temp'],
                    ['vapor_source', f'avg_zone{zone_number}_temperature'],
                    'degC',
                ],
                [
                    [key, 'sources', 's_cracker', f'zone{zone_number}_temp', 'value'],
                    ['vapor_source', f'zone{zone_number}_temperature', 'value'],
                    'degC',
                ],
                [
                    [key, 'sources', 's_cracker', f'zone{zone_number}_temp', 'time'],
                    ['vapor_source', f'zone{zone_number}_temperature', 'time'],
                    'second',
                ],
            ]
        )

    return s_cracker_param_nomad_map


def map_sputter_source_params_to_nomad(key, source_name, power_type):
    source_param_nomad_map = [
        [
            [key, 'sources', source_name, 'power_supply', 'power_type'],
            ['vapor_source', 'power_type'],
            None,
        ],
        [
            [key, 'sources', source_name, 'power_supply', 'avg_power_sp'],
            ['vapor_source', 'avg_power_sp'],
            'W',
        ],
        [
            [key, 'sources', source_name, 'power_supply', 'power_sp', 'value'],
            ['vapor_source', 'power_sp', 'value'],
            'W',
        ],
        [
            [key, 'sources', source_name, 'power_supply', 'power_sp', 'time'],
            ['vapor_source', 'power_sp', 'time'],
            'second',
        ],
        [
            [key, 'sources', source_name, 'source_shutter_open', 'value'],
            ['source_shutter_open', 'value'],
            None,
        ],
        [
            [key, 'sources', source_name, 'source_shutter_open', 'time'],
            ['source_shutter_open', 'time'],
            'second',
        ],
        [
            [key, 'sources', source_name, 'source_shutter_open', 'mode_value'],
            ['source_shutter_open', 'mode_value'],
            None,
        ],
    ]
    if power_type == 'RF':
        source_param_nomad_map.extend(
            [
                [
                    [key, 'sources', source_name, 'power_supply', 'avg_dc_bias'],
                    ['vapor_source', 'avg_dc_bias'],
                    'V',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'dc_bias', 'value'],
                    ['vapor_source', 'dc_bias', 'value'],
                    'V',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'dc_bias', 'time'],
                    ['vapor_source', 'dc_bias', 'time'],
                    'second',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'avg_fwd_power'],
                    ['vapor_source', 'avg_fwd_power'],
                    'W',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'avg_rfl_power'],
                    ['vapor_source', 'avg_rfl_power'],
                    'W',
                ],
            ]
        )
    if power_type in ['DC', 'pulsed_DC']:
        source_param_nomad_map.extend(
            [
                [
                    [key, 'sources', source_name, 'power_supply', 'avg_voltage'],
                    ['vapor_source', 'avg_voltage'],
                    'V',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'voltage', 'value'],
                    ['vapor_source', 'voltage', 'value'],
                    'V',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'voltage', 'time'],
                    ['vapor_source', 'voltage', 'time'],
                    'second',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'avg_current'],
                    ['vapor_source', 'avg_current'],
                    'A',  # Check if this is correct
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'current', 'value'],
                    ['vapor_source', 'current', 'value'],
                    'A',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'current', 'time'],
                    ['vapor_source', 'current', 'time'],
                    'second',
                ],
            ]
        )
    if power_type == 'pulsed_DC':
        source_param_nomad_map.extend(
            [
                [
                    [
                        key,
                        'sources',
                        source_name,
                        'power_supply',
                        'avg_pulse_frequency',
                    ],
                    ['vapor_source', 'avg_pulse_frequency'],
                    'kHz',
                ],
                [
                    [
                        key,
                        'sources',
                        source_name,
                        'power_supply',
                        'pulse_frequency',
                        'value',
                    ],
                    ['vapor_source', 'pulse_frequency', 'value'],
                    'kHz',
                ],
                [
                    [
                        key,
                        'sources',
                        source_name,
                        'power_supply',
                        'pulse_frequency',
                        'time',
                    ],
                    ['vapor_source', 'pulse_frequency', 'time'],
                    'second',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'avg_dead_time'],
                    ['vapor_source', 'avg_dead_time'],
                    'microsecond',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'dead_time', 'value'],
                    ['vapor_source', 'dead_time', 'value'],
                    'microsecond',
                ],
                [
                    [key, 'sources', source_name, 'power_supply', 'dead_time', 'time'],
                    ['vapor_source', 'dead_time', 'time'],
                    'second',
                ],
            ]
        )

    return source_param_nomad_map


def map_material_params_to_nomad(key, source_name):
    material_param_nomad_map = [
        [
            [key, 'sources', source_name, 'target_id'],
            ['lab_id'],
            None,
        ],
    ]
    return material_param_nomad_map


# -------CHAMBER VISUALIZATION PLOTTING METHODS-----------

# ----DEFINE GRAPHICAL PARAMETERS, SPUTTER CHAMBER AND PLATEN ----------

# Define the default grapihcal parameters
DEFAULT_FONTSIZE = 10
DEFAULT_LINEWIDTH = 1
GUN_TO_PLATEN = 1.4

X_LIM = (-130, 130)
Y_LIM = (-110, 110)

# Define the platen geometry
PLATEN_POS, PLATEN_DIAM, PLATEN_CENTER_DIAM = (0, 0), 75, 2

MIDDLE_SCREW_POS, MIDDLE_SCREW_DIAM = (0, 15), 3

TOXIC_GAS_INLET_ANGLE = np.radians(-58)

# Define a dictionary to map names to their colors and locations
GUN_PROPERTIES = {
    's_cracker': {'color': 'red', 'location': np.radians(180)},
    'taurus': {'color': 'green', 'location': np.radians(135)},
    'magkeeper3': {'color': 'blue', 'location': np.radians(315)},
    'magkeeper4': {'color': 'magenta', 'location': np.radians(45)},
}

GUN_OVERVIEW_NAMES = [
    'taurus',
    'magkeeper3',
    'magkeeper4',
]


# Very simples classes to store the samples and guns information
class Sample:
    # Note that sample positions are the position of the center of
    # the square samples. sub_size=40 is assumed by default.
    def __init__(self, label, pos: list, rotation, size: list, mat='cSi'):
        self.label = label
        self.pos_x = pos[0]
        self.pos_y = pos[1]
        self.rotation = rotation
        self.width = size[0]
        self.length = size[1]
        self.pos_x_bl = pos[0] - size[0] / 2
        self.pos_y_bl = pos[1] - size[1] / 2
        self.mat = mat


class Gun:
    def __init__(
        self,
        name,
        mat,
        pos_x=None,
        pos_y=None,
    ):
        self.name = name
        self.mat = mat
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.gcolor = GUN_PROPERTIES[name]['color']
        self.location = GUN_PROPERTIES[name]['location']

        # Function to go back in forth between polar and cartesian


def polar(x, y):
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    return r, theta


def cartesian(r, theta):
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return x, y


# function to read samples number and their position from the logbook
def read_samples(sample_list: list):
    samples = []
    for sample_obj in sample_list:
        label = str(sample_obj.relative_position)
        pos_x = sample_obj.position_x.to('mm').magnitude
        pos_y = sample_obj.position_y.to('mm').magnitude
        rotation = sample_obj.rotation.to('degree').magnitude
        width = sample_obj.substrate.geometry.width.to('mm').magnitude
        length = sample_obj.substrate.geometry.length.to('mm').magnitude
        sample = Sample(label, [pos_x, pos_y], rotation, [width, length])
        samples.append(sample)
    return samples


# Function to read the gun used from the logbook
def read_guns(gun_list: list, gun_names: str):
    guns = []
    for gun_obj, name in zip(gun_list, gun_names):
        if gun_obj is not None:
            if name in GUN_OVERVIEW_NAMES:
                if gun_obj.target_material is not None:
                    gun = Gun(name, gun_obj.target_material)
                    guns.append(gun)
            elif name == 's_cracker':
                gun = Gun(name, 'S')
                guns.append(gun)
    return guns


def plot_matplotlib_chamber_config(
    samples, guns, platen_angle, plot_platen_angle=False
):
    fig, ax = plt.subplots()

    # Define the shapes
    squares = [
        patches.Rectangle(
            (sample.pos_x_bl, sample.pos_y_bl),
            sample.width,
            sample.length,
            linewidth=DEFAULT_LINEWIDTH,
            edgecolor='g',
            facecolor='none',
        )
        for sample in samples
    ]

    arrowsX = [
        patches.FancyArrow(
            sample.pos_x_bl + sample.width / 10,
            sample.pos_y_bl + sample.length / 10,
            (sample.width + sample.length) / 8,
            0,
            width=1,
            head_width=3,
            head_length=3,
            color='red',
        )
        for sample in samples
    ]

    for arrow in arrowsX:
        ax.add_patch(arrow)

    arrowsY = [
        patches.FancyArrow(
            sample.pos_x_bl + sample.width / 10,
            sample.pos_y_bl + sample.length / 10,
            0,
            (sample.width + sample.length) / 8,
            width=1,
            head_width=3,
            head_length=3,
            color='blue',
        )
        for sample in samples
    ]

    for arrow in arrowsY:
        ax.add_patch(arrow)

    circles = [
        patches.Circle(
            (gun.pos_x, gun.pos_y),
            2,
            linewidth=DEFAULT_LINEWIDTH,
            edgecolor=gun.gcolor,
            facecolor=gun.gcolor,
        )
        for gun in guns
        if gun.pos_x is not None and gun.pos_y is not None
    ]

    circle_platen = patches.Circle(
        PLATEN_POS,
        PLATEN_DIAM,
        linewidth=DEFAULT_LINEWIDTH,
        edgecolor='black',
        facecolor='none',
    )

    circle_platen_center = patches.Circle(
        PLATEN_POS,
        PLATEN_CENTER_DIAM,
        linewidth=DEFAULT_LINEWIDTH,
        edgecolor='black',
        facecolor='black',
    )

    circle_middle_screw = patches.Circle(
        MIDDLE_SCREW_POS,
        MIDDLE_SCREW_DIAM,
        linewidth=DEFAULT_LINEWIDTH,
        edgecolor='black',
        facecolor='black',
    )

    # Create a transformation to rotate around the origin
    rotation_angle = platen_angle - 90
    rotation_transform = Affine2D().rotate_deg(rotation_angle)

    # Draw the shapes and rotate around the origin when necessary
    for square in squares:
        square.set_transform(rotation_transform + ax.transData)
        ax.add_patch(square)

    for arrow in arrowsX:
        arrow.set_transform(rotation_transform + ax.transData)
        ax.add_patch(arrow)

    for arrow in arrowsY:
        arrow.set_transform(rotation_transform + ax.transData)
        ax.add_patch(arrow)

    for circle in circles:
        ax.add_patch(circle)

    circle_middle_screw.set_transform(rotation_transform + ax.transData)
    ax.add_patch(circle_middle_screw)

    ax.add_patch(circle_platen_center)

    circle_platen.set_transform(rotation_transform + ax.transData)
    ax.add_patch(circle_platen)

    # Add text labels to samples (rotating with a)
    for sample in samples:
        rotated_edge = rotation_transform.transform(
            (
                sample.pos_x_bl + 0.8 * sample.width,
                sample.pos_y_bl + 0.8 * sample.length,
            )
        )
        rotated_arrowX_end = rotation_transform.transform(
            (
                sample.pos_x_bl + 0.55 * sample.width,
                sample.pos_y_bl + 0.15 * sample.length,
            )
        )
        rotated_arrowY_end = rotation_transform.transform(
            (
                sample.pos_x_bl + 0.15 * sample.width,
                sample.pos_y_bl + 0.55 * sample.length,
            )
        )
        ax.text(
            rotated_edge[0],
            rotated_edge[1],
            sample.label,
            ha='center',
            va='center',
            color='black',
            fontsize=DEFAULT_FONTSIZE,
        )
        # Add legend for X
        ax.text(
            rotated_arrowX_end[0],
            rotated_arrowX_end[1],
            'X',
            ha='center',
            va='center',
            color='red',
            fontsize=DEFAULT_FONTSIZE,
            weight='bold',
        )
        # Add legend for Y
        ax.text(
            rotated_arrowY_end[0],
            rotated_arrowY_end[1],
            'Y',
            ha='center',
            va='center',
            color='blue',
            fontsize=DEFAULT_FONTSIZE,
            weight='bold',
        )

    # Add text labels to sputter chamber modules (not rotating)
    for gun in guns:
        ax.text(
            cartesian(GUN_TO_PLATEN * PLATEN_DIAM, gun.location)[0],
            cartesian(GUN_TO_PLATEN * PLATEN_DIAM, gun.location)[1],
            f'{SOURCE_LABEL[gun.name]}\n({gun.mat})',
            ha='center',
            va='center',
            color=gun.gcolor,
            fontsize=DEFAULT_FONTSIZE,
        )

    ax.text(
        0,
        Y_LIM[1] - 10,
        'Glovebox Door',
        ha='center',
        va='center',
        color='black',
        fontsize=DEFAULT_FONTSIZE,
        weight='bold',
    )

    ax.text(
        0,
        Y_LIM[0] + 10,
        'Service Door',
        ha='center',
        va='center',
        color='black',
        fontsize=DEFAULT_FONTSIZE,
        weight='bold',
    )

    ax.text(
        cartesian((GUN_TO_PLATEN + 0.2) * PLATEN_DIAM, TOXIC_GAS_INLET_ANGLE)[0],
        cartesian((GUN_TO_PLATEN + 0.2) * PLATEN_DIAM, TOXIC_GAS_INLET_ANGLE)[1],
        'Toxic\nGas',
        ha='center',
        va='center',
        color='black',
        fontsize=DEFAULT_FONTSIZE,
        weight='bold',
    )

    # Add legend
    if plot_platen_angle:
        ax.legend(
            title=f'a={platen_angle}\u00b0', loc='upper left', fontsize=DEFAULT_FONTSIZE
        )

    # Remove axis lines and ticks
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Add a 50mm scale bar
    fontprops = fm.FontProperties(size=DEFAULT_FONTSIZE)
    scalebar = AnchoredSizeBar(
        ax.transData,
        50,
        '50 mm',
        'upper right',
        pad=0.1,
        color='black',
        frameon=False,
        size_vertical=1,
        fontproperties=fontprops,
    )

    ax.add_artist(scalebar)
    # Set limits and show the plot
    plt.xlim(X_LIM)
    plt.ylim(Y_LIM)
    ax.set_aspect('equal', adjustable='box')

    # make layout tight
    plt.tight_layout()

    return fig


# Rotation function
def rotate_point(x, y, angle_deg, platen_rot=True):
    if platen_rot:
        angle_rad = np.radians(angle_deg - 90)
    else:
        angle_rad = np.radians(angle_deg)
    x_rotated = x * np.cos(angle_rad) - y * np.sin(angle_rad)
    y_rotated = x * np.sin(angle_rad) + y * np.cos(angle_rad)
    return x_rotated, y_rotated


def plot_plotly_chamber_config(samples, guns, platen_angle, **kwargs):
    plot_platen_angle = kwargs.get('plot_platen_angle', True)
    plot_title = kwargs.get('plot_title', None)  # TODO add in_chamber
    in_chamber = kwargs.get('in_chamber', True)

    # define title
    if plot_title is not None:
        if plot_platen_angle:
            plot_title += f'Platen Angle={round(float(platen_angle), 1)}°'
    elif plot_platen_angle:
        plot_title = f'Platen Angle={round(float(platen_angle), 1)}°'

    # Create figure
    fig = go.Figure()
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        width=800,
        height=600,
        xaxis=dict(range=X_LIM, showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(
            range=Y_LIM,
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor='x',
            scaleratio=1,
        ),
        showlegend=False,
        title=plot_title,
    )

    # XY_PLOTTED = False

    # Add sample squares and arrows
    # Add sample rectangles and arrows
    for sample in samples:
        # Original rectangle coordinates
        x0, y0 = sample.pos_x_bl, sample.pos_y_bl
        width, length = sample.width, sample.length

        # Compute all four corners of the rectangle
        corners = [
            (x0, y0),
            (x0 + width, y0),
            (x0 + width, y0 + length),
            (x0, y0 + length),
        ]

        # rotate sample by sample.rotation around its center
        if sample.rotation != 0:
            center = [x0 + width / 2, y0 + length / 2]
            corners = [
                rotate_point(
                    x - center[0], y - center[1], sample.rotation, platen_rot=False
                )
                for x, y in corners
            ]
            corners = [(x + center[0], y + center[1]) for x, y in corners]

        # Rotate all corners
        rotated_corners = [rotate_point(x, y, platen_angle) for x, y in corners]

        # Create polygon shape for rotated rectangle
        fig.add_shape(
            type='path',
            path=f'M{rotated_corners[0][0]},{rotated_corners[0][1]} '
            + f'L{rotated_corners[1][0]},{rotated_corners[1][1]} '
            + f'L{rotated_corners[2][0]},{rotated_corners[2][1]} '
            + f'L{rotated_corners[3][0]},{rotated_corners[3][1]} Z',
            line=dict(color='green', width=DEFAULT_LINEWIDTH),
            fillcolor=None,
        )
        if sample.rotation == 0:
            # XY_PLOTTED = True

            # X arrow (aligned with rotated rectangle)
            arrow_x_start = x0 + width / 10
            arrow_x_end = arrow_x_start + width / 4
            x_arrow_points = [
                (arrow_x_start, y0 + length / 10),
                (arrow_x_end, y0 + length / 10),
            ]
            rotated_x_arrow = [
                rotate_point(x, y, platen_angle) for x, y in x_arrow_points
            ]

            fig.add_trace(
                go.Scatter(
                    x=[p[0] for p in rotated_x_arrow],
                    y=[p[1] for p in rotated_x_arrow],
                    mode='lines',
                    line=dict(color='red', width=2),
                    showlegend=False,
                )
            )

            # Y arrow (aligned with rotated rectangle)
            arrow_y_start = y0 + length / 10
            arrow_y_end = arrow_y_start + length / 4
            y_arrow_points = [
                (x0 + width / 10, arrow_y_start),
                (x0 + width / 10, arrow_y_end),
            ]
            rotated_y_arrow = [
                rotate_point(x, y, platen_angle) for x, y in y_arrow_points
            ]

            fig.add_trace(
                go.Scatter(
                    x=[p[0] for p in rotated_y_arrow],
                    y=[p[1] for p in rotated_y_arrow],
                    mode='lines',
                    line=dict(color='blue', width=2),
                    showlegend=False,
                )
            )
            # X and Y labels
            arrowX_label_x, arrowX_label_y = rotate_point(
                sample.pos_x_bl + 0.55 * width,
                sample.pos_y_bl + 0.15 * length,
                platen_angle,
            )
            arrowY_label_x, arrowY_label_y = rotate_point(
                sample.pos_x_bl + 0.15 * width,
                sample.pos_y_bl + 0.55 * length,
                platen_angle,
            )

            fig.add_annotation(
                x=arrowX_label_x,
                y=arrowX_label_y,
                text='X',
                showarrow=False,
                font=dict(color='red', size=DEFAULT_FONTSIZE + 4, family='Arial Black'),
            )
            fig.add_annotation(
                x=arrowY_label_x,
                y=arrowY_label_y,
                text='Y',
                showarrow=False,
                font=dict(
                    color='blue', size=DEFAULT_FONTSIZE + 4, family='Arial Black'
                ),
            )

        # Sample label
        label_x, label_y = rotate_point(
            sample.pos_x_bl + 0.5 * width,
            sample.pos_y_bl + 0.5 * length,
            platen_angle,
        )
        fig.add_annotation(
            x=label_x,
            y=label_y,
            text=sample.label,
            showarrow=False,
            font=dict(color='black', size=DEFAULT_FONTSIZE + 4),
        )

    # Platen and center
    platen_x, platen_y = rotate_point(PLATEN_POS[0], PLATEN_POS[1], platen_angle)
    fig.add_shape(
        type='circle',
        x0=platen_x - PLATEN_DIAM,
        y0=platen_y - PLATEN_DIAM,
        x1=platen_x + PLATEN_DIAM,
        y1=platen_y + PLATEN_DIAM,
        line=dict(color='black', width=DEFAULT_LINEWIDTH),
        fillcolor=None,
    )
    fig.add_trace(
        go.Scatter(
            x=[platen_x],
            y=[platen_y],
            mode='markers',
            marker=dict(color='black', size=2 * PLATEN_CENTER_DIAM),
        )
    )

    ## Middle screw
    # middle_screw_x, middle_screw_y = rotate_point(
    #    MIDDLE_SCREW_POS[0], MIDDLE_SCREW_POS[1], platen_angle
    # )
    # fig.add_trace(
    #    go.Scatter(
    #        x=[middle_screw_x],
    #        y=[middle_screw_y],
    #        mode='markers',
    #        marker=dict(color='black', size=2 * MIDDLE_SCREW_DIAM),
    #    )
    # )

    # Scale bar in top right
    fig.add_shape(
        type='line',
        x0=X_LIM[1] - 60,
        y0=Y_LIM[1] - 10,
        x1=X_LIM[1] - 10,
        y1=Y_LIM[1] - 10,
        line=dict(color='black', width=2),
    )
    fig.add_annotation(
        x=X_LIM[1] - 35,
        y=Y_LIM[1] - 15,
        text='50 mm',
        showarrow=False,
        font=dict(color='black', size=DEFAULT_FONTSIZE + 4),
    )

    if in_chamber:
        # Add guns
        for gun in guns:
            if gun.pos_x is not None and gun.pos_y is not None:
                fig.add_trace(
                    go.Scatter(
                        x=[gun.pos_x],
                        y=[gun.pos_y],
                        mode='markers',
                        marker=dict(
                            color=gun.gcolor,
                            size=4,
                            line=dict(color='black', width=DEFAULT_LINEWIDTH),
                        ),
                    )
                )

            # Gun label
            gun_label_pos = cartesian(GUN_TO_PLATEN * PLATEN_DIAM, gun.location)
            fig.add_annotation(
                x=gun_label_pos[0],
                y=gun_label_pos[1],
                text=f'{SOURCE_LABEL[gun.name]}<br>({gun.mat})',
                showarrow=False,
                font=dict(color=gun.gcolor, size=DEFAULT_FONTSIZE + 4),
            )

        # Additional text annotations
        fig.add_annotation(
            x=0,
            y=Y_LIM[1] - 10,
            text='Glovebox Door',
            showarrow=False,
            font=dict(color='black', size=DEFAULT_FONTSIZE + 4, family='Arial Black'),
        )
        fig.add_annotation(
            x=0,
            y=Y_LIM[0] + 10,
            text='Service Door',
            showarrow=False,
            font=dict(color='black', size=DEFAULT_FONTSIZE + 4, family='Arial Black'),
        )

        # Toxic gas inlet
        toxic_gas_pos = cartesian(
            (GUN_TO_PLATEN + 0.2) * PLATEN_DIAM, TOXIC_GAS_INLET_ANGLE
        )
        fig.add_annotation(
            x=toxic_gas_pos[0],
            y=toxic_gas_pos[1],
            text='Toxic<br>Gas',
            showarrow=False,
            font=dict(color='black', size=DEFAULT_FONTSIZE + 4, family='Arial Black'),
        )

    return fig


def explore_log_files(
    samples_dir,
    logfiles_extension=LOGFILES_EXTENSION,
    spectra_extension=SPECTRA_EXTENSION,
):
    logfiles = {'name': [], 'folder': [], 'spectra': []}

    # In samples_dir, explore all the folders (samples names)
    for folder in os.listdir(samples_dir):
        logfile_path = os.path.join(samples_dir, folder, 'log_files')
        spectra_path = os.path.join(samples_dir, folder, 'optix_spectra')

        # Check if the logfile_path exists and is a directory
        if os.path.isdir(logfile_path):
            # Iterate over files in the logfile_path directory
            for file in os.listdir(logfile_path):
                if re.match(r'^\w+\d{4}\w+', file) and file.endswith(
                    f'.{logfiles_extension}'
                ):
                    logfile_name = re.sub(rf'\.{logfiles_extension}$', '', file)
                    spectra_file_path = check_for_spectra(
                        spectra_path, spectra_extension
                    )
                    if TEST_SPECIFIC_LOGFILE:
                        if logfile_name in SAMPLES_TO_TEST:
                            logfiles['name'].append(logfile_name)
                            logfiles['folder'].append(logfile_path)
                            logfiles['spectra'].append(spectra_file_path)
                    elif not TEST_SPECIFIC_LOGFILE:
                        if REMOVE_SAMPLES and (logfile_name not in SAMPLES_TO_REMOVE):
                            logfiles['name'].append(logfile_name)
                            logfiles['folder'].append(logfile_path)
                            logfiles['spectra'].append(spectra_file_path)
                        elif not REMOVE_SAMPLES:
                            logfiles['name'].append(logfile_name)
                            logfiles['folder'].append(logfile_path)
                            logfiles['spectra'].append(spectra_file_path)
    print(logfiles['name'])
    return logfiles


def check_for_spectra(spectra_path, spectra_extension):
    # Check if the spectra_path exists and is a directory
    if os.path.isdir(spectra_path):
        # Iterate over files in the spectra_path directory
        for file in os.listdir(spectra_path):
            if (
                re.match(r'^\w+\d{4}\w+', file)
                and file.endswith(f'.{spectra_extension}')
                and 'RGA' not in file
            ):
                return os.path.join(spectra_path, file)
    return None


# ---------------MAIN-----------


def main():
    # global events_to_plot, main_params, step_params, all_params
    samples_dir = r'Z:\P110143-phosphosulfides-Andrea\Data\Samples'

    # Initialize the the general param dictionary
    all_params = {}

    logfiles = explore_log_files(samples_dir)

    # Loop over all the logfiles in the directory
    for i in range(len(logfiles['name'])):
        # Default Logfile location
        print('\n')
        print(f'Processing logfile {logfiles["name"][i]}.CSV')
        logfile_path = (
            f'{logfiles["folder"][i]}/{logfiles["name"][i]}.{LOGFILES_EXTENSION}'
        )

        # ---------DEFAULT EXPORT LOCATIONS-------------
        # Specify the path and filename for the report text file

        (
            txt_file_path,
            step_file_path,
            timeline_file_path,
            bias_file_path,
            overview_file_path,
            optix_file_path,
            chamber_file_path,
        ) = build_file_paths(logfiles, i)
        # ---------READ THE DATA-------------

        # Read the log file and spectrum data
        print('Extracting all the events from the logfile')
        data = read_logfile(logfile_path)

        # ----READ ALL THE EVENTS IN THE LOGFILE----
        events_to_plot, main_params, step_params = read_events(data)

        # ---APPEND THE MAIN PARAMS TO THE ALL PARAMS DICTIONARY---
        sample_key = '_'.join(str(logfiles['name'][i]).split('_')[0:3])
        all_params[sample_key] = main_params

        # --------GRAPH THE DIFFERENT STEPS ON A TIME LINE------------

        # Create the figure
        print('Generating the plotly plots')
        plotly_timeline = generate_timeline(events_to_plot, logfiles['name'][i])

        if PRINT_FIGURES:
            plotly_timeline.show(config=PLOTLY_CONFIG)

        # Save the image as an interactive html file
        plotly_timeline.write_html(timeline_file_path)

        # --------GRAPH THE DC BIAS AS A FUNCTION OF TIME------------

        bias_plot = generate_bias_plot(events_to_plot, logfiles['name'][i])

        if PRINT_FIGURES:
            bias_plot.show(config=PLOTLY_CONFIG)

        bias_plot.write_html(bias_file_path)

        # --------GRAPH THE OVERVIEW PLOT----------------

        overview_plot = generate_overview_plot(
            data, logfiles['name'][i], events_to_plot
        )

        if PRINT_FIGURES:
            overview_plot.show(config=PLOTLY_CONFIG)

        overview_plot.write_html(overview_file_path)

        # ------GRAPH THE OPTIX SPECTRA PLOT------------

        if logfiles['spectra'][i] is not None:
            spectra = read_spectrum(logfiles['spectra'][i])
            optix_plot = generate_optix_plot(
                spectra,
                events_to_plot,
                logfiles['name'][i],
            )

            if PRINT_FIGURES:
                optix_plot.show(config=PLOTLY_CONFIG)

            optix_plot.write_html(optix_file_path)

        # -----GRAPH THE CHAMBER CONFIG---

        if 'platen_position' in main_params['deposition']:
            plolty_chamber_plot, plotly_moutning_plot = plot_logfile_chamber(
                main_params, logfiles['name'][i]
            )

            plolty_chamber_plot.write_html(chamber_file_path.replace('.png', '.html'))

            plotly_moutning_plot.write_html(
                chamber_file_path.replace('.png', '_moutning.html')
            )

        # --------PRINT DERIVED QUANTITIES REPORTS-------------

        if PRINT_MAIN_PARAMS:
            print(f'Derived quantities report for logfile\n{logfiles["name"][i]}:\n')
            print_params(main_params)

        if PRINT_STEP_PARAMS:
            print(f'Step report for logfile\n{logfiles["name"][i]}:\n')
            print_params(step_params)

        # ---SAVE THE REPORT QUANTITIES IN A TEXT FILE---

        print('Saving the derived quantities report as a text file')
        save_report_as_text(main_params, txt_file_path, logfiles['name'][i])

        # --SAVE THE STEP REPORT QUANTITIES IN A TEXT FILE
        if SAVE_STEP_PARAMS:
            save_report_as_text(step_params, step_file_path, logfiles['name'][i])

    # ----CONSILIDATE THE DATA INTO A SINGLE CSV FILE-----

    print('Consolidating the data into a single CSV file')
    consolidate_data_to_csv(all_params, samples_dir, process_NaN=True)

    print('Processing done')


if __name__ == '__main__':
    main()
