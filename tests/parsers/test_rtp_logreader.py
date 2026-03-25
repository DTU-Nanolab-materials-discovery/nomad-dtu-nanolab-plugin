from nomad_dtu_nanolab_plugin.rtp_log_reader import (
    MIN_USED_GAS_FLOW_M3_S,
    parse_rtp_logfiles,
)

EKLIPSE_LOG = 'tests/data/indiogo_0019_RTP_Recording Set 2025.11.28-13.32.19.CSV'
T2B_LOG = 'tests/data/indiogo_0019_RTP_LOGFILE20251128140851 (1).txt'
MIN_POSITIVE_TEMPERATURE_K = 273.15
EXPECTED_OVERVIEW_KEYS = {
    'annealing_pressure',
    'annealing_time',
    'annealing_temperature',
    'annealing_ar_flow',
    'annealing_n2_flow',
    'annealing_ph3_in_ar_flow',
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
