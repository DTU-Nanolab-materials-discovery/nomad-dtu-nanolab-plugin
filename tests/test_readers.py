import io
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from PIL import Image

from nomad_dtu_nanolab_plugin.autosampler_reader import (
    MAX_ALPHA,
    WINDOW_SIZE,
    MultiMeasurement,
    SingleMeasurement,
    _build_alpha_dataframes,
    _standard_treatment_options,
)
from nomad_dtu_nanolab_plugin.raman_map_parser import MappingRamanMeas, RamanMeas


def _alpha_inputs(alpha, reflectance, method):
    reflectance = np.asarray(reflectance, dtype=float)
    alpha = np.asarray(alpha, dtype=float)
    transmission_fraction = {
        '1fr': (1 - reflectance) * np.exp(-alpha),
        '1fbr': (1 - reflectance) ** 2 * np.exp(-alpha),
        'infr': (1 - reflectance) ** 2
        * np.exp(-alpha)
        / (1 - reflectance**2 * np.exp(-2 * alpha)),
    }[method]
    wavelengths = np.array([500.0, 600.0])
    source = SimpleNamespace(
        data=pd.DataFrame({'Wavelength': wavelengths, 'Energy': 1239.84 / wavelengths})
    )
    transmission = {
        'wavelength': wavelengths,
        'energy': 1239.84 / wavelengths,
        'intensity': transmission_fraction * 100,
        'fraction': transmission_fraction,
    }
    reflection = {
        'wavelength': wavelengths,
        'energy': 1239.84 / wavelengths,
        'intensity': reflectance * 100,
        'fraction': reflectance,
    }
    return transmission, reflection, source


@pytest.mark.parametrize(
    ('method', 'input_alpha', 'expected_alpha'),
    [
        ('1fr', [0.5, 1.3], [0.5, 1.3]),
        ('1fbr', [0.5, 1.3], [0.5, 1.3]),
        ('infr', [0.5, 1.3], [-3.635608034402121, -3.9352248187787024]),
    ],
)
def test_build_alpha_dataframes_calculates_each_method(
    method, input_alpha, expected_alpha
):
    transmission, reflection, source = _alpha_inputs(input_alpha, [0.1, 0.2], method)

    t_df, r_df, alpha_df, normalized_df = _build_alpha_dataframes(
        transmission, reflection, source, method
    )

    np.testing.assert_allclose(alpha_df['alpha'], expected_alpha)
    np.testing.assert_allclose(t_df['T'], transmission['intensity'])
    np.testing.assert_allclose(r_df['R'], reflection['intensity'])
    expected_normalized = (np.array(expected_alpha) - min(expected_alpha)) / (
        max(expected_alpha) - min(expected_alpha)
    )
    np.testing.assert_allclose(normalized_df['normalized_alpha'], expected_normalized)
    assert 'alpha' not in normalized_df


def test_build_alpha_dataframes_clamps_inputs_and_alpha():
    wavelengths = np.array([500.0, 600.0])
    source = SimpleNamespace(
        data=pd.DataFrame({'Wavelength': wavelengths, 'Energy': [2.4, 2.0]})
    )
    transmission = {
        'wavelength': wavelengths,
        'energy': [2.4, 2.0],
        'intensity': [0.0, 25.0],
        'fraction': np.array([0.1, -0.5]),
    }
    reflection = {
        'wavelength': wavelengths,
        'energy': [2.4, 2.0],
        'intensity': [120.0, 50.0],
        'fraction': np.array([1.2, 0.5]),
    }

    with np.errstate(divide='ignore'):
        _, _, alpha_df, _ = _build_alpha_dataframes(
            transmission, reflection, source, '1fr'
        )

    assert reflection['fraction'][0] == 1
    assert np.isneginf(alpha_df.loc[0, 'alpha'])
    assert alpha_df.loc[1, 'alpha'] == MAX_ALPHA


