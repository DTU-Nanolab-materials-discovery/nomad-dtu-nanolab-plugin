from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from io import StringIO

# Keep heavy dependencies out of import-time to avoid breaking NOMAD startup.
np = None
pd = None

TORR_TO_PA = 133.322368421
MTORR_TO_PA = 0.133322368421
SCCM_TO_M3_S = 1e-6 / 60
LMIN_TO_M3_S = 1e-3 / 60
CELSIUS_TO_KELVIN_OFFSET = 273.15
PRESSURE_TORR_INTERPRETATION_MAX = 2000.0
MIN_USED_GAS_FLOW_SCCM = 1.0
MIN_USED_GAS_FLOW_M3_S = MIN_USED_GAS_FLOW_SCCM * SCCM_TO_M3_S
MIN_POINTS_FOR_STEPS = 3
MAX_PROBE_LINES = 200
TEMPERATURE_CELSIUS_MAX_CUTOFF = 350.0
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
    chiller_flow_m3_s: float | None
    overview: dict[str, float | None]
    steps: list[ParsedRTPStep]
    timeseries: dict[str, list[float]]


def _empty_result() -> ParsedRTPData:
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


def _ncol(line: str, delimiter: str) -> int:
    return len(
        next(
            csv.reader(
                [line], delimiter=delimiter, quotechar='"', skipinitialspace=True
            ),
            [],
        )
    )


def _best_delimiter(line: str) -> str | None:
    best_sep = None
    best_cols = 1
    for sep in [',', ';', '\t']:
        try:
            n = _ncol(line, sep)
        except Exception:
            continue
        if n > best_cols:
            best_cols = n
            best_sep = sep
    return best_sep


def _normalize(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(name).lower())


def _extract_trendlog_column_names(lines: list[str]) -> list[str]:
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


def _find_header_line_index(lines: list[str], delimiter: str) -> int:
    best_idx = 0
    best_cols = 1
    for i, line in enumerate(lines[:50]):
        if not line.strip():
            continue
        try:
            n = _ncol(line, delimiter)
        except Exception:
            continue
        if n > best_cols:
            best_cols = n
            best_idx = i
    return best_idx


def _read_csv_with_fallback(path: str):
    if not _ensure_deps() or pd is None:
        raise RuntimeError('pandas not available')

    with open(path, encoding='utf-8', errors='ignore') as handle:
        probe_lines = [line for line in handle if line.strip()][:MAX_PROBE_LINES]

    if not probe_lines:
        return pd.DataFrame()

    preferred = _best_delimiter(probe_lines[0])
    separators = [',', ';', '\t']
    if preferred in separators:
        separators.remove(preferred)
        separators.insert(0, preferred)

    for sep in separators:
        try:
            header_idx = _find_header_line_index(probe_lines, sep)
            df = pd.read_csv(
                path,
                sep=sep,
                engine='python',
                skipinitialspace=True,
                on_bad_lines='skip',
                quotechar='"',
                skiprows=header_idx,
            )
            if len(df.columns) > 1:
                return df
        except Exception:
            continue

    try:
        return pd.read_csv(path, sep=None, engine='python', on_bad_lines='skip')
    except Exception:
        return pd.DataFrame()


def _to_datetime(series):
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
    if pd is None:
        return series
    return pd.to_numeric(series, errors='coerce')


def _pressure_to_pa(value: float | None) -> float | None:
    if value is None or (np is not None and np.isnan(value)):
        return None
    if value <= 0:
        return value
    if value < PRESSURE_TORR_INTERPRETATION_MAX:
        return value * TORR_TO_PA
    return value


def _apply_parasitic_flow_cutoff(flow_m3_s: float, gas: str) -> float:
    """Zero out sub-threshold parasitic gas flows.

    Any gas-channel flow below 1 sccm is treated as parasitic instrumentation
    background and written back as 0.
    """
    _ = gas  # Keep the signature explicit for readability at call sites.
    if abs(float(flow_m3_s)) < MIN_USED_GAS_FLOW_M3_S:
        return 0.0
    return float(flow_m3_s)


