import importlib
import io
import logging
import os
from types import SimpleNamespace

import numpy as np
import pytest
from nomad import search as nomad_search
from nomad.client import normalize_all, parse
from nomad.datamodel import context as nomad_context
from nomad.datamodel.metainfo.annotations import ELNComponentEnum
from nomad.units import ureg

from nomad_dtu_nanolab_plugin.schema_packages.PL import (
    DTUPLMeasurement,
    PLMappingResult,
    PLSampleReference,
)
from nomad_dtu_nanolab_plugin.schema_packages.sample import DtuLibraryReference
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
FIGURE_COUNT = 3
WAFER_RADIUS_MM = 50
WAFER_FLAT_ANGLE_DEG = 270
EDGE_EXCLUSION_MM = 0
UNIQUE_MATCH_PAGE_SIZE = 1

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


def test_pl_schema_shows_ywa_upload_and_orders_eln_fields():
    section = DTUPLMeasurement.m_def
    expected_order = [
        'name',
        'pl_data_file',
        'pl_overview_file',
        'around_barycenter',
        'datetime',
        'lab_id',
        'location',
        'description',
        'samples',
        'results',
        'sample_alignment',
        'metadata',
        'instruments',
        'figures',
    ]

    assert section.a_eln.properties.order == expected_order
    assert section.a_eln.properties.visible.exclude == ['steps']
    assert (
        DTUPLMeasurement.pl_overview_file.a_eln.component
        == ELNComponentEnum.FileEditQuantity
    )
    sample_def = PLSampleReference.m_def
    assert sample_def.a_eln.properties.order == [
        'name',
        'reference',
        'lab_id',
        'measurement_x_range',
        'measurement_y_range',
        'library_x_range',
        'library_y_range',
    ]
    assert not PLSampleReference.measurement_x_range.m_annotations
    assert not PLSampleReference.measurement_y_range.m_annotations
    assert (
        PLSampleReference.library_x_range.a_eln.component
        == ELNComponentEnum.NumberEditQuantity
    )
    assert (
        PLSampleReference.library_y_range.a_eln.component
        == ELNComponentEnum.NumberEditQuantity
    )
    assert (
        PLMappingResult.samples.sub_section.section_cls.m_def
        is DtuLibraryReference.m_def
    )


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
    assert measurement.samples[0].measurement_x_range.to('mm').magnitude.tolist() == [
        -2,
        30,
    ]
    assert measurement.samples[0].measurement_y_range.to('mm').magnitude.tolist() == [
        -30,
        -4,
    ]
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
    assert measurement.metadata.wafer_radius.to('mm').magnitude == WAFER_RADIUS_MM
    assert measurement.metadata.edge_exclusion.to('mm').magnitude == EDGE_EXCLUSION_MM
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

    assert measurement.around_barycenter is False
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
    position_figure = measurement.figures[2].figure
    assert position_figure['data'][-1]['name'] == 'Measurement points'
    assert position_figure['data'][0]['name'] == 'mittma_0028_RTP'
    assert measurement.results[0].samples[0].lab_id == 'mittma_0028_RTP'


def test_read_native_ywf_rejects_files_without_saved_pl_traces():
    with pytest.raises(ValueError, match='No saved PL1 traces'):
        read_ywf(b'not a YWafer measurement')


def test_pl_automatically_links_only_unique_exact_four_part_match(monkeypatch):
    class FakeServerContext:
        pass

    monkeypatch.setattr(nomad_context, 'ServerContext', FakeServerContext)
    calls = []

    def fake_search(**kwargs):
        calls.append(kwargs)
        entries = [
            {
                'entry_id': 'exact-entry',
                'upload_id': 'upload-1',
                'results': {'eln': {'lab_ids': ['mittma_0028_RTP_ha']}},
            }
        ]
        return SimpleNamespace(
            pagination=SimpleNamespace(total=1),
            data=entries,
        )

    monkeypatch.setattr(nomad_search, 'search', fake_search)

    measurement = DTUPLMeasurement()
    measurement.add_pl_sample_references(
        'nested/path/mittma_0028_RTP--ha--1.ywf',
        SimpleNamespace(
            m_context=FakeServerContext(),
            metadata=SimpleNamespace(main_author=SimpleNamespace(user_id='test-user')),
        ),
        logging.getLogger('test'),
    )

    assert len(calls) == 1
    assert calls[0]['query'].to_dict() == {
        'term': {'results.eln.lab_ids': 'mittma_0028_RTP_ha'}
    }
    assert calls[0]['pagination'].page_size == UNIQUE_MATCH_PAGE_SIZE
    assert len(measurement.samples) == 1
    assert measurement.samples[0].lab_id == 'mittma_0028_RTP_ha'


