import os.path

from nomad.client import normalize_all, parse


def test_schema():
    test_library = os.path.join('tests', 'data', 'test_cobilib.archive.yaml')
    entry_archive2 = parse(test_library)[0]
    normalize_all(entry_archive2)

    test_cleave = os.path.join('tests', 'data', 'test_cleaving.archive.yaml')
    entry_archive = parse(test_cleave)[0]
    normalize_all(entry_archive)

    cleaving = entry_archive.data
    library = entry_archive2.data

    cleaving.input_library = library
    cleaving.create_from_pattern = True
    cleaving.pattern = 'squares'
    cleaving.number_of_pieces = 2


    normalize_all(entry_archive)
    assumed_pieces = cleaving.number_of_pieces** 2
    assert cleaving.new_pieces == assumed_pieces