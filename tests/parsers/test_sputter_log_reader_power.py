import numpy as np
import pandas as pd
import pytest

from nomad_dtu_nanolab_plugin.sputter_log_reader import (
    Deposition_Event,
    connect_source_to_power_supply,
)


def test_historical_power_type_inference_takes_precedence_over_supply_fallback():
    event = Deposition_Event('test deposition')
    event.data = pd.DataFrame(
        {
            'Source 1 Current': [0.02, 0.02, 0.02, 0.02],
            'Source 1 Pulse Enable': [0, 0, 0, 0],
            'Source 1 Power Supply': ['Power Supply 2'] * 4,
        }
    )

    assert event.get_power_type(1) == 'DC'


def test_power_type_falls_back_to_unambiguous_supply_mapping():
    event = Deposition_Event('test deposition')
    event.data = pd.DataFrame(
        {'Source 1 Power Supply': ['Power Supply 3', 'Power Supply 3']}
    )

    assert event.get_power_type(1) == 'RF'


def test_source_switching_supplies_maps_values_by_timestep():
    data = pd.DataFrame(
        {
            'PC Source 1 Shutter Open': [1, 1, 1, 1],
            'PC Source 1 Switch-RF1-PWS2': [1, 1, 0, 0],
            'PC Source 1 Switch-RF2-PWS3': [0, 0, 1, 1],
            'Power Supply 2 Fwd Power': [10, 11, 0, 0],
            'Power Supply 3 Fwd Power': [0, 0, 20, 21],
            'Source 1 Fwd Power': [-1, -1, -1, -1],
        }
    )

    connect_source_to_power_supply(data, [1])

    assert data['Source 1 Fwd Power'].tolist() == [10, 11, 20, 21]
    assert data['Source 1 Power Supply'].tolist() == [
        'Power Supply 2',
        'Power Supply 2',
        'Power Supply 3',
        'Power Supply 3',
    ]


def test_simultaneous_supply_mapping_warns_and_excludes_ambiguous_row():
    data = pd.DataFrame(
        {
            'PC Source 1 Shutter Open': [1],
            'PC Source 1 Switch-PDC-PWS1': [1],
            'PC Source 1 Switch-RF1-PWS2': [1],
            'Power Supply 1 Current': [0.2],
            'Power Supply 2 Fwd Power': [25],
            'Source 1 Current': [99],
        }
    )

    with pytest.warns(RuntimeWarning, match='connected to multiple power supplies'):
        connect_source_to_power_supply(data, [1])

    assert pd.isna(data.loc[0, 'Source 1 Power Supply'])
    assert np.isnan(data.loc[0, 'Source 1 Current'])
    assert np.isnan(data.loc[0, 'Source 1 Fwd Power'])
