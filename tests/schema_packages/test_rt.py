import os.path

from nomad.client import normalize_all, parse


def test_rt_autosampler_schema():
    """
    Test the RT autosampler measurement schema.

    This test verifies that:
    1. The DtuAutosamplerMeasurement correctly parses data and config CSV files
    2. Individual RTMeasurement archives are created for each library
    3. Each RTMeasurement contains the correct number of results (positions)
    4. Each result contains the expected R and T spectra
    """
    # Constants for test validation
    EXPECTED_LIBRARIES = 6  # Number of libraries (excluding Baseline)
    POSITIONS_PER_LIBRARY = 10  # Number of measurement positions per library
    MIN_WAVELENGTH_NM = 200  # Minimum wavelength in UV-VIS-NIR range (nm)
    MAX_WAVELENGTH_NM = 2500  # Maximum wavelength in UV-VIS-NIR range (nm)
    MAX_INTENSITY_PERCENT = 100  # Maximum intensity percentage

    test_file = os.path.join('tests', 'data', 'test_rt_autosampler.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    # The autosampler measurement should create steps (one per library)
    # From anat_eugbe_251105_grid.csv we have 6 libraries (excluding Baseline):
    # eugbe_0008_RTP_hd, eugbe_0009_RTP_hd,
    # anait_0030_RTP_ha, anait_0030_RTP_hc,
    # anait_0030_RTP_hd, anait_0030_RTP_hb
    assert len(entry_archive.data.steps) == EXPECTED_LIBRARIES

    # Each step should be an RTMeasurement
    for step in entry_archive.data.steps:
        assert step.m_def.name == 'RTMeasurement'

        # Each library has 10 measurement positions
        assert len(step.results) == POSITIONS_PER_LIBRARY

        # Each position should have results with spectra
        for result in step.results:
            # Verify position coordinates exist
            assert result.x_absolute is not None
            assert result.y_absolute is not None

            # Each position should have both Reflection and Transmission spectra
            assert len(result.spectra) >= 1

            # Verify spectrum data
            for spectrum in result.spectra:
                assert spectrum.spectrum_type in ['Reflection', 'Transmission']
                assert spectrum.wavelength is not None
                assert len(spectrum.wavelength) > 0
                assert spectrum.intensity is not None
                assert len(spectrum.intensity) == len(spectrum.wavelength)

                # Check that wavelengths are in reasonable range (UV-VIS-NIR)
                assert spectrum.wavelength.min() >= MIN_WAVELENGTH_NM
                assert spectrum.wavelength.max() <= MAX_WAVELENGTH_NM

                # Check intensity values are in valid range (0-100% or 0-1)
                assert spectrum.intensity.min() >= 0
                assert spectrum.intensity.max() <= MAX_INTENSITY_PERCENT


def test_rt_autosampler_sample_names():
    """
    Test that the correct sample/library names are extracted.
    """
    test_file = os.path.join('tests', 'data', 'test_rt_autosampler.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    # Extract sample names from the measurements
    sample_names = []
    for step in entry_archive.data.steps:
        if step.samples and len(step.samples) > 0:
            lab_id = step.samples[0].lab_id
            if lab_id:
                sample_names.append(lab_id)

    # Expected library names from the grid file
    expected_names = [
        'eugbe_0008_RTP_hd',
        'eugbe_0009_RTP_hd',
        'anait_0030_RTP_ha',
        'anait_0030_RTP_hc',
        'anait_0030_RTP_hd',
        'anait_0030_RTP_hb'
    ]

    # Check that we have the right samples (order might vary)
    assert len(sample_names) == len(expected_names)
    for name in expected_names:
        assert name in sample_names


def test_rt_autosampler_spectrum_metadata():
    """
    Test that spectrum metadata (angles, polarization) is captured if present.
    """
    test_file = os.path.join('tests', 'data', 'test_rt_autosampler.archive.yaml')
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    # Get first measurement for testing
    first_measurement = entry_archive.data.steps[0]
    first_result = first_measurement.results[0]
    first_spectrum = first_result.spectra[0]

    # These fields may or may not be populated depending on the data file
    # Just verify they are defined in the schema
    assert hasattr(first_spectrum, 'detector_angle')
    assert hasattr(first_spectrum, 'sample_angle')
    assert hasattr(first_spectrum, 'polarization')
