import os.path

import pytest
from nomad.client import normalize_all, parse

from nomad_dtu_nanolab_plugin.rtp_log_reader import (
    MIN_USED_GAS_FLOW_M3_S,
    ParsedRTPStep,
    _apply_parasitic_flow_cutoff,
    _derive_overview,
    _read_csv_with_fallback,
)

MIN_EXPECTED_STEPS = 2
EXPECTED_QUOTED_CSV_ROWS = 2


def test_rtp_logreader_populates_process_data():
    test_file = os.path.join('tests', 'data', 'test_rtp_logreader.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    data = entry_archive.data

    assert data.overview is not None
    assert len(data.steps) >= MIN_EXPECTED_STEPS
    assert data.overview.annealing_temperature is not None
    assert data.overview.annealing_pressure is not None
    assert data.overview.annealing_time is not None

    assert data.steps[0].step_overview.temperature_ramp is not None
    assert data.steps[0].step_overview.step_ph3_partial_pressure is not None
    assert data.steps[0].step_overview.step_h2s_partial_pressure is not None

    assert data.used_gases is not None
    assert 'PH3' in data.used_gases
    assert 'H2S' in data.used_gases

    # 11 l/min from diagnostics log.
    assert data.chiller_flow.magnitude == pytest.approx(11e-3 / 60)

    # 1.1 torr from diagnostics log.
    assert data.base_pressure.to('torr').magnitude == pytest.approx(1.1, abs=1e-3)


def test_read_csv_with_fallback_keeps_quoted_fields(tmp_path):
    csv_file = tmp_path / 'quoted_eklipse.csv'
    csv_file.write_text(
        'timestamp;comment;value\n'
        '2026-03-09 10:00:00;"note with ; semicolon";1\n'
        '2026-03-09 10:00:01;"note with , comma";2\n',
        encoding='utf-8',
    )

    df = _read_csv_with_fallback(str(csv_file))

    assert list(df.columns) == ['timestamp', 'comment', 'value']
    assert len(df) == EXPECTED_QUOTED_CSV_ROWS
    assert df.iloc[0]['comment'] == 'note with ; semicolon'
    assert df.iloc[1]['comment'] == 'note with , comma'


def test_derive_overview_uses_identified_annealing_step_values():
    steps = [
        ParsedRTPStep(
            name='Heating',
            duration_s=100.0,
            initial_temperature_k=300.0,
            final_temperature_k=900.0,
            pressure_pa=1000.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
        ParsedRTPStep(
            name='Annealing',
            duration_s=15.0,
            initial_temperature_k=950.0,
            final_temperature_k=950.0,
            pressure_pa=2100.0,
            ar_flow_m3_s=11.0,
            n2_flow_m3_s=12.0,
            ph3_in_ar_flow_m3_s=13.0,
            h2s_in_ar_flow_m3_s=14.0,
        ),
        ParsedRTPStep(
            name='Cooling',
            duration_s=25.0,
            initial_temperature_k=950.0,
            final_temperature_k=450.0,
            pressure_pa=1200.0,
            ar_flow_m3_s=2.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
    ]

    overview = _derive_overview(steps)

    assert overview['annealing_time'] == pytest.approx(15.0)
    assert overview['annealing_temperature'] == pytest.approx(950.0)
    assert overview['annealing_pressure'] == pytest.approx(2100.0)
    assert overview['annealing_ar_flow'] == pytest.approx(11.0)
    assert overview['annealing_n2_flow'] == pytest.approx(12.0)
    assert overview['annealing_ph3_in_ar_flow'] == pytest.approx(13.0)
    assert overview['annealing_h2s_in_ar_flow'] == pytest.approx(14.0)


def test_derive_overview_uses_annealing_mean_temperature_when_available():
    steps = [
        ParsedRTPStep(
            name='Heating',
            duration_s=10.0,
            initial_temperature_k=300.0,
            final_temperature_k=700.0,
            pressure_pa=1000.0,
            ar_flow_m3_s=0.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
            mean_temperature_k=500.0,
        ),
        ParsedRTPStep(
            name='Annealing',
            duration_s=20.0,
            initial_temperature_k=900.0,
            final_temperature_k=1000.0,
            pressure_pa=2000.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=1.0,
            ph3_in_ar_flow_m3_s=1.0,
            h2s_in_ar_flow_m3_s=1.0,
            mean_temperature_k=970.0,
        ),
        ParsedRTPStep(
            name='Cooling',
            duration_s=10.0,
            initial_temperature_k=1000.0,
            final_temperature_k=500.0,
            pressure_pa=1200.0,
            ar_flow_m3_s=0.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
            mean_temperature_k=700.0,
        ),
    ]

    overview = _derive_overview(steps)

    # Use mean over annealing timeframe, not endpoint average (which would be 950 K).
    assert overview['annealing_temperature'] == pytest.approx(970.0)


def test_derive_overview_sums_plateaus_before_and_after_annealing():
    steps = [
        ParsedRTPStep(
            name='Heating ramp',
            duration_s=50.0,
            initial_temperature_k=300.0,
            final_temperature_k=700.0,
            pressure_pa=1000.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
        ParsedRTPStep(
            name='Pre-anneal plateau',
            duration_s=20.0,
            initial_temperature_k=700.0,
            final_temperature_k=700.0,
            pressure_pa=1000.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
        ParsedRTPStep(
            name='Annealing',
            duration_s=30.0,
            initial_temperature_k=900.0,
            final_temperature_k=900.0,
            pressure_pa=2000.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
        ParsedRTPStep(
            name='Post-anneal plateau',
            duration_s=40.0,
            initial_temperature_k=900.0,
            final_temperature_k=900.0,
            pressure_pa=1500.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
        ParsedRTPStep(
            name='Cooling ramp',
            duration_s=60.0,
            initial_temperature_k=900.0,
            final_temperature_k=400.0,
            pressure_pa=1200.0,
            ar_flow_m3_s=1.0,
            n2_flow_m3_s=0.0,
            ph3_in_ar_flow_m3_s=0.0,
            h2s_in_ar_flow_m3_s=0.0,
        ),
    ]

    overview = _derive_overview(steps)

    assert overview['total_heating_time'] == pytest.approx(70.0)
    assert overview['total_cooling_time'] == pytest.approx(100.0)


def test_apply_parasitic_flow_cutoff_for_all_gases():
    below = 0.5 * MIN_USED_GAS_FLOW_M3_S
    at_limit = MIN_USED_GAS_FLOW_M3_S

    assert _apply_parasitic_flow_cutoff(below, 'Ar') == pytest.approx(0.0)
    assert _apply_parasitic_flow_cutoff(below, 'N2') == pytest.approx(0.0)
    assert _apply_parasitic_flow_cutoff(below, 'PH3') == pytest.approx(0.0)
    assert _apply_parasitic_flow_cutoff(below, 'H2S') == pytest.approx(0.0)

    assert _apply_parasitic_flow_cutoff(at_limit, 'Ar') == pytest.approx(at_limit)
    assert _apply_parasitic_flow_cutoff(at_limit, 'N2') == pytest.approx(at_limit)
    assert _apply_parasitic_flow_cutoff(at_limit, 'PH3') == pytest.approx(at_limit)
    assert _apply_parasitic_flow_cutoff(at_limit, 'H2S') == pytest.approx(at_limit)
