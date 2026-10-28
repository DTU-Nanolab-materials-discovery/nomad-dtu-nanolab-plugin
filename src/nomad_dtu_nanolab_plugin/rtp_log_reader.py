from __future__ import annotations

import csv
import io
import logging
import re
from dataclasses import dataclass

"""RTP log parsing helpers used during NOMAD normalization.

This parser lines up two logs by timestamp:
- Eklipse CSV process log (pressure, flows, valves)
- CX-Thermo diagnostics log (temperature, lamp power)

The output is shaped for the RTP schema and includes both summary values
and time-series channels.
"""

# Keep heavy imports out of module load so NOMAD startup stays stable.
np = None
pd = None
logger = logging.getLogger(__name__)

# Unit conversions and parser thresholds.
TORR_TO_PA = 133.322368421
SCCM_TO_M3_S = 1e-6 / 60
CELSIUS_TO_KELVIN_OFFSET = 273.15
MIN_USED_GAS_FLOW_SCCM = 1.0
MIN_USED_GAS_FLOW_M3_S = MIN_USED_GAS_FLOW_SCCM * SCCM_TO_M3_S
MIN_POINTS_FOR_STEPS = 3
MIN_COLUMNS_FOR_TABLE_ROW = 2
MIN_TRENDLOG_PARTS = 3
MIN_ANNEALING_PLATEAU_DURATION_S = 1.0
ANNEALING_DURATION_TOLERANCE_S = 0.05
MIN_PLATEAU_POINTS = 2
PLATEAU_TEMPERATURE_DELTA_TOLERANCE_K = 1e-6
VIRTUAL_TEMPERATURE_SETPOINT_C = 1450.0
ANNEAL_SEGMENT_INDEX = 1
STANDARD_SEGMENT_BOUND_COUNT = 4
FLAT_SEGMENT_DELTA_TEMPERATURE_K = 5.0
ORDINAL_SECOND = 2
ORDINAL_THIRD = 3
RATE_OF_RISE_MAX_START_CAPMAN_PRESSURE_MTORR = 15.0
RATE_OF_RISE_MAX_CAPMAN_PRESSURE_PA = (
    RATE_OF_RISE_MAX_START_CAPMAN_PRESSURE_MTORR * 1e-3 * TORR_TO_PA
)
RATE_OF_RISE_MAX_THROTTLE_POSITION = 100.0
RATE_OF_RISE_MIN_STATIC_SAMPLES = 10
RATE_OF_RISE_MIN_VALID_POINTS = 2
NUMBER_2 = 2

# ---------------------------------------------------------------------------
# Step segmentation thresholds.
# ---------------------------------------------------------------------------
# Minimum duration for a segment to be kept (seconds).
# Raised from 5 s to 60 s: short noise bursts in the cooling tail were being
# classified as separate Dwell/Cooling segments.
SEGMENT_MIN_DURATION_S = 5.0
# Minimum number of data points for a segment to be kept.
SEGMENT_MIN_POINTS = 3
# Temperature slope threshold (K/s) below which a segment is classified as a Dwell.
# Slopes with |dT/dt| < this value are considered flat.
DWELL_SLOPE_THRESHOLD_K_S = 0.05  # or lower if we want to be more strict
# Gaussian smoothing window half-width used before computing the derivative.
# Wider window suppresses sensor noise in the cooling plateau without losing
# the genuine Heating/Annealing/Cooling transitions.
SLOPE_SMOOTH_WINDOW = 15
# Minimum label-run length used to debounce slope flips before step extraction.
# Raised from 5 points / 2 s to 10 points / 30 s so brief noisy reversals
# inside a long cooling ramp do not fragment it into many short segments.
SLOPE_MIN_RUN_POINTS = 10
SLOPE_MIN_RUN_DURATION_S = 30.0
# Ambient temperature window (K) used to detect the room-temperature plateau
# at the end of a run. Any sample whose temperature is within this tolerance
# of AMBIENT_TEMPERATURE_K is considered "at room temperature".
# ±0.5 K tolerance matches the stated room-temperature criterion of
# 23.5 ±0.5 °C, preventing early triggering at warmer intermediates.
AMBIENT_TEMPERATURE_K = 296.65  # ≈ 23.5 °C
AMBIENT_TEMPERATURE_TOLERANCE_K = 0.5
# "Dwell-like" includes both plain dwell labels and any step already renamed
# to Annealing. This lets downstream code treat them uniformly.
DWELL_LIKE_NAME_RE = re.compile(
    r'^\s*(?:\d+(?:st|nd|rd|th)\s+)?(?:dwell|anneal(?:ing)?)\b'
)


@dataclass
class ParsedRTPStep:
    # Human-readable label assigned during segmentation.
    name: str
    # Duration and start/end temperatures of the step.
    duration_s: float
    initial_temperature_k: float
    final_temperature_k: float
    # Mean pressure over the step's averaging window, if available.
    pressure_pa: float | None
    # Mean gas flows over the step's averaging window, in SI units.
    ar_flow_m3_s: float
    n2_flow_m3_s: float
    ph3_in_ar_flow_m3_s: float
    nh3_in_ar_flow_m3_s: float
    h2s_in_ar_flow_m3_s: float
    # Mean temperature is used when identifying the main annealing dwell.
    mean_temperature_k: float | None = None
    # Absolute step boundaries on the merged process timeline.
    start_time_s: float | None = None
    end_time_s: float | None = None
    # Visual end boundary for plots — extends to recording end for the last
    # Cooling step so the shaded region covers the full cool-down including
    # the ambient plateau (which is excluded from duration/averages).
    plot_end_time_s: float | None = None


@dataclass
class ParsedRTPData:
    # Gases detected as genuinely used during the main dwell/anneal.
    used_gases: list[str]
    # General process-level vacuum diagnostics.
    base_pressure_pa: float | None
    base_pressure_ballast_pa: float | None
    rate_of_rise_pa_s: float | None
    # Kept for schema compatibility, intentionally not parsed from logs.
    chiller_flow_m3_s: float | None
    # Summary information for the overview section of the schema.
    overview: dict[str, float | None]
    # Segmented process steps in chronological order.
    steps: list[ParsedRTPStep]
    # Plot-ready SI-unit timeseries exported from the merged process dataframe.
    timeseries: dict[str, list[float]]
    # Flag indicating whether a main annealing step could be identified.
    has_detected_annealing: bool = False


def _empty_result() -> ParsedRTPData:
    """Return an empty result when parsing cannot continue safely."""
    return ParsedRTPData(
        used_gases=[],
        base_pressure_pa=None,
        base_pressure_ballast_pa=None,
        rate_of_rise_pa_s=None,
        chiller_flow_m3_s=None,
        overview={
            'annealing_pressure': None,
            'annealing_time': None,
            'annealing_temperature': None,
            'annealing_ar_flow': None,
            'annealing_n2_flow': None,
            'annealing_ph3_in_ar_flow': None,
            'annealing_nh3_in_ar_flow': None,
            'annealing_h2s_in_ar_flow': None,
            'total_heating_time': None,
            'total_cooling_time': None,
            'end_of_process_temperature': None,
        },
        steps=[],
        timeseries={},
        has_detected_annealing=False,
    )


def _ensure_deps() -> bool:
    """Load numpy/pandas only when needed, then cache them globally."""
    np_mod = globals().get('np')
    if np_mod is None:
        try:
            import numpy as _np

            globals()['np'] = _np
        except Exception:
            return False

    pd_mod = globals().get('pd')
    if pd_mod is None:
        try:
            import pandas as _pd

            globals()['pd'] = _pd
        except Exception:
            return False

    # Both heavy dependencies are now available for the rest of the parser.
    return True


def _normalize(name: str) -> str:
    """Normalize labels so matching works across different logfile variants."""
    # Strips punctuation/spacing/case so comparisons stay robust to slightly
    # different export formats.
    return re.sub(r'[^a-z0-9]+', '', str(name).lower())


def _extract_trendlog_column_names(lines: list[str]) -> list[str]:
    """To map numeric columns to known labels."""
    known_columns = [
        'Fixed SP - CH1',
        'Process Value - CH1',
        'Set Point - CH1',
        'Manual MV - CH1',
        'MV Monitor (Heating) - CH1',
        'MV Monitor (Cooling) - CH1',
    ]
    normalized_map = {_normalize(name): name for name in known_columns}

    for line in lines:
        line_norm = _normalize(line)
        if 'processvaluech1' not in line_norm:
            continue

        # Recover the order in which known columns appear in the header-like
        # line so numeric TrendLog rows can be mapped correctly.
        hits = [
            (line_norm.find(norm_name), original_name)
            for norm_name, original_name in normalized_map.items()
            if norm_name in line_norm
        ]
        ordered = [name for _, name in sorted(hits) if _ >= 0]
        if ordered:
            return ordered

    # Fall back to the standard expected order if no recognizable header is found.
    return known_columns


def _read_csv_with_fallback(path: str):
    """Read Eklipse CSV with its fixed recording-set layout."""
    if not _ensure_deps() or pd is None:
        raise RuntimeError('pandas not available')

    try:
        with open(path, encoding='utf-8', errors='ignore') as handle:
            header_idx = 0
            header_line = ''
            for i, line in enumerate(handle):
                line_norm = _normalize(line)
                if 'timestamp' in line_norm and 'mfc1flow' in line_norm:
                    header_idx = i
                    header_line = line
                    break

            # Generic fallback for tests/simpler CSVs that still have
            # a timestamp header.
            if not header_line:
                handle.seek(0)
                for i, line in enumerate(handle):
                    if 'timestamp' in _normalize(line):
                        header_idx = i
                        header_line = line
                        break

        # Infer delimiter from the header because exports can vary.
        delimiter = ','
        if header_line:
            try:
                sniff = csv.Sniffer().sniff(header_line, delimiters=',;\t')
                delimiter = sniff.delimiter
            except Exception:
                if header_line.count(';') > header_line.count(','):
                    delimiter = ';'

        # Read starting from the detected header row.
        return pd.read_csv(
            path,
            sep=delimiter,
            engine='python',
            skipinitialspace=True,
            on_bad_lines='skip',
            quotechar='"',
            skiprows=header_idx,
        )
    except Exception:
        # Return an empty dataframe instead of failing hard; caller decides how
        # to recover.
        return pd.DataFrame()


