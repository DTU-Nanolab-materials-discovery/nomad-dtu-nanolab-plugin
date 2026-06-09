import numpy as np
import pandas as pd

from nomad_dtu_nanolab_plugin.rtp_log_reader import (
    MIN_USED_GAS_FLOW_M3_S,
    _ensure_deps,
    _extract_steps,
    parse_rtp_logfiles,
)

EKLIPSE_LOG = 'tests/data/indiogo_0019_RTP_Recording Set 2025.11.28-13.32.19.CSV'
T2B_LOG = 'tests/data/indiogo_0019_RTP_LOGFILE20251128140851 (1).txt'
SYNTHETIC_TRACE_DURATION_S = 90.0
HEATING_END_TIME_S = 30.0
DWELL_END_TIME_S = 60.0
TIME_STEP_S = 1.0
EXPECTED_SYNTHETIC_STEP_COUNT = 3
MIN_POSITIVE_TEMPERATURE_K = 273.15
EXPECTED_OVERVIEW_KEYS = {
    'annealing_pressure',
    'annealing_time',
    'annealing_temperature',
    'annealing_ar_flow',
    'annealing_n2_flow',
    'annealing_ph3_in_ar_flow',
    'annealing_nh3_in_ar_flow',
    'annealing_h2s_in_ar_flow',
    'total_heating_time',
    'total_cooling_time',
    'end_of_process_temperature',
}


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _assert_step_shape(step):
    assert isinstance(step.name, str)
    assert step.name
    assert _is_number(step.duration_s)
    assert step.duration_s >= 0
    assert _is_number(step.initial_temperature_k)
    assert _is_number(step.final_temperature_k)
    assert step.initial_temperature_k > 0
    assert step.final_temperature_k > 0

    for flow in (
        step.ar_flow_m3_s,
        step.n2_flow_m3_s,
        step.ph3_in_ar_flow_m3_s,
        step.nh3_in_ar_flow_m3_s,
        step.h2s_in_ar_flow_m3_s,
    ):
        assert _is_number(flow)
        assert flow >= 0

    if step.start_time_s is not None and step.end_time_s is not None:
        assert step.start_time_s <= step.end_time_s
        assert step.duration_s <= (step.end_time_s - step.start_time_s) + 1e-6


def _assert_overview_shape(overview):
    assert set(overview.keys()) == EXPECTED_OVERVIEW_KEYS

    for key, value in overview.items():
        if value is not None:
            assert _is_number(value), f'Overview key {key} must be numeric or None'


def test_parse_rtp_logfiles():
    parsed = parse_rtp_logfiles(EKLIPSE_LOG, T2B_LOG)

    assert isinstance(parsed.steps, list)
    assert parsed.steps
    _assert_overview_shape(parsed.overview)

    assert parsed.overview['annealing_temperature'] is not None
    assert parsed.overview['annealing_temperature'] > MIN_POSITIVE_TEMPERATURE_K
    assert parsed.overview['annealing_time'] is not None
    assert parsed.overview['annealing_time'] >= 0

    for step in parsed.steps:
        _assert_step_shape(step)

    # Step time windows should be ordered and non-overlapping if present.
    timed_steps = [
        step
        for step in parsed.steps
        if step.start_time_s is not None and step.end_time_s is not None
    ]
    for prev, curr in zip(timed_steps, timed_steps[1:]):
        assert prev.end_time_s <= curr.start_time_s

    # Timeseries channels should be aligned and contain data.
    assert isinstance(parsed.timeseries, dict)
    assert parsed.timeseries
    channel_lengths = [len(values) for values in parsed.timeseries.values()]
    assert all(length > 0 for length in channel_lengths)
    assert len(set(channel_lengths)) == 1

    # Used gases must correspond to a positive annealing flow above threshold.
    anneal_flow_by_gas = {
        'Ar': parsed.overview['annealing_ar_flow'],
        'N2': parsed.overview['annealing_n2_flow'],
        'PH3': parsed.overview['annealing_ph3_in_ar_flow'],
        'NH3': parsed.overview['annealing_nh3_in_ar_flow'],
        'H2S': parsed.overview['annealing_h2s_in_ar_flow'],
    }
    for gas in parsed.used_gases:
        assert gas in anneal_flow_by_gas
        flow = anneal_flow_by_gas[gas]
        assert flow is not None
        assert flow > MIN_USED_GAS_FLOW_M3_S

    assert parsed.base_pressure_pa is None or parsed.base_pressure_pa >= 0
    assert (
        parsed.base_pressure_ballast_pa is None or parsed.base_pressure_ballast_pa >= 0
    )


def test_extract_steps_does_not_split_on_small_slope_wiggles():
    assert _ensure_deps()

    time_s = np.arange(0.0, SYNTHETIC_TRACE_DURATION_S, TIME_STEP_S)
    temperature_k = np.empty_like(time_s)

    heating_mask = time_s < HEATING_END_TIME_S
    dwell_mask = (time_s >= HEATING_END_TIME_S) & (time_s < DWELL_END_TIME_S)
    cooling_mask = time_s >= DWELL_END_TIME_S

    heating_t = time_s[heating_mask]
    dwell_t = time_s[dwell_mask] - HEATING_END_TIME_S
    cooling_t = time_s[cooling_mask] - DWELL_END_TIME_S

    temperature_k[heating_mask] = (
        300.0 + 0.8 * heating_t + 1.2 * np.sin(2.0 * np.pi * heating_t / 3.0)
    )
    temperature_k[dwell_mask] = 324.0 + 0.2 * np.sin(2.0 * np.pi * dwell_t / 4.0)
    temperature_k[cooling_mask] = (
        324.0 - 0.8 * cooling_t + 1.2 * np.sin(2.0 * np.pi * cooling_t / 3.0)
    )

    process_df = pd.DataFrame(
        {
            'time_s': time_s,
            'temperature_k': temperature_k,
        }
    )

    steps = _extract_steps(process_df)

    assert len(steps) == EXPECTED_SYNTHETIC_STEP_COUNT
    assert [step.name for step in steps] == ['Heating', 'Annealing', 'Cooling']
