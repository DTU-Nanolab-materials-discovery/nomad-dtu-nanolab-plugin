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
                '(-9.1, -14.2)',
                '(-9.6, -6.9)',
                '(-10.2, 0.5)',
                '(-10.8, 7.7)',
                '(-11.3, 15.1)',
                '(1.6, -13.4)',
                '(1.0, -6.0)',
                '(0.5, 1.3)',
                '(-0.2, 8.7)',
                '(-0.7, 16.0)',
                '(12.2, -12.4)',
                '(11.6, -5.2)',
                '(11.1, 2.2)',
                '(10.5, 9.5)',
                '(10.0, 16.8)',
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