def _to_datetime(series):
    """Parse timestamps with strict format first, then looser datetime/timedelta."""
    if pd is None:
        return series

    # Preferred explicit timestamp format from standard RTP exports.
    dt = pd.to_datetime(series, errors='coerce', format='%Y/%m/%d_%H:%M:%S')
    if dt.notna().sum() > 0:
        return dt

    # Fall back to pandas' generic parser.
    dt = pd.to_datetime(series, errors='coerce')
    if dt.notna().sum() > 0:
        return dt

    # Also support elapsed-time style fields by anchoring them to epoch.
    td = pd.to_timedelta(series, errors='coerce')
    if td.notna().sum() > 0:
        return pd.Timestamp('1970-01-01') + td

    return dt


def _to_num(series):
    """Convert a pd series to numbers, coercing missing values to NaN."""
    if pd is None:
        return series
    return pd.to_numeric(series, errors='coerce')


def _pressure_to_pa(value: float | None) -> float | None:
    """Convert Eklipse pressure from Torr to Pa."""
    if value is None or (np is not None and np.isnan(value)):
        return None
    return value * TORR_TO_PA


def _apply_parasitic_flow_cutoff(flow_m3_s: float, gas: str) -> float:
    """Zero out small gas flows we treat as instrumentation background.

    Any gas channel below 1 sccm is considered parasitic and set to 0.
    """
    _ = gas  # Keep gas explicit so call sites stay easy to read.
    if abs(float(flow_m3_s)) < MIN_USED_GAS_FLOW_M3_S:
        return 0.0
    return float(flow_m3_s)


def _mean_or_zero(df, col: str) -> float:
    """Return nanmean of a column or 0.0 if no valid data."""
    if col not in df.columns:
        return 0.0

    arr = _to_num(df[col]).to_numpy(dtype=float)

    if len(arr) == 0 or not np.any(np.isfinite(arr)):
        return 0.0

    return float(np.nanmean(arr))


def _temperature_to_kelvin(series):
    """Convert Celsius channels to Kelvin."""
    values = _to_num(series)
    return values + CELSIUS_TO_KELVIN_OFFSET


def _extract_key_values(txt: str) -> dict[str, float]:
    """Parse key/value diagnostics lines with fixed unit assumptions."""
    out: dict[str, float] = {}

    def _convert_value(key: str, value: float) -> float:
        key_norm = _normalize(key)

        # Pressure values are always given in Torr.
        if 'pressure' in key_norm:
            value *= TORR_TO_PA

        return value

    pattern = re.compile(
        r'^\s*([^:=\n]*?[A-Za-z][^:=\n]*?)\s*(?:[:=]\s*)?'
        r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([^\n]*)$'
    )

    for line in txt.splitlines():
        m = pattern.match(line)
        if not m:
            continue
        key = _normalize(m.group(1))
        value = float(m.group(2))

        out[key] = _convert_value(key, value)

    return out


def _find_cx_thermo_csv_header(lines: list[str]) -> int | None:
    for i, line in enumerate(lines):
        if 'timestamp' in _normalize(line) and any(d in line for d in [',', ';', '\t']):
            return i
    return None


def _parse_cx_thermo_csv(lines: list[str], header_idx: int):
    header_line = lines[header_idx]
    delimiter = ','
    try:
        delimiter = csv.Sniffer().sniff(header_line, delimiters=',;\t').delimiter
    except Exception:
        if header_line.count(';') > header_line.count(','):
            delimiter = ';'

    try:
        csv_df = pd.read_csv(
            io.StringIO('\n'.join(lines[header_idx:])),
            sep=delimiter,
            engine='python',
            skipinitialspace=True,
            on_bad_lines='skip',
            quotechar='"',
        )
    except Exception:
        return None

    has_timestamp = _find_col(csv_df, [r'timestamp', r'^time$']) is not None
    has_values = len(csv_df.columns) >= MIN_COLUMNS_FOR_TABLE_ROW
    return csv_df if has_timestamp and has_values else None


def _parse_trendlog_table(lines: list[str]):
    trendlog_columns = _extract_trendlog_column_names(lines)
    rows: list[dict[str, float | str]] = []
    for line in lines:
        parts = re.split(r'\s+', line.strip())
        if len(parts) < MIN_TRENDLOG_PARTS:
            continue
        if not re.match(r'^\d{4}/\d{2}/\d{2}_\d{2}:\d{2}:\d{2}$', parts[0]):
            continue

        nums: list[float] = []
        for token in parts[1:]:
            if token in {'', '-'}:
                continue
            try:
                nums.append(float(token))
            except Exception:
                continue

        if len(nums) >= MIN_COLUMNS_FOR_TABLE_ROW:
            row: dict[str, float | str] = {'Timestamp': parts[0]}
            for idx, column_name in enumerate(trendlog_columns):
                if idx >= len(nums):
                    break
                row[column_name] = nums[idx]
            rows.append(row)

    return pd.DataFrame(rows)


