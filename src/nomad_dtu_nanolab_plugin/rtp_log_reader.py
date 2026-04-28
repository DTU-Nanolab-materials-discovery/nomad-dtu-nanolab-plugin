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

# Step segmentation thresholds.
# Minimum duration for a segment to be kept (seconds).
SEGMENT_MIN_DURATION_S = 5.0
# Minimum number of data points for a segment to be kept.
SEGMENT_MIN_POINTS = 3
# Temperature slope threshold (K/s) below which a segment is classified as a Dwell.
# Slopes with |dT/dt| < this value are considered flat.
DWELL_SLOPE_THRESHOLD_K_S = 0.5
# Gaussian smoothing window half-width used before computing the derivative.
# A wider window reduces noise sensitivity at the cost of temporal resolution.
SLOPE_SMOOTH_WINDOW = 5


@dataclass
class ParsedRTPStep:
    name: str
    duration_s: float
    initial_temperature_k: float
    final_temperature_k: float
    pressure_pa: float | None
    ar_flow_m3_s: float
    n2_flow_m3_s: float
    ph3_in_ar_flow_m3_s: float
    h2s_in_ar_flow_m3_s: float
    mean_temperature_k: float | None = None
    start_time_s: float | None = None
    end_time_s: float | None = None
    real_start_time_s: float | None = None
    real_start_temperature_k: float | None = None


@dataclass
class ParsedRTPData:
    used_gases: list[str]
    base_pressure_pa: float | None
    base_pressure_ballast_pa: float | None
    rate_of_rise_pa_s: float | None
    # Kept for schema compatibility, intentionally not parsed from logs.
    chiller_flow_m3_s: float | None
    overview: dict[str, float | None]
    steps: list[ParsedRTPStep]
    timeseries: dict[str, list[float]]


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
            'annealing_h2s_in_ar_flow': None,
            'total_heating_time': None,
            'total_cooling_time': None,
            'end_of_process_temperature': None,
        },
        steps=[],
        timeseries={},
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

    return True


def _normalize(name: str) -> str:
    """Normalize labels so matching works across different logfile variants."""
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

        hits = [
            (line_norm.find(norm_name), original_name)
            for norm_name, original_name in normalized_map.items()
            if norm_name in line_norm
        ]
        ordered = [name for _, name in sorted(hits) if _ >= 0]
        if ordered:
            return ordered

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

            # Generic fallback for tests/simpler CSVs that still have a timestamp header
            if not header_line:
                handle.seek(0)
                for i, line in enumerate(handle):
                    if 'timestamp' in _normalize(line):
                        header_idx = i
                        header_line = line
                        break

        delimiter = ','
        if header_line:
            try:
                sniff = csv.Sniffer().sniff(header_line, delimiters=',;\t')
                delimiter = sniff.delimiter
            except Exception:
                if header_line.count(';') > header_line.count(','):
                    delimiter = ';'

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
        return pd.DataFrame()


def _to_datetime(series):
    """Parse timestamps with strict format first, then looser datetime/timedelta."""
    if pd is None:
        return series

    dt = pd.to_datetime(series, errors='coerce', format='%Y/%m/%d_%H:%M:%S')
    if dt.notna().sum() > 0:
        return dt

    dt = pd.to_datetime(series, errors='coerce')
    if dt.notna().sum() > 0:
        return dt

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


