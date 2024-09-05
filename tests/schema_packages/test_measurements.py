import os.path

import pytest
from nomad.client import normalize_all, parse

"""
Names can be generated from the test file by running the following command:
>>> import json
>>> with open('output.archive.json', 'r') as f: archive = json.load(f)
>>> print(json.dumps([r['name'] for r in archive['data']['results']], indent=4))
"""


@pytest.mark.parametrize(
    'test_file, expected_result_count, expected_names',
    [
        pytest.param(
            'test_xrd.archive.yaml',
            9,
            [
                '(-2.5, 2.5)',
                '(17.5, -17.5)',
                '(-12.5, -7.5)',
                '(-12.5, 12.5)',
                '(7.5, -7.5)',
                '(7.5, 12.5)',
                '(17.5, 22.5)',
                '(-22.5, 22.5)',
                '(-22.5, -17.5)',
            ],
            id='xrd',
        ),
        pytest.param(
            'test_edx.archive.yaml',
            15,
            [
                '(13.1, -41.5)',
                '(13.1, -33.1)',
                '(13.2, -24.6)',
                '(13.3, -16.1)',
                '(13.3, -7.6)',
                '(25.4, -41.6)',
                '(25.5, -33.1)',
                '(25.6, -24.7)',
                '(25.6, -16.2)',
                '(25.7, -7.7)',
                '(37.8, -41.7)',
                '(37.8, -33.2)',
                '(37.9, -24.7)',
                '(37.9, -16.3)',
                '(38.0, -7.8)',
            ],
            id='edx',
        ),
    ],
)
def test_schema(test_file, expected_result_count, expected_names):
    test_file_path = os.path.join('tests', 'data', test_file)
    entry_archive = parse(test_file_path)[0]
    normalize_all(entry_archive)

    assert len(entry_archive.data.results) == expected_result_count

    for result in entry_archive.data.results:
        assert result.name in expected_names