def _parse_cx_thermo_table(txt: str):
    """Parse CX-Thermo diagnostics table with metadata+CSV structure."""
    if pd is None:
        raise RuntimeError('pandas not loaded')

    lines = [line.rstrip() for line in txt.splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame()

    header_idx = _find_cx_thermo_csv_header(lines)
    if header_idx is not None:
        csv_df = _parse_cx_thermo_csv(lines, header_idx)
        if csv_df is not None:
            return csv_df

    return _parse_trendlog_table(lines)


def _find_col(df, patterns: list[str]) -> str | None:
    """Return the first dataframe column matching any normalized regex.
    In case we use this parser for other dataframes types (lab equipment changes
    or different lab).
    """
    # Normalize each column name first so regex matching is resilient to
    # punctuation/spacing/casing differences across export variants.
    norm_map = {_normalize(c): c for c in df.columns}
    for pattern in patterns:
        rx = re.compile(pattern)
        for norm, original in norm_map.items():
            if rx.search(norm):
                return original
    return None


def _identify_virtual_temperature_samples(process_df) -> np.ndarray | None:
    """Identify all samples at 1450°C (virtual temperature artifact).

    Returns a boolean numpy array where True indicates 1450°C samples.
    Returns None if temperature data is unavailable.
    """
    if (
        process_df is None
        or process_df.empty
        or 'temperature_k' not in process_df.columns
    ):
        return None

    temp_arr = process_df['temperature_k'].to_numpy(dtype=float)
    # Convert 1450°C setpoint to Kelvin for comparison.
    virtual_temp_k = VIRTUAL_TEMPERATURE_SETPOINT_C + CELSIUS_TO_KELVIN_OFFSET
    # Check if samples are at 1450°C (400°C tolerance to catch ramp up and down).
    # Note: atol=400 in Kelvin is equivalent to 400°C.
    virtual_mask = np.isfinite(temp_arr) & np.isclose(
        temp_arr,
        virtual_temp_k,
        rtol=0.0,
        atol=400.0,
    )
    return virtual_mask


def _mark_disregarded_samples(
    process_df,
    cooling_start_timestamp=None,
    cooling_end_timestamp=None,
    logger=None,
) -> bool:
    """Mark 1450°C samples in cooling phase as 'disregarded' for rate calculation.

    When recording is left running while the chamber is opened to air, CX-Thermo
    can emit fake 1450°C readings that are not real process temperatures.
    This helper marks matching samples with an 'is_disregarded' column so they
    can be excluded from cooling ramp rate calculations.

    Returns True if disregarded samples were found, False otherwise.
    """
    if process_df is None or process_df.empty:
        return False

    # Initialize disregarded column if not already present.
    if 'is_disregarded' not in process_df.columns:
        process_df['is_disregarded'] = False

    virtual_mask = _identify_virtual_temperature_samples(process_df)
    if virtual_mask is None or not np.any(virtual_mask):
        return False

    # Constrain to cooling phase if boundaries provided.
    if cooling_start_timestamp is not None or cooling_end_timestamp is not None:
        if 'timestamp' not in process_df.columns:
            return False

        timestamps = process_df['timestamp']
        cooling_mask = timestamps.notna()
        if cooling_start_timestamp is not None:
            cooling_mask &= timestamps >= cooling_start_timestamp
        if cooling_end_timestamp is not None:
            cooling_mask &= timestamps <= cooling_end_timestamp

        virtual_mask &= cooling_mask.to_numpy(dtype=bool)

    if not np.any(virtual_mask):
        return False

    # Mark all 1450°C samples as disregarded.
    process_df.loc[virtual_mask, 'is_disregarded'] = True

    if logger is not None:
        # Find the time interval containing disregarded samples.
        disregarded_indices = np.where(virtual_mask)[0]
        time_interval_str = 'unknown'
        if len(disregarded_indices) > 0 and 'time_s' in process_df.columns:
            start_idx = int(disregarded_indices[0])
            end_idx = int(disregarded_indices[-1])
            time_arr = _to_num(process_df['time_s']).to_numpy(dtype=float)
            if np.isfinite(time_arr[start_idx]) and np.isfinite(time_arr[end_idx]):
                start_time = float(time_arr[start_idx])
                end_time = float(time_arr[end_idx])
                duration = end_time - start_time
                time_interval_str = (
                    f'{start_time:.1f}–{end_time:.1f} s (duration: {duration:.1f} s)'
                )

        logger.warning(
            f'Chamber was left open without stopping recording: detected '
            f'virtual temperature samples at 1450°C in cooling phase at time interval '
            f'{time_interval_str}. '
            'These samples are marked as disregarded and excluded from cooling ramp '
            'rate calculations.'
        )

    return True


def _add_scaled_channels(output_df, input_df, channel_map):
    for output_column, patterns in channel_map.items():
        input_column = _find_col(input_df, patterns)
        if input_column is None:
            output_df[output_column] = 0.0
        else:
            output_df[output_column] = (
                _to_num(input_df[input_column]).fillna(0) * SCCM_TO_M3_S
            )


def _add_eklipse_flows(output_df, input_df):
    _add_scaled_channels(
        output_df,
        input_df,
        {
            'ar_flow_m3_s': [r'mfc1flow$'],
            'n2_flow_m3_s': [r'mfc2flow$'],
            'ph3_in_ar_flow_m3_s': [r'mfc4flow$'],
            'nh3_in_ar_flow_m3_s': [r'mfc5flow$'],
            'h2s_in_ar_flow_m3_s': [r'mfc6flow$'],
        },
    )
    _add_scaled_channels(
        output_df,
        input_df,
        {
            'ar_flow_setpoint_m3_s': [r'mfc1setpoint$'],
            'n2_flow_setpoint_m3_s': [r'mfc2setpoint$'],
            'ph3_in_ar_flow_setpoint_m3_s': [r'mfc4setpoint$'],
            'nh3_in_ar_flow_setpoint_m3_s': [r'mfc5setpoint$'],
            'h2s_in_ar_flow_setpoint_m3_s': [r'mfc6setpoint$'],
        },
    )


def _add_eklipse_valves(output_df, input_df):
    for output_column, pattern in (
        ('ballast', r'ballastvalve$'),
        ('vent_line', r'ventvalve$'),
    ):
        input_column = _find_col(input_df, [pattern])
        if input_column is not None:
            output_df[output_column] = _to_num(input_df[input_column]).fillna(0)

    throttle_columns = (
        ('throttle_closed', r'throttlevalveclosed$', True),
        ('throttle_open', r'throttlevalveopened$', True),
        ('throttle_position', r'throttlevalveposition$', False),
    )
    for output_column, pattern, fill_missing in throttle_columns:
        input_column = _find_col(input_df, [pattern])
        if input_column is not None:
            values = _to_num(input_df[input_column])
            output_df[output_column] = values.fillna(0) if fill_missing else values


def _build_eklipse_channels(eklipse_df):
    """Normalize Eklipse signals into the process dataframe's column names."""
    e = pd.DataFrame()
    e_time = _find_col(eklipse_df, [r'timestamp', r'^time$', r'timestamp'])
    if e_time is None:
        logger.warning(
            'Eklipse timestamp column not found; Eklipse data cannot be time-aligned.'
        )
    else:
        e['timestamp'] = _to_datetime(eklipse_df[e_time])

    pressure_column = _find_col(eklipse_df, [r'capmanpressure$'])
    e['pressure_raw'] = (
        _to_num(eklipse_df[pressure_column]) if pressure_column is not None else np.nan
    )
    _add_eklipse_flows(e, eklipse_df)
    _add_eklipse_valves(e, eklipse_df)
    return e


def _build_cx_thermo_channels(cx_thermo_df):
    """Normalize CX-Thermo signals into the process dataframe's column names."""
    t = pd.DataFrame()
    t_time = _find_col(cx_thermo_df, [r'timestamp'])
    t_temp = _find_col(cx_thermo_df, [r'processvalue.*ch1$', r'^temperature(c)?$'])
    t_setpoint = _find_col(cx_thermo_df, [r'setpointch1$', r'setpoint.*ch1$'])
    t_lamp_power = _find_col(cx_thermo_df, [r'mvmonitorheatingch1$'])
    if t_time is not None:
        t['timestamp'] = _to_datetime(cx_thermo_df[t_time])
    else:
        logger.warning(
            'CX-Thermo timestamp column not found; '
            'CX-Thermo data cannot be time-aligned.',
            stacklevel=2,
        )
    if t_temp is not None:
        # Diagnostics temperatures are logged in Celsius and converted to Kelvin.
        t['temperature_k'] = _temperature_to_kelvin(cx_thermo_df[t_temp])
    if t_setpoint is not None:
        t['temperature_setpoint_k'] = _temperature_to_kelvin(cx_thermo_df[t_setpoint])
    if t_lamp_power is not None:
        t['lamp_power'] = _to_num(cx_thermo_df[t_lamp_power])
    return t


def _align_process_streams(e, t):
    """Merge the normalized streams, retaining single-stream fallback behavior."""
    # Remove rows with invalid timestamps before any alignment/merge.
    if 'timestamp' in e:
        e = e.dropna(subset=['timestamp']).sort_values('timestamp')
        if e.empty:
            logger.warning(
                'Eklipse timestamps could not be parsed; Eklipse dataframe'
                ' is empty after filtering.',
                stacklevel=2,
            )
    if 'timestamp' in t:
        t = t.dropna(subset=['timestamp']).sort_values('timestamp')
        if t.empty:
            logger.warning(
                'CX-Thermo timestamps could not be parsed; CX-Thermo dataframe'
                ' is empty after filtering.',
                stacklevel=2,
            )

    if not t.empty and not e.empty:
        timeline = pd.DataFrame(
            {
                'timestamp': pd.concat([t['timestamp'], e['timestamp']])
                .dropna()
                .drop_duplicates()
                .sort_values()
                .reset_index(drop=True)
            }
        )
        process = pd.merge_asof(
            timeline,
            t,
            on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta(seconds=8),
        )
        return pd.merge_asof(
            process,
            e,
            on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta(seconds=8),
        )
    if not t.empty:
        process = t.copy()
        process['pressure_raw'] = np.nan
        for column in (
            'ar_flow_m3_s',
            'n2_flow_m3_s',
            'ph3_in_ar_flow_m3_s',
            'nh3_in_ar_flow_m3_s',
            'h2s_in_ar_flow_m3_s',
        ):
            process[column] = 0.0
        return process
    if not e.empty:
        process = e.copy()
        process['temperature_k'] = np.nan
        return process
    return pd.DataFrame()


def _build_process_df(eklipse_df, cx_thermo_df):
    """Merge Eklipse and CX-Thermo streams onto one shared process timeline."""
    if pd is None:
        raise RuntimeError('pandas not loaded')

    e = _build_eklipse_channels(eklipse_df)
    t = _build_cx_thermo_channels(cx_thermo_df)
    process = _align_process_streams(e, t)
    if process.empty:
        return process

    # Express time as elapsed seconds since the start of the merged process.
    process = process.dropna(subset=['timestamp']).sort_values('timestamp')
    if process.empty:
        return process
    process['time_s'] = (
        process['timestamp'] - process['timestamp'].iloc[0]
    ).dt.total_seconds()
    process = process[np.isfinite(process['time_s'])].copy()
    return process


def _extract_timeseries(process_df) -> dict[str, list[float]]:
    """Export process channels into SI-unit time-series arrays."""
    if process_df is None or process_df.empty:
        logger.warning('Process dataframe is empty, no timeseries data available')
        return {}

    df = process_df.copy()
    out: dict[str, list[float]] = {
        'time_s': [],
        'temperature_k': [],
        'temperature_setpoint_k': [],
        'lamp_power': [],
        'pressure_pa': [],
        'ar_flow_m3_s': [],
        'n2_flow_m3_s': [],
        'ph3_in_ar_flow_m3_s': [],
        'nh3_in_ar_flow_m3_s': [],
        'h2s_in_ar_flow_m3_s': [],
    }

    if 'time_s' not in df:
        logger.warning(
            'Time column missing from process data, cannot extract timeseries'
        )
        return out

    # Always export time, even if some channels are missing.
    out['time_s'] = [float(v) for v in _to_num(df['time_s']).fillna(0).to_list()]

    if 'temperature_k' in df:
        out['temperature_k'] = [
            float(v) for v in _to_num(df['temperature_k']).to_list()
        ]
    else:
        logger.warning('Temperature data missing from process logs')

    if 'temperature_setpoint_k' in df:
        out['temperature_setpoint_k'] = [
            float(v) for v in _to_num(df['temperature_setpoint_k']).to_list()
        ]

    if 'lamp_power' in df:
        out['lamp_power'] = [float(v) for v in _to_num(df['lamp_power']).to_list()]

    if 'pressure_raw' in df:
        pa_series = _to_num(df['pressure_raw']).apply(_pressure_to_pa)
        pressure_pa = [
            float(v) if v is not None and np.isfinite(v) else float('nan')
            for v in pa_series.to_list()
        ]
        # Leave pressure empty if we never got a finite pressure sample.
        if any(np.isfinite(v) for v in pressure_pa):
            out['pressure_pa'] = pressure_pa

    # Export each flow channel separately so plotting/schema code can consume
    # only the channels it needs.
    flow_cols = {
        'ar_flow_m3_s': 'ar_flow_m3_s',
        'n2_flow_m3_s': 'n2_flow_m3_s',
        'ph3_in_ar_flow_m3_s': 'ph3_in_ar_flow_m3_s',
        'nh3_in_ar_flow_m3_s': 'nh3_in_ar_flow_m3_s',
        'h2s_in_ar_flow_m3_s': 'h2s_in_ar_flow_m3_s',
    }
    for out_col, src_col in flow_cols.items():
        if src_col in df:
            out[out_col] = [
                float(v) if np.isfinite(v) else float('nan')
                for v in _to_num(df[src_col]).to_list()
            ]

    return out


def _find_gas_shutoff_time(step_df) -> float | None:
    """
    Find the time at which gases shut off during a step.

    Returns the timestamp (in seconds) when the first gas turns off after at
    least one gas was active, or None if gases remain active throughout the
    step or never activate. Uses the same threshold (MIN_USED_GAS_FLOW_M3_S)
    as the plot construction logic.
    """
    if (
        step_df.empty
        or 'time_s' not in step_df.columns
        or not all(
            col in step_df.columns
            for col in [
                'ar_flow_m3_s',
                'n2_flow_m3_s',
                'ph3_in_ar_flow_m3_s',
                'nh3_in_ar_flow_m3_s',
                'h2s_in_ar_flow_m3_s',
            ]
        )
    ):
        return None

    time_arr = step_df['time_s'].to_numpy()
    ar_arr = step_df['ar_flow_m3_s'].to_numpy()
    n2_arr = step_df['n2_flow_m3_s'].to_numpy()
    ph3_arr = step_df['ph3_in_ar_flow_m3_s'].to_numpy()
    nh3_arr = step_df['nh3_in_ar_flow_m3_s'].to_numpy()
    h2s_arr = step_df['h2s_in_ar_flow_m3_s'].to_numpy()

    if len(time_arr) != len(ar_arr):
        return None

    try:
        had_gas_on = False
        for t, ar_f, n2_f, ph3_f, nh3_f, h2s_f in zip(
            time_arr, ar_arr, n2_arr, ph3_arr, nh3_arr, h2s_arr
        ):
            flows = [ar_f, n2_f, ph3_f, nh3_f, h2s_f]
            # Check if any gas flow is above the threshold.
            gas_on = any(
                np.isfinite(flow) and abs(float(flow)) > MIN_USED_GAS_FLOW_M3_S
                for flow in flows
            )
            if gas_on:
                had_gas_on = True
            elif had_gas_on:
                # First point where all gases turn off after being on.
                return float(t)
        # Gases never shut off (remain active until step end).
        return None
    except Exception as e:
        logger.warning(f'Error detecting gas shutoff time: {e}')
        return None


def _find_cooling_vent_activation_time(step_df) -> float | None:
    """Find vent activation time during cooling.

    Returns the first timestamp where vent line is active (1) and throttle
    is closed (1).
    Returns None if required signals are unavailable or no such point exists
    in the provided step slice.
    """
    required = ['time_s', 'vent_line', 'throttle_closed']
    if step_df.empty or any(col not in step_df.columns for col in required):
        return None

    try:
        time_arr = _to_num(step_df['time_s']).to_numpy(dtype=float)
        vent_arr = _to_num(step_df['vent_line']).to_numpy(dtype=float)
        throttle_closed_arr = _to_num(step_df['throttle_closed']).to_numpy(dtype=float)
        mask = (
            np.isfinite(time_arr)
            & np.isfinite(vent_arr)
            & np.isfinite(throttle_closed_arr)
            & (vent_arr == 1)
            & (throttle_closed_arr == 1)
        )
        idx = np.where(mask)[0]
        if len(idx) == 0:
            return None
        return float(time_arr[int(idx[0])])
    except Exception as e:
        logger.warning(f'Error detecting cooling vent activation time: {e}')
        return None


def _find_setpoint_pre_drop_time(step_df, min_flow_threshold=1e-6) -> float | None:
    """Return the timestamp just before the first gas that was ON turns OFF.

    A gas is considered ON if its setpoint is finite and above `MIN_USED_GAS_FLOW_M3_S`.
    A gas is considered OFF if its setpoint is zero or <= threshold.

    Returns None if:
      - required columns missing
      - no gas ever turns ON
      - no ON→OFF transition occurs
    """
    _ = min_flow_threshold  # Kept for signature compatibility/readability.
    required = [
        'time_s',
        'ar_flow_setpoint_m3_s',
        'n2_flow_setpoint_m3_s',
        'ph3_in_ar_flow_setpoint_m3_s',
        'nh3_in_ar_flow_setpoint_m3_s',
        'h2s_in_ar_flow_setpoint_m3_s',
    ]
    if step_df.empty or any(col not in step_df.columns for col in required):
        return None

    try:
        time_arr = _to_num(step_df['time_s']).to_numpy(dtype=float)

        gas_cols = [
            'ar_flow_setpoint_m3_s',
            'n2_flow_setpoint_m3_s',
            'ph3_in_ar_flow_setpoint_m3_s',
            'nh3_in_ar_flow_setpoint_m3_s',
            'h2s_in_ar_flow_setpoint_m3_s',
        ]

        gas_arrays = [_to_num(step_df[col]).to_numpy(dtype=float) for col in gas_cols]

        # Determine ON/OFF state for each gas at each sample.
        gas_on = np.array(
            [
                [np.isfinite(v) and v > MIN_USED_GAS_FLOW_M3_S for v in gas_values]
                for gas_values in zip(*gas_arrays)
            ]
        )  # shape: (num_samples, num_gases)

        # If no gas is ever ON, nothing to detect.
        if not np.any(gas_on):
            return None

        # Track previous state to detect transitions.
        prev_state = gas_on[0]

        for i in range(1, len(gas_on)):
            current_state = gas_on[i]

            # A transition occurs if any gas was ON and is now OFF.
            turned_off = prev_state & ~current_state

            if np.any(turned_off):
                # Return timestamp of the previous sample.
                if np.isfinite(time_arr[i - 1]):
                    return float(time_arr[i - 1])
                return None

            prev_state = current_state

        return None

    except Exception as e:
        logger.warning(f'Error detecting setpoint pre-drop time: {e}')
        return None


# ---------------------------------------------------------------------------
# Step segmentation helpers
# ---------------------------------------------------------------------------


def _smooth_temperature(temp_arr: np.ndarray, half_window: int) -> np.ndarray:
    """Apply a simple moving-average to temperature before differentiation.

    A symmetric window of size (2*half_window + 1) is used. Near the edges
    the window is automatically reduced (same as 'same' convolution with
    uniform kernel, normalized).
    """
    n = len(temp_arr)
    smoothed = np.empty(n, dtype=float)
    for i in range(n):
        lo = max(0, i - half_window)
        hi = min(n, i + half_window + 1)
        window = temp_arr[lo:hi]
        valid = window[np.isfinite(window)]
        smoothed[i] = float(np.mean(valid)) if len(valid) > 0 else float('nan')
    return smoothed


def _classify_slope(slope_k_s: float) -> str:
    """Map a temperature slope (K/s) to a segment class label."""
    if slope_k_s > DWELL_SLOPE_THRESHOLD_K_S:
        return 'Heating'
    if slope_k_s < -DWELL_SLOPE_THRESHOLD_K_S:
        return 'Cooling'
    return 'Dwell'


def _merge_short_segments(
    labels: list[str],
    boundaries: list[int],
    time_s: np.ndarray,
    min_duration_s: float,
    min_points: int,
) -> tuple[list[str], list[int]]:
    """Merge segments that are too short into their neighbour.

    Short segments are absorbed by whichever adjacent segment has the larger
    absolute temperature difference (or simply the longer neighbour when
    temperature data is unavailable). After merging the neighbour label is
    kept – so a tiny heating blip between two Dwell segments will be absorbed
    without creating a spurious extra label.

    Args:
        labels:       List of per-segment class labels.
        boundaries:   List of start indices (length == len(labels));
                      the end of segment i is boundaries[i+1] or len(time_s).
        time_s:       Time axis (seconds).
        min_duration_s: Minimum allowed segment duration.
        min_points:   Minimum allowed number of data points per segment.

    Returns:
        (merged_labels, merged_boundaries) with the same format as input.
    """
    if len(labels) <= 1:
        return labels, boundaries

    def _seg_duration(idx: int) -> float:
        start = boundaries[idx]
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(time_s)
        return float(time_s[end - 1] - time_s[start]) if end > start else 0.0

    def _seg_points(idx: int) -> int:
        start = boundaries[idx]
        end = boundaries[idx + 1] if idx + 1 < len(boundaries) else len(time_s)
        return end - start

    changed = True
    while changed and len(labels) > 1:
        changed = False
        for i in range(len(labels)):
            dur = _seg_duration(i)
            pts = _seg_points(i)
            if dur < min_duration_s or pts < min_points:
                # Absorb into left or right neighbour (prefer longer one).
                if len(labels) == 1:
                    break  # nothing to merge into
                if i == 0:
                    absorb_into = 1
                elif i == len(labels) - 1:
                    absorb_into = len(labels) - 2
                else:
                    left_dur = _seg_duration(i - 1)
                    right_dur = _seg_duration(i + 1)
                    absorb_into = (i - 1) if left_dur >= right_dur else (i + 1)

                # Merge: remove segment i and extend its neighbour.
                # The neighbour's label wins.
                surviving_label = labels[absorb_into]
                # Update boundaries: remove boundary at index i.
                del labels[i]
                del boundaries[i]
                # After deletion, surviving segment index may have shifted.
                # Recompute from scratch on the next pass.
                # We keep the surviving label regardless of which direction.
                _ = surviving_label  # already applied via del above
                changed = True
                break  # restart outer loop

    return labels, boundaries


def _compute_segment_slope(
    df_slice: pd.DataFrame,
) -> float:
    """Compute the overall temperature slope (K/s) across a segment slice.

    Uses a linear regression of temperature vs time so isolated noisy samples
    do not dominate the sign decision.
    """
    if 'time_s' not in df_slice.columns or 'temperature_k' not in df_slice.columns:
        return 0.0

    t = _to_num(df_slice['time_s']).to_numpy(dtype=float)
    temp = _to_num(df_slice['temperature_k']).to_numpy(dtype=float)
    valid = np.isfinite(t) & np.isfinite(temp)
    if valid.sum() < ORDINAL_SECOND:
        return 0.0

    t_v = t[valid]
    temp_v = temp[valid]
    # Compute slope via least-squares (polyfit degree 1).
    try:
        slope, _ = np.polyfit(t_v, temp_v, 1)
        return float(slope)
    except Exception:
        # Fall back to simple end-to-end slope if the fit fails.
        return float((temp_v[-1] - temp_v[0]) / (t_v[-1] - t_v[0]))


def _segment_label_ordinals(base_names: list[str]) -> list[str]:
    """Add numeric suffixes (Cooling 2, Cooling 3, …) for repeated names."""

    # Count occurrences of each base label first so only repeated names
    # receive numeric suffixes.
    name_count: dict[str, int] = {}
    for bn in base_names:
        name_count[bn] = name_count.get(bn, 0) + 1

    name_seen: dict[str, int] = {}
    final: list[str] = []

    for bn in base_names:
        if name_count[bn] == 1:
            final.append(bn)
        else:
            name_seen[bn] = name_seen.get(bn, 0) + 1
            n = name_seen[bn]

            if n == 1:
                final.append(bn)
            else:
                final.append(f'{bn} {n}')

    return final


def _is_dwell_like_name(name: str) -> bool:
    # Treat both explicit "Dwell" labels and already-renamed "Annealing"
    # labels as the same plateau-like class.
    return bool(DWELL_LIKE_NAME_RE.match(name.lower()))


def _main_annealing_step_index(steps: list[ParsedRTPStep]) -> int | None:
    # Among all dwell-like steps, choose the one with the highest mean
    # temperature as the main annealing step.
    dwell_steps = [
        (i, step)
        for i, step in enumerate(steps)
        if _is_dwell_like_name(step.name or '')
    ]
    if dwell_steps:
        return max(
            dwell_steps,
            key=lambda idx_step: idx_step[1].mean_temperature_k or 0.0,
        )[0]
    return None


def _has_detected_annealing_step(steps: list[ParsedRTPStep]) -> bool:
    """Return True only if a main annealing step was detected."""
    return _main_annealing_step_index(steps) is not None


def _find_inflection_points(
    time_s: np.ndarray,
    temp_arr: np.ndarray,
) -> list[int]:
    """Detect indices where the sign of the temperature slope changes.

    Strategy:
    1. Smooth temperature with a moving average to reduce sensor noise.
    2. Compute a central-difference derivative.
    3. Classify each sample as Heating / Dwell / Cooling.
    4. Return the index of the first sample of each new class run.

    The returned list always starts with 0 (the beginning of the data).
    """
    n = len(temp_arr)
    if n < MIN_POINTS_FOR_STEPS:
        return [0]

    smoothed = _smooth_temperature(temp_arr, SLOPE_SMOOTH_WINDOW)

    # Central-difference derivative (K/s).
    deriv = np.empty(n, dtype=float)
    deriv[0] = float('nan')
    deriv[-1] = float('nan')
    for i in range(1, n - 1):
        dt = float(time_s[i + 1]) - float(time_s[i - 1])
        if dt > 0 and np.isfinite(smoothed[i + 1]) and np.isfinite(smoothed[i - 1]):
            deriv[i] = (float(smoothed[i + 1]) - float(smoothed[i - 1])) / dt
        else:
            deriv[i] = float('nan')

    # Fill edge NaNs from neighbours.
    if np.isfinite(deriv[1]):
        deriv[0] = deriv[1]
    if np.isfinite(deriv[-2]):
        deriv[-1] = deriv[-2]

    # Per-sample label.
    labels_per_sample = [
        _classify_slope(float(d)) if np.isfinite(d) else 'Dwell' for d in deriv
    ]

    # Boundaries = first index of each run of identical labels.
    boundaries = [0]
    run_labels = [labels_per_sample[0]]
    current = labels_per_sample[0]
    for i in range(1, n):
        if labels_per_sample[i] != current:
            boundaries.append(i)
            current = labels_per_sample[i]
            run_labels.append(current)

    # Debounce brief label flips so tiny wiggles do not become separate steps.
    run_labels, boundaries = _merge_short_segments(
        run_labels,
        boundaries,
        time_s,
        min_duration_s=SLOPE_MIN_RUN_DURATION_S,
        min_points=SLOPE_MIN_RUN_POINTS,
    )

    return boundaries


def _prepare_step_dataframe(process_df):
    """Validate process samples and exclude disregarded temperature artifacts."""
    if process_df.empty:
        logger.warning('Cannot extract steps: process dataframe is empty')
        return None

    df_for_steps = process_df
    if 'is_disregarded' in process_df.columns:
        df_for_steps = process_df[~process_df['is_disregarded']].reset_index(drop=True)
        if df_for_steps.empty:
            logger.warning(
                'All temperature samples are marked as disregarded (1450°C artifacts). '
                'Cannot extract steps.'
            )
            return None

    if df_for_steps['temperature_k'].notna().sum() < MIN_POINTS_FOR_STEPS:
        num_valid = df_for_steps['temperature_k'].notna().sum()
        logger.warning(
            f'Cannot extract steps: insufficient temperature data points '
            f'({num_valid} < {MIN_POINTS_FOR_STEPS}). '
            f'Falling back to single step.'
        )
        return None

    df = df_for_steps.dropna(subset=['temperature_k', 'time_s']).copy()
    if len(df) < MIN_POINTS_FOR_STEPS:
        logger.warning(
            f'Insufficient temperature data after dropna: {len(df)} points < '
            f'{MIN_POINTS_FOR_STEPS} minimum. Falling back to single step.'
        )
        return None
    return df


def _deduplicate_step_labels(labels: list[str], boundaries: list[int]):
    deduped_labels = [labels[0]]
    deduped_boundaries = [boundaries[0]]
    for label, boundary in zip(labels[1:], boundaries[1:]):
        if label != deduped_labels[-1]:
            deduped_labels.append(label)
            deduped_boundaries.append(boundary)
    return deduped_labels, deduped_boundaries


def _classify_step_segments(df):
    """Find, merge, and relabel temperature ramp segments."""
    temp = df['temperature_k'].to_numpy(dtype=float)
    time_s = df['time_s'].to_numpy(dtype=float)
    raw_boundaries = _find_inflection_points(time_s, temp)
    raw_labels: list[str] = []
    for seg_idx, start in enumerate(raw_boundaries):
        end = (
            raw_boundaries[seg_idx + 1]
            if seg_idx + 1 < len(raw_boundaries)
            else len(df)
        )
        seg_slice = df.iloc[start:end]
        slope = _compute_segment_slope(seg_slice)
        raw_labels.append(_classify_slope(slope))

    _, merged_boundaries = _merge_short_segments(
        raw_labels[:],
        raw_boundaries[:],
        time_s,
        min_duration_s=SEGMENT_MIN_DURATION_S,
        min_points=SEGMENT_MIN_POINTS,
    )

    final_base_labels: list[str] = []
    for seg_idx, start in enumerate(merged_boundaries):
        end = (
            merged_boundaries[seg_idx + 1]
            if seg_idx + 1 < len(merged_boundaries)
            else len(df)
        )
        seg_slice = df.iloc[start:end]
        slope = _compute_segment_slope(seg_slice)
        final_base_labels.append(_classify_slope(slope))
    return final_base_labels, merged_boundaries


def _normalize_step_labels(df, labels: list[str], boundaries: list[int]):
    labels, boundaries = _deduplicate_step_labels(labels, boundaries)
    first_heating_idx = next(
        (i for i, label in enumerate(labels) if label == 'Heating'), None
    )
    if first_heating_idx is not None and first_heating_idx > 0:
        labels = labels[first_heating_idx:]
        boundaries = boundaries[first_heating_idx:]

    last_cooling_anchor = next(
        (i for i in range(len(labels) - 1, -1, -1) if labels[i] == 'Cooling'),
        None,
    )
    if last_cooling_anchor is not None and len(labels) >= NUMBER_2:
        for tail_idx in range(len(labels) - 1, last_cooling_anchor, -1):
            seg_start = boundaries[tail_idx]
            trailing_slice = df.iloc[seg_start:]
            trailing_slope = _compute_segment_slope(trailing_slice)
            if trailing_slope < 0.0:
                labels[tail_idx] = 'Cooling'
            else:
                break

    return _deduplicate_step_labels(labels, boundaries)


def _find_ambient_cutoff(df, labels: list[str], boundaries: list[int]) -> int | None:
    temp_arr_full = df['temperature_k'].to_numpy(dtype=float)
    last_cooling_idx = next(
        (i for i in range(len(labels) - 1, -1, -1) if labels[i] == 'Cooling'),
        None,
    )
    if last_cooling_idx is not None:
        for ai in range(boundaries[last_cooling_idx], len(temp_arr_full)):
            t_val = temp_arr_full[ai]
            if not np.isfinite(t_val):
                continue
            if (
                abs(float(t_val) - AMBIENT_TEMPERATURE_K)
                <= AMBIENT_TEMPERATURE_TOLERANCE_K
            ):
                return int(ai)
    return None


def _build_parsed_step(df, start: int, end: int, name: str, base_label: str):
    sl = df.iloc[start:end]
    if len(sl) < 1:
        return None

    duration = float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0])
    if duration <= 0 and len(sl) > 1:
        return None

    is_cooling = base_label == 'Cooling'
    shutoff_time = _find_gas_shutoff_time(sl)
    pressure_average_window_df = (
        sl[sl['time_s'] <= shutoff_time] if shutoff_time is not None else sl
    )
    flow_average_window_df = pressure_average_window_df
    if is_cooling:
        setpoint_pre_drop_time = _find_setpoint_pre_drop_time(sl)
        vent_activation_time = _find_cooling_vent_activation_time(sl)
        flow_cutoff = setpoint_pre_drop_time
        pressure_cutoff = setpoint_pre_drop_time or vent_activation_time

        if flow_cutoff is not None:
            candidate = sl[sl['time_s'] <= flow_cutoff]
            flow_average_window_df = candidate if not candidate.empty else sl
        if pressure_cutoff is not None:
            candidate = sl[sl['time_s'] <= pressure_cutoff]
            pressure_average_window_df = candidate if not candidate.empty else sl

    start_time = float(sl['time_s'].iloc[0])
    pressure_pa: float | None = None
    if 'pressure_raw' in sl.columns:
        raw_mean = float(np.nanmean(pressure_average_window_df['pressure_raw']))
        pressure_pa = _pressure_to_pa(raw_mean)

    return ParsedRTPStep(
        name=name,
        duration_s=float(sl['time_s'].iloc[-1] - start_time),
        start_time_s=start_time,
        end_time_s=float(sl['time_s'].iloc[-1]),
        plot_end_time_s=None,
        initial_temperature_k=float(sl['temperature_k'].iloc[0]),
        final_temperature_k=float(sl['temperature_k'].iloc[-1]),
        pressure_pa=pressure_pa,
        ar_flow_m3_s=_apply_parasitic_flow_cutoff(
            _mean_or_zero(flow_average_window_df, 'ar_flow_m3_s'), 'Ar'
        ),
        n2_flow_m3_s=_apply_parasitic_flow_cutoff(
            _mean_or_zero(flow_average_window_df, 'n2_flow_m3_s'), 'N2'
        ),
        ph3_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
            _mean_or_zero(flow_average_window_df, 'ph3_in_ar_flow_m3_s'), 'PH3'
        ),
        nh3_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
            _mean_or_zero(flow_average_window_df, 'nh3_in_ar_flow_m3_s'), 'NH3'
        ),
        h2s_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
            _mean_or_zero(flow_average_window_df, 'h2s_in_ar_flow_m3_s'), 'H2S'
        ),
        mean_temperature_k=float(np.nanmean(sl['temperature_k'])),
    )


