import os
from types import SimpleNamespace

import numpy as np
import pytest
from nomad import search as nomad_search
from nomad.client import normalize_all, parse
from nomad.datamodel import context as nomad_context

from nomad_dtu_nanolab_plugin.schema_packages.PL import DTUPLMeasurement
from nomad_dtu_nanolab_plugin.ywf_reader import read_ywa_metadata, read_ywf

TRACE_COUNT = 12
SPECTRUM_POINT_COUNT = 1024
EXCITATION_WAVELENGTH_NM = 405
INTEGRATION_TIME_MS = 10000
INTEGRATION_TIME_S = 10
LASER_POWER_PERCENTAGE = 100
EXPECTED_FIRST_X_MM = -2
EXPECTED_FIRST_Y_MM = -4
SAMPLE_WIDTH_MM = 50
SAMPLE_HEIGHT_MM = 40
MAP_CENTER_X_MM = 14
MAP_CENTER_Y_MM = -17
FIGURE_COUNT = 2
MATCHING_SAMPLE_COUNT = 105
EXPECTED_SEARCH_PAGE_COUNT = 2
WAFER_RADIUS_MM = 50
WAFER_FLAT_ANGLE_DEG = 270
EDGE_EXCLUSION_MM = 0

YWF_FILE = os.path.join('tests', 'data', 'mittma_0028_RTP--1.ywf')
YWA_FILE = os.path.join('tests', 'data', 'mittma_0028_RTP--1.ywa')


def test_read_native_ywf_traces():
    with open(YWF_FILE, 'rb') as file:
        parsed_data = read_ywf(file.read())

    assert len(parsed_data['traces']) == TRACE_COUNT
    assert all(trace['wavelength_nm'] is not None for trace in parsed_data['traces'])
    assert all(
        len(trace['wavelength_nm']) == SPECTRUM_POINT_COUNT
        for trace in parsed_data['traces']
    )
    assert [(trace['x'], trace['y']) for trace in parsed_data['traces'][:3]] == [
        (-2, -4),
        (-2, -17),
        (-2, -30),
    ]
    assert parsed_data['metadata']['software_version'] == 'YWafer v7.06'
    assert (
        parsed_data['metadata']['excitation_wavelength_nm'] == EXCITATION_WAVELENGTH_NM
    )
    assert parsed_data['metadata']['integration_time_ms'] == INTEGRATION_TIME_MS
    assert parsed_data['metadata']['accumulations'] == 1
    assert parsed_data['metadata']['wavelength_range_nm'] == [480, 900]
    assert parsed_data['metadata']['laser_power_percentage'] == LASER_POWER_PERCENTAGE


def test_read_ywa_overview_metadata():
    with open(YWA_FILE, 'rb') as file:
        metadata = read_ywa_metadata(file.read())

    assert metadata['software_version'] == 'YWafer v7.06'
    assert metadata['lot_id'] == 'mittma_0028_RTP'
    assert metadata['wafer_number'] == '-1'
    assert metadata['chamber'] == 'cbbmo'
    assert metadata['scan_pitch_mm'] == [1, 1]
    assert metadata['scan_center_mm'] == [0, 0]
    assert metadata['wafer_radius_mm'] == WAFER_RADIUS_MM
    assert metadata['edge_exclusion_mm'] == EDGE_EXCLUSION_MM
    assert metadata['wafer_flat_angle_deg'] == WAFER_FLAT_ANGLE_DEG
    assert metadata['data_type'] == 'YWafer'