def _parse_cx_thermo_table(txt: str):
    """Parse CX-Thermo diagnostics table with metadata+CSV structure.

    Expected primary structure:
    - key/value metadata lines
    - blank line(s)
    - CSV table starting with a timestamp header
    """
    if pd is None:
        raise RuntimeError('pandas not loaded')

    lines = [line.rstrip() for line in txt.splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame()

    # Primary path: CSV-style diagnostics block, e.g.:
    # Timestamp,Temperature
    # 2025-12-09 14:53:05,25
    header_idx = None
    for i, line in enumerate(lines):
        line_norm = _normalize(line)
        if 'timestamp' in line_norm and any(d in line for d in [',', ';', '\t']):
            header_idx = i
            break

    if header_idx is not None:
        header_line = lines[header_idx]
        delimiter = ','
        try:
            sniff = csv.Sniffer().sniff(header_line, delimiters=',;\t')
            delimiter = sniff.delimiter
        except Exception:
            if header_line.count(';') > header_line.count(','):
                delimiter = ';'

        csv_block = '\n'.join(lines[header_idx:])
        try:
            csv_df = pd.read_csv(
                io.StringIO(csv_block),
                sep=delimiter,
                engine='python',
                skipinitialspace=True,
                on_bad_lines='skip',
                quotechar='"',
            )
            has_timestamp = _find_col(csv_df, [r'timestamp', r'^time$']) is not None
            has_values = len(csv_df.columns) >= MIN_COLUMNS_FOR_TABLE_ROW
            if has_timestamp and has_values:
                return csv_df
        except Exception:
            pass

    # Secondary fallback: TrendLog-style rows, e.g. 2025/11/28_14:12:00 ...
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


def _find_col(df, patterns: list[str]) -> str | None:
    """Return the first dataframe column matching any normalized regex.
    In case we use this parser for other dataframes types (lab equipment changes
    or different lab)."""
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
    # Convert 1450°C setpoint to Kelvin for comparison
    virtual_temp_k = VIRTUAL_TEMPERATURE_SETPOINT_C + CELSIUS_TO_KELVIN_OFFSET
    # Check if samples are at 1450°C (400°C tolerance to catch ramp up and down)
    # Note: atol=400 in Kelvin is equivalent to 400°C
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

    # Initialize disregarded column if not already present
    if 'is_disregarded' not in process_df.columns:
        process_df['is_disregarded'] = False

    virtual_mask = _identify_virtual_temperature_samples(process_df)
    if virtual_mask is None or not np.any(virtual_mask):
        return False

    # Constrain to cooling phase if boundaries provided
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

    # Mark all 1450°C samples as disregarded
    process_df.loc[virtual_mask, 'is_disregarded'] = True

    if logger is not None:
        # Find the time interval containing disregarded samples
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


def _build_process_df(eklipse_df, cx_thermo_df):
    """Merge Eklipse and CX-Thermo streams onto one shared process timeline."""
    if pd is None:
        raise RuntimeError('pandas not loaded')

    e = pd.DataFrame()
    t = pd.DataFrame()

    e_time = _find_col(eklipse_df, [r'timestamp', r'^time$', r'timestamp'])
    if e_time is not None:
        e['timestamp'] = _to_datetime(eklipse_df[e_time])
    else:
        logger.warning(
            'Eklipse timestamp column not found; Eklipse data cannot be time-aligned.'
        )

    p_col = _find_col(
        eklipse_df,
        [r'capmanpressure$'],  # add more options if different logfiles in the future
    )
    if p_col is not None:
        e['pressure_raw'] = _to_num(eklipse_df[p_col])
    else:
        e['pressure_raw'] = np.nan

    flow_map = {  # add more options if different logfiles in the future
        'ar_flow_m3_s': [r'mfc1flow$'],
        'n2_flow_m3_s': [r'mfc2flow$'],
        'ph3_in_ar_flow_m3_s': [r'mfc4flow$'],
        'h2s_in_ar_flow_m3_s': [r'mfc6flow$'],
    }
    for out_col, patterns in flow_map.items():
        c = _find_col(eklipse_df, patterns)
        if c is None:
            e[out_col] = 0.0
        else:
            e[out_col] = _to_num(eklipse_df[c]).fillna(0) * SCCM_TO_M3_S

    flow_setpoint_map = {  # add more options if different logfiles in the future
        'ar_flow_setpoint_m3_s': [r'mfc1setpoint$'],
        'n2_flow_setpoint_m3_s': [r'mfc2setpoint$'],
        'ph3_in_ar_flow_setpoint_m3_s': [r'mfc4setpoint$'],
        'h2s_in_ar_flow_setpoint_m3_s': [r'mfc6setpoint$'],
    }
    for out_col, patterns in flow_setpoint_map.items():
        c = _find_col(eklipse_df, patterns)
        if c is None:
            e[out_col] = 0.0
        else:
            e[out_col] = _to_num(eklipse_df[c]).fillna(0) * SCCM_TO_M3_S

    # Diagnostic columns used for base pressure and rate-of-rise.
    ballast_col = _find_col(
        eklipse_df,
        [r'ballastvalve$'],
    )
    if ballast_col is not None:
        e['ballast'] = _to_num(eklipse_df[ballast_col]).fillna(0)

    vent_col = _find_col(
        eklipse_df,
        [r'ventvalve$'],
    )
    if vent_col is not None:
        e['vent_line'] = _to_num(eklipse_df[vent_col]).fillna(0)

    throttle_closed_col = _find_col(
        eklipse_df,
        [r'throttlevalveclosed$'],
    )
    throttle_open_col = _find_col(
        eklipse_df,
        [r'throttlevalveopened$'],
    )
    throttle_pos_col = _find_col(
        eklipse_df,
        [r'throttlevalveposition$'],
    )

    if throttle_closed_col is not None:
        # Binary encoding: 1 means throttle closed, 0 means open.
        e['throttle_closed'] = _to_num(eklipse_df[throttle_closed_col]).fillna(0)
    if throttle_open_col is not None:
        # Binary encoding: 1 means throttle open, 0 means not open.
        e['throttle_open'] = _to_num(eklipse_df[throttle_open_col]).fillna(0)
    if throttle_pos_col is not None:
        # Continuous position value: 0 = fully closed, 100 = fully open.
        e['throttle_position'] = _to_num(eklipse_df[throttle_pos_col])

    # add more options if different logfiles in the future
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
        t['temperature_k'] = _temperature_to_kelvin(cx_thermo_df[t_temp])
    if t_setpoint is not None:
        t['temperature_setpoint_k'] = _temperature_to_kelvin(cx_thermo_df[t_setpoint])
    if t_lamp_power is not None:
        t['lamp_power'] = _to_num(cx_thermo_df[t_lamp_power])

    # Removing missing values from each dataframe before merging
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

    # Build a union timeline so plots can cover the full range of both logs.
    if not t.empty and not e.empty:
        # Step 1: stacking all timestamps from CX-Thermo and Eklipse into one series
        #  and removing duplicates, NaN and sorting them.
        timeline = pd.DataFrame(
            {
                'timestamp': pd.concat([t['timestamp'], e['timestamp']])
                .dropna()
                .drop_duplicates()
                .sort_values()
                .reset_index(drop=True)
            }
        )
        # Step 2: For each timestamp in timeline, pandas picks the closest CX-Thermo row
        # (before or after) within 8 seconds and copies CX-Thermo columns into process.
        process = pd.merge_asof(
            timeline,
            t,
            on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta(seconds=8),
        )
        # Step 3: Same idea again, now matching each row to the closest Eklipse
        #  sample within 8 seconds and adding pressure/flow/valve columns.
        process = pd.merge_asof(
            process,
            e,
            on='timestamp',
            direction='nearest',
            tolerance=pd.Timedelta(seconds=8),
        )
    elif not t.empty:
        process = t.copy()
        process['pressure_raw'] = np.nan
        process['ar_flow_m3_s'] = 0.0
        process['n2_flow_m3_s'] = 0.0
        process['ph3_in_ar_flow_m3_s'] = 0.0
        process['h2s_in_ar_flow_m3_s'] = 0.0
    elif not e.empty:
        process = e.copy()
        process['temperature_k'] = np.nan
    else:
        return pd.DataFrame()

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
        'h2s_in_ar_flow_m3_s': [],
    }

    if 'time_s' not in df:
        logger.warning(
            'Time column missing from process data, cannot extract timeseries'
        )
        return out

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

    flow_cols = {
        'ar_flow_m3_s': 'ar_flow_m3_s',
        'n2_flow_m3_s': 'n2_flow_m3_s',
        'ph3_in_ar_flow_m3_s': 'ph3_in_ar_flow_m3_s',
        'h2s_in_ar_flow_m3_s': 'h2s_in_ar_flow_m3_s',
    }
    for out_col, src_col in flow_cols.items():
        if src_col in df:
            out[out_col] = [
                float(v) if np.isfinite(v) else float('nan')
                for v in _to_num(df[src_col]).to_list()
            ]

    return out


