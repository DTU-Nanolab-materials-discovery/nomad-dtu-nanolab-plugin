import csv
import re
from dataclasses import dataclass
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd

# Parsing and unit-conversion thresholds used by the RTP log reader.
MIN_TABLE_DATA_COLUMNS = 2
MIN_TABLE_ROWS = 2
TORR_TO_PA = 133.322368421
MTORR_TO_PA = 0.133322368421
SCCM_TO_M3_S = 1e-6 / 60
LMIN_TO_M3_S = 1e-3 / 60
PRESSURE_TORR_INTERPRETATION_MAX = 2000.0
CELSIUS_TO_KELVIN_OFFSET = 273.15
CELSIUS_MEDIAN_THRESHOLD = 350.0
MIN_POINTS_FOR_STEP_EXTRACTION = 2
MIN_PROCESS_ROWS_FOR_RATE_OF_RISE = 4
MIN_LINEAR_FIT_POINTS = 3
STATIC_FLOW_THRESHOLD_M3_S = 1e-9
MIN_USED_GAS_FLOW_M3_S = 1e-12


@dataclass
class ParsedRTPStep:
    name: str
    duration_s: float
    initial_temperature_k: float
    final_temperature_k: float
    pressure_pa: float
    ar_flow_m3_s: float
    n2_flow_m3_s: float
    ph3_in_ar_flow_m3_s: float
    h2s_in_ar_flow_m3_s: float


@dataclass
class ParsedRTPData:
    used_gases: list[str]
    base_pressure_pa: float | None
    base_pressure_ballast_pa: float | None
    rate_of_rise_pa_s: float | None
    chiller_flow_m3_s: float | None
    overview: dict[str, float | None]
    steps: list[ParsedRTPStep]


def _normalize_column_name(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', str(name).lower())


def _count_columns_for_delimiter(line: str, delimiter: str) -> int:
    row = next(
        csv.reader(
            [line],
            delimiter=delimiter,
            quotechar='"',
            skipinitialspace=True,
        )
    )
    return len(row)


def _detect_delimiter_from_line(line: str) -> str | None:
    best_delimiter = None
    best_columns = 1
    for delimiter in [',', ';', '\t']:
        try:
            n_columns = _count_columns_for_delimiter(line, delimiter)
        except Exception:
            continue
        if n_columns > best_columns:
            best_columns = n_columns
            best_delimiter = delimiter

    if best_columns <= 1:
        return None
    return best_delimiter


def _read_csv_with_fallback(path: str) -> pd.DataFrame:
    # The exported RTP CSV can use different delimiters depending on locale.
    with open(path, encoding='utf-8', errors='ignore') as handle:
        non_empty_lines = [line for line in handle if line.strip()]

    preferred_sep = None
    if non_empty_lines:
        preferred_sep = _detect_delimiter_from_line(non_empty_lines[0])

    separators = [',', ';', '\t']
    if preferred_sep in separators:
        separators.remove(preferred_sep)
        separators.insert(0, preferred_sep)

    for sep in separators:
        try:
            df = pd.read_csv(path, sep=sep, engine='python', skipinitialspace=True)
            if len(df.columns) > 1:
                return df
        except Exception:
            continue

    # Fall back to the preferred separator if all attempts failed.
    fallback_sep = preferred_sep or ','
    return pd.read_csv(
        path,
        sep=fallback_sep,
        engine='python',
        skipinitialspace=True,
    )


def _extract_key_values_from_text(content: str) -> dict[str, float]:
    key_values: dict[str, float] = {}
    pattern = re.compile(
        r'^\s*([^:=\n]+?)\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*([^\n]*)$'
    )
    for line in content.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        key = _normalize_column_name(match.group(1))
        value = float(match.group(2))
        unit = _normalize_column_name(match.group(3))

        # Normalize a few known engineering units directly when parsing keys.
        if 'torr' in unit:
            value = value * TORR_TO_PA
        elif 'mtorr' in unit:
            value = value * MTORR_TO_PA
        elif ('lmin' in unit or 'lminute' in unit) and 'flow' in key:
            value = value * LMIN_TO_M3_S
        elif ('sccm' in unit or 'cm3min' in unit) and 'flow' in key:
            value = value * SCCM_TO_M3_S

        key_values[key] = value
    return key_values


def _parse_table_from_text(content: str) -> pd.DataFrame:
    lines = [line.rstrip() for line in content.splitlines() if line.strip()]
    if not lines:
        return pd.DataFrame()

    # Find the first likely temperature table header in the diagnostics text.
    header_idx = None
    for i, line in enumerate(lines):
        if not re.search(r'[;,\t]', line):
            continue
        lower = line.lower()
        if ('time' in lower or 'timestamp' in lower) and (
            'temp' in lower or 'temperature' in lower
        ):
            header_idx = i
            break

    if header_idx is None:
        return pd.DataFrame()

    header_delimiter = _detect_delimiter_from_line(lines[header_idx])
    if header_delimiter is None:
        return pd.DataFrame()

    # Collect only contiguous tabular rows after the header.
    table_lines = [lines[header_idx]]
    n_cols = _count_columns_for_delimiter(lines[header_idx], header_delimiter)
    for line in lines[header_idx + 1 :]:
        if not re.search(r'\d', line):
            break
        cols = next(
            csv.reader(
                [line],
                delimiter=header_delimiter,
                quotechar='"',
                skipinitialspace=True,
            )
        )
        if len(cols) < MIN_TABLE_DATA_COLUMNS:
            break
        if len(cols) != n_cols:
            # Keep rows that still resemble the table.
            if abs(len(cols) - n_cols) > 1:
                break
        table_lines.append(line)

    if len(table_lines) < MIN_TABLE_ROWS:
        return pd.DataFrame()

    return pd.read_csv(
        StringIO('\n'.join(table_lines)),
        sep=header_delimiter,
        engine='python',
        skipinitialspace=True,
    )


def _find_column(df: pd.DataFrame, patterns: list[str]) -> str | None:
    normalized = {_normalize_column_name(col): col for col in df.columns}
    for pattern in patterns:
        regex = re.compile(pattern)
        for norm_col, col in normalized.items():
            if regex.search(norm_col):
                return col
    return None


def _to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors='coerce')


