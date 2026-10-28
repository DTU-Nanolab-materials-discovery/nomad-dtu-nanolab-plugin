from importlib import import_module
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from nomad.units import ureg

rt = import_module('nomad_dtu_nanolab_plugin.schema_packages.rt')
rtp = import_module('nomad_dtu_nanolab_plugin.schema_packages.rtp')


class _RawFile:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _ArchiveContext:
    def raw_file(self, name, *_args, **_kwargs):
        return _RawFile(name)


def _measurement(measurement_type='T', **metadata):
    return SimpleNamespace(
        metadata={'MeasurementType': measurement_type, **metadata},
        data={
            'Wavelength': SimpleNamespace(values=np.array([400, 600, 800])),
            'Intensity': np.array([10.0, 50.0, 90.0]),
        },
    )


def test_single_point_spectrum_parses_geometry_and_polarization():
    logger = SimpleNamespace(debug=lambda *_args: None)

    spectrum, has_geometry = rt.RTMeasurement._single_point_spectrum(
        _measurement(
            'T',
            DetectorAngle='15',
            SampleAngle='30',
            Polarization='p',
            PolarizationAngle='45',
        ),
        'sample.csv',
        logger,
    )

    assert spectrum.spectrum_type == 'Transmission'
    assert spectrum.wavelength.to('nm').magnitude.tolist() == [400, 600, 800]
    assert spectrum.intensity.tolist() == pytest.approx([0.1, 0.5, 0.9])
    assert spectrum.detector_angle.to('degree').magnitude == pytest.approx(15)
    assert spectrum.sample_angle.to('degree').magnitude == pytest.approx(30)
    assert spectrum.polarization == 'p'
    assert has_geometry


def test_single_point_spectrum_uses_filename_and_rejects_incomplete_data():
    logger = SimpleNamespace(debug=lambda *_args: None)
    measurement = _measurement('Unknown')

    spectrum, has_geometry = rt.RTMeasurement._single_point_spectrum(
        measurement, 'measurement_T.csv', logger
    )
    assert spectrum.spectrum_type == 'Transmission'
    assert not has_geometry

    measurement.data.pop('Intensity')
    spectrum, has_geometry = rt.RTMeasurement._single_point_spectrum(
        measurement, 'measurement_R.csv', logger
    )
    assert spectrum is None
    assert not has_geometry


def test_normalize_single_point_csv_creates_position_and_infers_accessory(
    monkeypatch,
):
    parsed_measurement = _measurement('R', DetectorAngle='20')
    monkeypatch.setattr(
        rt.autosampler_reader,
        'parse_file',
        lambda *_args, **_kwargs: [parsed_measurement],
    )
    measurement = rt.RTMeasurement(data_file=['run_R.csv', 'unused.csv'])
    archive = SimpleNamespace(m_context=_ArchiveContext())
    logger = SimpleNamespace()

    measurement._normalize_single_point_csv(archive, logger)

    assert len(measurement.results) == 1
    result = measurement.results[0]
    assert result.name == 'run_R'
    assert result.x_absolute.to('mm').magnitude == 0
    assert result.y_absolute.to('mm').magnitude == 0
    assert result.spectra[0].spectrum_type == 'Reflection'
    assert measurement.accessory == 'UMA'


def test_spectrum_average_uses_visible_wavelength_band_and_exact_configuration():
    measurement = rt.RTMeasurement()
    spectrum = rt.RTSpectrum(
        spectrum_type='Reflection',
        detector_angle=10 * ureg('degree'),
        sample_angle=20 * ureg('degree'),
        polarization='s',
        wavelength=np.array([399, 400, 600, 800, 801]) * ureg('nm'),
        intensity=np.array([0.0, 0.2, 0.4, 0.6, 1.0]),
    )
    result = rt.RTResult(spectra=[spectrum])
    config = ('Reflection', 10.0, 20.0, 's')

    assert measurement._compute_avg_for_config(result, config) == pytest.approx(0.4)
    assert np.isnan(
        measurement._compute_avg_for_config(result, ('Reflection', 10.0, 20.0, 'p'))
    )


def test_collect_config_values_skips_results_without_complete_position():
    measurement = rt.RTMeasurement(
        results=[
            rt.RTResult(
                x_absolute=1 * ureg('mm'),
                y_absolute=2 * ureg('mm'),
                spectra=[
                    rt.RTSpectrum(
                        spectrum_type='Transmission',
                        wavelength=np.array([500, 700]) * ureg('nm'),
                        intensity=np.array([0.2, 0.4]),
                    )
                ],
            ),
            rt.RTResult(x_absolute=3 * ureg('mm')),
        ]
    )
    configs = measurement._get_spectrum_configs()

    positions, values = measurement._collect_config_values(configs)

    assert positions == [(1, 2)]
    assert values == [[pytest.approx(0.3)]]


def test_autosampler_grid_plot_includes_boundary_baseline_and_samples():
    measurement = rt.DtuAutosamplerMeasurement()
    grid = pd.DataFrame(
        {
            'X': [0.0, 10.0, 20.0],
            'Y': [0.0, 5.0, 10.0],
            'Sample Name': ['Baseline', 'Library_A', 'Library_A'],
            'Xsample': [0.0, 1.0, 2.0],
            'Ysample': [0.0, 3.0, 4.0],
        }
    )

    measurement._append_grid_figure(grid)

    figure = measurement.figures[0].figure
    assert measurement.figures[0].label == 'Measurement Grid Layout'
    assert [trace['name'] for trace in figure['data']] == [
        'Autosampler Boundary',
        'Baseline Center',
        'Library_A',
    ]
    assert figure['data'][2]['customdata'] == [[1.0, 3.0], [2.0, 4.0]]


