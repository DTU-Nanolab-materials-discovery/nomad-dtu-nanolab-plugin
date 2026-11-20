import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

NOTEBOOK = (
    Path(__file__).resolve().parents[2]
    / 'notebooks'
    / 'oasis_trends'
    / 'exp8_exp9_anion_stoichiometry_and_basins.ipynb'
)
MINIMUM_VALID_BOOTSTRAPS = 900


def notebook_cells():
    notebook = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    return {
        cell['id']: ''.join(cell['source'])
        for cell in notebook['cells']
        if cell['cell_type'] == 'code'
    }


def run_cell(cells, cell_id, scope):
    exec(compile(cells[cell_id], cell_id, 'exec'), scope)


def test_exp8_uses_references_and_excludes_missing_elements(monkeypatch):
    monkeypatch.setattr(go.Figure, 'show', lambda *args, **kwargs: None)
    cells = notebook_cells()
    scope = {
        'np': np,
        'pd': pd,
        'px': px,
        'go': go,
        're': re,
        'PAULING_EN': {
            'Ag': 1.93,
            'Ba': 0.89,
            'Cu': 1.90,
            'N': 3.04,
            'P': 2.19,
            'S': 2.58,
            'Sb': 2.05,
            'Se': 2.55,
            'Sn': 1.96,
            'Te': 2.10,
            'Zn': 1.65,
            'Zr': 1.33,
        },
        'PLOTLY_CONFIG': {},
        'display': lambda value: None,
    }
    rows = []
    samples_per_system = 24
    for space, elements in [
        ('Sn-P-S', ('Sn', 'P', 'S')),
        ('Cu-P-S', ('Cu', 'P', 'S')),
        ('Ba-P-Te', ('Ba', 'P', 'Te')),
    ]:
        for i in range(samples_per_system):
            oxygen = 0.02 + i / 1000
            rows.append(
                {
                    'entry_id': f'{space}-{i}',
                    'lab_id': f'{space}_family{i // 3}_{i}',
                    'material_space': space,
                    'composition': {
                        elements[0]: 0.35,
                        elements[1]: 0.35,
                        elements[2]: 0.30 - oxygen,
                        'O': oxygen,
                    },
                }
            )
    rows.extend(
        [
            {
                'entry_id': 'no-oxygen',
                'lab_id': 'missing_1',
                'material_space': 'Cu-P-S',
                'composition': {'Cu': 0.3, 'P': 0.2, 'S': 0.5},
            },
            {
                'entry_id': 'no-sulfur',
                'lab_id': 'missing_2',
                'material_space': 'Cu-P-S',
                'composition': {'Cu': 0.3, 'P': 0.6, 'O': 0.1},
            },
        ]
    )
    scope['samples'] = pd.DataFrame(rows)
    for cell_id in ('8016fc5d', 'shared-phase-references', 'e8f02ee1'):
        run_cell(cells, cell_id, scope)

    refs = scope['EXP8_REFERENCES']
    assert {'Cu3PS4', 'BaTe2P4', 'SnS', 'Zr2SeN2'} <= {ref['phase'] for ref in refs}
    assert {'Cu3P', 'ZrZnN2'}.isdisjoint({ref['phase'] for ref in refs})
    te = next(ref for ref in refs if ref['phase'] == 'BaTe2P4')
    assert te['anion'] == 'Te' and set(te['matrix_elements']) == {'Ba', 'P'}
    cu = scope['exp8'].query("phase == 'Cu3PS4'")
    assert len(cu) == samples_per_system
    assert {'no-oxygen', 'no-sulfur'}.isdisjoint(cu['entry_id'])
    binary = scope['exp8'].query("phase == 'SnS'")
    assert len(binary) == samples_per_system
    assert set(binary['matrix_elements']) == {'Sn'}
    family_bootstrap = scope['family_bootstrap_summary']
    copper = family_bootstrap.query("phase == 'Cu3PS4' and metric == 'fraction'").iloc[
        0
    ]
    assert copper['valid_bootstraps'] >= MINIMUM_VALID_BOOTSTRAPS
    assert copper['ci_2_5'] <= copper['ci_97_5']