def _build_parsed_steps(
    df,
    labels: list[str],
    boundaries: list[int],
    ambient_cutoff_idx: int | None,
):
    names = _segment_label_ordinals(labels)
    steps: list[ParsedRTPStep] = []
    for seg_idx, (start, name) in enumerate(zip(boundaries, names)):
        if seg_idx + 1 < len(boundaries):
            end = boundaries[seg_idx + 1]
        elif ambient_cutoff_idx is not None and ambient_cutoff_idx > start:
            end = ambient_cutoff_idx
        else:
            end = len(df)
        step = _build_parsed_step(df, start, end, name, labels[seg_idx])
        if step is not None:
            steps.append(step)
    return steps


def _build_fallback_step(df):
    """Represent a run with no distinct ramp segments as one neutral step."""
    logger.warning(
        'No distinct Heating/Cooling steps identified. Using single Dwell step.'
    )
    shutoff_time = _find_gas_shutoff_time(df)
    df_for_average = (
        df[df['time_s'] <= shutoff_time] if shutoff_time is not None else df
    )
    pressure_pa = None
    if 'pressure_raw' in df.columns:
        pressure_pa = _pressure_to_pa(float(np.nanmean(df_for_average['pressure_raw'])))

    def flow_average(column: str, gas: str) -> float:
        value = (
            float(np.nanmean(df_for_average[column]))
            if column in df_for_average.columns
            else 0.0
        )
        return _apply_parasitic_flow_cutoff(value, gas)

    return ParsedRTPStep(
        name='Step',
        duration_s=float(df['time_s'].iloc[-1] - df['time_s'].iloc[0]),
        start_time_s=float(df['time_s'].iloc[0]),
        end_time_s=float(df['time_s'].iloc[-1]),
        initial_temperature_k=float(df['temperature_k'].iloc[0]),
        final_temperature_k=float(df['temperature_k'].iloc[-1]),
        pressure_pa=pressure_pa,
        ar_flow_m3_s=flow_average('ar_flow_m3_s', 'Ar'),
        n2_flow_m3_s=flow_average('n2_flow_m3_s', 'N2'),
        ph3_in_ar_flow_m3_s=flow_average('ph3_in_ar_flow_m3_s', 'PH3'),
        nh3_in_ar_flow_m3_s=flow_average('nh3_in_ar_flow_m3_s', 'NH3'),
        h2s_in_ar_flow_m3_s=flow_average('h2s_in_ar_flow_m3_s', 'H2S'),
        mean_temperature_k=float(np.nanmean(df['temperature_k'])),
    )


