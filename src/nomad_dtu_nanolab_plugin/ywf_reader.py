"""Reader for saved photoluminescence traces in YSystems YWafer files."""

from __future__ import annotations

import csv
import io
import math
import re
import struct
from typing import Any

import numpy as np

TRACE_PATTERN = re.compile(rb'P\x00L\x001\x00 \x00#\x00(?:[0-9]\x00)+')
WAVELENGTH_LABEL = 'Wavelength'.encode('utf-16le')
COORDINATE_INTEGER_TOLERANCE = 1e-5
MINIMUM_SPECTRUM_POINTS = 50
MAXIMUM_SPECTRUM_POINTS = 10000
MINIMUM_WAVELENGTH_NM = 100
MAXIMUM_WAVELENGTH_NM = 3000


def read_ywa_metadata(data: bytes) -> dict[str, Any]:
    """Read wafer and scan metadata from a YSystems YWafer overview file."""
    text = data.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(text)))
    if not rows or not rows[0][0].startswith('YSystems -- YWafer'):
        raise ValueError('The overview file is not a YSystems YWafer .ywa file.')

    metadata: dict[str, Any] = {}
    version_match = re.search(r'YWafer\s+(v[\w.]+)', rows[0][0])
    if version_match:
        metadata['software_version'] = f'YWafer {version_match.group(1)}'

    fields = {
        'lot': 'lot_id',
        'wafer': 'wafer_number',
        'chamber': 'chamber',
        'datatype': 'data_type',
        'setup': 'measurement_setup',
    }
    numeric_fields = {
        'pitch': ('scan_pitch_mm', 2),
        'center': ('scan_center_mm', 2),
        'radius': ('wafer_radius_mm', 1),
        'exclusion': ('edge_exclusion_mm', 1),
        'flat': ('wafer_flat_angle_deg', 1),
    }
    for row in rows[1:]:
        if not row or not row[0]:
            continue
        key = row[0].strip().lower()
        values = [value.strip() for value in row[1:]]
        if key in fields and values and values[0]:
            metadata[fields[key]] = values[0]
        elif key in numeric_fields and values:
            target, count = numeric_fields[key]
            if len(values) < count or any(not value for value in values[:count]):
                continue
            try:
                numbers = [float(value) for value in values[:count]]
            except ValueError as exc:
                raise ValueError(f'Invalid numeric value for YWafer {key}.') from exc
            metadata[target] = numbers if count > 1 else numbers[0]
        if key == 'xadr':
            break
    return metadata


def _float32(data: bytes, offset: int) -> float:
    return struct.unpack_from('<f', data, offset)[0]


def _clean_coordinate(value: float) -> float | int:
    if (
        math.isfinite(value)
        and abs(value - round(value)) < COORDINATE_INTEGER_TOLERANCE
    ):
        return int(round(value))
    return value


def _trace_records(data: bytes) -> list[dict[str, Any]]:
    records = []
    for match in TRACE_PATTERN.finditer(data):
        name = match.group().decode('utf-16le')
        record_start = match.start() - 4
        if record_start < 0:
            continue

        record_data_start = record_start + 4 + 2 * len(name)
        x_offset = record_data_start + 437
        y_offset = record_data_start + 465
        if y_offset + 4 > len(data):
            continue

        x = _float32(data, x_offset)
        y = _float32(data, y_offset)
        if not math.isfinite(x) or not math.isfinite(y):
            continue
        records.append(
            {
                'name': name,
                'record_start': record_start,
                'x': _clean_coordinate(x),
                'y': _clean_coordinate(y),
                'wavelength_nm': None,
                'intensity': None,
            }
        )
    return records


def _spectrum_at(
    data: bytes, label_position: int
) -> tuple[np.ndarray, np.ndarray] | None:
    search_start = label_position + len(WAVELENGTH_LABEL)
    search_end = min(len(data) - 4, search_start + 200)
    for count_position in range(search_start, search_end):
        count = struct.unpack_from('<I', data, count_position)[0]
        if not MINIMUM_SPECTRUM_POINTS <= count <= MAXIMUM_SPECTRUM_POINTS:
            continue

        wavelength_start = count_position + 4
        intensity_start = wavelength_start + 4 * count
        data_end = intensity_start + 4 * count
        if data_end > len(data):
            continue

        wavelengths = np.frombuffer(
            data, dtype='<f4', count=count, offset=wavelength_start
        )
        intensity = np.frombuffer(
            data, dtype='<f4', count=count, offset=intensity_start
        )
        if (
            np.all(np.isfinite(wavelengths))
            and np.all(
                (wavelengths > MINIMUM_WAVELENGTH_NM)
                & (wavelengths < MAXIMUM_WAVELENGTH_NM)
            )
            and np.all(np.diff(wavelengths) > 0)
            and np.all(np.isfinite(intensity))
        ):
            return wavelengths.astype(float), intensity.astype(float)
    return None