def _temperature_to_kelvin(series):
    values = _to_num(series)
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return values
    median = float(np.nanmedian(finite))
    if median < TEMPERATURE_CELSIUS_MAX_CUTOFF:
        return values + CELSIUS_TO_KELVIN_OFFSET
    return values


def _extract_key_values(txt: str) -> dict[str, float]:
    out: dict[str, float] = {}
    rate_keys = {'rateofrise', 'riserate'}

    def _convert_value(key: str, value: float, unit: str) -> float:
        key_norm = _normalize(key)
        unit_norm = _normalize(unit)

        if 'mtorr' in unit_norm:
            value *= MTORR_TO_PA
        elif 'torr' in unit_norm:
            value *= TORR_TO_PA

        if ('lmin' in unit_norm or 'lminute' in unit_norm) and 'flow' in key_norm:
            value *= LMIN_TO_M3_S
        elif ('sccm' in unit_norm or 'cm3min' in unit_norm) and 'flow' in key_norm:
            value *= SCCM_TO_M3_S

        if (key_norm in rate_keys or ('rate' in key_norm and 'rise' in key_norm)) and (
            'min' in unit_norm or 'minute' in unit_norm
        ):
            value /= 60

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
        unit = _normalize(m.group(3))

        out[key] = _convert_value(key, value, unit)

    return out