def test_process_correlations_use_runs_and_keep_missing_values(monkeypatch):
    figures = []
    monkeypatch.setattr(
        go.Figure, 'show', lambda figure, **kwargs: figures.append(figure)
    )
    count = 24
    rtp_count = 4
    run_means = pd.DataFrame(
        {
            'run_id': [f'r{i}' for i in range(count)],
            'space': ['A'] * 12 + ['B'] * 12,
            'mean_oxygen': [i / 100 for i in range(12)] * 2,
            'mean_rate_nm_min': np.arange(count) + 1,
        }
    )
    pressure_conversion = 101325 / 760
    runs_data = [
        (
            f'r{i}',
            'u',
            {
                'base_pressure': (1 + i % 12) * pressure_conversion * 1e-7,
                'deposition_parameters': {
                    'deposition_time': 60 * (i % 12 + 1),
                    'deposition_temperature': 273.15 + i % 12,
                    'ar_flow': 1e-6 / 60 * (i % 12 + 1),
                    'magkeeper3': {
                        'target_usage': 2.5,
                        'target_id': {'lab_id': f'target-{i % 2}'},
                    },
                    's_cracker': {'valve_on_time': 0.02},
                },
                'source_presput': [
                    {
                        'target_name': 'magkeeper3',
                        'presput_time': 120,
                        'presput_power': 50,
                    },
                    {
                        'target_name': 'magkeeper3',
                        'presput_time': 60,
                        'presput_power': 100,
                    },
                ],
                'source_ramp_up': [
                    {
                        'target_name': 'magkeeper3',
                        'plasma_ignition_power': 25,
                        'plasma_ignition_pressure': pressure_conversion * 2e-6,
                    }
                ],
                'source_deprate': [
                    {'target_name': 'magkeeper3', 'source_deprate': 2e-9}
                ],
            },
        )
        for i in range(count)
    ]
    scope = {
        'np': np,
        'pd': pd,
        'go': go,
        'PLOTLY_CONFIG': {},
        'display': lambda value: None,
        'run_means': run_means,
        'points': pd.DataFrame(
            {
                'run_id': run_means['run_id'],
                'rtp_input_any_time': [False] * (count - rtp_count)
                + [True] * rtp_count,
            }
        ),
        'runs_data': runs_data,
        'PA_PER_TORR': pressure_conversion,
        'finite': lambda value: float(value) if value is not None else np.nan,
    }
    run_cell(notebook_cells(), 'oxygen-process-correlations', scope)
    result = scope['oxygen_process_correlations'].set_index('parameter')
    time = result.loc['deposition_time_min']
    assert time['n_runs'] == count
    assert np.isclose(time['pooled_spearman'], 1)
    assert np.isclose(time['within_space_rank_correlation'], 1)
    missing = result.loc['o2_in_ar_flow_sccm']
    assert missing['n_runs'] == 0 and np.isnan(missing['pooled_spearman'])
    assert np.isclose(scope['process_runs']['ar_flow_sccm'].iloc[0], 1)
    assert np.isclose(scope['process_runs']['deposition_temperature_C'].iloc[0], 0)
    assert np.isclose(scope['process_runs']['magkeeper3_target_usage_kWh'].iloc[0], 2.5)
    assert np.isclose(scope['process_runs']['magkeeper3_presput_time_min'].iloc[0], 3)
    assert np.isclose(
        scope['process_runs']['magkeeper3_presput_power_W'].iloc[0], 200 / 3
    )
    assert np.isclose(scope['process_runs']['cracker_valve_on_s'].iloc[0], 0.02)
    assert np.isclose(scope['process_runs']['magkeeper3_ignition_power_W'].iloc[0], 25)
    assert np.isclose(
        scope['process_runs']['magkeeper3_source_deprate_nm_min'].iloc[0], 120
    )
    assert 'magkeeper3_presput_records' not in result.index
    assert 'magkeeper3_target_id' not in result.index
    assert 'magkeeper3_presput_recorded' in set(
        scope['categorical_process_summary']['parameter']
    )
    rtp = scope['rtp_sensitivity'].set_index('parameter')
    assert rtp.loc['deposition_time_min', 'n_runs'] == count - rtp_count
    assert scope['pair_counts'].loc['mean_oxygen', 'deposition_time_min'] == count
    assert len(figures) == 1
