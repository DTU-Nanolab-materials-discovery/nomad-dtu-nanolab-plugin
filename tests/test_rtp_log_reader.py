# ruff: noqa: PLR2004

import logging

import numpy as np
import pandas as pd
import pytest

from nomad_dtu_nanolab_plugin import rtp_log_reader as reader


@pytest.fixture(autouse=True)
def load_parser_dependencies():
    reader.np = np
    reader.pd = pd


def test_normalize_and_extract_trendlog_column_names():
    assert reader._normalize('Process Value - CH1') == 'processvaluech1'

    columns = reader._extract_trendlog_column_names(
        ['Fixed SP - CH1;Process Value - CH1;Set Point - CH1']
    )
    assert columns == [
        'Fixed SP - CH1',
        'Process Value - CH1',
        'Set Point - CH1',
    ]


def test_parse_trendlog_table_ignores_non_data_and_maps_columns():
    frame = reader._parse_trendlog_table(
        [
            'Process Value - CH1 Set Point - CH1',
            'not a timestamp 1 2',
            '2024/01/02_03:04:05 1250 -',
            '2024/01/02_03:04:06 1300 1400',
        ]
    )

    assert frame.to_dict('records') == [
        {
            'Timestamp': '2024/01/02_03:04:06',
            'Process Value - CH1': 1300.0,
            'Set Point - CH1': 1400.0,
        }
    ]


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('Base Pressure: 0.02 Torr', {'basepressure': 0.02 * reader.TORR_TO_PA}),
        ('Lamp power = -3.5 W', {'lamppower': -3.5}),
        ('unstructured text', {}),
    ],
)
def test_extract_key_values_normalizes_and_converts_pressure(text, expected):
    assert reader._extract_key_values(text) == pytest.approx(expected)


def test_parse_cx_thermo_table_supports_semicolon_csv_and_trendlog():
    csv_frame = reader._parse_cx_thermo_table(
        'metadata\nTimestamp;Process Value - CH1\n2024/01/02_03:04:05;850\n'
    )
    assert csv_frame.iloc[0]['Process Value - CH1'] == 850

    trend_frame = reader._parse_cx_thermo_table(
        'Process Value - CH1 Set Point - CH1\n2024/01/02_03:04:05 850 900\n'
    )
    assert trend_frame.iloc[0]['Process Value - CH1'] == 850


def test_datetime_parser_falls_back_to_elapsed_time():
    result = reader._to_datetime(pd.Series(['00:00:02', '00:00:05']))
    assert (result.iloc[1] - result.iloc[0]).total_seconds() == 3


def test_pressure_and_flow_conversion_boundaries():
    assert reader._pressure_to_pa(None) is None
    assert reader._pressure_to_pa(float('nan')) is None
    assert reader._pressure_to_pa(2) == pytest.approx(2 * reader.TORR_TO_PA)

    threshold = reader.MIN_USED_GAS_FLOW_M3_S
    assert reader._apply_parasitic_flow_cutoff(threshold / 2, 'Ar') == 0
    assert reader._apply_parasitic_flow_cutoff(-threshold / 2, 'N2') == 0
    assert reader._apply_parasitic_flow_cutoff(threshold, 'Ar') == threshold


def test_mark_disregarded_samples_only_marks_virtual_temperatures_in_window():
    frame = pd.DataFrame(
        {
            'temperature_k': [reader.VIRTUAL_TEMPERATURE_SETPOINT_C + 273.15] * 3,
            'timestamp': pd.date_range('2024-01-01', periods=3, freq='s'),
            'time_s': [0, 1, 2],
        }
    )

    found = reader._mark_disregarded_samples(
        frame,
        cooling_start_timestamp=frame['timestamp'].iloc[1],
        cooling_end_timestamp=frame['timestamp'].iloc[2],
    )

    assert found
    assert frame['is_disregarded'].tolist() == [False, True, True]