def _extract_steps(process_df) -> list[ParsedRTPStep]:
    """Split the run into named RTP steps: Heating, Dwell, and Cooling."""
    df = _prepare_step_dataframe(process_df)
    if df is None:
        return []

    labels, boundaries = _classify_step_segments(df)
    labels, boundaries = _normalize_step_labels(df, labels, boundaries)
    ambient_cutoff_idx = _find_ambient_cutoff(df, labels, boundaries)
    steps = _build_parsed_steps(df, labels, boundaries, ambient_cutoff_idx)
    main_annealing_idx = _main_annealing_step_index(steps)
    if main_annealing_idx is not None:
        steps[main_annealing_idx].name = 'Annealing'
    if steps:
        return steps

    return [_build_fallback_step(df)]


def _flow_or_zero(val: float | None) -> float:
    # Normalize missing/NaN flow values to 0.0 so overview values always
    # remain numeric and serializable.
    if val is None:
        return 0.0
    try:
        if np.isnan(val):
            return 0.0
    except Exception:
        pass
    return float(val)


def _derive_overview(steps: list[ParsedRTPStep]) -> dict[str, float | None]:
    """Compute high-level overview values from the extracted steps.

    The 'annealing' step for the overview is the Dwell with the highest mean
    temperature (i.e. the main high-temperature dwell), consistent with the
    physical meaning of annealing even though we now use 'Dwell' as the label.
    """
    if not steps:
        logger.warning(
            'Cannot derive overview: no steps were extracted from process data. '
            'All overview values will be None.'
        )
        return _empty_result().overview

    def _step_role(step: ParsedRTPStep) -> str:
        # Determine a coarse heating/dwell/cooling role for a step, preferring
        # explicit labels and falling back to the sign of ΔT if needed.
        name = (step.name or '').lower()
        if _is_dwell_like_name(name):
            return 'dwell'
        if 'heat' in name:
            return 'heating'
        if 'cool' in name:
            return 'cooling'

        delta_t = step.final_temperature_k - step.initial_temperature_k
        if abs(delta_t) <= PLATEAU_TEMPERATURE_DELTA_TOLERANCE_K:
            return 'dwell'
        return 'heating' if delta_t > 0 else 'cooling'

    anneal_idx = _main_annealing_step_index(steps)
    if anneal_idx is None:
        logger.warning(
            'No annealing step could be identified from RTP logs. '
            'Leaving process overview empty.'
        )
        return _empty_result().overview

    anneal = steps[anneal_idx]

    if anneal.pressure_pa is None:
        logger.warning('Main dwell pressure could not be extracted from process data')
    if anneal.mean_temperature_k is None:
        logger.warning(
            'Main dwell mean temperature is None; using average of initial and final '
            'temperatures instead'
        )

    # Sum heating and cooling durations excluding the main dwell.
    total_heating = 0.0
    total_cooling = 0.0
    for i, step in enumerate(steps):
        if i == anneal_idx:
            continue
        role = _step_role(step)
        if i < anneal_idx and role in {'heating', 'dwell'}:
            total_heating += step.duration_s
        if i > anneal_idx and role in {'cooling', 'dwell'}:
            total_cooling += step.duration_s

    return {
        'annealing_pressure': anneal.pressure_pa,
        'annealing_time': anneal.duration_s,
        'annealing_temperature': (
            anneal.mean_temperature_k
            if anneal.mean_temperature_k is not None
            else (anneal.initial_temperature_k + anneal.final_temperature_k) / 2
        ),
        'annealing_ar_flow': _flow_or_zero(anneal.ar_flow_m3_s),
        'annealing_n2_flow': _flow_or_zero(anneal.n2_flow_m3_s),
        'annealing_ph3_in_ar_flow': _flow_or_zero(anneal.ph3_in_ar_flow_m3_s),
        'annealing_nh3_in_ar_flow': _flow_or_zero(anneal.nh3_in_ar_flow_m3_s),
        'annealing_h2s_in_ar_flow': _flow_or_zero(anneal.h2s_in_ar_flow_m3_s),
        'total_heating_time': total_heating,
        'total_cooling_time': total_cooling,
        'end_of_process_temperature': None,
    }


