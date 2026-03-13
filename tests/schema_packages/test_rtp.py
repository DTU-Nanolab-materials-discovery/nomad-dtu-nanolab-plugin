import os.path
from types import SimpleNamespace

import pytest
from nomad.client import normalize_all, parse

import nomad_dtu_nanolab_plugin.schema_packages.rtp as rtp_schema
from nomad_dtu_nanolab_plugin.rtp_log_reader import ParsedRTPData, ParsedRTPStep
from nomad_dtu_nanolab_plugin.schema_packages.rtp import (
    DtuRTP,
    DtuRTPSources,
    DTURTPSteps,
    RTPOverview,
)


def test_schema():
    test_file = os.path.join('tests', 'data', 'test_rtp_2.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert (
        entry_archive.data.steps[0].step_overview.temperature_ramp.units
        == 'kelvin / second'
    )
    assert entry_archive.data.steps[
        0
    ].step_overview.temperature_ramp.magnitude == pytest.approx(1.5277777777777777)


def _mock_input_sample_with_elements(*elements: str):
    composition = [SimpleNamespace(element=element) for element in elements]
    layer_ref = SimpleNamespace(elemental_composition=composition)
    origin = SimpleNamespace(
        layers=[SimpleNamespace(reference=layer_ref)],
        elemental_composition=composition,
    )
    return SimpleNamespace(input_combi_lib=origin)


def _mock_rtp_for_material_space(
    *, material_space=None, used_gases=None, input_samples=None
):
    rtp = SimpleNamespace(
        overview=RTPOverview(material_space=material_space),
        used_gases=used_gases,
        input_samples=input_samples or [],
    )
    rtp._get_input_sample_material_elements = (  # noqa: SLF001
        lambda: DtuRTP._get_input_sample_material_elements(rtp)
    )
    return rtp


def test_material_space_is_none_without_input_sample_composition():
    """Gas-only runs must not produce a material_space."""
    rtp = _mock_rtp_for_material_space(used_gases=['PH3', 'H2S'])

    DtuRTP._autofill_material_space(rtp)

    assert rtp.overview.material_space is None


def test_material_space_is_none_when_stale_value_and_no_input_sample():
    """A stale P-S must be cleared when no input sample is present."""
    rtp = _mock_rtp_for_material_space(material_space='P-S', used_gases=['PH3', 'H2S'])

    DtuRTP._autofill_material_space(rtp)

    assert rtp.overview.material_space is None


def test_material_space_derives_from_input_sample_and_adds_gas_elements():
    """Input sample composition comes first; new gas-derived elements are appended."""
    rtp = _mock_rtp_for_material_space(
        material_space='P-S',
        used_gases=['PH3', 'H2S'],
        input_samples=[_mock_input_sample_with_elements('Sn', 'P')],
    )

    DtuRTP._autofill_material_space(rtp)

    assert rtp.overview.material_space == 'Sn-P-S'


def test_sync_step_sources_populates_only_empty_steps_without_overwrite():
    rtp = DtuRTP(used_gases=['PH3', 'H2S'])

    step_empty = DTURTPSteps(name='Step with empty sources')
    step_existing = DTURTPSteps(name='Step with manual source')
    manual_source = DtuRTPSources(name='Manual', sources=['Xe'])
    step_existing.sources = [manual_source]
    rtp.steps = [step_empty, step_existing]

    rtp._sync_step_sources_from_used_gases(overwrite=False)

    assert [src.name for src in step_empty.sources] == ['PH3', 'H2S']
    assert [src.sources for src in step_empty.sources] == [['PH3'], ['H2S']]

    # Existing user/manual sources must be kept when overwrite is disabled.
    assert len(step_existing.sources) == 1
    assert step_existing.sources[0].name == 'Manual'
    assert step_existing.sources[0].sources == ['Xe']