def _find_heating_real_start(
    step_df: pd.DataFrame,
) -> tuple[float | None, float | None]:
    """Find the real start time of a heating step.

    Real start is defined as the first moment when setpoint temperature
    meets or exceeds the actual temperature during heating.

    Returns: (real_start_time_s, real_start_temperature_k) or (None, None)
    """
    if 'temperature_setpoint_k' not in step_df.columns:
        logger.warning(
            'Temperature setpoint data missing; cannot identify real heating start '
            '(setpoint-vs-actual crossover)'
        )
        return None, None
    if 'temperature_k' not in step_df.columns:
        logger.warning('Temperature data missing; cannot identify real heating start')
        return None, None
    if 'time_s' not in step_df.columns:
        logger.warning('Time data missing; cannot identify real heating start timing')
        return None, None

    try:
        time_arr = _to_num(step_df['time_s']).to_numpy()
        temp_arr = _to_num(step_df['temperature_k']).to_numpy()
        setpoint_arr = _to_num(step_df['temperature_setpoint_k']).to_numpy()

        # Find where setpoint >= actual temperature (setpoint is trying to drive system)
        # Looking for the first valid crossover point
        for i in range(len(temp_arr)):
            if not (
                np.isfinite(time_arr[i])
                and np.isfinite(temp_arr[i])
                and np.isfinite(setpoint_arr[i])
            ):
                continue
            # Real heating starts when setpoint first meets/exceeds actual temp
            if float(setpoint_arr[i]) >= float(temp_arr[i]):
                return float(time_arr[i]), float(temp_arr[i])

        # If no crossover found, return None
        logger.warning(
            'No heating real start detected: setpoint temperature never '
            'met or exceeded actual temperature during step.'
        )
        return None, None
    except Exception as e:
        logger.warning(
            f'Error detecting heating real start time: {e}. Using step boundary values.'
        )
        return None, None


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
                'h2s_in_ar_flow_m3_s',
            ]
        )
    ):
        return None

    time_arr = step_df['time_s'].to_numpy()
    ar_arr = step_df['ar_flow_m3_s'].to_numpy()
    n2_arr = step_df['n2_flow_m3_s'].to_numpy()
    ph3_arr = step_df['ph3_in_ar_flow_m3_s'].to_numpy()
    h2s_arr = step_df['h2s_in_ar_flow_m3_s'].to_numpy()

    if len(time_arr) != len(ar_arr):
        return None

    try:
        had_gas_on = False
        for t, ar_f, n2_f, ph3_f, h2s_f in zip(
            time_arr, ar_arr, n2_arr, ph3_arr, h2s_arr
        ):
            flows = [ar_f, n2_f, ph3_f, h2s_f]
            # Check if any gas flow is above the threshold
            gas_on = any(
                np.isfinite(flow) and abs(float(flow)) > MIN_USED_GAS_FLOW_M3_S
                for flow in flows
            )
            if gas_on:
                had_gas_on = True
            elif had_gas_on:
                # First point where all gases turn off after being on
                return float(t)
        # Gases never shut off (remain active until step end)
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
    required = [
        'time_s',
        'ar_flow_setpoint_m3_s',
        'n2_flow_setpoint_m3_s',
        'ph3_in_ar_flow_setpoint_m3_s',
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
            'h2s_in_ar_flow_setpoint_m3_s',
        ]

        gas_arrays = [_to_num(step_df[col]).to_numpy(dtype=float) for col in gas_cols]

        # Determine ON/OFF state for each gas at each sample
        gas_on = np.array(
            [
                [np.isfinite(v) and v > MIN_USED_GAS_FLOW_M3_S for v in gas_values]
                for gas_values in zip(*gas_arrays)
            ]
        )  # shape: (num_samples, num_gases)

        # If no gas is ever ON, nothing to detect
        if not np.any(gas_on):
            return None

        # Track previous state to detect transitions
        prev_state = gas_on[0]

        for i in range(1, len(gas_on)):
            current_state = gas_on[i]

            # A transition occurs if any gas was ON and is now OFF
            turned_off = prev_state & ~current_state

            if np.any(turned_off):
                # Return timestamp of the previous sample
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

    A symmetric window of size (2*half_window + 1) is used.  Near the edges
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
    temperature data is unavailable).  After merging the neighbour label is
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
                # Update boundaries: remove boundary at index i
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
        return float((temp_v[-1] - temp_v[0]) / (t_v[-1] - t_v[0]))


def _segment_label_ordinals(base_names: list[str]) -> list[str]:
    """Add ordinal prefixes (2nd, 3rd, …) only when the same base name repeats.

    The first occurrence keeps the plain name; later ones become "2nd X", "3rd X", …
    """

    def _ordinal(n: int) -> str:
        if n == ORDINAL_SECOND:
            return '2nd'
        if n == ORDINAL_THIRD:
            return '3rd'
        return f'{n}th'

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
            final.append(f'{_ordinal(n)} {bn}' if n > 1 else bn)
    return final


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
    current = labels_per_sample[0]
    for i in range(1, n):
        if labels_per_sample[i] != current:
            boundaries.append(i)
            current = labels_per_sample[i]

    return boundaries


