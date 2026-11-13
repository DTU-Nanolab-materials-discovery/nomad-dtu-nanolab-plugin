from unittest.mock import Mock

import pytest
from nomad_material_processing.combinatorial import CombinatorialSample

from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    Composition,
    DTUCombinatorialSample,
    SampleProperty,
)


@pytest.mark.parametrize(
    ('confidence', 'expected', 'warns'),
    [(None, None, False), (0, 1, True), (3, 3, False), (6, 5, True)],
)
def test_sample_property_confidence(confidence, expected, warns):
    logger = Mock()
    prop = SampleProperty(confidence=confidence)
    prop.normalize(None, logger)
    assert prop.confidence == expected
    assert logger.warning.called is warns
    if warns:
        assert str(confidence) in logger.warning.call_args.args[0]


@pytest.mark.parametrize('field', ['composition', 'surface_composition'])
def test_combinatorial_sample_normalizes_repeated_composition(monkeypatch, field):
    monkeypatch.setattr(CombinatorialSample, 'normalize', lambda *args: None)
    sample = DTUCombinatorialSample(**{field: [Composition(Cu=0.4, S=0.6)]})
    sample.normalize(None, Mock())
    fractions = {
        entry.element: entry.atomic_fraction for entry in sample.elemental_composition
    }
    assert fractions == pytest.approx({'Cu': 0.4, 'S': 0.6})
