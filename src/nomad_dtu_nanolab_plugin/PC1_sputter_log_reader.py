import os
import pandas as pd
import tkinter as tk
from tkinter import filedialog

# -----USEFUL DICTIONARIES AND LISTS-----

# column names dictionary
COL = {
    'time': 'Time Stamp',
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
    # "n2_flow": "PC MFC 2 Flow",  # Need to check
    # "n2_sp": "PC MFC 2 Setpoint",  # Need to check
    'mfc3_flow': 'PC MFC 3 Flow',
    'mfc3_sp': 'PC MFC 3 Setpoint',
    # "o2_flow": "PC MFC 3 Flow",   # Need to check
    # "o2_sp": "PC MFC 3 Setpoint",   # Need to check
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
    'sul_crk_zone1_en': 'Sulfur Cracker Zone 1 Enabled',
    'sul_crk_zone1_sp': 'Sulfur Cracker Zone 1 Temperature Setpoint',
    'sul_crk_zone2_temp': 'Sulfur Cracker Zone 2 Current Temperature',
    'sul_crk_zone2_en': 'Sulfur Cracker Zone 2 Enabled',
    'sul_crk_zone2_sp': 'Sulfur Cracker Zone 2 Temperature Setpoint',
    'sul_crk_zone3_temp': 'Sulfur Cracker Zone 3 Current Temperature',
    'sul_crk_zone3_en': 'Sulfur Cracker Zone 3 Enabled',
    'sul_crk_zone3_sp': 'Sulfur Cracker Zone 3 Temperature Setpoint',
    'sul_crk_lambda': 'Sulfur Cracker Control Sensor Value',
    'sul_crk_ctrl_en': 'Sulfur Cracker Control Enabled',
    'sul_crk_ctrl_mode': 'Sulfur Cracker Control Mode',
    'sul_crk_ctrl_sensor': 'Sulfur Cracker Control Sensor Value',
    'sul_crk_ctrl_sp': 'Sulfur Cracker Control Setpoint',
    'sul_crk_ctrl_fb': 'Sulfur Cracker Control Setpoint Feedback',
    'sul_crk_valve_freq_sp': 'Sulfur Cracker Control Valve InitFrequency Setpoint',
    'sul_crk_valve_pw_sp': 'Sulfur Cracker Control Valve PulseWidth Setpoint',
    'sul_crk_valve_pw_fb': 'Sulfur Cracker Control Valve PulseWidth Setpoint Feedback',
    'sul_crk_valve_sp': 'Sulfur Cracker Control Valve Setpoint',
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