def _spectrum_blocks(data: bytes) -> list[dict[str, Any]]:
    blocks = []
    start = 0
    while (label_position := data.find(WAVELENGTH_LABEL, start)) != -1:
        spectrum = _spectrum_at(data, label_position)
        if spectrum is not None:
            context = data[max(0, label_position - 1200) : label_position].decode(
                'utf-16le', errors='ignore'
            )
            wavelengths, intensity = spectrum
            blocks.append(
                {
                    'position': label_position,
                    'is_reference': any(
                        marker in context
                        for marker in ('Reference', 'TR REF', 'PL REF')
                    ),
                    'wavelength_nm': wavelengths,
                    'intensity': intensity,
                }
            )
        start = label_position + 1
    return blocks


def _metadata_strings(data: bytes) -> list[str]:
    strings = []
    pattern = re.compile(rb'(?:[\x20-\x7e]\x00){4,200}')
    for match in pattern.finditer(data):
        value = match.group().decode('utf-16le', errors='ignore').strip()
        if value and value not in strings:
            strings.append(value)
    return strings


def _measurement_metadata(data: bytes) -> dict[str, Any]:
    strings = _metadata_strings(data)
    text = '\n'.join(strings)
    setup = next(
        (value for value in strings if value.startswith('New measurement setup:')),
        '',
    )
    metadata: dict[str, Any] = {
        'software_version': next(
            (value for value in strings if re.fullmatch(r'YWafer v[\w.]+', value)),
            None,
        ),
        'measurement_setup': setup or None,
    }

    match = re.search(r'\b(\d+(?:\.\d+)?)-\d+(?:\.\d+)?-CW\b', setup)
    if match:
        metadata['excitation_source'] = match.group()
        metadata['excitation_wavelength_nm'] = float(match.group(1))

    match = re.search(r'\b(\d+(?:\.\d+)?)\s*mW\s*\(', text)
    if match:
        metadata['laser_power_mw'] = float(match.group(1))
    match = re.search(r'\((\d+(?:\.\d+)?)\s*%\)', text)
    if match:
        metadata['laser_power_percentage'] = float(match.group(1))

    match = re.search(r'\+\s*(\d+(?:\.\d+)?)\s*ms\s*x\s*(\d+)', setup)
    if match:
        metadata['integration_time_ms'] = float(match.group(1))
        metadata['accumulations'] = int(match.group(2))

    match = re.search(r'\b(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)nm\b', setup)
    if match:
        metadata['wavelength_range_nm'] = [
            float(match.group(1)),
            float(match.group(2)),
        ]

    metadata['detector'] = next(
        (
            value
            for value in strings
            if re.fullmatch(r'[A-Za-z]+-\d+-\d+', value)
            and value not in {'YWafer v7.06'}
        ),
        None,
    )
    metadata['emission_filter'] = next(
        (value for value in strings if re.fullmatch(r'LP\d+', value)),
        None,
    )
    return metadata


def read_ywf(data: bytes) -> dict[str, Any]:
    """Extract saved PL1 spectra, stage positions, and acquisition settings.

    The binary record layout was reverse-engineered from YWafer v7.x files.
    """
    records = sorted(_trace_records(data), key=lambda record: record['record_start'])
    if not records:
        raise ValueError('No saved PL1 traces were found in the YWafer file.')

    sample_blocks = [
        block for block in _spectrum_blocks(data) if not block['is_reference']
    ]
    used = set()
    for index, record in enumerate(records):
        end = (
            records[index + 1]['record_start']
            if index + 1 < len(records)
            else len(data)
        )
        matches = [
            (block_index, block)
            for block_index, block in enumerate(sample_blocks)
            if record['record_start'] < block['position'] < end
        ]
        if len(matches) == 1:
            block_index, block = matches[0]
            used.add(block_index)
            record.update(
                wavelength_nm=block['wavelength_nm'],
                intensity=block['intensity'],
            )

    missing = [record for record in records if record['wavelength_nm'] is None]
    remaining = [
        (index, block) for index, block in enumerate(sample_blocks) if index not in used
    ]
    if len(missing) == len(remaining):
        for record, (_, block) in zip(missing, remaining):
            record.update(
                wavelength_nm=block['wavelength_nm'],
                intensity=block['intensity'],
            )

    records.sort(key=lambda record: int(record['name'].rsplit('#', 1)[-1]))
    if not any(record['wavelength_nm'] is not None for record in records):
        raise ValueError('No saved PL spectra could be extracted from the YWafer file.')

    return {'traces': records, 'metadata': _measurement_metadata(data)}
