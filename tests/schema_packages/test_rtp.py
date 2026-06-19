import os.path
import pytest

from nomad.client import normalize_all, parse

MIN_POSITIVE_TEMPERATURE_K = 273.15

def test_schema():
    test_file = os.path.join('tests', 'data', 'test_rtp.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    data = entry_archive.data

    # If used gases are detected,
    # each gas should have at least one corresponding source.
    if data.used_gases:
        gas_sources = set()
        for step in data.steps:
            for source in step.sources or []:
                for gas in source.sources or []:
                    gas_sources.add(gas)

        for gas in data.used_gases:
            assert gas in gas_sources
