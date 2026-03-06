import os.path

import pytest
from nomad.client import normalize_all, parse

MIN_EXPECTED_STEPS = 2


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

    assert data.used_gases is not None
    assert 'PH3' in data.used_gases
    assert 'H2S' in data.used_gases

    # 11 l/min from diagnostics log.
    assert data.chiller_flow.magnitude == pytest.approx(11e-3 / 60)

    # 1.1 torr from diagnostics log.
    assert data.base_pressure.to('torr').magnitude == pytest.approx(1.1, abs=1e-3)