def _to_datetime(series: pd.Series) -> pd.Series:
    dt = pd.to_datetime(series, errors='coerce')
    if dt.notna().sum() > 0:
        return dt

    # Fallback for HH:MM:SS style values without date.
    td = pd.to_timedelta(series, errors='coerce')
    if td.notna().sum() > 0:
        ref = pd.Timestamp('1970-01-01')
        return ref + td

    return dt


def _series_in_sccm_to_m3_s(series: pd.Series) -> pd.Series:
    return _to_numeric(series) * SCCM_TO_M3_S


def _pressure_to_pa(value: float | None) -> float | None:
    if value is None or np.isnan(value):
        return None
    if value <= 0:
        return value
    # Typical RTP process pressures are often logged in torr around 100-800.
    if value < PRESSURE_TORR_INTERPRETATION_MAX:
        return value * TORR_TO_PA
    return value


def _temperature_to_kelvin(series: pd.Series) -> pd.Series:
    values = _to_numeric(series)
    finite = values[np.isfinite(values)]
    if len(finite) == 0:
        return values

    median = float(np.nanmedian(finite))
    # Heuristic: values in the RTP process are usually in celsius if centered
    # below ~350, while kelvin logs are typically around 500-900.
    if median < CELSIUS_MEDIAN_THRESHOLD:
        return values + CELSIUS_TO_KELVIN_OFFSET
    return values


