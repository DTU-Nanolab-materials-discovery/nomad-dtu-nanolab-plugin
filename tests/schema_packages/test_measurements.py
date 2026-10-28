import os.path
from types import SimpleNamespace

import pytest
from nomad import search as nomad_search
from nomad.client import normalize_all, parse
from nomad.datamodel.metainfo.basesections import CompositeSystemReference
from nomad_material_processing.general import RectangleCuboid

import nomad_dtu_nanolab_plugin.schema_packages.rt as rt_module
from nomad_dtu_nanolab_plugin.schema_packages.basesections import DtuNanolabMeasurement
from nomad_dtu_nanolab_plugin.schema_packages.edx import (
    DTUSampleAlignment,
    EDXMeasurement,
)
from nomad_dtu_nanolab_plugin.schema_packages.sample import DTUCombinatorialLibrary

"""
Names can be generated from the test file by running the following command:
>>> import json
>>> with open('output.archive.json', 'r') as f: archive = json.load(f)
>>> print(json.dumps([r['name'] for r in archive['data']['results']], indent=4))
"""


@pytest.mark.usefixtures('caplog')
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
                'Stage x = -10.8 mm, y = -14.6 mm',
                'Stage x = -10.7 mm, y = -7.3 mm',
                'Stage x = -10.7 mm, y = 0.1 mm',
                'Stage x = -10.7 mm, y = 7.4 mm',
                'Stage x = -10.6 mm, y = 14.8 mm',
                'Stage x = -0.1 mm, y = -14.7 mm',
                'Stage x = -0.1 mm, y = -7.3 mm',
                'Stage x = 0.0 mm, y = -0.0 mm',
                'Stage x = 0.0 mm, y = 7.4 mm',
                'Stage x = 0.1 mm, y = 14.7 mm',
                'Stage x = 10.6 mm, y = -14.7 mm',
                'Stage x = 10.6 mm, y = -7.4 mm',
                'Stage x = 10.7 mm, y = -0.0 mm',
                'Stage x = 10.7 mm, y = 7.3 mm',
                'Stage x = 10.8 mm, y = 14.6 mm',
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


def test_resolve_library_folder_uses_lab_id_search(monkeypatch):
    """
    The autosampler should resolve library folders
    using the same direct lab-id search as the notebook.
    """
    archive = SimpleNamespace(
        metadata=SimpleNamespace(
            mainfile='uploads/123/archive/current.archive.json',
            upload_id='upload-456',
            main_author=SimpleNamespace(user_id='user-1'),
        )
    )

    class FakeSearchResult:
        class Pagination:
            total = 1

        pagination = Pagination()
        data = [{'upload_id': 'upload-456', 'entry_id': 'entry-789'}]

    monkeypatch.setattr(
        nomad_search,
        'search',
        lambda **kwargs: FakeSearchResult(),
    )
    monkeypatch.setattr(
        nomad_search,
        'MetadataPagination',
        lambda page_size=1: SimpleNamespace(page_size=page_size),
    )

    folder = rt_module.resolve_library_folder(
        archive, __import__('logging').getLogger('test'), 'indiogo_0020_Sn_G'
    )

    assert folder == '../uploads/upload-456/archive'


def test_measurement_alignment_uses_linked_library_geometry():
    logger = __import__('logging').getLogger('test')
    library = DTUCombinatorialLibrary(geometry=RectangleCuboid(width=0.04, length=0.03))
    measurement = EDXMeasurement(
        samples=[CompositeSystemReference(reference=library)],
        results=[],
        sample_alignment=DTUSampleAlignment(
            x_upper_left=-0.01,
            y_upper_left=0.01,
            x_lower_right=0.01,
            y_lower_right=-0.01,
        ),
    )

    assert measurement.sample_alignment.width is None
    assert measurement.sample_alignment.height is None
    measurement._apply_library_geometry_to_alignment(logger)

    assert measurement.sample_alignment.width == library.geometry.width
    assert measurement.sample_alignment.height == library.geometry.length
    assert measurement.sample_alignment.x_upper_left == -library.geometry.width / 2
    assert measurement.sample_alignment.y_upper_left == library.geometry.length / 2
    assert measurement.sample_alignment.x_lower_right == library.geometry.width / 2
    assert measurement.sample_alignment.y_lower_right == -library.geometry.length / 2


def test_measurement_dimensions_fall_back_to_substrate_geometry():
    logger = __import__('logging').getLogger('test')
    substrate_geometry = RectangleCuboid(width=0.05, length=0.025)
    measurement = SimpleNamespace(
        samples=[
            SimpleNamespace(
                reference=SimpleNamespace(
                    geometry=SimpleNamespace(),
                    substrate=SimpleNamespace(
                        reference=SimpleNamespace(geometry=substrate_geometry)
                    ),
                )
            )
        ]
    )

    assert DtuNanolabMeasurement._get_sample_dimensions(
        measurement, logger
    ) == pytest.approx((0.05, 0.025))


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
        'eugbe_0008_RTP_hd_rt_measurement_20251105_190408',
        'eugbe_0009_RTP_hd_rt_measurement_20251105_195149',
        'anait_0030_RTP_ha_rt_measurement_20251105_203950',
        'anait_0030_RTP_hc_rt_measurement_20251105_212832',
        'anait_0030_RTP_hd_rt_measurement_20251105_221715',
        'anait_0030_RTP_hb_rt_measurement_20251105_230614',
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
        assert expected_name in step_library_names, (
            f'Expected library {expected_name} not found in steps'
        )