def _extract_steps(process_df) -> list[ParsedRTPStep]:
    """Split the run into named RTP steps: Heating, Dwell, and Cooling.

    The algorithm:
    1. Smooth the temperature trace and compute a derivative.
    2. Classify each sample as Heating (dT/dt > threshold),
       Cooling (dT/dt < -threshold), or Dwell (|dT/dt| <= threshold).
    3. Group consecutive same-class samples into candidate segments.
    4. Merge segments that are too short (< SEGMENT_MIN_DURATION_S or
       < SEGMENT_MIN_POINTS) into their longer neighbour.
    5. Recompute each segment's final label from its overall linear slope
       (this guards against a segment that flipped label due to noise).
    6. Add ordinal prefixes when the same label appears more than once
       (e.g. "Heating", "2nd Heating", "3rd Heating").

    The word "Dwell" is used throughout instead of "Annealing" or "Plateau".
    """
    if process_df.empty:
        logger.warning('Cannot extract steps: process dataframe is empty')
        return []

    # Filter out 1450°C samples (marked as disregarded) for step extraction
    df_for_steps = process_df
    if 'is_disregarded' in process_df.columns:
        df_for_steps = process_df[~process_df['is_disregarded']].reset_index(drop=True)
        if df_for_steps.empty:
            logger.warning(
                'All temperature samples are marked as disregarded (1450°C artifacts). '
                'Cannot extract steps.'
            )
            return []

    if df_for_steps['temperature_k'].notna().sum() < MIN_POINTS_FOR_STEPS:
        num_valid = df_for_steps['temperature_k'].notna().sum()
        logger.warning(
            f'Cannot extract steps: insufficient temperature data points '
            f'({num_valid} < {MIN_POINTS_FOR_STEPS}). '
            f'Falling back to single step.'
        )
        return []

    df = df_for_steps.dropna(subset=['temperature_k', 'time_s']).copy()
    if len(df) < MIN_POINTS_FOR_STEPS:
        logger.warning(
            f'Insufficient temperature data after dropna: {len(df)} points < '
            f'{MIN_POINTS_FOR_STEPS} minimum. Falling back to single step.'
        )
        return []

    temp = df['temperature_k'].to_numpy(dtype=float)
    time_s = df['time_s'].to_numpy(dtype=float)

    # ------------------------------------------------------------------ #
    # 1. Find inflection points using smoothed derivative.                #
    # ------------------------------------------------------------------ #
    raw_boundaries = _find_inflection_points(time_s, temp)

    # Build initial label list (one label per segment) from first-sample slope.
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

    # ------------------------------------------------------------------ #
    # 2. Merge short segments.                                            #
    # ------------------------------------------------------------------ #
    merged_labels, merged_boundaries = _merge_short_segments(
        raw_labels[:],
        raw_boundaries[:],
        time_s,
        min_duration_s=SEGMENT_MIN_DURATION_S,
        min_points=SEGMENT_MIN_POINTS,
    )

    # ------------------------------------------------------------------ #
    # 3. Recompute labels after merging (full-segment linear slope).      #
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 4. Add ordinal prefixes for repeated labels.                        #
    # ------------------------------------------------------------------ #
    final_names = _segment_label_ordinals(final_base_labels)

    # ------------------------------------------------------------------ #
    # 5. Build ParsedRTPStep objects.                                      #
    # ------------------------------------------------------------------ #
    steps: list[ParsedRTPStep] = []
    for seg_idx, (start, name) in enumerate(zip(merged_boundaries, final_names)):
        end = (
            merged_boundaries[seg_idx + 1]
            if seg_idx + 1 < len(merged_boundaries)
            else len(df)
        )
        sl = df.iloc[start:end]
        if len(sl) < 1:
            continue

        duration = float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0])
        if duration <= 0 and len(sl) > 1:
            continue

        initial_temp = float(sl['temperature_k'].iloc[0])
        final_temp = float(sl['temperature_k'].iloc[-1])
        base_label = final_base_labels[seg_idx]
        is_heating = base_label == 'Heating'
        is_cooling = base_label == 'Cooling'

        # Find gas shutoff time for the averaging window.
        shutoff_time = _find_gas_shutoff_time(sl)
        pressure_average_window_df = (
            sl[sl['time_s'] <= shutoff_time] if shutoff_time is not None else sl
        )
        flow_average_window_df = pressure_average_window_df

        # For cooling: use setpoint drop for flows, vent for pressure.
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

        # Real start detection for heating segments.
        real_start_time = None
        real_start_temp = None
        if is_heating:
            real_start_time, real_start_temp = _find_heating_real_start(sl)

        start_time = (
            real_start_time
            if real_start_time is not None
            else float(sl['time_s'].iloc[0])
        )
        initial_temperature = (
            real_start_temp if real_start_temp is not None else initial_temp
        )
        adjusted_duration = float(sl['time_s'].iloc[-1] - start_time)

        pressure_pa: float | None = None
        if 'pressure_raw' in sl.columns:
            raw_mean = float(np.nanmean(pressure_average_window_df['pressure_raw']))
            pressure_pa = _pressure_to_pa(raw_mean)

        step = ParsedRTPStep(
            name=name,
            duration_s=adjusted_duration,
            start_time_s=start_time,
            end_time_s=float(sl['time_s'].iloc[-1]),
            initial_temperature_k=initial_temperature,
            final_temperature_k=final_temp,
            pressure_pa=pressure_pa,
            real_start_time_s=real_start_time,
            real_start_temperature_k=real_start_temp,
            ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(flow_average_window_df['ar_flow_m3_s']))
                if 'ar_flow_m3_s' in flow_average_window_df.columns
                else 0.0,
                'Ar',
            ),
            n2_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(flow_average_window_df['n2_flow_m3_s']))
                if 'n2_flow_m3_s' in flow_average_window_df.columns
                else 0.0,
                'N2',
            ),
            ph3_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(flow_average_window_df['ph3_in_ar_flow_m3_s']))
                if 'ph3_in_ar_flow_m3_s' in flow_average_window_df.columns
                else 0.0,
                'PH3',
            ),
            h2s_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(flow_average_window_df['h2s_in_ar_flow_m3_s']))
                if 'h2s_in_ar_flow_m3_s' in flow_average_window_df.columns
                else 0.0,
                'H2S',
            ),
            mean_temperature_k=float(np.nanmean(sl['temperature_k'])),
        )
        steps.append(step)

    if steps:
        return steps

    # ------------------------------------------------------------------ #
    # Fallback: single Dwell across entire run.                           #
    # ------------------------------------------------------------------ #
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
    return [
        ParsedRTPStep(
            name='Dwell',
            duration_s=float(df['time_s'].iloc[-1] - df['time_s'].iloc[0]),
            start_time_s=float(df['time_s'].iloc[0]),
            end_time_s=float(df['time_s'].iloc[-1]),
            initial_temperature_k=float(df['temperature_k'].iloc[0]),
            final_temperature_k=float(df['temperature_k'].iloc[-1]),
            pressure_pa=pressure_pa,
            ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(df_for_average['ar_flow_m3_s']))
                if 'ar_flow_m3_s' in df_for_average.columns
                else 0.0,
                'Ar',
            ),
            n2_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(df_for_average['n2_flow_m3_s']))
                if 'n2_flow_m3_s' in df_for_average.columns
                else 0.0,
                'N2',
            ),
            ph3_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(df_for_average['ph3_in_ar_flow_m3_s']))
                if 'ph3_in_ar_flow_m3_s' in df_for_average.columns
                else 0.0,
                'PH3',
            ),
            h2s_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmean(df_for_average['h2s_in_ar_flow_m3_s']))
                if 'h2s_in_ar_flow_m3_s' in df_for_average.columns
                else 0.0,
                'H2S',
            ),
            mean_temperature_k=float(np.nanmean(df['temperature_k'])),
        )
    ]


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

    def _is_dwell_name(name: str) -> bool:
        return bool(re.match(r'^\s*(?:\d+(?:st|nd|rd|th)\s+)?dwell\b', name.lower()))

    def _step_role(step: ParsedRTPStep) -> str:
        name = (step.name or '').lower()
        if _is_dwell_name(name):
            return 'dwell'
        if 'heat' in name:
            return 'heating'
        if 'cool' in name:
            return 'cooling'

        delta_t = step.final_temperature_k - step.initial_temperature_k
        if abs(delta_t) <= PLATEAU_TEMPERATURE_DELTA_TOLERANCE_K:
            return 'dwell'
        return 'heating' if delta_t > 0 else 'cooling'

    # Pick the main Dwell as the one with the highest mean temperature.
    dwell_steps = [(i, s) for i, s in enumerate(steps) if _is_dwell_name(s.name or '')]

    if dwell_steps:
        anneal_idx, anneal = max(
            dwell_steps,
            key=lambda idx_s: idx_s[1].mean_temperature_k or 0.0,
        )
    else:
        # Fallback heuristic when no step carries a Dwell label.
        logger.warning(
            'No step labeled "Dwell" found. '
            'Using heuristic (highest mean temperature + duration) to '
            'select the main dwell step for the overview.'
        )
        score = [
            0.7 * ((s.initial_temperature_k + s.final_temperature_k) / 2)
            + 0.3 * s.duration_s
            for s in steps
        ]
        anneal_idx = int(np.argmax(score))
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
        'annealing_ar_flow': anneal.ar_flow_m3_s,
        'annealing_n2_flow': anneal.n2_flow_m3_s,
        'annealing_ph3_in_ar_flow': anneal.ph3_in_ar_flow_m3_s,
        'annealing_h2s_in_ar_flow': anneal.h2s_in_ar_flow_m3_s,
        'total_heating_time': total_heating,
        'total_cooling_time': total_cooling,
        'end_of_process_temperature': None,
    }


