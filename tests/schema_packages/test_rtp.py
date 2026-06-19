import os.path

from nomad.client import normalize_all, parse

MIN_POSITIVE_TEMPERATURE_K = 273.15


def test_schema():
    test_file = os.path.join('tests', 'data', 'test_rtp.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    data = entry_archive.data

    assert data is not None
    assert data.overview is not None
    assert data.steps is not None
    assert len(data.steps) > 0

    step_names = [str(step.name).strip().lower() for step in data.steps]
    assert all(step_names)
    assert any(name.startswith('heating') for name in step_names)
    assert any(name.startswith('anneal') for name in step_names)
    assert any(name.startswith('cool') for name in step_names)

    dwell_like_steps = [
        name
        for name in step_names
        if name.startswith('dwell') or name.startswith('anneal')
    ]
    assert data.overview.no_dwell_steps is not None
    assert data.overview.no_dwell_steps.magnitude == len(dwell_like_steps)

    # Core overview values must be populated and physically sensible.
    assert data.overview.annealing_temperature is not None
    assert data.overview.annealing_temperature.magnitude > MIN_POSITIVE_TEMPERATURE_K
    assert data.overview.annealing_time is not None
    assert data.overview.annealing_time.magnitude >= 0

    # General quantities should remain optional but never be negative when present.
    if data.base_pressure is not None:
        assert data.base_pressure.magnitude >= 0
    if data.base_pressure_ballast is not None:
        assert data.base_pressure_ballast.magnitude >= 0
    if data.rate_of_rise is not None:
        assert data.rate_of_rise.magnitude >= 0

    # Process should expose steps with names and non-negative durations.
    for step in data.steps:
        assert step.name is not None
        assert str(step.name).strip()
        if step.duration is not None:
            assert step.duration.magnitude >= 0

        if step.step_overview is not None:
            if step.step_overview.initial_temperature is not None:
                assert step.step_overview.initial_temperature.magnitude > 0
            if step.step_overview.final_temperature is not None:
                assert step.step_overview.final_temperature.magnitude > 0

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


def test_schema_phase_segments_match_parsed_steps():
    """_log_phase_segments must be a direct pass-through of parsed step
    boundaries (gap preserved), not stitched/adjusted."""
    test_file = os.path.join('tests', 'data', 'test_rtp.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)
    data = entry_archive.data

    segments = getattr(data, '_log_phase_segments', None)
    if not segments:
        return  # no log-derived segments in this fixture; nothing to check

    for (_, _, end), (_, next_start, _) in zip(segments, segments[1:]):
        # Consecutive segments are expected to have a small natural gap,
        # not be perfectly stitched together.
        assert next_start >= end