def test_extract_timeseries_converts_pressure_and_preserves_missing_values():
    frame = pd.DataFrame(
        {
            'time_s': [0, 1],
            'temperature_k': [300, np.nan],
            'pressure_raw': [1, np.nan],
            'ar_flow_m3_s': [1e-6, np.nan],
        }
    )

    result = reader._extract_timeseries(frame)

    assert result['time_s'] == [0.0, 1.0]
    assert result['temperature_k'][0] == 300
    assert np.isnan(result['temperature_k'][1])
    assert result['pressure_pa'][0] == pytest.approx(reader.TORR_TO_PA)
    assert np.isnan(result['pressure_pa'][1])
    assert result['ar_flow_m3_s'][0] == 1e-6
    assert result['n2_flow_m3_s'] == []


def test_extract_timeseries_empty_and_missing_time_inputs():
    assert reader._extract_timeseries(pd.DataFrame()) == {}

    result = reader._extract_timeseries(pd.DataFrame({'temperature_k': [300]}))
    assert result['time_s'] == []
    assert result['temperature_k'] == []


def test_gas_shutoff_uses_any_flow_and_returns_first_all_off_sample():
    flows = {
        column: [0.0, 0.0, 0.0]
        for column in (
            'ar_flow_m3_s',
            'n2_flow_m3_s',
            'ph3_in_ar_flow_m3_s',
            'nh3_in_ar_flow_m3_s',
            'h2s_in_ar_flow_m3_s',
        )
    }
    flows['n2_flow_m3_s'] = [0, 2 * reader.MIN_USED_GAS_FLOW_M3_S, 0]
    frame = pd.DataFrame({'time_s': [0, 5, 9], **flows})

    assert reader._find_gas_shutoff_time(frame) == 9
    assert reader._find_gas_shutoff_time(frame.iloc[:2]) is None
    assert reader._find_gas_shutoff_time(pd.DataFrame()) is None


def test_cooling_activation_helpers_find_transitions_and_handle_missing_data():
    frame = pd.DataFrame(
        {
            'time_s': [0, 2, 4],
            'vent_line': [0, 1, 1],
            'throttle_closed': [1, 0, 1],
            'ar_flow_setpoint_m3_s': [2e-6, 2e-6, 0],
            'n2_flow_setpoint_m3_s': [0, 0, 0],
            'ph3_in_ar_flow_setpoint_m3_s': [0, 0, 0],
            'nh3_in_ar_flow_setpoint_m3_s': [0, 0, 0],
            'h2s_in_ar_flow_setpoint_m3_s': [0, 0, 0],
        }
    )

    assert reader._find_cooling_vent_activation_time(frame) == 4
    assert reader._find_setpoint_pre_drop_time(frame) == 2
    assert reader._find_cooling_vent_activation_time(frame[['time_s']]) is None
    assert reader._find_setpoint_pre_drop_time(frame.iloc[:0]) is None


def test_temperature_smoothing_and_slope_classification_cover_nan_edges():
    smoothed = reader._smooth_temperature(np.array([1.0, np.nan, 3.0]), half_window=1)
    assert smoothed == pytest.approx([1.0, 2.0, 3.0])
    assert reader._classify_slope(reader.DWELL_SLOPE_THRESHOLD_K_S) == 'Dwell'
    assert reader._classify_slope(0.1) == 'Heating'
    assert reader._classify_slope(-0.1) == 'Cooling'


def test_segment_ordinals_and_annealing_step_selection():
    assert reader._segment_label_ordinals(['Cooling', 'Heating', 'Cooling']) == [
        'Cooling',
        'Heating',
        'Cooling 2',
    ]
    steps = [
        reader.ParsedRTPStep('1st Dwell', 1, 300, 300, None, 0, 0, 0, 0, 0, 350),
        reader.ParsedRTPStep('Annealing', 1, 900, 900, None, 0, 0, 0, 0, 0, 900),
    ]
    assert reader._main_annealing_step_index(steps) == 1
    assert reader._has_detected_annealing_step(steps)
    assert not reader._is_dwell_like_name('Heating')


