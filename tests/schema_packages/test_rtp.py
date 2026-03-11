import os.path
from types import SimpleNamespace

import pytest
from nomad.client import normalize_all, parse

from nomad_dtu_nanolab_plugin.schema_packages.rtp import DtuRTP, RTPOverview


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
