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
                'Sample x = -2.5 mm, y = 2.5 mm',
                'Sample x = 17.5 mm, y = -17.5 mm',
                'Sample x = -12.5 mm, y = -7.5 mm',
                'Sample x = -12.5 mm, y = 12.5 mm',
                'Sample x = 7.5 mm, y = -7.5 mm',
                'Sample x = 7.5 mm, y = 12.5 mm',
                'Sample x = 17.5 mm, y = 22.5 mm',
                'Sample x = -22.5 mm, y = 22.5 mm',
                'Sample x = -22.5 mm, y = -17.5 mm',
            ],
            id='xrd',
        ),
        pytest.param(
            'test_edx.archive.yaml',
            15,
            [
                'Sample x = -9.1 mm, y = -14.2 mm',
                'Sample x = -9.6 mm, y = -6.9 mm',
                'Sample x = -10.2 mm, y = 0.5 mm',
                'Sample x = -10.8 mm, y = 7.7 mm',
                'Sample x = -11.3 mm, y = 15.1 mm',
                'Sample x = 1.6 mm, y = -13.4 mm',
                'Sample x = 1.0 mm, y = -6.0 mm',
                'Sample x = 0.5 mm, y = 1.3 mm',
                'Sample x = -0.2 mm, y = 8.7 mm',
                'Sample x = -0.7 mm, y = 16.0 mm',
                'Sample x = 12.2 mm, y = -12.4 mm',
                'Sample x = 11.6 mm, y = -5.2 mm',
                'Sample x = 11.1 mm, y = 2.2 mm',
                'Sample x = 10.5 mm, y = 9.5 mm',
                'Sample x = 10.0 mm, y = 16.8 mm',
            ],
            id='edx',
        ),
        pytest.param(
            'test_raman.archive.yaml',
            9,
            [
                'Stage x = 2.0 mm, y = 5.0 mm',
                'Stage x = 6.5 mm, y = 5.0 mm',
                'Stage x = 11.0 mm, y = 5.0 mm',
                'Stage x = 15.5 mm, y = 5.0 mm',
                'Stage x = 20.0 mm, y = 5.0 mm',
                'Stage x = 24.5 mm, y = 5.0 mm',
                'Stage x = 29.0 mm, y = 5.0 mm',
                'Stage x = 33.5 mm, y = 5.0 mm',
                'Stage x = 38.0 mm, y = 5.0 mm',
            ],
            id='raman',
        ),
        pytest.param(
            'test_ellipsometry.archive.yaml',
            11,
            [
                'Stage x = -18.0 mm, y = 0.0 mm',
                'Stage x = -14.4 mm, y = 0.0 mm',
                'Stage x = -10.8 mm, y = 0.0 mm',
                'Stage x = -7.2 mm, y = 0.0 mm',
                'Stage x = -3.6 mm, y = 0.0 mm',
                'Stage x = 0.0 mm, y = 0.0 mm',
                'Stage x = 3.6 mm, y = 0.0 mm',
                'Stage x = 7.2 mm, y = 0.0 mm',
                'Stage x = 10.8 mm, y = 0.0 mm',
                'Stage x = 14.4 mm, y = 0.0 mm',
                'Stage x = 18.0 mm, y = 0.0 mm',
            ],
            id='ellipsometry',
        ),
    ],
)
def test_mapping_schema(test_file, expected_result_count, expected_names):
    test_file_path = os.path.join('tests', 'data', test_file)
    entry_archive = parse(test_file_path)[0]
    normalize_all(entry_archive)

    assert len(entry_archive.data.results) == expected_result_count

    for result in entry_archive.data.results:
        assert result.name in expected_names


def test_rt_autosampler_schema():
    """
    Test the RT autosampler measurement schema.

    This test verifies that the DtuAutosamplerMeasurement correctly parses
    data and config CSV files and creates individual RTMeasurement steps
    for each library.
    """
    test_file = os.path.join('tests', 'data', 'test_rt_autosampler.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    # Expected library names from the grid file (excluding Baseline)
    expected_libraries = [
        'eugbe_0008_RTP_hd',
        'eugbe_0009_RTP_hd',
        'anait_0030_RTP_ha',
        'anait_0030_RTP_hc',
        'anait_0030_RTP_hd',
        'anait_0030_RTP_hb'
    ]

    # The autosampler measurement should create steps (one per library)
    assert len(entry_archive.data.steps) == len(expected_libraries)

    # Extract library names from step names and verify they match expected
    step_library_names = []
    for step in entry_archive.data.steps:
        assert step.name is not None
        assert 'measurement' in step.name.lower()
        # Extract library name (it's the first part before ' measurement')
        library_name = step.name.split(' ')[0]
        step_library_names.append(library_name)
        # Each step should have an activity reference
        assert step.activity is not None

    # Check that we have the right libraries (order might vary)
    assert len(step_library_names) == len(expected_libraries)
    for expected_name in expected_libraries:
        assert expected_name in step_library_names, f"Expected library {expected_name} not found in steps"

