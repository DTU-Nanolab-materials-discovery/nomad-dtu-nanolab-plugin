import os.path

import pytest
from nomad.client import normalize_all, parse
from nomad_dtu_nanolab_plugin.rtp_log_reader import _read_csv_with_fallback

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
    assert len(df) == 2
    assert df.iloc[0]['comment'] == 'note with ; semicolon'
    assert df.iloc[1]['comment'] == 'note with , comma'