def test_standard_treatment_options_resolves_positional_keywords_and_defaults():
    expected_wavelength_range = (450, 750)
    expected_min_r = 0.95
    options = _standard_treatment_options(
        (*expected_wavelength_range, 'infr'),
        {'tauc_method': 'indirect', 'min_r': expected_min_r},
    )

    assert (options['wv_start'], options['wv_end']) == expected_wavelength_range
    assert options['alpha_method'] == 'infr'
    assert options['tauc_method'] == 'indirect'
    assert options['min_r'] == expected_min_r
    assert options['window_size'] == WINDOW_SIZE
    assert options['method'] == 'normalized'


@pytest.mark.parametrize(
    ('args', 'kwargs', 'error'),
    [
        ((1,) * 13, {}, 'takes 12 positional arguments'),
        ((), {'not_an_option': 1}, 'unexpected keyword argument'),
        ((500,), {'wv_start': 600}, 'multiple values for argument'),
    ],
)
def test_standard_treatment_options_rejects_invalid_arguments(args, kwargs, error):
    with pytest.raises(TypeError, match=error):
        _standard_treatment_options(args, kwargs)


def test_standard_treatment_forwards_options_to_processing_steps():
    measurement = MultiMeasurement('sample')
    measurement.avg_sp_pol = Mock()
    measurement.calc_avg_transmission_refl = Mock()
    measurement.find_max_transmission_refl = Mock()
    measurement.calc_alpha = Mock()
    measurement.calc_tauc = Mock()
    measurement.estimate_bandgap_inflection = Mock()
    measurement.estimate_bandgap_tauc = Mock()
    measurement.estimate_bandgap_threshold = Mock()

    measurement.standard_treatment(
        450,
        750,
        alpha_method='infr',
        tauc_method='indirect',
        max_energy=2.8,
        window_size=9,
        window_size_intercept=6,
        window_size_threshold=4,
        alpha_threshold=0.2,
        method='default',
        min_r=0.95,
        min_slope=1.5,
    )

    measurement.avg_sp_pol.assert_called_once_with()
    measurement.calc_avg_transmission_refl.assert_called_once_with(
        wv_start=450, wv_end=750
    )
    measurement.find_max_transmission_refl.assert_called_once_with(
        wv_start=450, wv_end=750
    )
    measurement.calc_alpha.assert_called_once_with(
        method='infr', wv_start=450, wv_end=750
    )
    measurement.calc_tauc.assert_called_once_with(method='indirect')
    measurement.estimate_bandgap_inflection.assert_called_once_with(
        max_energy=2.8, window_size=9
    )
    measurement.estimate_bandgap_tauc.assert_called_once_with(
        window_size=6, max_energy=2.8, min_r=0.95, min_slope=1.5
    )
    measurement.estimate_bandgap_threshold.assert_called_once_with(
        threshold=0.2, window_size=4, method='default'
    )


def test_rt_helpers_filter_measurements_and_return_fractions():
    transmission = SingleMeasurement('sample__0__0__0')
    transmission.add_data(np.array([400, 500, 600]), [80, 60, 40], 'T%')
    reflection = SingleMeasurement('sample__0__0__0')
    reflection.add_data(np.array([400, 500, 600]), [10, 20, 30], 'R%')
    multi = MultiMeasurement('sample')
    multi.avg_sp_measurements = [transmission, reflection]

    grouped = multi._get_rt_measurements()
    multi._filter_rt_wavelengths(grouped, 500, 600)
    t_values, r_values, source = multi._get_rt_arrays(grouped)

    assert source is reflection
    np.testing.assert_array_equal(t_values['wavelength'], [500, 600])
    np.testing.assert_allclose(t_values['fraction'], [0.6, 0.4])
    np.testing.assert_allclose(r_values['fraction'], [0.2, 0.3])


def test_rt_helper_rejects_missing_or_duplicate_measurement_types():
    transmission = SingleMeasurement('sample__0__0__0')
    transmission.add_data(np.array([500]), [80], 'T%')
    multi = MultiMeasurement('sample')
    multi.avg_sp_measurements = [transmission]
    assert multi._get_rt_measurements() is None

    duplicate = SingleMeasurement('sample__0__0__0')
    duplicate.add_data(np.array([500]), [70], 'T%')
    multi.avg_sp_measurements.append(duplicate)
    assert multi._get_rt_measurements() is None


