import pytest
from nomad.datamodel import EntryArchive
from nomad.utils import get_logger

from nomad_dtu_nanolab_plugin.parsers.myparser import MyParser


@pytest.mark.usefixtures('caplog')
def test_parse_file():
    parser = MyParser()
    archive = EntryArchive()
    parser.parse('tests/data/example.out', archive, get_logger(__name__))

    assert archive.results.material.elements == ['H', 'O']