def _derive_total_heating_cooling_times(
    steps: list[ParsedRTPStep],
) -> tuple[float | None, float | None]:
    """Return total heating and cooling durations from identified steps.

    This is independent of whether a main annealing step was detected.
    """
    if not steps:
        return None, None

    total_heating = 0.0
    total_cooling = 0.0

    for step in steps:
        name = (step.name or '').lower()

        if 'heat' in name:
            # Accumulate duration of every identified heating step, including
            # numbered variants like "Heating 2".
            total_heating += step.duration_s
        elif 'cool' in name:
            # Accumulate duration of every identified cooling step, including
            # numbered variants like "Cooling 2".
            total_cooling += step.duration_s

    return total_heating, total_cooling


def _derive_end_of_process_temperature(
    process_df, steps: list[ParsedRTPStep]
) -> float | None:
    """
    End-of-process temperature = temperature at the LAST gas shutoff event
    (last ON -> OFF transition in the full timeline).
    """
    _ = steps  # Kept for signature symmetry/extensibility; not used currently.

    end_temp_k: float | None = None

    valid = True

    if process_df is None or process_df.empty:
        logger.warning(
            'Cannot derive end-of-process temperature: empty process dataframe'
        )
        valid = False

    required_cols = [
        'time_s',
        'temperature_k',
        'ar_flow_m3_s',
        'n2_flow_m3_s',
        'ph3_in_ar_flow_m3_s',
        'nh3_in_ar_flow_m3_s',
        'h2s_in_ar_flow_m3_s',
    ]

    if valid and any(col not in process_df.columns for col in required_cols):
        logger.warning(
            'Missing required columns; cannot determine end-of-process temperature'
        )
        valid = False

    if valid:
        df = process_df.copy()

        temp_arr = _to_num(df['temperature_k']).to_numpy(dtype=float)

        # Stack all gas channels sample-wise so "any gas on?" can be evaluated
        # across the full process timeline.
        flow_stack = np.column_stack(
            [
                np.abs(_to_num(df[col]).fillna(0).to_numpy(dtype=float))
                for col in required_cols[2:]
            ]
        )

        gas_on = np.any(flow_stack > MIN_USED_GAS_FLOW_M3_S, axis=1)

        if not np.any(gas_on):
            logger.warning(
                'No gas activity detected; cannot determine end-of-process temperature'
            )
        else:
            shutoff_idx = None

            # Find LAST ON -> OFF transition.
            for i in range(1, len(gas_on)):
                if gas_on[i - 1] and not gas_on[i]:
                    shutoff_idx = i

            if shutoff_idx is None:
                logger.warning('Gases never shut off (remain active until end of run)')
            else:
                temp_k = temp_arr[shutoff_idx]

                if np.isfinite(temp_k):
                    end_temp_k = float(temp_k)
                else:
                    logger.warning('Gas shutoff detected, but temperature is invalid')

    return end_temp_k