def test_alpha_smoothing_handles_uniform_and_nonuniform_wavelengths():
    multi = MultiMeasurement('sample')
    uniform_wavelength = np.arange(9, dtype=float)
    alpha = uniform_wavelength**2

    smoothed, first, second = multi._smooth_alpha(
        uniform_wavelength, alpha, window_size=5
    )
    assert smoothed.shape == first.shape == second.shape == alpha.shape
    np.testing.assert_allclose(smoothed, alpha, atol=1e-10)

    nonuniform_wavelength = np.array([0, 1, 2, 4, 7, 11], dtype=float)
    smoothed, first, second = multi._smooth_alpha(
        nonuniform_wavelength, np.arange(6, dtype=float), window_size=3
    )
    assert smoothed.shape == first.shape == second.shape == nonuniform_wavelength.shape
    assert np.isfinite(first).all()
    assert np.isfinite(second).all()


def test_inflection_helpers_trim_edges_and_store_derived_frames():
    multi = MultiMeasurement('sample')
    arrays = tuple(np.arange(1, 7, dtype=float) for _ in range(4))

    trimmed = multi._trim_inflection_edges(*arrays, edge_points_to_remove=1)
    assert all(len(values) == len(arrays[0]) - 2 for values in trimmed)
    np.testing.assert_array_equal(trimmed[0], [2, 3, 4, 5])

    untrimmed = multi._trim_inflection_edges(*arrays, edge_points_to_remove=3)
    assert all(actual is expected for actual, expected in zip(untrimmed, arrays))

    multi._store_inflection_data(*arrays)
    assert set(multi.derived_data) == {
        'normalized_smoothed_alpha',
        'smoothed_alpha',
        '1st_deriv_alpha',
        '2nd_deriv_alpha',
    }
    np.testing.assert_allclose(
        multi.derived_data['normalized_smoothed_alpha']['normalized_smoothed_alpha'],
        np.linspace(0, 1, 6),
    )
    np.testing.assert_allclose(
        multi.derived_data['smoothed_alpha']['Energy'], 1239.84 / arrays[0]
    )


def test_threshold_helpers_select_alpha_source_and_find_bandgap_region():
    multi = MultiMeasurement('sample')
    energies = np.array([3.0, 2.0, 1.0, 0.5])
    multi.derived_data = {
        'alpha': pd.DataFrame({'Energy': energies, 'alpha': [0.1, 0.6, 0.8, 0.9]}),
        'normalized_alpha': pd.DataFrame(
            {'Energy': energies, 'normalized_alpha': [0.0, 0.6, 0.8, 0.9]}
        ),
        'smoothed_alpha': pd.DataFrame({'smoothed_alpha': [0.1, 0.2, 0.3, 0.4]}),
    }

    alpha_df, normalized = multi._threshold_alpha('normalized')
    assert alpha_df is multi.derived_data['normalized_alpha']
    np.testing.assert_array_equal(normalized, [0.0, 0.6, 0.8, 0.9])
    alpha_df, raw = multi._threshold_alpha('default')
    assert alpha_df is multi.derived_data['alpha']
    np.testing.assert_array_equal(raw, [0.1, 0.6, 0.8, 0.9])

    assert multi._has_threshold_data(min_alpha=1) is True
    assert multi._find_threshold_energy(energies, normalized, 0.5, 2) == pytest.approx(
        1.5
    )
    assert np.isnan(multi._find_threshold_energy(energies, normalized, 0.95, 2))
    with pytest.raises(ValueError, match='Unknown method'):
        multi._threshold_alpha('other')


