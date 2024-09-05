import os.path

from nomad.client import normalize_all, parse


def test_schema():
    test_file = os.path.join('tests', 'data', 'test_xrd.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    EXPECTED_RESULT_COUNT = 9
    EXPECTED_NAMES = [
        '(-2.5, 2.5)',
        '(17.5, -17.5)',
        '(-12.5, -7.5)',
        '(-12.5, 12.5)',
        '(7.5, -7.5)',
        '(7.5, 12.5)',
        '(17.5, 22.5)',
        '(-22.5, 22.5)',
        '(-22.5, -17.5)',
    ]

    assert len(entry_archive.data.results) == EXPECTED_RESULT_COUNT

    for result in entry_archive.data.results:
        assert result.name in EXPECTED_NAMES
