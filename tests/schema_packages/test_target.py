import os.path

import pytest
from nomad.client import normalize_all, parse

from nomad_dtu_nanolab_plugin.schema_packages.target import DTUTarget


def test_target():
    test_file = os.path.join('tests', 'data', 'test_target.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)
    target = entry_archive.data
    assert isinstance(target, DTUTarget)
    symbol_map = {
        c.pure_substance.molecular_formula: idx
        for idx, c in enumerate(target.components)
    }
    assert 'Ag' in symbol_map
    assert target.lab_id == 'Ag_T_001'
    assert target.supplier_id == 'Testbourne'
    assert target.components[symbol_map['Ag']].mass_fraction == pytest.approx(0.999955)
