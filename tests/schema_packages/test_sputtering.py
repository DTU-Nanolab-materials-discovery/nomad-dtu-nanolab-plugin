import os.path

import pytest
from nomad.client import normalize_all, parse


def test_schema():
    test_file = os.path.join('tests', 'data', 'logfile_test.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert entry_archive.data.deposition_parameters.deposition_temperature.to(
        'K'
    ).magnitude == pytest.approx(473.14870714)
