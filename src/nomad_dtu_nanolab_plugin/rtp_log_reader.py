from __future__ import annotations

import csv
import io
import re
import warnings
from dataclasses import dataclass

"""RTP log parsing helpers used during NOMAD normalization.

This parser lines up two logs by timestamp:
- Eklipse CSV process log (pressure, flows, valves)
- T2B diagnostics log (temperature, lamp power)

The output is shaped for the RTP schema and includes both summary values
and time-series channels.
"""

# Keep heavy imports out of module load so NOMAD startup stays stable.
np = None
pd = None

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
RATE_OF_RISE_WINDOW_S = 60.0
ANNEAL_SEGMENT_INDEX = 1
STANDARD_SEGMENT_BOUND_COUNT = 4
FLAT_SEGMENT_DELTA_TEMPERATURE_K = 5.0
ORDINAL_SECOND = 2
ORDINAL_THIRD = 3


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
    """Zero out tiny gas flows we treat as instrumentation background.

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


def _parse_t2b_table(txt: str):
    """Parse T2B diagnostics table with metadata+CSV structure.

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
    In case we use this parser for other dataframes types (lab equipment changeso
    or different lab)."""
    norm_map = {_normalize(c): c for c in df.columns}
    for pattern in patterns:
        rx = re.compile(pattern)
        for norm, original in norm_map.items():
            if rx.search(norm):
                return original
    return None


def _build_process_df(eklipse_df, t2b_df):
    """Merge Eklipse and T2B streams onto one shared process timeline."""
    if pd is None:
        raise RuntimeError('pandas not loaded')

    e = pd.DataFrame()
    t = pd.DataFrame()

    e_time = _find_col(eklipse_df, [r'timestamp', r'^time$', r'timestamp'])
    if e_time is not None:
        e['timestamp'] = _to_datetime(eklipse_df[e_time])
    else:
        warnings.warn(
            'Eklipse timestamp column not found; Eklipse data cannot be time-aligned.',
            RuntimeWarning,
            stacklevel=2,
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
    t_time = _find_col(t2b_df, [r'timestamp'])
    t_temp = _find_col(
        t2b_df,
        [  # add more options if different logfiles in the future
            r'processvalue.*ch1$',
            r'^temperature(c)?$',
        ],
    )
    t_setpoint = _find_col(
        t2b_df,
        [  # add more options if different logfiles in the future
            r'setpointch1$',
            r'setpoint.*ch1$',
        ],
    )
    t_lamp_power = _find_col(
        t2b_df,
        [  # add more options if different logfiles in the future
            r'mvmonitorheatingch1$',
        ],
    )
    if t_time is not None:
        t['timestamp'] = _to_datetime(t2b_df[t_time])
    else:
        warnings.warn(
            'T2B timestamp column not found; T2B data cannot be time-aligned.',
            RuntimeWarning,
            stacklevel=2,
        )
    if t_temp is not None:
        t['temperature_k'] = _temperature_to_kelvin(t2b_df[t_temp])
    if t_setpoint is not None:
        t['temperature_setpoint_k'] = _temperature_to_kelvin(t2b_df[t_setpoint])
    if t_lamp_power is not None:
        t['lamp_power'] = _to_num(t2b_df[t_lamp_power])

    # Removing missing values from each dataframe before merging
    if 'timestamp' in e:
        e = e.dropna(subset=['timestamp']).sort_values('timestamp')
        if e.empty:
            warnings.warn(
                'Eklipse timestamps could not be parsed; Eklipse dataframe'
                ' is empty after filtering.',
                RuntimeWarning,
                stacklevel=2,
            )
    if 'timestamp' in t:
        t = t.dropna(subset=['timestamp']).sort_values('timestamp')
        if t.empty:
            warnings.warn(
                'T2B timestamps could not be parsed; T2B dataframe'
                ' is empty after filtering.',
                RuntimeWarning,
                stacklevel=2,
            )

    # Build a union timeline so plots can cover the full range of both logs.
    if not t.empty and not e.empty:
        # Step 1: stacking all timestamps from T2B and Eklipse into one series
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
        # Step 2: For each timestamp in timeline, pandas picks the closest T2B row
        # (before or after) within 8 seconds and copies T2B columns into process.
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
        return out

    out['time_s'] = [float(v) for v in _to_num(df['time_s']).fillna(0).to_list()]

    if 'temperature_k' in df:
        out['temperature_k'] = [
            float(v) for v in _to_num(df['temperature_k']).to_list()
        ]

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


def _extract_steps(process_df) -> list[ParsedRTPStep]:
    """Split the run into RTP-style heating, annealing, and cooling steps."""
    if (
        process_df.empty
        or process_df['temperature_k'].notna().sum() < MIN_POINTS_FOR_STEPS
    ):
        return []

    df = process_df.dropna(subset=['temperature_k', 'time_s']).copy()
    if len(df) < MIN_POINTS_FOR_STEPS:
        return []

    temp = df['temperature_k'].to_numpy()
    time_s = df['time_s'].to_numpy()

    max_temp = float(np.nanmax(temp))
    min_temp = float(np.nanmin(temp))
    band = max(5.0, 0.03 * (max_temp - min_temp))
    plateau_mask = temp >= (max_temp - band)

    if np.any(plateau_mask):
        true_idx = np.where(plateau_mask)[0]
        split_idx = np.where(np.diff(true_idx) > 1)[0]
        runs: list[tuple[int, int]] = []

        start = int(true_idx[0])
        for split_pos in split_idx:
            end = int(true_idx[split_pos])
            runs.append((start, end))
            start = int(true_idx[split_pos + 1])
        runs.append((start, int(true_idx[-1])))

        valid_runs = [
            (s, e)
            for s, e in runs
            if (e - s + 1) >= MIN_PLATEAU_POINTS
            and float(time_s[e] - time_s[s])
            >= (MIN_ANNEALING_PLATEAU_DURATION_S - ANNEALING_DURATION_TOLERANCE_S)
        ]
        candidate_runs = valid_runs if valid_runs else runs

        def _anneal_run_key(se: tuple[int, int]) -> tuple[float, float]:
            s, e = se
            run_max_temp = float(np.nanmax(temp[s : e + 1]))
            run_duration = float(time_s[e] - time_s[s])
            return (run_max_temp, run_duration)

        i_start, i_end = max(
            candidate_runs,
            key=_anneal_run_key,
        )
        bounds = [0, i_start, i_end, len(df) - 1]
    else:
        i_peak = int(np.nanargmax(temp))
        bounds = [0, i_peak, len(df) - 1]

    uniq: list[int] = []
    for b in bounds:
        if not uniq or b > uniq[-1]:
            uniq.append(b)

    # In a standard 3-segment split, annealing is the middle segment.
    anneal_segment_idx = (
        ANNEAL_SEGMENT_INDEX if len(uniq) == STANDARD_SEGMENT_BOUND_COUNT else None
    )

    def _segment_base_name(seg_df, is_anneal: bool) -> str:
        if is_anneal:
            return 'Annealing'
        delta_t = float(seg_df['temperature_k'].iloc[-1]) - float(
            seg_df['temperature_k'].iloc[0]
        )
        if abs(delta_t) < FLAT_SEGMENT_DELTA_TEMPERATURE_K:
            return 'Plateau'
        return 'Heating' if delta_t > 0 else 'Cooling'

    def _ordinal_prefix(n: int) -> str:
        if n == ORDINAL_SECOND:
            return '2nd'
        if n == ORDINAL_THIRD:
            return '3rd'
        return f'{n}th'

    # First pass: collect valid segments and their base names.
    seg_slices: list[tuple[int, int]] = []
    base_names: list[str] = []
    for i in range(len(uniq) - 1):
        s = uniq[i]
        e = uniq[i + 1]
        if e <= s:
            continue
        sl = df.iloc[s : e + 1]
        duration = float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0])
        if duration <= 0:
            continue
        seg_slices.append((s, e))
        base_names.append(
            _segment_base_name(
                sl, anneal_segment_idx is not None and i == anneal_segment_idx
            )
        )

    # Second pass: add ordinals only when the same base name repeats.
    # First one keeps the plain name; later ones become "2nd", "3rd", etc.
    name_count: dict[str, int] = {}
    for bn in base_names:
        name_count[bn] = name_count.get(bn, 0) + 1
    name_seen: dict[str, int] = {}
    final_names: list[str] = []
    for bn in base_names:
        if name_count[bn] == 1:
            final_names.append(bn)
        else:
            name_seen[bn] = name_seen.get(bn, 0) + 1
            n = name_seen[bn]
            final_names.append(f'{_ordinal_prefix(n)} {bn}' if n > 1 else bn)

    steps: list[ParsedRTPStep] = []
    for (s, e), name in zip(seg_slices, final_names):
        sl = df.iloc[s : e + 1]
        duration = float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0])
        pressure_pa = _pressure_to_pa(float(np.nanmedian(sl['pressure_raw'])))
        step = ParsedRTPStep(
            name=name,
            duration_s=duration,
            start_time_s=float(sl['time_s'].iloc[0]),
            end_time_s=float(sl['time_s'].iloc[-1]),
            initial_temperature_k=float(sl['temperature_k'].iloc[0]),
            final_temperature_k=float(sl['temperature_k'].iloc[-1]),
            pressure_pa=pressure_pa,
            ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(sl['ar_flow_m3_s'])),
                'Ar',
            ),
            n2_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(sl['n2_flow_m3_s'])),
                'N2',
            ),
            ph3_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(sl['ph3_in_ar_flow_m3_s'])),
                'PH3',
            ),
            h2s_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(sl['h2s_in_ar_flow_m3_s'])),
                'H2S',
            ),
            mean_temperature_k=float(np.nanmean(sl['temperature_k'])),
        )
        steps.append(step)

    if steps:
        return steps

    sl = df.iloc[[0, -1]]
    pressure_pa = _pressure_to_pa(float(np.nanmedian(df['pressure_raw'])))
    return [
        ParsedRTPStep(
            name='Annealing',
            duration_s=float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0]),
            start_time_s=float(sl['time_s'].iloc[0]),
            end_time_s=float(sl['time_s'].iloc[-1]),
            initial_temperature_k=float(sl['temperature_k'].iloc[0]),
            final_temperature_k=float(sl['temperature_k'].iloc[-1]),
            pressure_pa=pressure_pa,
            ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(df['ar_flow_m3_s'])),
                'Ar',
            ),
            n2_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(df['n2_flow_m3_s'])),
                'N2',
            ),
            ph3_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(df['ph3_in_ar_flow_m3_s'])),
                'PH3',
            ),
            h2s_in_ar_flow_m3_s=_apply_parasitic_flow_cutoff(
                float(np.nanmedian(df['h2s_in_ar_flow_m3_s'])),
                'H2S',
            ),
            mean_temperature_k=float(np.nanmean(df['temperature_k'])),
        )
    ]


def _derive_overview(steps: list[ParsedRTPStep]) -> dict[str, float | None]:
    """Compute high-level overview values from the extracted steps."""
    if not steps:
        return _empty_result().overview

    def _is_annealing_name(name: str) -> bool:
        return bool(re.match(r'^\s*anneal(?:ing)?\b', name.lower()))

    def _step_role(step: ParsedRTPStep) -> str:
        name = (step.name or '').lower()
        if _is_annealing_name(name):
            return 'annealing'
        if 'heat' in name:
            return 'heating'
        if 'cool' in name:
            return 'cooling'

        delta_t = step.final_temperature_k - step.initial_temperature_k
        if abs(delta_t) <= PLATEAU_TEMPERATURE_DELTA_TOLERANCE_K:
            return 'plateau'
        return 'heating' if delta_t > 0 else 'cooling'

    anneal_idx = next(
        (i for i, step in enumerate(steps) if _is_annealing_name(step.name or '')),
        None,
    )
    if anneal_idx is None:
        # Fallback if no step is explicitly labeled as annealing.
        score = [  # Annealing is usually the warmest step and somewhat long.
            0.7 * ((s.initial_temperature_k + s.final_temperature_k) / 2)
            + 0.3 * s.duration_s
            for s in steps
        ]
        anneal_idx = int(np.argmax(score))

    anneal = steps[anneal_idx]

    total_heating = 0.0
    total_cooling = 0.0
    for i, step in enumerate(steps):
        if i == anneal_idx:
            continue
        role = _step_role(step)
        if i < anneal_idx and role in {'heating', 'plateau'}:
            total_heating += step.duration_s
        if i > anneal_idx and role in {'cooling', 'plateau'}:
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

    if (
        process_df is not None
        and not process_df.empty
        and 'time_s' in process_df
        and 'temperature_k' in process_df
    ):
        cooling_step = next(
            (step for step in steps if 'cool' in (step.name or '').lower()), None
        )
        if cooling_step is None:
            cooling_step = next(
                (step for step in steps if _is_cooling_step(step)),
                None,
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

    return end_temp_k


def _compute_rate_of_rise(
    time_s_arr, pressure_pa_arr, start_mask, window_s=RATE_OF_RISE_WINDOW_S
):
    """Compute rate of rise (Pa/s) from the first valid static vacuum start point.

    start_mask marks rows where static conditions are satisfied:
        -Throttle valve is closed (1, "closed" column)
        -Vent valve is closed (0, "vent_line" column)
        -Throttle NOT open (0, if the open column exists)
        -Throttle position at 0 (fully closed, if that column exists)
    We take the first such row i0 and return:
    (P(t0+window_s) - P(i0)) / window_s.
    """
    start_idx = np.where(start_mask)[0]
    if len(start_idx) == 0:
        return None

    i0 = int(start_idx[0])
    p0 = float(pressure_pa_arr[i0])
    t0 = float(time_s_arr[i0])
    if not np.isfinite(p0) or not np.isfinite(t0):
        return None

    target_time = t0 + float(window_s)
    future_idx = np.where(
        np.isfinite(time_s_arr)
        & np.isfinite(pressure_pa_arr)
        & (time_s_arr >= target_time)
    )[0]
    if len(future_idx) == 0:
        return None

    p1 = float(pressure_pa_arr[int(future_idx[0])])
    if not np.isfinite(p1):
        return None

    return (p1 - p0) / float(window_s)


def _derive_general_values(process_df, key_values: dict[str, float]):
    """Derive base pressure, ballast pressure and rate of rise."""
    base_pressure = None
    base_pressure_ballast = None
    # Not read from diagnostics metadata; compute from logfile signals when possible.
    rate_of_rise = None
    has_vent_column = False
    has_throttle_column = False
    has_ballast_column = False

    if not process_df.empty and process_df['pressure_raw'].notna().sum() > 0:
        pressure_pa = _to_num(process_df['pressure_raw']).apply(_pressure_to_pa)
        p_arr = pressure_pa.values.astype(float)
        has_ballast_column = 'ballast' in process_df.columns

        if has_ballast_column:
            # Use the Eklipse ballast on/off signal to split pre/post ballast pressure.
            ballast = _to_num(process_df['ballast']).fillna(0).values
            on_positions = np.where(ballast == 1)[0]
            if len(on_positions) > 0:
                first_on = int(on_positions[0])
                pre_valid = p_arr[:first_on][np.isfinite(p_arr[:first_on])]
                if len(pre_valid) > 0:
                    base_pressure = float(np.nanmin(pre_valid))
                post_valid = p_arr[on_positions][np.isfinite(p_arr[on_positions])]
                if len(post_valid) > 0:
                    base_pressure_ballast = float(np.nanmax(post_valid))
            else:
                # Ballast column exists but was never turned on.
                # This is normal for runs using only inert gases
                # (Ar, N2) without toxic gases.
                valid = p_arr[np.isfinite(p_arr)]
                if len(valid) > 0:
                    base_pressure = float(np.nanmin(valid))
                # base_pressure_ballast remains None (no ballast activation)
        else:
            # No ballast signal, so we cannot distinguish pressure with/without ballast.
            # Therefore, neither base pressure can be derived.
            warnings.warn(
                'Ballast valve column not found in Eklipse log.',
                RuntimeWarning,
                stacklevel=2,
            )
            warnings.warn(
                'Base pressure values cannot be derived; set to None.',
                RuntimeWarning,
                stacklevel=2,
            )
            base_pressure = None
            base_pressure_ballast = None

        # Derive rate of rise from the first moment where throttle is closed
        # and vent is closed. Optionally require open=0 and position=0 when present.
        has_vent_column = 'vent_line' in process_df.columns
        has_throttle_closed = 'throttle_closed' in process_df.columns
        has_throttle_open = 'throttle_open' in process_df.columns
        has_throttle_pos = 'throttle_position' in process_df.columns
        has_throttle_column = has_throttle_closed
        if 'time_s' in process_df.columns and has_vent_column and has_throttle_column:
            time_arr = _to_num(process_df['time_s']).values.astype(float)
            vent = _to_num(process_df['vent_line']).values.astype(float)
            throt_closed = _to_num(process_df['throttle_closed']).values.astype(float)

            start_mask = (
                np.isfinite(time_arr)
                & np.isfinite(p_arr)
                & (vent == 0)
                & (throt_closed == 1)
            )
            if has_throttle_open:
                throt_open = _to_num(process_df['throttle_open']).values.astype(float)
                start_mask &= throt_open == 0
            if has_throttle_pos:
                throt_pos = _to_num(process_df['throttle_position']).values.astype(
                    float
                )
                start_mask &= throt_pos == 0
            rate_of_rise = _compute_rate_of_rise(time_arr, p_arr, start_mask)

    return base_pressure, base_pressure_ballast, rate_of_rise


def _detect_used_gases(
    steps: list[ParsedRTPStep], overview: dict[str, float | None]
) -> list[str]:
    """Detect which process gases were really used during annealing."""
    annealing_step = next((s for s in steps if s.name == 'Annealing'), None)
    if annealing_step is not None:
        flow_values = {
            'Ar': annealing_step.ar_flow_m3_s,
            'N2': annealing_step.n2_flow_m3_s,
            'PH3': annealing_step.ph3_in_ar_flow_m3_s,
            'H2S': annealing_step.h2s_in_ar_flow_m3_s,
        }
    else:
        # Fall back to overview annealing flows if step splitting did not succeed.
        flow_values = {
            'Ar': overview.get('annealing_ar_flow'),
            'N2': overview.get('annealing_n2_flow'),
            'PH3': overview.get('annealing_ph3_in_ar_flow'),
            'H2S': overview.get('annealing_h2s_in_ar_flow'),
        }

    return [
        gas
        for gas, flow in flow_values.items()
        if flow is not None and float(flow) > MIN_USED_GAS_FLOW_M3_S
    ]


def parse_rtp_logfiles(
    eklipse_csv_path: str,
    t2b_diagnostics_txt_path: str,
) -> ParsedRTPData:
    """Parse RTP log files and return schema-ready process, step, and overview data."""
    if not _ensure_deps():
        return _empty_result()

    try:
        eklipse_df = _read_csv_with_fallback(eklipse_csv_path)
        with open(t2b_diagnostics_txt_path, encoding='utf-8', errors='ignore') as h:
            txt = h.read()
        key_values = _extract_key_values(txt)
        t2b_df = _parse_t2b_table(txt)

        process_df = _build_process_df(eklipse_df, t2b_df)
        steps = _extract_steps(process_df)
        overview = _derive_overview(steps)
        overview['end_of_process_temperature'] = _derive_end_of_process_temperature(
            process_df, steps
        )
        base_pressure, base_pressure_ballast, rate_of_rise = _derive_general_values(
            process_df, key_values
        )
        used_gases = _detect_used_gases(steps, overview)
        timeseries = _extract_timeseries(process_df)

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
    except Exception:
        # Never let parser edge cases crash NOMAD normalization.
        return _empty_result()