def _build_process_dataframe(
    eklipse_df: pd.DataFrame,
    t2b_df: pd.DataFrame,
) -> pd.DataFrame:
    time_col_eklipse = _find_column(eklipse_df, [r'timestamp', r'^time$'])
    time_col_t2b = _find_column(t2b_df, [r'timestamp', r'^time$'])

    eklipse = pd.DataFrame()
    if time_col_eklipse is not None:
        eklipse['timestamp'] = _to_datetime(eklipse_df[time_col_eklipse])

    pressure_col = _find_column(
        eklipse_df,
        [r'capmanpressure$', r'pressure$', r'chamberpressure', r'processpressure'],
    )
    if pressure_col is not None:
        eklipse['pressure_raw'] = _to_numeric(eklipse_df[pressure_col])

    flow_col_map = {
        'ar_flow_m3_s': [r'mfc1flow$', r'\bar\b.*flow', r'argon.*flow'],
        'n2_flow_m3_s': [r'mfc2flow$', r'n2.*flow'],
        'ph3_in_ar_flow_m3_s': [r'mfc4flow$', r'ph3.*flow'],
        'h2s_in_ar_flow_m3_s': [r'mfc6flow$', r'h2s.*flow'],
    }
    for key, patterns in flow_col_map.items():
        col = _find_column(eklipse_df, patterns)
        if col is not None:
            eklipse[key] = _series_in_sccm_to_m3_s(eklipse_df[col])
        else:
            eklipse[key] = 0.0

    t2b = pd.DataFrame()
    if time_col_t2b is not None:
        t2b['timestamp'] = _to_datetime(t2b_df[time_col_t2b])

    temp_col = _find_column(t2b_df, [r'temperature$', r'pyro.*temp', r'temp'])
    if temp_col is not None:
        t2b['temperature_k'] = _temperature_to_kelvin(t2b_df[temp_col])

    if 'timestamp' in t2b and t2b['timestamp'].notna().sum() > 1:
        t2b = t2b.sort_values('timestamp')
    if 'timestamp' in eklipse and eklipse['timestamp'].notna().sum() > 1:
        eklipse = eklipse.sort_values('timestamp')

    # Prefer temperature timeline from diagnostics and align gas/pressure from
    # Eklipse on nearest timestamp.
    if not t2b.empty and 'timestamp' in t2b and t2b['timestamp'].notna().sum() > 1:
        if 'timestamp' in eklipse and eklipse['timestamp'].notna().sum() > 1:
            process = pd.merge_asof(
                t2b,
                eklipse,
                on='timestamp',
                direction='nearest',
                tolerance=pd.Timedelta(seconds=5),
            )
        else:
            process = t2b.copy()
            for col in [
                'pressure_raw',
                'ar_flow_m3_s',
                'n2_flow_m3_s',
                'ph3_in_ar_flow_m3_s',
                'h2s_in_ar_flow_m3_s',
            ]:
                process[col] = 0.0
    else:
        process = eklipse.copy()
        temp_from_eklipse = _find_column(
            eklipse_df,
            [r'substrateheatertemperature$', r'temperature$', r'temp'],
        )
        if temp_from_eklipse is not None:
            process['temperature_k'] = _temperature_to_kelvin(
                eklipse_df[temp_from_eklipse]
            )

    process = process.dropna(subset=['timestamp'], how='all').copy()
    if process.empty:
        return process

    process = process.sort_values('timestamp')
    process['time_s'] = (
        process['timestamp'] - process['timestamp'].iloc[0]
    ).dt.total_seconds()

    if 'temperature_k' not in process:
        process['temperature_k'] = np.nan

    process = process[np.isfinite(process['time_s'])]
    return process


