import os.path

from nomad.client import normalize_all, parse


def test_cleaving():
    test_library = os.path.join('tests', 'data', 'test_cobilib.archive.yaml')
    entry_archive2 = parse(test_library)[0]
    normalize_all(entry_archive2)

    test_cleave = os.path.join('tests', 'data', 'test_cleaving.archive.yaml')
    entry_archive = parse(test_cleave)[0]
    normalize_all(entry_archive)

    test_substrate = os.path.join('tests', 'data', 'test_substrate.archive.yaml')
    entry_archive3 = parse(test_substrate)[0]
    normalize_all(entry_archive3)

    cleaving = entry_archive.data
    library = entry_archive2.data
    substrate = entry_archive3.data

    library.lab_id= 'mittma_0000_test_BL'
    library.name= 'mittma 0000 test BL'
    library.substrate= substrate

    cleaving.combinatorial_Library = library
    #cleaving.library_size = [40, 40]
    cleaving.create_from_pattern = True
    cleaving.pattern = 'squares'
    cleaving.number_of_pieces = 2


    normalize_all(entry_archive)
    normalize_all(entry_archive2)
    normalize_all(entry_archive3)

    #assumed_pieces = cleaving.number_of_pieces** 2
    #assert len(cleaving.new_pieces) == assumed_pieces
    input_width = 100
    assert cleaving.combinatorial_Library is not None
    assert cleaving.combinatorial_Library.geometry.width == input_width