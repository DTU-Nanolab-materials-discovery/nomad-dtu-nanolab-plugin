import importlib
import os.path
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from nomad.client import normalize_all, parse
from nomad_material_processing.general import RectangleCuboid

from nomad_dtu_nanolab_plugin.schema_packages.sample import DTUCombinatorialLibrary
from nomad_dtu_nanolab_plugin.schema_packages.sputtering import (
    DepositionParameters,
    DTUSputtering,
    DtuSubstrateMounting,
)
from nomad_dtu_nanolab_plugin.schema_packages.substrate import DTUSubstrate

sputtering_schema = importlib.import_module(
    'nomad_dtu_nanolab_plugin.schema_packages.sputtering'
)


def test_schema():
    test_file = os.path.join('tests', 'data', 'test_logfile.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    assert entry_archive.data.deposition_parameters.deposition_temperature.to(
        'K'
    ).magnitude == pytest.approx(473.11482589301943)


def test_mounting_accepts_combinatorial_library_and_preserves_parent(monkeypatch):
    origin = DTUCombinatorialLibrary(
        name='origin',
        lab_id='origin-library',
        elemental_composition=[{'element': 'Zr'}],
    )
    origin.geometry = RectangleCuboid()
    origin.substrate = None

    mounting = DtuSubstrateMounting(
        name='BR',
        input_combi_lib=origin,
        position_x=0.02,
        position_y=0.035,
    )
    sputtering = DTUSputtering(
        name='capping',
        lab_id='capping-run',
        substrates=[mounting],
        deposition_parameters=DepositionParameters(material_space='Zr-Ta'),
    )

    created = []

    def fake_create_archive(section, archive, filename, overwrite=False):
        created.append((section, filename))
        return section

    monkeypatch.setattr(sputtering_schema, 'create_archive', fake_create_archive)
    sputtering.add_libraries(type('Archive', (), {})(), Mock())

    assert len(sputtering.samples) == 1
    derived = created[-1][0]
    assert derived.parent_library.reference is origin
    assert derived.parent_library.lab_id == 'origin-library'
    assert derived.geometry is origin.geometry
    assert [item.element for item in derived.elemental_composition] == ['Zr', 'Ta']
    assert len(derived.layers) == 1
    assert derived.layers[0].lab_id.endswith('-Layer')


def test_substrate_only_mounting_behavior_is_preserved(monkeypatch):
    substrate = DTUSubstrate(name='blank', lab_id='blank-substrate')
    mounting = DtuSubstrateMounting(
        name='FR',
        substrate=substrate,
        position_x=0.02,
        position_y=-0.005,
    )
    sputtering = DTUSputtering(
        name='main',
        lab_id='main-run',
        substrates=[mounting],
        deposition_parameters=DepositionParameters(material_space='Ba-Zr'),
    )

    created = []

    def fake_create_archive(section, archive, filename, overwrite=False):
        created.append((section, filename))
        return section

    monkeypatch.setattr(sputtering_schema, 'create_archive', fake_create_archive)
    sputtering.add_libraries(type('Archive', (), {})(), Mock())

    assert len(sputtering.samples) == 1
    derived = created[-1][0]
    assert derived.parent_library is None
    assert derived.substrate.reference is substrate
    assert [item.element for item in derived.elemental_composition] == ['Ba', 'Zr']


def test_output_library_is_created_without_available_composition(monkeypatch):
    substrate = DTUSubstrate(name='blank', lab_id='blank-substrate')
    sputtering = DTUSputtering(
        name='partial',
        lab_id='partial-run',
        substrates=[
            DtuSubstrateMounting(
                name='BL',
                substrate=substrate,
                position_x=-0.02,
                position_y=0.035,
            )
        ],
        deposition_parameters=None,
    )

    monkeypatch.setattr(
        sputtering_schema,
        'create_archive',
        lambda section, archive, filename, overwrite=False: section,
    )
    logger = Mock()
    sputtering.add_libraries(type('Archive', (), {})(), logger)

    assert len(sputtering.samples) == 1
    assert sputtering.samples[0].lab_id == 'partial-run_BL'
    logger.warning.assert_called_once()


def test_incomplete_log_parse_preserves_manually_entered_data(monkeypatch):
    archive = SimpleNamespace(
        m_context=SimpleNamespace(
            raw_file=lambda *args: nullcontext(SimpleNamespace(name='sample.csv'))
        )
    )
    sputtering = DTUSputtering(
        name='partial',
        lab_id='partial-run',
        log_file='sample.csv',
        steps=[],
        flags=[],
    )
    logger = Mock()

    monkeypatch.setattr(sputtering_schema, 'read_logfile', lambda _: object())
    monkeypatch.setattr(sputtering_schema, 'format_logfile', lambda _: (object(), []))
    monkeypatch.setattr(sputtering_schema, 'read_events', lambda _: ([], {}, {}))
    monkeypatch.setattr(sputtering_schema, 'generate_plots', lambda *args: {})
    monkeypatch.setattr(
        sputtering_schema.DTUSputtering,
        'plot_plotly_chamber_config',
        lambda *args: {},
    )
    monkeypatch.setattr(sputtering_schema.DTUSputtering, 'plot', lambda *args: None)
    monkeypatch.setattr(
        sputtering_schema.DTUSputtering,
        'correct_platen_angle',
        lambda *args: None,
    )
    monkeypatch.setattr(
        sputtering_schema.DTUSputtering,
        'write_sulfur_pressure',
        lambda *args: None,
    )
    monkeypatch.setattr(
        sputtering_schema.DTUSputtering,
        'generate_general_log_data',
        lambda *args: pytest.fail('incomplete parse must not overwrite manual data'),
    )

    sputtering.parse_log_file(archive, logger)

    logger.warning.assert_called_once()