def _parse_t2b_table(txt: str):
    if pd is None:
        raise RuntimeError('pandas not loaded')

    lines = [line.rstrip() for line in txt.splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame()

    # Case 1: explicit CSV/TSV table with timestamp + temperature header.
    header_idx = None
    for i, line in enumerate(lines):
        low = line.lower()
        if (
            ('timestamp' in low or re.search(r'\btime\b', low))
            and (
                'temp' in low
                or 'temperature' in low
                or 'process value - ch1' in low
                or 'set point - ch1' in low
                or 'mv monitor' in low
            )
            and re.search(r'[;,\t]', line)
        ):
            header_idx = i
            break

    if header_idx is not None:
        table_lines = [lines[header_idx]]
        sep = _best_delimiter(lines[header_idx]) or ','
        ncols = _ncol(lines[header_idx], sep)
        for line in lines[header_idx + 1 :]:
            if not re.search(r'\d', line):
                break
            cols = next(
                csv.reader(
                    [line],
                    delimiter=sep,
                    quotechar='"',
                    skipinitialspace=True,
                ),
                [],
            )
            if len(cols) < MIN_COLUMNS_FOR_TABLE_ROW:
                break
            if abs(len(cols) - ncols) > 1:
                break
            table_lines.append(line)

        try:
            return pd.read_csv(
                StringIO('\n'.join(table_lines)),
                sep=sep,
                engine='python',
                skipinitialspace=True,
                on_bad_lines='skip',
            )
        except Exception:
            return pd.DataFrame()

    # Case 2: TrendLog-style rows: 2025/11/28_14:12:00 ...
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

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


def _find_col(df, patterns: list[str]) -> str | None:
    norm_map = {_normalize(c): c for c in df.columns}
    for pattern in patterns:
        rx = re.compile(pattern)
        for norm, original in norm_map.items():
            if rx.search(norm):
                return original
    return None


def _build_process_df(eklipse_df, t2b_df):
    if pd is None:
        raise RuntimeError('pandas not loaded')

    e = pd.DataFrame()
    t = pd.DataFrame()

    e_time = _find_col(eklipse_df, [r'timestamp', r'^time$', r'timestamp'])
    if e_time is not None:
        e['timestamp'] = _to_datetime(eklipse_df[e_time])

    p_col = _find_col(
        eklipse_df,
        [r'capmanpressure$', r'chamberpressure', r'processpressure', r'pressure$'],
    )
    if p_col is not None:
        e['pressure_raw'] = _to_num(eklipse_df[p_col])
    else:
        e['pressure_raw'] = np.nan

    flow_map = {
        'ar_flow_m3_s': [r'mfc1flow$', r'\bar\b.*flow', r'argon.*flow'],
        'n2_flow_m3_s': [r'mfc2flow$', r'n2.*flow'],
        'ph3_in_ar_flow_m3_s': [r'mfc4flow$', r'ph3.*flow'],
        'h2s_in_ar_flow_m3_s': [r'mfc6flow$', r'h2s.*flow'],
    }
    for out_col, patterns in flow_map.items():
        c = _find_col(eklipse_df, patterns)
        if c is None:
            e[out_col] = 0.0
        else:
            e[out_col] = _to_num(eklipse_df[c]).fillna(0) * SCCM_TO_M3_S

    # Optional diagnostic columns for base pressure and rate-of-rise derivation.
    ballast_col = _find_col(
        eklipse_df,
        [r'ballast.*valve', r'valve.*ballast', r'pcballast', r'ballast'],
    )
    if ballast_col is not None:
        e['ballast'] = _to_num(eklipse_df[ballast_col]).fillna(0)

    vent_col = _find_col(
        eklipse_df,
        [r'ventline', r'vent.*line', r'pcvent', r'vent'],
    )
    if vent_col is not None:
        e['vent_line'] = _to_num(eklipse_df[vent_col]).fillna(0)

    throttle_closed_col = _find_col(
        eklipse_df,
        [r'throttle.*clos', r'clos.*throttle'],
    )
    throttle_pos_col = _find_col(
        eklipse_df,
        [r'throttle.*pos(?:ition)?', r'rtpthrottle', r'throttlevalve', r'throttle'],
    )
    if throttle_closed_col is not None:
        # Binary column: 1 = throttle valve is closed, 0 = open.
        e['throttle_closed'] = _to_num(eklipse_df[throttle_closed_col]).fillna(0)
    elif throttle_pos_col is not None:
        # Position column: 0 = fully closed.
        e['throttle_position'] = _to_num(eklipse_df[throttle_pos_col]).fillna(-1)

    t_time = _find_col(t2b_df, [r'timestamp', r'^time$'])
    t_temp = _find_col(
        t2b_df,
        [
            r'processvaluech1$',
            r'processvalue.*ch1$',
            r'pyro.*temp',
            r'temperature$',
            r'temp',
        ],
    )
    t_setpoint = _find_col(
        t2b_df,
        [
            r'setpointch1$',
            r'setpoint.*ch1$',
            r'temp.*setpoint',
            r'setpoint.*temp',
            r'target.*temp',
            r'pyro.*sp',
        ],
    )
    t_lamp_power = _find_col(
        t2b_df,
        [
            r'mvmonitorheaingch1$',
            r'mvmonitorheatingch1$',
            r'mvmonitor.*ch1$',
            r'lamp.*power',
            r'power.*lamp',
            r'heater.*power',
            r'power.*percent',
        ],
    )
    if t_time is not None:
        t['timestamp'] = _to_datetime(t2b_df[t_time])
    if t_temp is not None:
        t['temperature_k'] = _temperature_to_kelvin(t2b_df[t_temp])
    if t_setpoint is not None:
        t['temperature_setpoint_k'] = _temperature_to_kelvin(t2b_df[t_setpoint])
    if t_lamp_power is not None:
        t['lamp_power'] = _to_num(t2b_df[t_lamp_power])

    # Optional fallbacks from eklipse logs when present.
    e_setpoint = _find_col(
        eklipse_df,
        [r'temp.*setpoint', r'setpoint.*temp', r'target.*temp', r'pyro.*sp'],
    )
    if e_setpoint is not None and 'temperature_setpoint_k' not in t:
        e_setpoint_series = _temperature_to_kelvin(eklipse_df[e_setpoint])
        if 'timestamp' in e and len(e_setpoint_series) == len(e.index):
            e['temperature_setpoint_k'] = e_setpoint_series

    e_lamp_power = _find_col(
        eklipse_df,
        [r'lamp.*power', r'power.*lamp', r'heater.*power', r'power.*percent'],
    )
    if e_lamp_power is not None and 'lamp_power' not in t:
        e_power_series = _to_num(eklipse_df[e_lamp_power])
        if 'timestamp' in e and len(e_power_series) == len(e.index):
            e['lamp_power'] = e_power_series

    if 'timestamp' in e:
        e = e.dropna(subset=['timestamp']).sort_values('timestamp')
    if 'timestamp' in t:
        t = t.dropna(subset=['timestamp']).sort_values('timestamp')

    if not t.empty and not e.empty:
        # Build a union timeline so downstream plots can span the full time range
        # covered by both log files.
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
        e_temp = _find_col(eklipse_df, [r'temperature$', r'substrate.*temp', r'temp'])
        if e_temp is not None:
            process['temperature_k'] = _temperature_to_kelvin(eklipse_df[e_temp])
        else:
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
    if process_df is None or process_df.empty:
        return {}

    df = process_df.copy()
    out: dict[str, list[float]] = {
        'time_s': [],
        'temperature_c': [],
        'temperature_setpoint_c': [],
        'lamp_power': [],
        'pressure_torr': [],
        'ar_flow_sccm': [],
        'n2_flow_sccm': [],
        'ph3_in_ar_flow_sccm': [],
        'h2s_in_ar_flow_sccm': [],
    }

    if 'time_s' not in df:
        return out

    out['time_s'] = [float(v) for v in _to_num(df['time_s']).fillna(0).to_list()]

    if 'temperature_k' in df:
        out['temperature_c'] = [
            float(v)
            for v in (_to_num(df['temperature_k']) - CELSIUS_TO_KELVIN_OFFSET)
            .fillna(np.nan)
            .to_list()
        ]

    if 'temperature_setpoint_k' in df:
        out['temperature_setpoint_c'] = [
            float(v)
            for v in (_to_num(df['temperature_setpoint_k']) - CELSIUS_TO_KELVIN_OFFSET)
            .fillna(np.nan)
            .to_list()
        ]

    if 'lamp_power' in df:
        out['lamp_power'] = [float(v) for v in _to_num(df['lamp_power']).to_list()]

    if 'pressure_raw' in df:
        pa_series = _to_num(df['pressure_raw']).apply(_pressure_to_pa)
        pressure_torr = [
            (float(v) / TORR_TO_PA)
            if v is not None and np.isfinite(v)
            else float('nan')
            for v in pa_series.to_list()
        ]
        # Keep pressure series empty when no finite pressure samples exist.
        if any(np.isfinite(v) for v in pressure_torr):
            out['pressure_torr'] = pressure_torr

    flow_cols = {
        'ar_flow_sccm': 'ar_flow_m3_s',
        'n2_flow_sccm': 'n2_flow_m3_s',
        'ph3_in_ar_flow_sccm': 'ph3_in_ar_flow_m3_s',
        'h2s_in_ar_flow_sccm': 'h2s_in_ar_flow_m3_s',
    }
    for out_col, src_col in flow_cols.items():
        if src_col in df:
            out[out_col] = [
                float(v) / SCCM_TO_M3_S if np.isfinite(v) else float('nan')
                for v in _to_num(df[src_col]).to_list()
            ]

    return out


def _extract_steps(process_df) -> list[ParsedRTPStep]:
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

    # In the standard 3-segment split the annealing plateau is segment index 1.
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

    # Second pass: add ordinal suffix only when a base name appears more than once.
    # The first occurrence keeps the plain name; later ones get "2nd", "3rd", etc.
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
        ar_flow = _apply_parasitic_flow_cutoff(
            float(np.nanmedian(sl['ar_flow_m3_s'])),
            'Ar',
        )
        n2_flow = _apply_parasitic_flow_cutoff(
            float(np.nanmedian(sl['n2_flow_m3_s'])),
            'N2',
        )
        step = ParsedRTPStep(
            name=name,
            duration_s=duration,
            start_time_s=float(sl['time_s'].iloc[0]),
            end_time_s=float(sl['time_s'].iloc[-1]),
            initial_temperature_k=float(sl['temperature_k'].iloc[0]),
            final_temperature_k=float(sl['temperature_k'].iloc[-1]),
            pressure_pa=pressure_pa,
            ar_flow_m3_s=ar_flow,
            n2_flow_m3_s=n2_flow,
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
        # Fallback when no explicit annealing label exists.
        score = [
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
    """Derive end-of-process temperature from cooling gas shutoff moment.

    End-of-process is defined as the first point during the cooling step where all
    process gases are off (below parasitic-flow threshold), after they were on.
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
                    # Cooling started with gases already off.
                    shutoff_rel_idx = 0

                if shutoff_rel_idx is not None:
                    temp_k = temp_arr[idx[shutoff_rel_idx]]
                    if np.isfinite(temp_k):
                        end_temp_k = float(temp_k)

    return end_temp_k


def _compute_rate_of_rise(
    time_s_arr, pressure_pa_arr, static_mask, window_s=RATE_OF_RISE_WINDOW_S
):
    """Return rate of rise (Pa/s) from the first qualifying static-vacuum window.

    Scans *time_s_arr* for the first contiguous run where *static_mask* is True
    for at least *window_s* seconds.  Within that run the algorithm:

    1. Finds the minimum-pressure index – the chamber base pressure P_min.
    2. Finds the pressure *window_s* seconds later, P_end.
    3. Returns ``(P_end - P_min) / window_s``.
    """
    n = len(time_s_arr)
    i = 0
    while i < n:
        if not static_mask[i]:
            i += 1
            continue
        run_start = i
        j = i + 1
        while j < n and static_mask[j]:
            j += 1
        run_end = j - 1
        t_run_start = time_s_arr[run_start]
        t_run_end = time_s_arr[run_end]
        if (t_run_end - t_run_start) >= window_s:
            run_pressures = pressure_pa_arr[run_start : run_end + 1]
            run_times = time_s_arr[run_start : run_end + 1]
            if not np.any(np.isfinite(run_pressures)):
                i = j
                continue
            min_rel = int(np.nanargmin(run_pressures))
            p_min = float(run_pressures[min_rel])
            t_min = float(run_times[min_rel])
            future = run_times >= t_min + window_s
            if not np.any(future):
                i = j
                continue
            p_end = float(run_pressures[int(np.argmax(future))])
            if np.isfinite(p_min) and np.isfinite(p_end):
                return (p_end - p_min) / window_s
        i = j
    return None


def _derive_general_values(process_df, key_values: dict[str, float]):
    base_pressure = None
    base_pressure_ballast = None
    rate_of_rise = None
    chiller_flow = None
    has_ballast_column = False
    has_vent_column = False
    has_throttle_column = False

    if not process_df.empty and process_df['pressure_raw'].notna().sum() > 0:
        pressure_pa = _to_num(process_df['pressure_raw']).apply(_pressure_to_pa)
        p_arr = pressure_pa.values.astype(float)
        has_ballast_column = 'ballast' in process_df.columns

        if has_ballast_column:
            # Use Eklipse ballast on/off column to split pre- and post-ballast
            # pressure series.
            ballast = _to_num(process_df['ballast']).fillna(0).values
            on_positions = np.where(ballast == 1)[0]
            if len(on_positions) > 0:
                first_on = int(on_positions[0])
                pre_valid = p_arr[:first_on][np.isfinite(p_arr[:first_on])]
                if len(pre_valid) > 0:
                    base_pressure = float(np.nanmin(pre_valid))
                post_valid = p_arr[on_positions][np.isfinite(p_arr[on_positions])]
                if len(post_valid) > 0:
                    base_pressure_ballast = float(np.nanmin(post_valid))
            else:
                # Ballast column present but never turned on.
                valid = p_arr[np.isfinite(p_arr)]
                if len(valid) > 0:
                    base_pressure = float(np.nanmin(valid))
        else:
            # Without ballast signal, do not derive base pressures.
            base_pressure = None

        # Rate of rise from a static-vacuum period (vent line off + throttle closed).
        has_vent_column = 'vent_line' in process_df.columns
        has_throttle_closed = 'throttle_closed' in process_df.columns
        has_throttle_pos = 'throttle_position' in process_df.columns
        has_throttle_column = has_throttle_closed or has_throttle_pos
        if 'time_s' in process_df.columns and has_vent_column and has_throttle_column:
            time_arr = _to_num(process_df['time_s']).values.astype(float)
            static_mask = np.ones(len(process_df), dtype=bool)
            vent = _to_num(process_df['vent_line']).fillna(1).values
            static_mask &= vent == 0
            if has_throttle_closed:
                throt = _to_num(process_df['throttle_closed']).fillna(0).values
                static_mask &= throt == 1  # 1 = throttle valve closed
            elif has_throttle_pos:
                throt = _to_num(process_df['throttle_position']).fillna(1).values
                static_mask &= throt == 0  # 0 = fully closed position
            rate_of_rise = _compute_rate_of_rise(time_arr, p_arr, static_mask)
        else:
            # Columns needed to identify a static-vacuum window are absent;
            # keep empty so the user can decide whether to fill it manually.
            rate_of_rise = None

        if not has_ballast_column and base_pressure_ballast is None:
            # No ballast column available; keep empty for manual entry.
            base_pressure_ballast = None

    # Override with values parsed from the diagnostics text-file when present.
    for k, v in key_values.items():
        if (
            'basepressure' in k
            and 'without' in k
            and 'ballast' in k
            and has_ballast_column
        ):
            base_pressure = v
        elif (
            'basepressure' in k
            and 'with' in k
            and 'ballast' in k
            and has_ballast_column
        ):
            base_pressure_ballast = v
        elif (
            ('rateofrise' in k or 'riserate' in k or ('rate' in k and 'rise' in k))
            and has_vent_column
            and has_throttle_column
        ):
            rate_of_rise = v
        elif 'chiller' in k and 'flow' in k:
            chiller_flow = v

    if not has_ballast_column and base_pressure_ballast is None:
        base_pressure_ballast = None
    if (not has_vent_column or not has_throttle_column) and rate_of_rise is None:
        rate_of_rise = None

    return base_pressure, base_pressure_ballast, rate_of_rise, chiller_flow


def _detect_used_gases(
    steps: list[ParsedRTPStep], overview: dict[str, float | None]
) -> list[str]:
    annealing_step = next((s for s in steps if s.name == 'Annealing'), None)
    if annealing_step is not None:
        flow_values = {
            'Ar': annealing_step.ar_flow_m3_s,
            'N2': annealing_step.n2_flow_m3_s,
            'PH3': annealing_step.ph3_in_ar_flow_m3_s,
            'H2S': annealing_step.h2s_in_ar_flow_m3_s,
        }
    else:
        # Fallback to overview-derived annealing values when the split failed.
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
    """Parse RTP eklipse CSV + diagnostics TXT and return rtp.py-compatible data."""
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
        base_pressure, base_pressure_ballast, rate_of_rise, chiller_flow = (
            _derive_general_values(process_df, key_values)
        )
        used_gases = _detect_used_gases(steps, overview)
        timeseries = _extract_timeseries(process_df)

        return ParsedRTPData(
            used_gases=used_gases,
            base_pressure_pa=base_pressure,
            base_pressure_ballast_pa=base_pressure_ballast,
            rate_of_rise_pa_s=rate_of_rise,
            chiller_flow_m3_s=chiller_flow,
            overview=overview,
            steps=steps,
            timeseries=timeseries,
        )
    except Exception:
        # Never crash NOMAD normalization because of parser edge cases.
        return _empty_result()
