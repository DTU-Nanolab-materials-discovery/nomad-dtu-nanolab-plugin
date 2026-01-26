"""
Quick test script to verify Raman data parsing
Run with: python -m pytest test_raman_parsing.py -v -s
Or just: python test_raman_parsing.py (if nomad is installed)
"""

import os
import sys

NBR_SPECTRA = 2  # Number of spectra to print detailed info for

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from nomad.client import normalize_all, parse

    test_file_path = os.path.join('tests', 'data', 'test_raman.archive.yaml')

    print('Parsing Raman test file...')
    entry_archive = parse(test_file_path)[0]

    print('Normalizing archive...')
    normalize_all(entry_archive)

    print(f'\n✓ Successfully parsed {len(entry_archive.data.results)} Raman spectra\n')

    print('Results:')
    for i, result in enumerate(entry_archive.data.results):
        print(f'  {i + 1}. {result.name}')
        print(f'     - Position: x={result.x_absolute}, y={result.y_absolute}')
        print(f'     - Laser wavelength: {result.laser_wavelength}')
        print(f'     - Data points: {len(result.raman_shift)}')
        if i < NBR_SPECTRA:  # Show first few data points for first 2 spectra
            print(
                "- Raman shift range:",
                f"{min(result.raman_shift)} - {max(result.raman_shift)}"
            )
            print(
                "- Intensity range:",
                f"{min(result.intensity)} - {max(result.intensity)}"
            )

    print(f'\nTotal results: {len(entry_archive.data.results)}')

    # Generate expected names list for test
    print('\n' + '=' * 60)
    print('For test_measurements.py, use this list:')
    print('=' * 60)
    names = [r.name for r in entry_archive.data.results]
    import json

    print(json.dumps(names, indent=4))

except ModuleNotFoundError as e:
    print(f'Error: {e}')
    print('\nTo run this test, first install the package:')
    print("  pip install -e '.[dev]'")
    print('\nThen run:')
    print('  python test_raman_parsing.py')
    print('OR')
    print(
        '  pytest tests/schema_packages/test_measurements.py::test_schema[raman] -v -s'
    )