def _compute_rate_of_rise(time_s_arr, pressure_pa_arr, start_mask):
    """Compute rate of rise (Pa/s) from first to last valid static-vacuum point.

    start_mask marks rows where static conditions are satisfied:
        - Throttle valve is closed (1, "closed" column)
        - Vent valve is closed (0, "vent_line" column)
        - Throttle NOT open (0, if the open column exists)
        - Throttle position is 0 and before it was not zero
        - All gas flows are below the parasitic cutoff
        - Ballast valve is off (0, "ballast" column)
        - Pressure valve capman pressure is below 11mTorr
        - These conditions are met for at least 10 samples (to avoid false starts)
    We use the first and last rows that satisfy start_mask and return:
    (P(last) - P(first)) / (t(last) - t(first)).
    """
    start_idx = np.where(start_mask)[0]
    if len(start_idx) < RATE_OF_RISE_MIN_VALID_POINTS:
        return None

    i_first = int(start_idx[0])
    i_last = int(start_idx[-1])

    t_first = float(time_s_arr[i_first])
    t_last = float(time_s_arr[i_last])
    p_first = float(pressure_pa_arr[i_first])
    p_last = float(pressure_pa_arr[i_last])

    if not (
        np.isfinite(t_first)
        and np.isfinite(t_last)
        and np.isfinite(p_first)
        and np.isfinite(p_last)
    ):
        return None

    window_s = t_last - t_first
    if window_s <= 0:
        return None

    return (p_last - p_first) / window_s


def _derive_ballast_pressures(working_df, pressure_arr):
    """Derive pressure values from ballast activation and vent signals."""
    if 'ballast' not in working_df.columns:
        logger.warning(
            'Ballast valve column not found in Eklipse log. '
            'Cannot compute base_pressure and base_pressure_ballast;'
            ' both remain None.'
        )
        return None, None

    ballast = _to_num(working_df['ballast']).fillna(0).values
    on_positions = np.where(ballast == 1)[0]
    if not len(on_positions):
        logger.warning(
            'Ballast valve was never activated. Assuming '
            'inert-only process (Ar, N2). Base pressure will be '
            'set; ballast pressure remains None.'
        )
        valid = pressure_arr[np.isfinite(pressure_arr)]
        base_pressure = float(np.nanmin(valid)) if len(valid) else None
        return base_pressure, None

    first_on = int(on_positions[0])
    pre_ballast = pressure_arr[:first_on]
    pre_valid = pre_ballast[np.isfinite(pre_ballast)]
    base_pressure = float(np.nanmin(pre_valid)) if len(pre_valid) else None
    if not len(pre_valid):
        logger.warning(
            'No valid pressure data before ballast activation. '
            'Base pressure remains None.'
        )

    post_end = len(pressure_arr)
    if 'vent_line' in working_df.columns:
        vent = _to_num(working_df['vent_line']).fillna(0).values.astype(float)
        vent_positions = np.where((np.arange(len(vent)) > first_on) & (vent == 1))[0]
        if len(vent_positions):
            post_end = int(vent_positions[0])

    post_values = pressure_arr[first_on:post_end]
    post_valid = post_values[np.isfinite(post_values)]
    ballast_pressure = float(np.nanmean(post_valid)) if len(post_valid) else None
    if not len(post_valid):
        logger.warning(
            'No valid pressure data in ballast window '
            '(ballast on until vent reopen). '
            'Ballast base pressure remains None.'
        )
    return base_pressure, ballast_pressure


_RATE_OF_RISE_REQUIRED_COLUMNS = (
    'ar_flow_m3_s',
    'n2_flow_m3_s',
    'ph3_in_ar_flow_m3_s',
    'nh3_in_ar_flow_m3_s',
    'h2s_in_ar_flow_m3_s',
)


def _missing_rate_of_rise_columns(working_df):
    missing = []
    for column in (
        'time_s',
        'vent_line',
        'throttle_closed',
        'throttle_open',
        'throttle_position',
        'ballast',
        *_RATE_OF_RISE_REQUIRED_COLUMNS,
    ):
        if column not in working_df.columns:
            missing.append(column)
    return missing


def _static_vacuum_runs(static_vacuum_mask):
    static_idx = np.where(static_vacuum_mask)[0]
    if not len(static_idx):
        return []
    run_edges = np.where(np.diff(static_idx) > 1)[0]
    run_starts = np.concatenate(([0], run_edges + 1))
    run_ends = np.concatenate((run_edges, [len(static_idx) - 1]))
    return [
        static_idx[int(start) : int(end) + 1]
        for start, end in zip(run_starts, run_ends)
        if int(end) - int(start) + 1 >= RATE_OF_RISE_MIN_STATIC_SAMPLES
    ]


def _select_rate_of_rise_run(valid_runs, throttle_motion_mask, start_point_mask, warn):
    for run in valid_runs:
        motion_positions = np.where(throttle_motion_mask[run])[0]
        if not len(motion_positions):
            continue
        first_motion_idx = int(run[motion_positions[0]])
        run_candidates = run[start_point_mask[run]]
        if np.any(run_candidates >= first_motion_idx):
            return run

    if valid_runs:
        warn(
            'Rate-of-rise settled start sample with throttle position 0 and '
            'pressure below 15 mTorr was not found inside static-vacuum '
            'window; falling back to first valid static-vacuum run.'
        )
        return valid_runs[0]
    return None


@dataclass
class _RateOfRiseArrays:
    time: np.ndarray
    pressure: np.ndarray
    throttle_position: np.ndarray


def _compute_selected_rate_of_rise(
    arrays: _RateOfRiseArrays, selected_run, start_point_mask, warn, logger
):
    start_mask = np.zeros_like(start_point_mask, dtype=bool)
    if selected_run is not None:
        start_candidates = selected_run[start_point_mask[selected_run]]
        if len(start_candidates):
            start_point = int(start_candidates[0])
            run_start_time = float(arrays.time[int(selected_run[0])])
            run_end_time = float(arrays.time[int(selected_run[-1])])
            start_time = float(arrays.time[start_point])
            start_position = float(arrays.throttle_position[start_point])
            start_mask[start_point : int(selected_run[-1]) + 1] = True
            warn(
                'Rate-of-rise window selected from '
                f'{run_start_time:.3f} s to {run_end_time:.3f} s; '
                f'start sample at {start_time:.3f} s with throttle '
                f'position {start_position:.3f}.'
            )
        else:
            warn(
                'Rate-of-rise run was found, but no settled static sample '
                'with throttle position 0 and pressure below 15 mTorr '
                'was present in that run.'
            )

    start_idx = np.where(start_mask)[0]
    rate = _compute_rate_of_rise(arrays.time, arrays.pressure, start_mask)
    if rate is not None and len(start_idx):
        match_time = float(arrays.time[int(start_idx[0])])
        end_time = float(arrays.time[int(start_idx[-1])])
        message = (
            'Rate-of-rise static-vacuum window matched from '
            f'{match_time:.3f} s to {end_time:.3f} s.'
        )
        if logger is not None:
            logger.warning(message)
        else:
            logger.warning(message)
    else:
        warn(
            'Rate of rise could not be computed: '
            'need at least two valid points from a static-vacuum run of '
            f'{RATE_OF_RISE_MIN_STATIC_SAMPLES}+ samples '
            '(vent/throttle static, gas flows below cutoff, ballast off, '
            'and first sample below 15 mTorr with 0 < throttle position < 100)'
        )
    return rate