def test_store_log_timeseries_converts_units_and_respects_overwrite():
    process = rtp.DtuRTP()
    parsed = SimpleNamespace(
        timeseries={
            'time_s': [0, 5],
            'temperature_k': [273.15, 373.15],
            'pressure_pa': [133.322368421, 266.644736842],
            'ar_flow_m3_s': [rtp.SCCM_TO_M3_S, 2 * rtp.SCCM_TO_M3_S],
        },
        steps=[SimpleNamespace(name='Heat', start_time_s=0, end_time_s=5)],
    )

    process._store_log_timeseries(parsed, overwrite=False)
    assert process._log_time_s == [0, 5]
    assert process._log_temperature_c == pytest.approx([0, 100])
    assert process._log_pressure_torr == pytest.approx([1, 2])
    assert process._log_ar_flow_sccm == pytest.approx([1, 2])
    assert process._log_phase_segments == [('Heat', 0, 5)]

    process._log_time_s = [99]
    process._store_log_timeseries(parsed, overwrite=False)
    assert process._log_time_s == [99]
    process._store_log_timeseries(parsed, overwrite=True)
    assert process._log_time_s == [0, 5]


def test_store_log_timeseries_keeps_nonfinite_values_as_nan():
    process = rtp.DtuRTP()
    parsed = SimpleNamespace(
        timeseries={'temperature_k': [273.15, np.inf, np.nan]},
        steps=[],
    )

    process._store_log_timeseries(parsed, overwrite=True)

    assert process._log_temperature_c[0] == pytest.approx(0)
    assert np.isnan(process._log_temperature_c[1])
    assert np.isnan(process._log_temperature_c[2])


def test_store_log_overview_counts_dwell_steps_and_preserves_manual_values():
    original_dwell_count = 7
    expected_heating_time = 12
    expected_annealing_temperature = 600
    process = rtp.DtuRTP()
    process.overview = rtp.RTPOverview(no_dwell_steps=original_dwell_count)
    parsed = SimpleNamespace(
        overview={
            'total_heating_time': expected_heating_time,
            'annealing_temperature': expected_annealing_temperature,
        },
        steps=[
            SimpleNamespace(name='1st Dwell'),
            SimpleNamespace(name='Annealing'),
            SimpleNamespace(name='Ramp'),
        ],
    )

    process._store_log_overview(parsed, has_detected_annealing=True, overwrite=False)
    assert process.overview.no_dwell_steps == original_dwell_count
    assert (
        process.overview.total_heating_time.to('s').magnitude == expected_heating_time
    )
    assert (
        process.overview.annealing_temperature.to('K').magnitude
        == expected_annealing_temperature
    )

    process._store_log_overview(parsed, has_detected_annealing=True, overwrite=True)
    assert process.overview.no_dwell_steps == len(parsed.steps) - 1


def test_sync_step_sources_preserves_existing_sources_unless_overwriting():
    process = rtp.DtuRTP(used_gases=['Ar', 'PH3'])
    existing = rtp.DtuRTPSources(name='Manual', sources=['Manual'])
    step = rtp.DTURTPSteps(name='Process', sources=[existing])
    process.steps = [step]

    process._sync_step_sources_from_used_gases()
    assert step.sources == [existing]

    process._sync_step_sources_from_used_gases(overwrite=True)
    assert [source.name for source in step.sources] == ['Ar', 'PH3']
    assert [source.sources for source in step.sources] == [['Ar'], ['PH3']]


def test_build_phase_segments_uses_log_boundaries_or_positive_step_durations():
    process = rtp.DtuRTP()
    process.steps = [
        rtp.DTURTPSteps(
            name=' Heat ',
            step_overview=rtp.RTPStepOverview(duration=4 * ureg('s')),
        ),
        rtp.DTURTPSteps(
            name='Ignored',
            step_overview=rtp.RTPStepOverview(duration=0 * ureg('s')),
        ),
        rtp.DTURTPSteps(
            name='Cool',
            step_overview=rtp.RTPStepOverview(duration=6 * ureg('s')),
        ),
    ]

    assert process._build_phase_segments() == [
        ('Heat', 0.0, 4.0),
        ('Cool', 4.0, 10.0),
    ]

    process._log_phase_segments = [('Actual Heat', 15.0, 20.0)]
    assert process._build_phase_segments() == [('Actual Heat', 15.0, 20.0)]


def test_normalize_temperature_profile_prefers_complete_log_series():
    process = rtp.DtuRTP()
    process._log_time_s = [0, 1, 2]
    process._log_temperature_c = [20, 200, 400]

    process._normalize_temperature_profile(SimpleNamespace(warning=lambda *_: None))

    assert process._time == [0, 1, 2]
    assert process._temperature_profile == [20, 200, 400]


def test_find_gas_shutoff_ignores_noise_and_stays_within_cooling_segment():
    shutoff_time_s = 10
    process = rtp.DtuRTP()
    process._log_ar_flow_sccm = [0, 2.0, 0.5, 0]
    process._log_n2_flow_sccm = [0, 0, 0, 0]
    process._log_ph3_flow_sccm = [0, 0, 0, 0]
    process._log_h2s_flow_sccm = [0, 0, 0, 0]

    assert process._find_gas_shutoff_time([0, 5, 10, 15], 5, 15) == shutoff_time_s
    assert process._find_gas_shutoff_time([0, 5, 10], 5, 10) is None
