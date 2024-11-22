import os.path

from nomad.client import normalize_all, parse


def test_target():
    test_file = os.path.join('tests', 'data', 'test_target.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert entry_archive.data.lab_id == 'Ag_T_001'