def _derive_rate_of_rise(working_df, pressure_arr, warn, logger):
    missing = _missing_rate_of_rise_columns(working_df)
    if missing:
        warn(
            'Rate of rise could not be computed: missing required column(s): '
            + ', '.join(sorted(set(missing)))
        )
        return None

    time_arr = _to_num(working_df['time_s']).values.astype(float)
    vent = _to_num(working_df['vent_line']).values.astype(float)
    throttle_closed = _to_num(working_df['throttle_closed']).values.astype(float)
    throttle_open = _to_num(working_df['throttle_open']).values.astype(float)
    throttle_position = _to_num(working_df['throttle_position']).values.astype(float)
    ballast = _to_num(working_df['ballast']).values.astype(float)
    flow_arrays = [
        _to_num(working_df[column]).values.astype(float)
        for column in _RATE_OF_RISE_REQUIRED_COLUMNS
    ]
    gas_static = np.ones_like(time_arr, dtype=bool)
    for flow in flow_arrays:
        gas_static &= np.isfinite(flow) & (np.abs(flow) < MIN_USED_GAS_FLOW_M3_S)

    static_vacuum_mask = (
        np.isfinite(time_arr)
        & np.isfinite(pressure_arr)
        & (vent == 0)
        & (throttle_closed == 1)
        & (throttle_open == 0)
        & gas_static
        & (ballast == 0)
    )
    throttle_motion_mask = (
        np.isfinite(throttle_position)
        & (throttle_position > 0)
        & (throttle_position < RATE_OF_RISE_MAX_THROTTLE_POSITION)
    )
    throttle_settled_mask = np.isfinite(throttle_position) & (throttle_position == 0)
    pressure_start_mask = pressure_arr < RATE_OF_RISE_MAX_CAPMAN_PRESSURE_PA
    start_point_mask = static_vacuum_mask & throttle_settled_mask & pressure_start_mask
    valid_runs = _static_vacuum_runs(static_vacuum_mask)
    selected_run = _select_rate_of_rise_run(
        valid_runs,
        throttle_motion_mask,
        start_point_mask,
        warn,
    )
    arrays = _RateOfRiseArrays(
        time_arr,
        pressure_arr,
        throttle_position,
    )
    return _compute_selected_rate_of_rise(
        arrays,
        selected_run,
        start_point_mask,
        warn,
        logger,
    )


def _derive_general_values(process_df, key_values: dict[str, float], logger=None):
    """Derive base pressure, ballast pressure and rate of rise."""
    _ = key_values

    def emit_rate_warning(message: str) -> None:
        if logger is not None:
            logger.warning(message)

    working_df = process_df.copy()
    if 'is_disregarded' in working_df.columns:
        working_df = working_df[~working_df['is_disregarded']].reset_index(drop=True)

    base_pressure = None
    base_pressure_ballast = None
    rate_of_rise = None
    if not working_df.empty and working_df['pressure_raw'].notna().sum() > 0:
        pressure_arr = (
            _to_num(working_df['pressure_raw'])
            .apply(_pressure_to_pa)
            .values.astype(float)
        )
        has_ballast_column = 'ballast' in working_df.columns
        if has_ballast_column:
            base_pressure, base_pressure_ballast = _derive_ballast_pressures(
                working_df, pressure_arr
            )
        else:
            logger.warning(
                'Ballast valve column not found in Eklipse log. '
                'Cannot compute base_pressure and base_pressure_ballast;'
                ' both remain None.'
            )
        rate_of_rise = _derive_rate_of_rise(
            working_df,
            pressure_arr,
            emit_rate_warning,
            logger,
        )
    else:
        emit_rate_warning(
            'Rate of rise could not be computed: process data is empty or pressure '
            'samples are missing.'
        )

    return base_pressure, base_pressure_ballast, rate_of_rise


def _detect_used_gases(
    steps: list[ParsedRTPStep], overview: dict[str, float | None]
) -> list[str]:
    """Detect which process gases were really used.

    Priority:
    1. Main dwell / annealing step
    2. First heating ramp (last resort)

    """
    _ = overview  # Reserved for future metadata-derived values.
    flow_values: dict[str, float | None]

    # ------------------------------------------------------------------
    # 1. Prefer the highest-temperature dwell-like step
    # ------------------------------------------------------------------
    dwell_steps = [s for s in steps if _is_dwell_like_name(s.name or '')]
    main_dwell = (
        max(dwell_steps, key=lambda s: s.mean_temperature_k or 0.0)
        if dwell_steps
        else None
    )

    if main_dwell is not None:
        flow_values = {
            'Ar': main_dwell.ar_flow_m3_s,
            'N2': main_dwell.n2_flow_m3_s,
            'PH3': main_dwell.ph3_in_ar_flow_m3_s,
            'NH3': main_dwell.nh3_in_ar_flow_m3_s,
            'H2S': main_dwell.h2s_in_ar_flow_m3_s,
        }
    else:
        # ------------------------------------------------------------------
        # 2. Last resort: first heating ramp in chronological order
        # ------------------------------------------------------------------
        first_heating_step = next(
            (s for s in steps if 'heat' in (s.name or '').lower()),
            None,
        )

        if first_heating_step is not None:
            logger.warning(
                'No explicit Dwell step found. Using the first Heating ramp '
                'to detect used gases.'
            )
            flow_values = {
                'Ar': first_heating_step.ar_flow_m3_s,
                'N2': first_heating_step.n2_flow_m3_s,
                'PH3': first_heating_step.ph3_in_ar_flow_m3_s,
                'NH3': first_heating_step.nh3_in_ar_flow_m3_s,
                'H2S': first_heating_step.h2s_in_ar_flow_m3_s,
            }
        else:
            logger.warning(
                'No explicit Dwell step and no Heating step found. '
                'Used gases cannot be determined.'
            )
            flow_values = {
                'Ar': None,
                'N2': None,
                'PH3': None,
                'NH3': None,
                'H2S': None,
            }

    used_gases = [
        gas
        for gas, flow in flow_values.items()
        if flow is not None and float(flow) > MIN_USED_GAS_FLOW_M3_S
    ]

    if not used_gases:
        logger.warning(
            'No process gases detected as being used. '
            'All gas flows are either None or below the threshold '
            f'({MIN_USED_GAS_FLOW_M3_S} m³/s).'
        )

    return used_gases


def _read_cx_thermo_diagnostics(paths):
    unique_paths = list(dict.fromkeys(path for path in paths or [] if path))
    if not unique_paths:
        raise FileNotFoundError('No temperature diagnostics logfile path was provided.')

    key_values: dict[str, float] = {}
    tables = []
    for path in unique_paths:
        with open(path, encoding='utf-8', errors='ignore') as handle:
            txt = handle.read()
        for key, value in _extract_key_values(txt).items():
            if key not in key_values:
                key_values[key] = value
        tables.append(_parse_cx_thermo_table(txt))
    return key_values, tables


def _combine_cx_thermo_tables(tables, logger=None):
    if len(tables) == 1:
        return tables[0]

    cx_thermo_df = pd.concat(tables, ignore_index=True, sort=False)
    time_column = _find_col(cx_thermo_df, [r'timestamp', r'^time$'])
    if time_column is not None:
        cx_thermo_df['_parsed_timestamp'] = _to_datetime(cx_thermo_df[time_column])
        return (
            cx_thermo_df.sort_values('_parsed_timestamp')
            .drop_duplicates(subset=['_parsed_timestamp'], keep='first')
            .drop(columns=['_parsed_timestamp'])
            .reset_index(drop=True)
        )
    if logger is not None:
        logger.warning(
            'Could not find a timestamp column while stacking multiple '
            'temperature logfiles; keeping concatenated row order as-is.'
        )
    return cx_thermo_df


def _build_rtp_result(eklipse_df, cx_thermo_df, key_values, logger):
    process_df = _build_process_df(eklipse_df, cx_thermo_df)
    if 'is_disregarded' not in process_df.columns:
        process_df['is_disregarded'] = False
    _mark_disregarded_samples(process_df, logger=logger)

    steps = _extract_steps(process_df)
    has_detected_annealing = _main_annealing_step_index(steps) is not None
    overview = _empty_result().overview
    total_heating_time, total_cooling_time = _derive_total_heating_cooling_times(steps)
    overview['total_heating_time'] = total_heating_time
    overview['total_cooling_time'] = total_cooling_time
    overview['end_of_process_temperature'] = _derive_end_of_process_temperature(
        process_df, steps
    )

    if has_detected_annealing:
        anneal_overview = _derive_overview(steps)
        overview_fields = {
            'total_heating_time',
            'total_cooling_time',
            'end_of_process_temperature',
        }
        for key, value in anneal_overview.items():
            if key not in overview_fields:
                overview[key] = value
    elif logger is not None:
        logger.warning(
            'No annealing step detected; RTP overview will not be auto-populated '
            'except for end of process temperature, number of dwells'
            ' and material space. Feel free to manually populate'
            ' the overview fields.'
        )

    base_pressure, base_pressure_ballast, rate_of_rise = _derive_general_values(
        process_df, key_values, logger=logger
    )
    used_gases = _detect_used_gases(steps, overview)
    timeseries = _extract_timeseries(process_df)
    if not steps and logger is not None:
        logger.warning('No process steps extracted from log files')

    return ParsedRTPData(
        used_gases=used_gases,
        base_pressure_pa=base_pressure,
        base_pressure_ballast_pa=base_pressure_ballast,
        rate_of_rise_pa_s=rate_of_rise,
        chiller_flow_m3_s=None,
        overview=overview,
        steps=steps,
        timeseries=timeseries,
        has_detected_annealing=has_detected_annealing,
    )


def _parse_rtp_logfiles(eklipse_csv_path, diagnostics_paths, logger):
    eklipse_df = _read_csv_with_fallback(eklipse_csv_path)
    key_values, tables = _read_cx_thermo_diagnostics(diagnostics_paths)
    cx_thermo_df = _combine_cx_thermo_tables(tables, logger)
    return _build_rtp_result(eklipse_df, cx_thermo_df, key_values, logger)


def parse_rtp_logfiles(
    eklipse_csv_path: str,
    cx_thermo_diagnostics_txt_paths: list[str] | None = None,
    logger=None,
) -> ParsedRTPData:
    """Parse RTP log files and return schema-ready process, step, and overview data.

    If one temperature logfile is provided, it is used directly.
    If multiple logfiles are provided, they are stacked by timestamp.
    """
    if not _ensure_deps():
        return _empty_result()

    try:
        return _parse_rtp_logfiles(
            eklipse_csv_path,
            cx_thermo_diagnostics_txt_paths,
            logger,
        )
    except Exception as e:
        # Never let parser edge cases crash NOMAD normalization.
        if logger is not None:
            logger.warning(
                f'RTP log parsing encountered critical error: {e}. '
                'Returning empty result.'
            )
        return _empty_result()