def _extract_steps(process_df: pd.DataFrame) -> list[ParsedRTPStep]:
    if (
        process_df.empty
        or process_df['temperature_k'].notna().sum() < MIN_POINTS_FOR_STEP_EXTRACTION
    ):
        return []

    df = process_df[['time_s', 'temperature_k', 'pressure_raw']].copy()
    for col in [
        'ar_flow_m3_s',
        'n2_flow_m3_s',
        'ph3_in_ar_flow_m3_s',
        'h2s_in_ar_flow_m3_s',
    ]:
        df[col] = process_df.get(col, 0.0)

    df = df.dropna(subset=['time_s', 'temperature_k']).sort_values('time_s')
    if len(df) < MIN_POINTS_FOR_STEP_EXTRACTION:
        return []

    # Segment the process by detecting a high-temperature plateau region.
    temp_k = df['temperature_k'].to_numpy()
    temp_range = float(np.nanmax(temp_k) - np.nanmin(temp_k))
    plateau_tol = max(5.0, 0.03 * temp_range)
    max_temp = float(np.nanmax(temp_k))
    plateau_mask = temp_k >= (max_temp - plateau_tol)

    if not np.any(plateau_mask):
        i_max = int(np.nanargmax(temp_k))
        bounds = [0, i_max, len(df) - 1]
    else:
        first = int(np.argmax(plateau_mask))
        last = int(len(plateau_mask) - 1 - np.argmax(plateau_mask[::-1]))
        bounds = [0, first, last, len(df) - 1]

    # Keep strictly increasing boundaries.
    cleaned_bounds: list[int] = []
    for idx in bounds:
        if not cleaned_bounds or idx > cleaned_bounds[-1]:
            cleaned_bounds.append(idx)

    # Map the segmented intervals to the canonical RTP phases.
    step_names = ['Heating', 'Annealing', 'Cooling']
    steps: list[ParsedRTPStep] = []
    for i in range(len(cleaned_bounds) - 1):
        start = cleaned_bounds[i]
        end = cleaned_bounds[i + 1]
        if end <= start:
            continue
        sl = df.iloc[start : end + 1]

        duration_s = float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0])
        if duration_s <= 0:
            continue

        step = ParsedRTPStep(
            name=step_names[i] if i < len(step_names) else f'Step {i + 1}',
            duration_s=duration_s,
            initial_temperature_k=float(sl['temperature_k'].iloc[0]),
            final_temperature_k=float(sl['temperature_k'].iloc[-1]),
            pressure_pa=float(
                _pressure_to_pa(float(np.nanmedian(sl['pressure_raw'])) or 0) or 0
            ),
            ar_flow_m3_s=float(np.nanmedian(sl['ar_flow_m3_s'])),
            n2_flow_m3_s=float(np.nanmedian(sl['n2_flow_m3_s'])),
            ph3_in_ar_flow_m3_s=float(np.nanmedian(sl['ph3_in_ar_flow_m3_s'])),
            h2s_in_ar_flow_m3_s=float(np.nanmedian(sl['h2s_in_ar_flow_m3_s'])),
        )
        steps.append(step)

    if not steps:
        sl = df.iloc[[0, -1]]
        steps.append(
            ParsedRTPStep(
                name='Annealing',
                duration_s=float(sl['time_s'].iloc[-1] - sl['time_s'].iloc[0]),
                initial_temperature_k=float(sl['temperature_k'].iloc[0]),
                final_temperature_k=float(sl['temperature_k'].iloc[-1]),
                pressure_pa=float(
                    _pressure_to_pa(float(np.nanmedian(df['pressure_raw']))) or 0
                ),
                ar_flow_m3_s=float(np.nanmedian(df['ar_flow_m3_s'])),
                n2_flow_m3_s=float(np.nanmedian(df['n2_flow_m3_s'])),
                ph3_in_ar_flow_m3_s=float(np.nanmedian(df['ph3_in_ar_flow_m3_s'])),
                h2s_in_ar_flow_m3_s=float(np.nanmedian(df['h2s_in_ar_flow_m3_s'])),
            )
        )

    return steps


def _derive_overview(
    process_df: pd.DataFrame,
    steps: list[ParsedRTPStep],
) -> dict[str, float | None]:
    if not steps:
        return {
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
        }

    # Pick the most representative annealing step by weighted temperature and
    # duration score. This is robust when extra setup/cleanup intervals exist.
    anneal_idx = int(
        np.argmax(
            [
                (0.7 * ((s.initial_temperature_k + s.final_temperature_k) / 2))
                + (0.3 * s.duration_s)
                for s in steps
            ]
        )
    )
    anneal = steps[anneal_idx]

    total_heating = sum(s.duration_s for s in steps[:anneal_idx])
    total_cooling = sum(s.duration_s for s in steps[anneal_idx + 1 :])

    end_temp = steps[-1].final_temperature_k

    return {
        'annealing_pressure': anneal.pressure_pa,
        'annealing_time': anneal.duration_s,
        'annealing_temperature': (
            anneal.initial_temperature_k + anneal.final_temperature_k
        )
        / 2,
        'annealing_ar_flow': anneal.ar_flow_m3_s,
        'annealing_n2_flow': anneal.n2_flow_m3_s,
        'annealing_ph3_in_ar_flow': anneal.ph3_in_ar_flow_m3_s,
        'annealing_h2s_in_ar_flow': anneal.h2s_in_ar_flow_m3_s,
        'total_heating_time': total_heating,
        'total_cooling_time': total_cooling,
        'end_of_process_temperature': end_temp,
    }