def test_merge_short_segments_absorbs_edge_noise_into_neighbor():
    labels, boundaries = reader._merge_short_segments(
        ['Dwell', 'Heating', 'Cooling'],
        [0, 1, 5],
        np.arange(10, dtype=float),
        min_duration_s=3,
        min_points=3,
    )

    assert labels == ['Heating', 'Cooling']
    assert boundaries == [1, 5]


def test_extract_steps_falls_back_to_single_step_for_flat_trace():
    frame = pd.DataFrame(
        {
            'time_s': [0, 1, 2, 3],
            'temperature_k': [300.0] * 4,
            'pressure_raw': [1.0] * 4,
            'ar_flow_m3_s': [2 * reader.MIN_USED_GAS_FLOW_M3_S] * 4,
        }
    )

    steps = reader._extract_steps(frame)

    assert len(steps) == 1
    assert steps[0].name == 'Annealing'
    assert steps[0].duration_s == 3
    assert steps[0].pressure_pa == pytest.approx(reader.TORR_TO_PA)
    assert steps[0].ar_flow_m3_s == 2 * reader.MIN_USED_GAS_FLOW_M3_S
    assert reader._has_detected_annealing_step(steps)


def test_extract_steps_identifies_heating_annealing_and_cooling_phases():
    time_s = np.arange(240, dtype=float)
    temperature_k = np.concatenate(
        [
            np.linspace(300, 900, 60),
            np.full(120, 900.0),
            np.linspace(900, 296.65, 60),
        ]
    )
    frame = pd.DataFrame({'time_s': time_s, 'temperature_k': temperature_k})

    steps = reader._extract_steps(frame)

    assert [step.name for step in steps] == ['Heating', 'Annealing', 'Cooling']
    assert steps[0].duration_s > 0
    assert steps[1].mean_temperature_k == pytest.approx(900)
    assert steps[2].duration_s > 0
    assert reader._has_detected_annealing_step(steps)


def test_build_parsed_cooling_step_limits_flows_and_pressure_at_setpoint_drop():
    frame = pd.DataFrame(
        {
            'time_s': [0, 1, 2, 3],
            'temperature_k': [700, 600, 500, 400],
            'pressure_raw': [1, 2, 3, 4],
            'ar_flow_m3_s': [2e-6, 2e-6, 0, 0],
            'n2_flow_m3_s': [0, 0, 0, 0],
            'ph3_in_ar_flow_m3_s': [0, 0, 0, 0],
            'nh3_in_ar_flow_m3_s': [0, 0, 0, 0],
            'h2s_in_ar_flow_m3_s': [0, 0, 0, 0],
            'ar_flow_setpoint_m3_s': [2e-6, 2e-6, 0, 0],
            'n2_flow_setpoint_m3_s': [0, 0, 0, 0],
            'ph3_in_ar_flow_setpoint_m3_s': [0, 0, 0, 0],
            'nh3_in_ar_flow_setpoint_m3_s': [0, 0, 0, 0],
            'h2s_in_ar_flow_setpoint_m3_s': [0, 0, 0, 0],
            'vent_line': [0, 0, 0, 1],
            'throttle_closed': [0, 0, 0, 1],
        }
    )

    step = reader._build_parsed_step(frame, 0, 4, 'Cooling', 'Cooling')

    assert step.duration_s == 3
    assert step.pressure_pa == pytest.approx(1.5 * reader.TORR_TO_PA)
    assert step.ar_flow_m3_s == 2e-6


def test_derive_overview_and_step_duration_totals():
    steps = [
        reader.ParsedRTPStep('Heating', 4, 300, 800, None, 1e-6, 0, 0, 0, 0),
        reader.ParsedRTPStep(
            'Annealing', 10, 800, 900, 12, 2e-6, 3e-6, 0, 0, 0, mean_temperature_k=850
        ),
        reader.ParsedRTPStep('Cooling 2', 6, 900, 300, None, 0, 0, 0, 0, 0),
    ]

    overview = reader._derive_overview(steps)

    assert overview['annealing_pressure'] == 12
    assert overview['annealing_time'] == 10
    assert overview['annealing_temperature'] == 850
    assert overview['annealing_ar_flow'] == 2e-6
    assert overview['total_heating_time'] == 4
    assert overview['total_cooling_time'] == 6
    assert reader._derive_total_heating_cooling_times(steps) == (4, 6)
    assert reader._derive_overview([])['annealing_time'] is None