def _derive_end_of_process_temperature(
    process_df, steps: list[ParsedRTPStep]
) -> float | None:
    """Estimate end-of-process temperature from gas shutoff during cooling.

    We define end-of-process as the first cooling point where all process gases
    are off (below the parasitic-flow cutoff), after being on earlier.
    """
    end_temp_k = None

    def _is_cooling_step(step: ParsedRTPStep) -> bool:
        name = (step.name or '').lower()
        if 'cool' in name:
            return True
        return (
            step.final_temperature_k - step.initial_temperature_k
            < -PLATEAU_TEMPERATURE_DELTA_TOLERANCE_K
        )

    if process_df is None or process_df.empty:
        logger.warning(
            'Cannot derive end-of-process temperature: '
            'process dataframe is empty or None'
        )
        return end_temp_k
    if 'time_s' not in process_df or 'temperature_k' not in process_df:
        logger.warning(
            'Cannot derive end-of-process temperature: '
            'time or temperature data missing from process logs'
        )
        return end_temp_k

    cooling_step = next(
        (step for step in steps if 'cool' in (step.name or '').lower()), None
    )
    if cooling_step is None:
        cooling_step = next(
            (step for step in steps if _is_cooling_step(step)),
            None,
        )
        if cooling_step is None:
            logger.warning(
                'No cooling step identified in process. '
                'Cannot determine end-of-process temperature.'
            )

    flow_cols = [
        'ar_flow_m3_s',
        'n2_flow_m3_s',
        'ph3_in_ar_flow_m3_s',
        'h2s_in_ar_flow_m3_s',
    ]

    if cooling_step is not None and not any(
        col not in process_df.columns for col in flow_cols
    ):
        df = process_df.copy()
        time_arr = _to_num(df['time_s']).to_numpy(dtype=float)
        temp_arr = _to_num(df['temperature_k']).to_numpy(dtype=float)

        cooling_mask = np.isfinite(time_arr)
        if cooling_step.start_time_s is not None:
            cooling_mask &= time_arr >= float(cooling_step.start_time_s)
        if cooling_step.end_time_s is not None:
            cooling_mask &= time_arr <= float(cooling_step.end_time_s)

        idx = np.where(cooling_mask)[0]
        if len(idx) > 0:
            flow_stack = np.column_stack(
                [
                    np.abs(_to_num(df[col]).fillna(0).to_numpy(dtype=float))[idx]
                    for col in flow_cols
                ]
            )
            gas_on = np.any(flow_stack > MIN_USED_GAS_FLOW_M3_S, axis=1)

            shutoff_rel_idx = None
            if np.any(gas_on):
                for i in range(len(gas_on)):
                    if not gas_on[i] and np.any(gas_on[:i]):
                        shutoff_rel_idx = i
                        break
            else:
                # Cooling already starts with gases off.
                shutoff_rel_idx = 0

            if shutoff_rel_idx is not None:
                temp_k = temp_arr[idx[shutoff_rel_idx]]
                if np.isfinite(temp_k):
                    end_temp_k = float(temp_k)
                else:
                    logger.warning(
                        'Gas shutoff time identified in cooling step, '
                        'but temperature at shutoff is NaN or infinite'
                    )
            else:
                logger.warning(
                    'No gas shutoff detected during cooling. '
                    'End-of-process temperature remains None.'
                )
    elif cooling_step is None:
        # Already warned above
        pass
    else:
        logger.warning(
            'One or more gas flow columns missing from process data. '
            'Cannot determine gas shutoff for end-of-process temperature.'
        )

    return end_temp_k