def _derive_general_values(
    process_df: pd.DataFrame,
    key_values: dict[str, float],
) -> tuple[float | None, float | None, float | None, float | None]:
    pressure_series = process_df.get('pressure_raw')
    base_pressure = None
    base_pressure_ballast = None
    rate_of_rise = None
    chiller_flow = None

    if pressure_series is not None and pressure_series.notna().sum() > 0:
        pressure_pa = _to_numeric(pressure_series).apply(_pressure_to_pa)
        n_head = max(3, int(0.1 * len(pressure_pa)))
        baseline = pressure_pa.iloc[:n_head].dropna()
        if not baseline.empty:
            base_pressure = float(np.nanmin(baseline))
            base_pressure_ballast = float(np.nanmedian(baseline))

        # Estimate rate-of-rise in low-flow region near start.
        if len(process_df) >= MIN_PROCESS_ROWS_FOR_RATE_OF_RISE:
            total_flow = (
                process_df.get('ar_flow_m3_s', 0)
                + process_df.get('n2_flow_m3_s', 0)
                + process_df.get('ph3_in_ar_flow_m3_s', 0)
                + process_df.get('h2s_in_ar_flow_m3_s', 0)
            )
            static_cond = _to_numeric(total_flow).fillna(0) < STATIC_FLOW_THRESHOLD_M3_S
            candidates = process_df.loc[static_cond]
            if len(candidates) < MIN_LINEAR_FIT_POINTS:
                candidates = process_df.iloc[: max(4, int(0.15 * len(process_df)))]

            t = _to_numeric(candidates['time_s']).to_numpy()
            p = (
                _to_numeric(candidates.get('pressure_raw'))
                .apply(_pressure_to_pa)
                .to_numpy()
            )
            valid = np.isfinite(t) & np.isfinite(p)
            if np.count_nonzero(valid) >= MIN_LINEAR_FIT_POINTS:
                slope, _ = np.polyfit(t[valid], p[valid], 1)
                rate_of_rise = float(slope)

    # Allow explicit key/value diagnostics to override time-series estimates.
    for key, value in key_values.items():
        if 'basepressurewithoutballast' in key:
            base_pressure = value
        elif 'basepressurewithballast' in key:
            base_pressure_ballast = value
        elif 'rateofrise' in key:
            if 'minute' in key or 'min' in key:
                rate_of_rise = value / 60
            else:
                rate_of_rise = value
        elif 'chiller' in key and 'flow' in key:
            chiller_flow = value

    return base_pressure, base_pressure_ballast, rate_of_rise, chiller_flow


def parse_rtp_logfiles(
    eklipse_csv_path: str,
    t2b_diagnostics_txt_path: str,
) -> ParsedRTPData:
    """Parse RTP Eklipse and diagnostics logs into a schema-friendly payload."""
    eklipse_df = _read_csv_with_fallback(eklipse_csv_path)

    with open(t2b_diagnostics_txt_path, encoding='utf-8', errors='ignore') as handle:
        t2b_content = handle.read()

    key_values = _extract_key_values_from_text(t2b_content)
    t2b_df = _parse_table_from_text(t2b_content)

    process_df = _build_process_dataframe(eklipse_df, t2b_df)
    steps = _extract_steps(process_df)
    overview = _derive_overview(process_df, steps)

    base_pressure, base_pressure_ballast, rate_of_rise, chiller_flow = (
        _derive_general_values(process_df, key_values)
    )

    gas_flow_map: dict[str, Any] = {
        'Ar': overview.get('annealing_ar_flow'),
        'N2': overview.get('annealing_n2_flow'),
        'PH3': overview.get('annealing_ph3_in_ar_flow'),
        'H2S': overview.get('annealing_h2s_in_ar_flow'),
    }
    used_gases = [
        gas
        for gas, flow in gas_flow_map.items()
        if flow is not None and float(flow) > MIN_USED_GAS_FLOW_M3_S
    ]

    return ParsedRTPData(
        used_gases=used_gases,
        base_pressure_pa=base_pressure,
        base_pressure_ballast_pa=base_pressure_ballast,
        rate_of_rise_pa_s=rate_of_rise,
        chiller_flow_m3_s=chiller_flow,
        overview=overview,
        steps=steps,
    )