def test_pl_requires_manual_samples_and_full_point_coverage_when_match_is_not_unique(
    monkeypatch,
):
    class FakeServerContext:
        pass

    monkeypatch.setattr(nomad_context, 'ServerContext', FakeServerContext)
    monkeypatch.setattr(
        nomad_search,
        'search',
        lambda **kwargs: SimpleNamespace(
            pagination=SimpleNamespace(total=2),
            data=[
                {
                    'entry_id': f'entry-{index}',
                    'upload_id': f'upload-{index}',
                    'results': {'eln': {'lab_ids': ['mittma_0028_RTP_ha']}},
                }
                for index in range(2)
            ],
        ),
    )
    measurement = DTUPLMeasurement(
        results=[
            PLMappingResult(
                x_absolute=ureg.Quantity(x, 'mm'),
                y_absolute=ureg.Quantity(y, 'mm'),
            )
            for x, y in [(0, 0), (12, 4)]
        ]
    )
    archive = SimpleNamespace(
        m_context=FakeServerContext(),
        metadata=SimpleNamespace(main_author=SimpleNamespace(user_id='test-user')),
    )
    warning_messages = []
    logger = SimpleNamespace(warning=warning_messages.append)
    with pytest.raises(ValueError, match='Add each combinatorial library in Samples'):
        measurement.add_pl_sample_references(
            'mittma_0028_RTP_ha--1.ywf', archive, logger
        )

    measurement.samples = [
        PLSampleReference(
            name='manual-library-1',
            lab_id='manual-library-1',
            library_x_range=ureg.Quantity([-1, 1], 'mm'),
            library_y_range=ureg.Quantity([-1, 1], 'mm'),
        )
    ]
    measurement.add_pl_sample_references('mittma_0028_RTP_ha--1.ywf', archive, logger)
    assert 'do not cover every PL measurement point' in warning_messages[0]
    assert len(measurement.samples) == 1

    measurement.samples.append(
        PLSampleReference(
            name='manual-library-2',
            lab_id='manual-library-2',
            library_x_range=ureg.Quantity([11, 13], 'mm'),
            library_y_range=ureg.Quantity([3, 5], 'mm'),
        )
    )
    measurement.add_pl_sample_references('mittma_0028_RTP_ha--1.ywf', archive, logger)
    assert [sample.lab_id for sample in measurement.samples] == [
        'manual-library-1',
        'manual-library-2',
    ]
    assert [len(result.samples) for result in measurement.results] == [1, 1]


def test_pl_builds_plots_before_raising_for_missing_samples(monkeypatch):
    class FakeServerContext:
        def raw_file(self, _path, _mode):
            return io.BytesIO(b'fake')

    monkeypatch.setattr(nomad_context, 'ServerContext', FakeServerContext)
    monkeypatch.setattr(
        nomad_search,
        'search',
        lambda **kwargs: SimpleNamespace(
            pagination=SimpleNamespace(total=0),
            data=[],
        ),
    )
    pl_schema = importlib.import_module('nomad_dtu_nanolab_plugin.schema_packages.PL')
    monkeypatch.setattr(
        pl_schema,
        'read_ywf',
        lambda _data: {
            'metadata': {},
            'traces': [
                {
                    'name': 'PL1 #1',
                    'x': 1,
                    'y': 2,
                    'wavelength_nm': [500, 600],
                    'intensity': [1, 2],
                }
            ],
        },
    )
    measurement = DTUPLMeasurement(pl_data_file='no_matching_sample--1.ywf')
    archive = SimpleNamespace(
        m_context=FakeServerContext(),
        metadata=SimpleNamespace(main_author=SimpleNamespace(user_id='test-user')),
    )

    with pytest.raises(ValueError, match='Add each combinatorial library in Samples'):
        measurement.normalize(archive, logging.getLogger('test'))

    assert len(measurement.figures) == FIGURE_COUNT
    assert len(measurement.results[0].figures) == 1
    assert measurement.samples == []