def _compute_rate_of_rise(time_s_arr, pressure_pa_arr, start_mask):
    """Compute rate of rise (Pa/s) from first to last valid static-vacuum point.

    start_mask marks rows where static conditions are satisfied:
        -Throttle valve is closed (1, "closed" column)
        -Vent valve is closed (0, "vent_line" column)
        -Throttle NOT open (0, if the open column exists)
        -Throttle position is 0 and before it was not zero
        -All gas flows are below the parasitic cutoff
        -Ballast valve is off (0, "ballast" column)
        -Pressure valve capman pressure is below 11mTorr
        -These conditions are met for at least 10 samples (to avoid false starts)
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


def _derive_general_values(process_df, key_values: dict[str, float], logger=None):
    """Derive base pressure, ballast pressure and rate of rise."""

    def _emit_rate_warning(message: str) -> None:
        if logger is not None:
            logger.warning(message)

    base_pressure = None
    base_pressure_ballast = None
    # Not read from diagnostics metadata; compute from logfile signals when possible.
    rate_of_rise = None
    has_vent_column = False
    has_throttle_column = False
    has_ballast_column = False

    # Filter out disregarded samples (1450°C artifacts) for rate-of-rise calculation
    working_df = process_df.copy()
    if 'is_disregarded' in working_df.columns:
        working_df = working_df[~working_df['is_disregarded']].reset_index(drop=True)

    if not working_df.empty and working_df['pressure_raw'].notna().sum() > 0:
        pressure_pa = _to_num(working_df['pressure_raw']).apply(_pressure_to_pa)
        p_arr = pressure_pa.values.astype(float)
        has_ballast_column = 'ballast' in working_df.columns

        if has_ballast_column:
            # Use the Eklipse ballast on/off signal to split pre/post ballast pressure.
            ballast = _to_num(working_df['ballast']).fillna(0).values
            on_positions = np.where(ballast == 1)[0]
            if len(on_positions) > 0:
                first_on = int(on_positions[0])
                pre_valid = p_arr[:first_on][np.isfinite(p_arr[:first_on])]
                if len(pre_valid) > 0:
                    base_pressure = float(np.nanmin(pre_valid))
                else:
                    logger.warning(
                        'No valid pressure data before ballast activation. '
                        'Base pressure remains None.'
                    )

                # Ballast-pressure window: from ballast activation until vent reopens.
                post_start = first_on
                post_end = len(p_arr)
                if 'vent_line' in working_df.columns:
                    vent = (
                        _to_num(working_df['vent_line']).fillna(0).values.astype(float)
                    )
                    vent_positions = np.where(
                        (np.arange(len(vent)) > first_on) & (vent == 1)
                    )[0]
                    if len(vent_positions) > 0:
                        post_end = int(vent_positions[0])

                post_slice = p_arr[post_start:post_end]
                post_valid = post_slice[np.isfinite(post_slice)]
                if len(post_valid) > 0:
                    base_pressure_ballast = float(np.nanmean(post_valid))
                else:
                    logger.warning(
                        'No valid pressure data in ballast window '
                        '(ballast on until vent reopen). '
                        'Ballast base pressure remains None.'
                    )
            else:
                # Ballast column exists but was never turned on.
                # This is normal for runs using only inert gases
                # (Ar, N2) without toxic gases.
                logger.warning(
                    'Ballast valve was never activated. Assuming '
                    'inert-only process (Ar, N2). Base pressure will be '
                    'set; ballast pressure remains None.'
                )
                valid = p_arr[np.isfinite(p_arr)]
                if len(valid) > 0:
                    base_pressure = float(np.nanmin(valid))
                # base_pressure_ballast remains None (no ballast activation)
        else:
            # No ballast signal, so we cannot distinguish pressure with/without ballast.
            # Therefore, neither base pressure can be derived.
            logger.warning(
                'Ballast valve column not found in Eklipse log. '
                'Cannot compute base_pressure and base_pressure_ballast;'
                ' both remain None.'
            )
            base_pressure = None
            base_pressure_ballast = None

        # Derive rate of rise from static-vacuum points where all conditions hold:
        # vent closed, throttle closed, throttle transitioned to 0, all process gas
        # flows below cutoff, ballast off, and pressure below 11 mTorr.
        # Keep only runs that stay valid for at least RATE_OF_RISE_MIN_STATIC_SAMPLES.
        # Throttle valve open=0 is mandatory.
        has_vent_column = 'vent_line' in working_df.columns
        has_throttle_closed = 'throttle_closed' in working_df.columns
        has_throttle_open = 'throttle_open' in working_df.columns
        has_throttle_pos = 'throttle_position' in working_df.columns
        has_gas_flow_columns = all(
            col in working_df.columns
            for col in [
                'ar_flow_m3_s',
                'n2_flow_m3_s',
                'ph3_in_ar_flow_m3_s',
                'h2s_in_ar_flow_m3_s',
            ]
        )
        has_throttle_column = has_throttle_closed
        if (
            'time_s' in working_df.columns
            and has_vent_column
            and has_throttle_column
            and has_throttle_open
            and has_throttle_pos
            and has_ballast_column
            and has_gas_flow_columns
        ):
            time_arr = _to_num(working_df['time_s']).values.astype(float)
            vent = _to_num(working_df['vent_line']).values.astype(float)
            throt_closed = _to_num(working_df['throttle_closed']).values.astype(float)
            throt_open = _to_num(working_df['throttle_open']).values.astype(float)
            throt_pos = _to_num(working_df['throttle_position']).values.astype(float)
            ballast = _to_num(working_df['ballast']).values.astype(float)
            ar_flow = _to_num(working_df['ar_flow_m3_s']).values.astype(float)
            n2_flow = _to_num(working_df['n2_flow_m3_s']).values.astype(float)
            ph3_flow = _to_num(working_df['ph3_in_ar_flow_m3_s']).values.astype(float)
            h2s_flow = _to_num(working_df['h2s_in_ar_flow_m3_s']).values.astype(float)
            gas_static = (
                np.isfinite(ar_flow)
                & np.isfinite(n2_flow)
                & np.isfinite(ph3_flow)
                & np.isfinite(h2s_flow)
                & (np.abs(ar_flow) < MIN_USED_GAS_FLOW_M3_S)
                & (np.abs(n2_flow) < MIN_USED_GAS_FLOW_M3_S)
                & (np.abs(ph3_flow) < MIN_USED_GAS_FLOW_M3_S)
                & (np.abs(h2s_flow) < MIN_USED_GAS_FLOW_M3_S)
            )

            static_vacuum_mask = (
                np.isfinite(time_arr)
                & np.isfinite(p_arr)
                & (vent == 0)
                & (throt_closed == 1)
                & (throt_open == 0)
                & gas_static
                & (ballast == 0)
            )
            throttle_motion_mask = (
                np.isfinite(throt_pos)
                & (throt_pos > 0)
                & (throt_pos < RATE_OF_RISE_MAX_THROTTLE_POSITION)
            )
            throttle_settled_mask = np.isfinite(throt_pos) & (throt_pos == 0)
            pressure_start_mask = p_arr < RATE_OF_RISE_MAX_CAPMAN_PRESSURE_PA

            # Build valid static-vacuum runs first, then prefer one that contains
            # a settled zero-position sample after an in-motion throttle segment.
            start_mask = np.zeros_like(static_vacuum_mask, dtype=bool)
            static_idx = np.where(static_vacuum_mask)[0]
            valid_runs: list[np.ndarray] = []
            if len(static_idx) > 0:
                run_edges = np.where(np.diff(static_idx) > 1)[0]
                run_starts = np.concatenate(([0], run_edges + 1))
                run_ends = np.concatenate((run_edges, [len(static_idx) - 1]))
                for rs, re in zip(run_starts, run_ends):
                    run = static_idx[int(rs) : int(re) + 1]
                    if len(run) >= RATE_OF_RISE_MIN_STATIC_SAMPLES:
                        valid_runs.append(run)

            selected_run: np.ndarray | None = None
            start_point_mask = (
                static_vacuum_mask & throttle_settled_mask & pressure_start_mask
            )
            for run in valid_runs:
                # Prefer a run that contains a zero-position sample below 15 mTorr
                # after the throttle has already been in motion within that run.
                run_motion_positions = np.where(throttle_motion_mask[run])[0]
                if len(run_motion_positions) == 0:
                    continue

                first_motion_idx = int(run[run_motion_positions[0]])
                run_candidates = run[start_point_mask[run]]
                if np.any(run_candidates >= first_motion_idx):
                    selected_run = run
                    break
            if selected_run is None and valid_runs:
                selected_run = valid_runs[0]
                _emit_rate_warning(
                    'Rate-of-rise settled start sample with throttle position 0 and '
                    'pressure below 15 mTorr was not found inside static-vacuum '
                    'window; falling back to first valid static-vacuum run.'
                )

            if selected_run is not None:
                start_candidates = selected_run[start_point_mask[selected_run]]
                if len(start_candidates) > 0:
                    start_point = int(start_candidates[0])
                    run_start_time_s = float(time_arr[int(selected_run[0])])
                    run_end_time_s = float(time_arr[int(selected_run[-1])])
                    start_time_s = float(time_arr[start_point])
                    start_throttle_pos = float(throt_pos[start_point])
                    start_mask[start_point : int(selected_run[-1]) + 1] = True
                    _emit_rate_warning(
                        'Rate-of-rise window selected from '
                        f'{run_start_time_s:.3f} s to {run_end_time_s:.3f} s; '
                        f'start sample at {start_time_s:.3f} s with throttle '
                        f'position {start_throttle_pos:.3f}.'
                    )
                else:
                    _emit_rate_warning(
                        'Rate-of-rise run was found, but no settled static sample '
                        'with throttle position 0 and pressure below 15 mTorr '
                        'was present in that run.'
                    )

            start_idx = np.where(start_mask)[0]
            rate_of_rise = _compute_rate_of_rise(time_arr, p_arr, start_mask)
            if rate_of_rise is not None and len(start_idx) > 0:
                match_time_s = float(time_arr[int(start_idx[0])])
                end_time_s = float(time_arr[int(start_idx[-1])])
                message = (
                    'Rate-of-rise static-vacuum window matched from '
                    f'{match_time_s:.3f} s to {end_time_s:.3f} s.'
                )
                if logger is not None:
                    logger.warning(message)
                else:
                    logger.warning(message)
            else:
                _emit_rate_warning(
                    'Rate of rise could not be computed: '
                    'need at least two valid points from a static-vacuum run of '
                    f'{RATE_OF_RISE_MIN_STATIC_SAMPLES}+ samples '
                    '(vent/throttle static, gas flows below cutoff, ballast off, '
                    'and first sample below 15 mTorr with 0 < throttle position < 100)'
                )
        else:
            missing_requirements: list[str] = []
            if 'time_s' not in process_df.columns:
                missing_requirements.append('time_s')
            if not has_vent_column:
                missing_requirements.append('vent_line')
            if not has_throttle_column:
                missing_requirements.append('throttle_closed')
            if not has_throttle_open:
                missing_requirements.append('throttle_open')
            if not has_throttle_pos:
                missing_requirements.append('throttle_position')
            if not has_ballast_column:
                missing_requirements.append('ballast')
            if not has_gas_flow_columns:
                missing_requirements.extend(
                    [
                        'ar_flow_m3_s',
                        'n2_flow_m3_s',
                        'ph3_in_ar_flow_m3_s',
                        'h2s_in_ar_flow_m3_s',
                    ]
                )

            _emit_rate_warning(
                'Rate of rise could not be computed: missing required column(s): '
                + ', '.join(sorted(set(missing_requirements)))
            )
    else:
        _emit_rate_warning(
            'Rate of rise could not be computed: process data is empty or pressure '
            'samples are missing.'
        )

    return base_pressure, base_pressure_ballast, rate_of_rise


def _detect_used_gases(
    steps: list[ParsedRTPStep], overview: dict[str, float | None]
) -> list[str]:
    """Detect which process gases were really used during the main dwell."""
    # Look for the highest-temperature dwell step (the main anneal).
    dwell_steps = [
        s
        for s in steps
        if re.match(r'^\s*(?:\d+(?:st|nd|rd|th)\s+)?dwell\b', (s.name or '').lower())
    ]
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
            'H2S': main_dwell.h2s_in_ar_flow_m3_s,
        }
    else:
        # Fall back to overview annealing flows if step splitting did not succeed.
        logger.warning(
            'No explicit Dwell step found. Using overview annealing flows '
            'to detect used gases.'
        )
        flow_values = {
            'Ar': overview.get('annealing_ar_flow'),
            'N2': overview.get('annealing_n2_flow'),
            'PH3': overview.get('annealing_ph3_in_ar_flow'),
            'H2S': overview.get('annealing_h2s_in_ar_flow'),
        }

    used_gases = [
        gas
        for gas, flow in flow_values.items()
        if flow is not None and float(flow) > MIN_USED_GAS_FLOW_M3_S
    ]

    if not used_gases:
        logger.warning(
            'No process gases detected as being used during the main dwell. '
            'All gas flows are either None or below the threshold '
            f'({MIN_USED_GAS_FLOW_M3_S} m³/s).'
        )

    return used_gases


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
        eklipse_df = _read_csv_with_fallback(eklipse_csv_path)
        # Collect and deduplicate temperature logfile paths
        diagnostics_paths: list[str] = []
        if cx_thermo_diagnostics_txt_paths:
            diagnostics_paths.extend([p for p in cx_thermo_diagnostics_txt_paths if p])

        deduped_diagnostics_paths: list[str] = []
        for path in diagnostics_paths:
            if path not in deduped_diagnostics_paths:
                deduped_diagnostics_paths.append(path)

        if not deduped_diagnostics_paths:
            raise FileNotFoundError(
                'No temperature diagnostics logfile path was provided.'
            )

        key_values: dict[str, float] = {}
        cx_thermo_tables = []
        for diagnostics_path in deduped_diagnostics_paths:
            with open(diagnostics_path, encoding='utf-8', errors='ignore') as h:
                txt = h.read()
            # Keep the first occurrence of each key from metadata across files.
            for key, value in _extract_key_values(txt).items():
                if key not in key_values:
                    key_values[key] = value
            cx_thermo_tables.append(_parse_cx_thermo_table(txt))

        # If one file, use it directly. If multiple, stack by timestamp.
        if len(cx_thermo_tables) == 1:
            cx_thermo_df = cx_thermo_tables[0]
        else:
            cx_thermo_df = pd.concat(cx_thermo_tables, ignore_index=True, sort=False)
            t_time = _find_col(cx_thermo_df, [r'timestamp', r'^time$'])
            if t_time is not None:
                cx_thermo_df['_parsed_timestamp'] = _to_datetime(cx_thermo_df[t_time])
                cx_thermo_df = (
                    cx_thermo_df.sort_values('_parsed_timestamp')
                    .drop_duplicates(subset=['_parsed_timestamp'], keep='first')
                    .drop(columns=['_parsed_timestamp'])
                    .reset_index(drop=True)
                )
            elif logger is not None:
                logger.warning(
                    'Could not find a timestamp column while stacking multiple '
                    'temperature logfiles; keeping concatenated row order as-is.'
                )

        process_df = _build_process_df(eklipse_df, cx_thermo_df)

        # Pre-identify 1450°C samples and mark them to exclude from step extraction
        if 'is_disregarded' not in process_df.columns:
            process_df['is_disregarded'] = False
        _mark_disregarded_samples(process_df, logger=logger)

        steps = _extract_steps(process_df)

        overview = _derive_overview(steps)
        overview['end_of_process_temperature'] = _derive_end_of_process_temperature(
            process_df, steps
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
        )
    except Exception as e:
        # Never let parser edge cases crash NOMAD normalization.
        if logger is not None:
            logger.warning(
                f'RTP log parsing encountered critical error: {e}. '
                'Returning empty result.'
            )
        return _empty_result()