def test_tauc_fit_helpers_find_and_resolve_linear_bandgap():
    energy = np.arange(1.0, 6.0)
    tauc = 2 * energy - 3
    fit_result = MultiMeasurement._find_tauc_fit(
        energy, tauc, window_size=3, min_slope=1
    )

    bandgap, correlation, region, center = MultiMeasurement('sample')._resolve_tauc_fit(
        np.array([0.5, 0.6]), fit_result, min_r=0.9, min_slope=1
    )
    assert bandgap == pytest.approx(1.5)
    assert correlation == pytest.approx(1)
    assert region == (0, 3)
    assert center == pytest.approx(1.5)
    assert fit_result[3].coef_[0] == pytest.approx(2)

    no_fit = MultiMeasurement._find_tauc_fit(
        energy, -energy, window_size=3, min_slope=1
    )
    no_bandgap = MultiMeasurement('sample')._resolve_tauc_fit(
        np.array([0.5]), no_fit, min_r=0.9, min_slope=1
    )
    assert all(np.isnan(value) for value in no_bandgap)


def test_raman_mapping_position_and_spectrum_helpers():
    assert MappingRamanMeas._has_mapping_positions(
        SimpleNamespace(xpos=[1, 2], ypos=[3, 4])
    )
    assert not MappingRamanMeas._has_mapping_positions(
        SimpleNamespace(xpos=[1], ypos=[3])
    )
    assert not MappingRamanMeas._has_mapping_positions(SimpleNamespace(xpos=[1]))

    measurement = RamanMeas()
    MappingRamanMeas._set_spectrum_data(measurement, [100, 200, 300], [[1, 2], [3, 4]])
    assert measurement.data.to_dict('list') == {
        'wavenumber': [100, 200, 300],
        'intensity': [1, 2, 3],
    }


def test_read_mapping_spectra_flattens_grid_and_assigns_positions_images():
    reader = SimpleNamespace(
        spectra=np.array([[[1, 2, 3], [4, 5, 6]]]),
        xdata=np.array([100, 200, 300]),
        xpos=np.array([10, 20]),
        ypos=np.array([1, 2]),
        laser_length=532,
    )
    mapping = MappingRamanMeas()
    first_image = object()

    mapping._read_mapping_spectra(reader, [first_image], verbose=False)

    assert len(mapping.raman_meas_list) == len(reader.xpos)
    first, second = mapping.raman_meas_list
    assert (first.x_pos, first.y_pos, first.laser_wavelength) == (-10, 1, 532)
    assert first.image is first_image
    assert first.data['intensity'].tolist() == [1, 2, 3]
    assert (second.x_pos, second.y_pos) == (-20, 2)
    assert second.image is None
    assert second.data['intensity'].tolist() == [4, 5, 6]


def test_decode_wxdb_images_decodes_jpeg_and_preserves_failed_slots(capsys):
    image_buffer = io.BytesIO()
    Image.new('RGB', (2, 3), color='red').save(image_buffer, format='JPEG')
    valid_jpeg = image_buffer.getvalue()
    corrupt_jpeg = b'\xff\xd8\xffnot-a-jpeg\xff\xd9'

    images = MappingRamanMeas._decode_wxdb_images(
        b'prefix' + valid_jpeg + b'gap' + corrupt_jpeg, io, Image, verbose=True
    )
    output = capsys.readouterr().out

    assert images[0].size == (2, 3)
    assert images[1] is None
    assert 'Successfully extracted image 1' in output
    assert 'Failed to extract image 2' in output


def test_extract_optical_images_from_reader_handles_missing_wxdb():
    mapping = MappingRamanMeas()
    assert mapping._extract_optical_images_from_reader(SimpleNamespace()) == []
    assert (
        mapping._extract_optical_images_from_reader(
            SimpleNamespace(file_obj=io.BytesIO(), block_info={})
        )
        == []
    )


def test_normalize_intensity_uses_requested_range_and_handles_zero_spectra():
    mapping = MappingRamanMeas()
    regular = RamanMeas()
    regular.data = pd.DataFrame({'wavenumber': [100, 200, 300], 'intensity': [2, 8, 4]})
    zero = RamanMeas()
    zero.data = pd.DataFrame({'wavenumber': [100, 200], 'intensity': [0, 0]})
    mapping.raman_meas_list = [regular, zero]

    mapping.normalize_intensity(x_range=(100, 200))

    np.testing.assert_allclose(regular.data['norm_intensity'], [0.25, 1, 0.5])
    np.testing.assert_array_equal(zero.data['norm_intensity'], [0, 0])