def test_derive_end_temperature_uses_last_gas_shutoff_transition():
    frame = pd.DataFrame(
        {
            'time_s': [0, 1, 2, 3, 4],
            'temperature_k': [500, 600, 700, 800, 900],
            'ar_flow_m3_s': [2e-6, 0, 2e-6, 0, 0],
            'n2_flow_m3_s': [0] * 5,
            'ph3_in_ar_flow_m3_s': [0] * 5,
            'nh3_in_ar_flow_m3_s': [0] * 5,
            'h2s_in_ar_flow_m3_s': [0] * 5,
        }
    )

    assert reader._derive_end_of_process_temperature(frame, []) == 800
    assert reader._derive_end_of_process_temperature(pd.DataFrame(), []) is None


def test_ballast_pressure_windows_and_static_vacuum_runs():
    frame = pd.DataFrame(
        {'ballast': [0, 0, 1, 1, 1, 0], 'vent_line': [0, 0, 0, 0, 0, 1]}
    )
    base, ballast = reader._derive_ballast_pressures(
        frame, np.array([5.0, 3.0, 8.0, 10.0, 12.0, 50.0])
    )
    assert base == 3
    assert ballast == pytest.approx(10)

    runs = reader._static_vacuum_runs(np.array([True] * 10 + [False] + [True] * 9))
    assert [run.tolist() for run in runs] == [list(range(10))]


def test_rate_of_rise_rejects_invalid_windows_and_computes_valid_slope():
    times = np.arange(4, dtype=float)
    pressures = np.array([1.0, 2.0, 5.0, 8.0])
    assert (
        reader._compute_rate_of_rise(
            times, pressures, np.array([True, True, False, False])
        )
        == 1
    )
    assert (
        reader._compute_rate_of_rise(
            times, pressures, np.array([True, False, False, False])
        )
        is None
    )
    assert reader._compute_rate_of_rise(
        times, pressures, np.array([True, True, False, True])
    ) == pytest.approx(7 / 3)


def test_derive_rate_of_rise_uses_settled_static_window_and_warns_on_missing_columns():
    count = 12
    frame = pd.DataFrame(
        {
            'time_s': np.arange(count, dtype=float),
            'vent_line': 0,
            'throttle_closed': 1,
            'throttle_open': 0,
            'throttle_position': [0, 0, 10] + [0] * (count - 3),
            'ballast': 0,
            **{column: 0.0 for column in reader._RATE_OF_RISE_REQUIRED_COLUMNS},
        }
    )
    pressure = np.linspace(0.1, 0.21, count)
    warnings = []

    rate = reader._derive_rate_of_rise(
        frame, pressure, warnings.append, logging.getLogger()
    )

    assert rate == pytest.approx((pressure[-1] - pressure[3]) / (count - 1 - 3))
    assert any('window selected' in warning for warning in warnings)

    warnings.clear()
    assert (
        reader._derive_rate_of_rise(frame[['time_s']], pressure, warnings.append, None)
        is None
    )
    assert any('missing required column' in warning for warning in warnings)


def test_detect_used_gases_prefers_highest_temperature_dwell():
    heating = reader.ParsedRTPStep('Heating', 1, 300, 700, None, 2e-6, 0, 0, 0, 0)
    low_dwell = reader.ParsedRTPStep(
        'Dwell', 1, 700, 700, None, 0, 3e-6, 0, 0, 0, mean_temperature_k=700
    )
    high_dwell = reader.ParsedRTPStep(
        'Annealing', 1, 900, 900, None, 0, 0, 0, 4e-6, 0, mean_temperature_k=900
    )

    assert reader._detect_used_gases([heating, low_dwell, high_dwell], {}) == ['NH3']
    assert reader._detect_used_gases([], {}) == []
