import os.path
import shutil

import pytest
from nomad.client import normalize_all, parse

from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
    DTULibraryCleaving,
)


@pytest.mark.usefixtures("tmp_path")
def test_cleaving(tmp_path):
    test_library = os.path.join('tests', 'data', 'test_combilib.archive.yaml')
    tmp_file = tmp_path / "combilib.archive.yaml"
    shutil.copy(test_library, tmp_file)
    library_archive = parse(tmp_file)[0]
    normalize_all(library_archive)

    test_cleave = os.path.join('tests', 'data', 'test_cleaving.archive.yaml')
    tmp_file = tmp_path / "cleaving.archive.yaml"
    shutil.copy(test_cleave, tmp_file)
    cleaving_archive = parse(tmp_file)[0]
    normalize_all(cleaving_archive)

    test_substrate = os.path.join('tests', 'data', 'test_substrate.archive.yaml')
    tmp_file = tmp_path / "substrate.archive.yaml"
    shutil.copy(test_substrate, tmp_file)
    substrate_archive = parse(tmp_file)[0]
    normalize_all(substrate_archive)

    cleaving = cleaving_archive.data
    library = library_archive.data
    substrate = substrate_archive.data
    assert isinstance(cleaving, DTULibraryCleaving)
    assert isinstance(library, DTUCombinatorialLibrary)

    library.lab_id = 'mittma_0000_test_BL'
    library.name = 'mittma 0000 test BL'
    library.substrate = substrate

    cleaving.combinatorial_library = library
    cleaving.fetch_library_size = True
    cleaving.generate_pattern = True
    cleaving.pattern = 'horizontal stripes'
    cleaving.number_of_pieces = 2

    substrate_archive.data = substrate
    library_archive.data = library
    cleaving_archive.data = cleaving

    normalize_all(cleaving_archive)
    normalize_all(library_archive)
    normalize_all(substrate_archive)

    cleaving.create_child_libraries = True
    cleaving_archive.data = cleaving
    normalize_all(cleaving_archive)

    assumed_pieces = cleaving.number_of_pieces
    assert len(cleaving.new_pieces) == assumed_pieces
    assert len(cleaving.child_libraries) == len(cleaving.new_pieces)
