import os.path

import pytest
from nomad.client import normalize_all, parse


def test_schema():
    test_file = os.path.join('tests', 'data', 'test_rtp_2.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert entry_archive.data.steps[0].step_overview.temperature_ramp == pytest.approx(
        1.5277777777777777
    )
