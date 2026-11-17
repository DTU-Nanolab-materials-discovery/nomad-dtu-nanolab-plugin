import numpy as np
from nomad.units import ureg

from nomad_dtu_nanolab_plugin.schema_packages.ellipsometry import (
    DTUEllipsometryMeasurement,
    EllipsometryMappingResult,
)
from nomad_dtu_nanolab_plugin.schema_packages.raman import (
    RamanMeasurement,
    RamanResult,
)


def _raman_result(x, y, intensities, *, relative=True):
    coordinates = {
        'x_absolute': x * ureg.mm,
        'y_absolute': y * ureg.mm,
    }
    if relative:
        coordinates.update(
            x_relative=x * ureg.mm,
            y_relative=y * ureg.mm,
        )
    return RamanResult(
        raman_shift=np.array([520.0, 600.0, 601.0, 602.0]),
        intensity=np.array(intensities),
        **coordinates,
    )


def _ellipsometry_result(x, y, thickness, *, relative=True):
    coordinates = {
        'x_absolute': x * ureg.mm,
        'y_absolute': y * ureg.mm,
    }
    if relative:
        coordinates.update(
            x_relative=x * ureg.mm,
            y_relative=y * ureg.mm,
        )
    return EllipsometryMappingResult(
        thickness=thickness * ureg.nm,
        **coordinates,
    )


def test_raman_intensity_map_averages_coincident_positions():
    measurement = RamanMeasurement(
        results=[
            _raman_result(0, 0, [999, 10, 30, 20]),
            _raman_result(0, 0, [999, 50, 70, 30]),
            _raman_result(1, 0, [999, 90, 110, 70]),
        ]
    )

    figure = measurement.plot_intensity_map_from_results(wavenumber_tolerance=1)

    assert figure.label == 'Raman Intensity Map'
    heatmap = figure.figure['data'][0]
    np.testing.assert_allclose(heatmap['z'], [[35, 90]])
    assert list(heatmap['x']) == [0, 1]
    assert list(heatmap['y']) == [0]
    assert figure.figure['layout']['title']['text'] == (
        'Raman Intensity Map at 601.00 cm-1'
    )
    assert figure.figure['layout']['xaxis']['title']['text'] == (
        'X Sample Position (mm)'
    )


def test_raman_intensity_map_uses_absolute_positions_when_relative_are_incomplete():
    measurement = RamanMeasurement(
        results=[
            _raman_result(2, 4, [999, 0, 10, 0]),
            _raman_result(3, 4, [999, 0, 20, 0], relative=False),
        ]
    )

    figure = measurement.plot_intensity_map_from_results(wavenumber_tolerance=0)

    heatmap = figure.figure['data'][0]
    np.testing.assert_allclose(heatmap['z'], [[10, 20]])
    assert list(heatmap['x']) == [2, 3]
    assert figure.figure['layout']['xaxis']['title']['text'] == (
        'X Stage Position (mm)'
    )


def test_raman_intensity_map_is_absent_without_results():
    assert RamanMeasurement().plot_intensity_map_from_results() is None


def test_ellipsometry_parameter_map_uses_line_plot_for_one_dimensional_scan():
    measurement = DTUEllipsometryMeasurement(
        results=[
            _ellipsometry_result(0, 0, 10),
            _ellipsometry_result(0, 1, 12),
            _ellipsometry_result(0, 2, 15),
        ]
    )

    figure = measurement._create_parameter_map('thickness', 'Thickness')

    assert figure.label == 'Thickness Map'
    assert len(figure.figure['data']) == 1
    line = figure.figure['data'][0]
    assert line['type'] == 'scatter'
    assert list(line['x']) == [0, 1, 2]
    np.testing.assert_allclose(line['y'], [10, 12, 15])
    assert figure.figure['layout']['title']['text'] == (
        'Thickness vs Y Sample Position'
    )
    assert figure.figure['layout']['yaxis']['title']['text'] == 'Thickness (nm)'


def test_ellipsometry_parameter_map_uses_heatmap_for_two_dimensional_scan():
    measurement = DTUEllipsometryMeasurement(
        results=[
            _ellipsometry_result(0, 0, 10, relative=False),
            _ellipsometry_result(1, 0, 20, relative=False),
            _ellipsometry_result(0, 1, 30, relative=False),
            _ellipsometry_result(1, 1, 40, relative=False),
        ]
    )

    figure = measurement._create_parameter_map('thickness', 'Thickness')

    assert figure.label == 'Thickness Map'
    assert [trace['type'] for trace in figure.figure['data']] == [
        'heatmap',
        'scatter',
    ]
    markers = figure.figure['data'][1]
    assert list(markers['x']) == [0, 1, 0, 1]
    assert list(markers['y']) == [0, 0, 1, 1]
    np.testing.assert_allclose(markers['customdata'], [10, 20, 30, 40])
    assert figure.figure['layout']['title']['text'] == 'Thickness Stage Colormap'
    assert figure.figure['layout']['xaxis']['title']['text'] == (
        'X Stage Position (mm)'
    )


def test_ellipsometry_parameter_map_skips_missing_values_and_coordinates():
    measurement = DTUEllipsometryMeasurement(
        results=[
            EllipsometryMappingResult(thickness=None),
            EllipsometryMappingResult(thickness=12 * ureg.nm),
        ]
    )

    assert measurement._create_parameter_map('thickness', 'Thickness') is None