def test_native_pl_measurement_normalization(monkeypatch):
    monkeypatch.setattr(
        DTUPLMeasurement,
        '_get_sample_dimensions',
        lambda self, logger: (
            SAMPLE_WIDTH_MM / 1000,
            SAMPLE_HEIGHT_MM / 1000,
        ),
    )
    archive_path = os.path.join('tests', 'data', 'test_pl.archive.yaml')
    archive = parse(archive_path)[0]
    normalize_all(archive)

    measurement = archive.data
    assert len(measurement.results) == TRACE_COUNT
    assert measurement.samples[0].lab_id == 'mittma_0028_RTP'
    assert measurement.metadata.software_version == 'YWafer v7.06'
    assert (
        measurement.metadata.excitation_wavelength.to('nm').magnitude
        == EXCITATION_WAVELENGTH_NM
    )
    assert measurement.metadata.laser_power.to('mW').magnitude == pytest.approx(
        LASER_POWER_PERCENTAGE
    )
    assert (
        measurement.metadata.laser_power_percentage.to('%').magnitude
        == LASER_POWER_PERCENTAGE
    )
    assert measurement.metadata.integration_time.to('s').magnitude == INTEGRATION_TIME_S
    assert measurement.metadata.wavelength_range.to('nm').magnitude.tolist() == [
        480,
        900,
    ]
    assert measurement.metadata.lot_id == 'mittma_0028_RTP'
    assert measurement.metadata.wafer_number == '-1'
    assert measurement.metadata.chamber == 'cbbmo'
    assert measurement.metadata.scan_pitch.to('mm').magnitude.tolist() == [1, 1]
    assert measurement.metadata.scan_center.to('mm').magnitude.tolist() == [0, 0]
    assert (
        measurement.metadata.wafer_radius.to('mm').magnitude == WAFER_RADIUS_MM
    )
    assert (
        measurement.metadata.edge_exclusion.to('mm').magnitude == EDGE_EXCLUSION_MM
    )
    assert (
        measurement.metadata.wafer_flat_angle.to('deg').magnitude
        == WAFER_FLAT_ANGLE_DEG
    )
    assert measurement.metadata.data_type == 'YWafer'

    first_result = measurement.results[0]
    assert first_result.trace_id == 'PL1 #1'
    assert first_result.x_absolute.to('mm').magnitude == EXPECTED_FIRST_X_MM
    assert first_result.y_absolute.to('mm').magnitude == EXPECTED_FIRST_Y_MM
    assert first_result.x_relative.to('mm').magnitude == pytest.approx(-16)
    assert first_result.y_relative.to('mm').magnitude == pytest.approx(13)
    assert len(first_result.wavelength) == SPECTRUM_POINT_COUNT
    assert len(first_result.intensity) == SPECTRUM_POINT_COUNT
    assert np.isfinite(first_result.peak_lambda.magnitude)
    assert first_result.peak_intensity == pytest.approx(max(first_result.intensity))
    assert len(first_result.figures) == 1
    spectrum_figure = first_result.figures[0].figure
    assert len(spectrum_figure['data']) == 1
    assert len(spectrum_figure['data'][0]['x']) == SPECTRUM_POINT_COUNT
    assert len(spectrum_figure['data'][0]['y']) == SPECTRUM_POINT_COUNT
    assert all(len(result.figures) == 1 for result in measurement.results)

    assert measurement.around_barycenter is True
    assert measurement.sample_alignment.width.to('mm').magnitude == pytest.approx(
        SAMPLE_WIDTH_MM
    )
    assert measurement.sample_alignment.height.to('mm').magnitude == pytest.approx(
        SAMPLE_HEIGHT_MM
    )
    x_upper_left_mm = measurement.sample_alignment.x_upper_left.to('mm').magnitude
    y_upper_left_mm = measurement.sample_alignment.y_upper_left.to('mm').magnitude
    assert x_upper_left_mm == pytest.approx(MAP_CENTER_X_MM - SAMPLE_WIDTH_MM / 2)
    assert y_upper_left_mm == pytest.approx(MAP_CENTER_Y_MM + SAMPLE_HEIGHT_MM / 2)
    assert len(measurement.figures) == FIGURE_COUNT
    map_data = measurement.figures[1].figure['data'][0]
    assert map_data['x'][0] == pytest.approx(-16)
    assert map_data['y'][0] == pytest.approx(13)


def test_read_native_ywf_rejects_files_without_saved_pl_traces():
    with pytest.raises(ValueError, match='No saved PL1 traces'):
        read_ywf(b'not a YWafer measurement')


def test_pl_links_all_matching_samples_across_search_pages(monkeypatch):
    class FakeServerContext:
        pass

    monkeypatch.setattr(nomad_context, 'ServerContext', FakeServerContext)
    calls = []

    def fake_search(**kwargs):
        page = kwargs['pagination'].page
        calls.append(kwargs)
        first_index = (page - 1) * 100
        last_index = min(first_index + 100, MATCHING_SAMPLE_COUNT)
        entries = [
            {
                'entry_id': f'entry-{index}',
                'upload_id': 'upload-1',
                'results': {
                    'eln': {
                        'lab_ids': [f'mittma_0028_RTP_{index:03d}'],
                    }
                },
            }
            for index in range(first_index, last_index)
        ]
        return SimpleNamespace(
            pagination=SimpleNamespace(total=MATCHING_SAMPLE_COUNT),
            data=entries,
        )

    monkeypatch.setattr(nomad_search, 'search', fake_search)

    measurement = DTUPLMeasurement()
    measurement.add_pl_sample_references(
        'nested/path/mittma_0028_RTP--1.ywf',
        SimpleNamespace(
            m_context=FakeServerContext(),
            metadata=SimpleNamespace(main_author=SimpleNamespace(user_id='test-user')),
        ),
        __import__('logging').getLogger('test'),
    )

    assert len(measurement.samples) == MATCHING_SAMPLE_COUNT
    assert len(calls) == EXPECTED_SEARCH_PAGE_COUNT
    assert [call['pagination'].page for call in calls] == [1, 2]
    query = calls[0]['query'].to_dict()
    assert query['bool']['should'][0]['term']['results.eln.lab_ids'] == (
        'mittma_0028_RTP'
    )
    assert query['bool']['should'][1]['prefix']['results.eln.lab_ids'] == (
        'mittma_0028_RTP_'
    )
    assert measurement.samples[0].lab_id == 'mittma_0028_RTP_000'
    assert measurement.samples[-1].lab_id == 'mittma_0028_RTP_104'