def test_parse_log_files_preserves_existing_data_without_overwrite(
    tmp_path, monkeypatch
):
    eklipse_file = tmp_path / 'eklipse.csv'
    diagnostics_file = tmp_path / 'diagnostics.txt'
    eklipse_file.write_text('timestamp\n2026-01-01 00:00:00\n', encoding='utf-8')
    diagnostics_file.write_text('dummy\n', encoding='utf-8')

    parsed = ParsedRTPData(
        used_gases=['PH3', 'H2S'],
        base_pressure_pa=111.0,
        base_pressure_ballast_pa=222.0,
        rate_of_rise_pa_s=333.0,
        chiller_flow_m3_s=444.0,
        overview={
            'annealing_pressure': 555.0,
            'annealing_time': 666.0,
            'annealing_temperature': 777.0,
            'annealing_ar_flow': 0.0,
            'annealing_n2_flow': 0.0,
            'annealing_ph3_in_ar_flow': 0.0,
            'annealing_h2s_in_ar_flow': 0.0,
            'total_heating_time': 10.0,
            'total_cooling_time': 20.0,
            'end_of_process_temperature': 300.0,
        },
        steps=[
            ParsedRTPStep(
                name='Parsed step',
                duration_s=15.0,
                initial_temperature_k=300.0,
                final_temperature_k=500.0,
                pressure_pa=555.0,
                ar_flow_m3_s=0.0,
                n2_flow_m3_s=0.0,
                ph3_in_ar_flow_m3_s=0.0,
                h2s_in_ar_flow_m3_s=0.0,
            )
        ],
        timeseries={
            'time_s': [0.0, 1.0],
            'temperature_c': [25.0, 26.0],
            'temperature_setpoint_c': [],
            'lamp_power': [],
            'pressure_torr': [],
            'ar_flow_sccm': [],
            'n2_flow_sccm': [],
            'ph3_in_ar_flow_sccm': [],
            'h2s_in_ar_flow_sccm': [],
        },
    )

    monkeypatch.setattr(rtp_schema, 'parse_rtp_logfiles', lambda **kwargs: parsed)

    class DummyContext:
        @staticmethod
        def raw_file(path, mode):
            raise FileNotFoundError(path)

    archive = SimpleNamespace(m_context=DummyContext())
    logger = SimpleNamespace(warning=lambda *args, **kwargs: None)

    rtp = DtuRTP(
        log_file_eklipse=str(eklipse_file),
        log_file_T2BDiagnostics=str(diagnostics_file),
        used_gases=['Ar'],
        base_pressure=42.0,
        base_pressure_ballast=43.0,
        rate_of_rise=44.0,
        chiller_flow=45.0,
        overview=RTPOverview(annealing_pressure=99.0, annealing_time=88.0),
    )
    rtp.steps = [DTURTPSteps(name='Existing step')]

    rtp.parse_log_files(archive, logger, overwrite=False)

    assert rtp.used_gases == ['Ar']
    assert rtp.steps[0].name == 'Existing step'

    assert float(
        getattr(rtp.base_pressure, 'magnitude', rtp.base_pressure)
    ) == pytest.approx(42.0)
    assert float(
        getattr(rtp.base_pressure_ballast, 'magnitude', rtp.base_pressure_ballast)
    ) == pytest.approx(43.0)
    assert float(
        getattr(rtp.rate_of_rise, 'magnitude', rtp.rate_of_rise)
    ) == pytest.approx(44.0)
    assert float(
        getattr(rtp.chiller_flow, 'magnitude', rtp.chiller_flow)
    ) == pytest.approx(45.0)

    assert float(
        getattr(
            rtp.overview.annealing_pressure,
            'magnitude',
            rtp.overview.annealing_pressure,
        )
    ) == pytest.approx(99.0)
    assert float(
        getattr(rtp.overview.annealing_time, 'magnitude', rtp.overview.annealing_time)
    ) == pytest.approx(88.0)
