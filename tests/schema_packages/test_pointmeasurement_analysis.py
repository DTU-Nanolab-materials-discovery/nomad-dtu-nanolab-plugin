import io
from importlib import import_module
from types import SimpleNamespace

import nbformat
import numpy as np
import pandas as pd
import pytest
from nomad.datamodel.metainfo.basesections import Analysis
from nomad.datamodel.metainfo.plot import PlotlyFigure

from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)
from nomad_dtu_nanolab_plugin.schema_packages.pointmeasurement import PointMeasurement

analysis_module = import_module('nomad_dtu_nanolab_plugin.schema_packages.analysis')


class _MemoryContext:
    def __init__(self, files=None, existing=()):
        self.files = dict(files or {})
        self.existing = set(existing)
        self.updated_files = []
        self.installation_url = 'https://nomad.example'

    def raw_file(self, path, mode='r'):
        if 'w' in mode:
            return _MemoryWriter(self, path)
        return io.StringIO(self.files.get(path, ''))

    def raw_path_exists(self, path):
        return path in self.existing

    def process_updated_raw_file(self, path, allow_modify=False):
        self.updated_files.append((path, allow_modify))


class _MemoryWriter(io.StringIO):
    def __init__(self, context, path):
        super().__init__()
        self.context = context
        self.path = path

    def close(self):
        self.context.files[self.path] = self.getvalue()
        super().close()


def _archive(context, *, mainfile='analysis.archive.yaml'):
    return SimpleNamespace(
        m_context=context,
        metadata=SimpleNamespace(
            mainfile=mainfile,
            entry_id='entry-123',
            upload_id='upload-456',
            main_author=SimpleNamespace(name='Test User'),
        ),
    )


def _logger():
    return SimpleNamespace(warn=lambda *_args: None)


@pytest.mark.parametrize(
    ('plot_type', 'expected_mode', 'expected_title'),
    [
        ('scatter', 'markers', 'Scatter Plot'),
        ('line', 'lines', 'Line Plot'),
    ],
)
def test_point_measurement_plot_creates_traces_for_each_y_column(
    monkeypatch, plot_type, expected_mode, expected_title
):
    frame = pd.DataFrame(
        {
            'Elapsed time (s)': [0, 1, 2],
            'Temperature (K)': [300, 400, 500],
            'Pressure (Pa)': [10, 20, 30],
        }
    )
    monkeypatch.setattr(pd, 'read_excel', lambda _file: frame)
    measurement = PointMeasurement(plotting_file='values.xlsx', plot_type=plot_type)

    measurement.plot(_archive(_MemoryContext()))

    assert len(measurement.figures) == 1
    figure = measurement.figures[0]
    assert figure.label == 'Plot'
    assert figure.figure['layout']['title']['text'] == expected_title
    assert figure.figure['layout']['xaxis']['title']['text'] == 'Elapsed time (s)'
    assert [trace['name'] for trace in figure.figure['data']] == [
        'Temperature (K)',
        'Pressure (Pa)',
    ]
    assert all(trace['mode'] == expected_mode for trace in figure.figure['data'])
    np.testing.assert_array_equal(figure.figure['data'][0]['x'], [0, 1, 2])
    np.testing.assert_array_equal(figure.figure['data'][1]['y'], [10, 20, 30])
    assert figure.figure['config'] == {'scrollZoom': False}


def test_point_measurement_map_uses_xy_coordinates_and_each_value_column(monkeypatch):
    frame = pd.DataFrame(
        {
            'X position (mm)': [0, 1, 0],
            'Y position (mm)': [0, 0, 1],
            'Thickness (nm)': [10, 20, 30],
            'Roughness (nm)': [1, 2, 3],
        }
    )
    monkeypatch.setattr(pd, 'read_excel', lambda _file: frame)
    measurement = PointMeasurement(plotting_file='map.xlsx', plot_type='map')

    measurement.plot(_archive(_MemoryContext()))

    figure = measurement.figures[0].figure
    assert figure['layout']['title']['text'] == 'Heatmap'
    expected_trace_count = 2
    assert len(figure['data']) == expected_trace_count
    for trace, title in zip(figure['data'], ['Thickness (nm)', 'Roughness (nm)']):
        assert trace['type'] == 'scatter'
        assert trace['mode'] == 'markers'
        assert trace['name'] == title
        assert trace['marker']['colorbar']['title']['text'] == title
    assert figure['layout']['xaxis']['title']['text'] == 'X position (mm)'
    assert figure['layout']['yaxis']['title']['text'] == 'Y position (mm)'


def test_point_measurement_plot_without_file_does_not_add_figure(monkeypatch):
    monkeypatch.setattr(
        pd,
        'read_excel',
        lambda *_args: pytest.fail('Excel data should not be read without a file'),
    )
    measurement = PointMeasurement(plot_type='line')

    measurement.plot(_archive(_MemoryContext()))

    assert measurement.figures == []


def test_point_measurement_normalize_sets_location_resolves_raw_file_and_plots(
    monkeypatch,
):
    monkeypatch.setattr(DtuNanolabMeasurement, 'normalize', lambda *_args: None)
    measurement = PointMeasurement(
        raw_file=['sample_001_002_003.csv'],
        plotting_file='plot.xlsx',
        plot_type='scatter',
    )
    resolved = []
    plots = []
    logger = _logger()

    def record_plot(archive):
        plots.append(archive)

    monkeypatch.setattr(
        measurement,
        'add_sample_reference',
        lambda *args: resolved.append(args),
    )
    monkeypatch.setattr(measurement, 'plot', record_plot)
    archive = _archive(_MemoryContext())

    measurement.normalize(archive, logger)

    assert measurement.location == 'DTU Nanolab'
    assert len(resolved) == 1
    assert resolved[0][:3] == ('sample_001_002_003.csv', 'Raw Data', archive)
    assert resolved[0][3] is logger
    assert plots == [archive]
    assert measurement.figures == []


def test_point_measurement_normalize_skips_disabled_plot_and_keeps_location(
    monkeypatch,
):
    monkeypatch.setattr(DtuNanolabMeasurement, 'normalize', lambda *_args: None)
    measurement = PointMeasurement(
        location='Existing location',
        plotting_file='plot.xlsx',
        plot_type='none',
    )
    measurement.figures.append(PlotlyFigure(label='Old figure', figure={}))
    plot_called = []
    monkeypatch.setattr(measurement, 'plot', lambda *_args: plot_called.append(True))

    measurement.normalize(_archive(_MemoryContext()), _logger())

    assert measurement.location == 'Existing location'
    assert measurement.figures == []
    assert not plot_called


def test_replace_analysis_id_updates_matching_code_cell_only():
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(source=analysis_module.FIRST_CODE_CELL),
            nbformat.v4.new_code_cell(source='print("before")'),
            nbformat.v4.new_code_cell(
                source=analysis_module.FIRST_CODE_CELL % 'old-entry'
            ),
        ]
    )

    result = analysis_module.replace_analysis_id(notebook, 'new-entry')

    assert result is notebook
    assert notebook.cells[2].source == analysis_module.FIRST_CODE_CELL % 'new-entry'
    assert notebook.cells[0].source == analysis_module.FIRST_CODE_CELL
    assert notebook.cells[1].source == 'print("before")'


def test_replace_analysis_id_returns_none_without_query_cell():
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell(source='print("not a query")')]
    )

    assert analysis_module.replace_analysis_id(notebook, 'entry') is None


def test_copy_from_analysis_writes_template_with_placeholder_id():
    source_notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                source=analysis_module.FIRST_CODE_CELL % 'source-entry'
            )
        ]
    )
    source_context = _MemoryContext(
        files={'source.ipynb': nbformat.writes(source_notebook)}
    )
    source_analysis = analysis_module.DtuJupyterAnalysis(notebook='source.ipynb')
    source_analysis.m_context = source_context
    template = analysis_module.DtuJupyterAnalysisTemplate(from_analysis=source_analysis)
    context = _MemoryContext()
    archive = _archive(context, mainfile='derived.archive.yaml')

    result = template.copy_from_analysis(archive, _logger())

    assert result == 'derived.ipynb'
    written = nbformat.reads(context.files[result], as_version=4)
    assert written.cells[0].source == (
        analysis_module.FIRST_CODE_CELL % 'THE_ANALYSIS_ID'
    )


def test_copy_from_analysis_handles_missing_query_and_existing_file():
    source_context = _MemoryContext(
        files={
            'source.ipynb': nbformat.writes(
                nbformat.v4.new_notebook(
                    cells=[nbformat.v4.new_code_cell(source='print("missing")')]
                )
            )
        }
    )
    source_analysis = analysis_module.DtuJupyterAnalysis(notebook='source.ipynb')
    source_analysis.m_context = source_context
    template = analysis_module.DtuJupyterAnalysisTemplate(
        template_notebook='previous.ipynb', from_analysis=source_analysis
    )

    assert template.copy_from_analysis(_archive(_MemoryContext()), _logger()) == (
        'previous.ipynb'
    )

    source_context.files['source.ipynb'] = nbformat.writes(
        nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_code_cell(
                    source=analysis_module.FIRST_CODE_CELL % 'source-entry'
                )
            ]
        )
    )
    target_context = _MemoryContext(existing={'analysis.ipynb'})

    assert template.copy_from_analysis(_archive(target_context), _logger()) == (
        'previous.ipynb'
    )


def test_analysis_template_normalize_defaults_active_and_generates_notebook(
    monkeypatch,
):
    monkeypatch.setattr(Analysis, 'normalize', lambda *_args: None)
    template = analysis_module.DtuJupyterAnalysisTemplate(
        generate_notebook=True,
        from_analysis=analysis_module.DtuJupyterAnalysis(notebook='source.ipynb'),
    )
    generated = []
    monkeypatch.setattr(
        template,
        'copy_from_analysis',
        lambda *_args: generated.append(True) or 'template.ipynb',
    )
    archive = _archive(_MemoryContext())

    template.normalize(archive, _logger())

    assert template.active is True
    assert template.template_notebook == 'template.ipynb'
    assert template.generate_notebook is False
    assert generated == [True]


def test_analysis_create_notebook_writes_expected_cells_and_marks_raw_file_updated():
    context = _MemoryContext()
    archive = _archive(context)
    analysis = analysis_module.DtuJupyterAnalysis(name='Example analysis')

    analysis.create_notebook(archive, _logger())

    assert analysis.notebook == 'analysis.ipynb'
    notebook = nbformat.reads(context.files[analysis.notebook], as_version=4)
    assert notebook.metadata.trusted
    minimum_generated_cell_count = 5
    assert len(notebook.cells) > minimum_generated_cell_count
    query_cells = [
        cell
        for cell in notebook.cells
        if cell.cell_type == 'code'
        and analysis_module.FIRST_CODE_CELL % 'entry-123' == cell.source
    ]
    assert len(query_cells) == 1
    assert context.updated_files == [('analysis.ipynb', True)]


def test_analysis_create_notebook_does_not_overwrite_existing_file():
    context = _MemoryContext(existing={'analysis.ipynb'})
    archive = _archive(context)
    analysis = analysis_module.DtuJupyterAnalysis()

    analysis.create_notebook(archive, _logger())

    assert analysis.notebook is None
    assert context.files == {}


def test_copy_from_template_replaces_entry_id_and_sets_notebook_path():
    source_notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                source=analysis_module.FIRST_CODE_CELL % 'template-id'
            )
        ]
    )
    template_context = _MemoryContext(
        files={'template.ipynb': nbformat.writes(source_notebook)}
    )
    template = analysis_module.DtuJupyterAnalysisTemplate(
        template_notebook='template.ipynb',
    )
    template.m_context = template_context
    analysis = analysis_module.DtuJupyterAnalysis(template=template)
    context = _MemoryContext()
    archive = _archive(context)

    analysis.copy_from_template(archive, _logger())

    assert analysis.notebook == 'analysis.ipynb'
    copied = nbformat.reads(context.files[analysis.notebook], as_version=4)
    assert copied.cells[0].source == (analysis_module.FIRST_CODE_CELL % 'entry-123')


def test_copy_from_template_missing_query_or_existing_file_does_not_write():
    template_context = _MemoryContext(
        files={
            'template.ipynb': nbformat.writes(
                nbformat.v4.new_notebook(
                    cells=[nbformat.v4.new_code_cell(source='print("missing")')]
                )
            )
        }
    )
    template = analysis_module.DtuJupyterAnalysisTemplate(
        template_notebook='template.ipynb',
    )
    template.m_context = template_context
    analysis = analysis_module.DtuJupyterAnalysis(template=template)
    context = _MemoryContext()
    archive = _archive(context)

    assert analysis.copy_from_template(archive, _logger()) is None
    assert analysis.notebook is None
    assert context.files == {}

    template_context.files['template.ipynb'] = nbformat.writes(
        nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_code_cell(
                    source=analysis_module.FIRST_CODE_CELL % 'template-id'
                )
            ]
        )
    )
    context.existing.add('analysis.ipynb')

    assert analysis.copy_from_template(archive, _logger()) is None
    assert context.files == {}


def test_analysis_save_uses_parent_archive_metadata(monkeypatch):
    calls = []
    monkeypatch.setattr(
        analysis_module,
        'create_entry_with_api',
        lambda **kwargs: calls.append(kwargs),
    )
    archive = _archive(_MemoryContext())
    analysis = analysis_module.DtuJupyterAnalysis()
    analysis.m_parent = archive

    analysis.save()

    assert calls == [
        {
            'section': analysis,
            'base_url': 'https://nomad.example',
            'upload_id': 'upload-456',
            'file_name': 'analysis.archive.yaml',
        }
    ]


def test_analysis_normalize_generates_notebook_and_clears_flag(monkeypatch):
    monkeypatch.setattr(Analysis, 'normalize', lambda *_args: None)
    analysis = analysis_module.DtuJupyterAnalysis(generate_notebook=True)
    generated = []
    monkeypatch.setattr(
        analysis,
        'create_notebook',
        lambda *_args: generated.append('created'),
    )

    analysis.normalize(_archive(_MemoryContext()), _logger())

    assert generated == ['created']
    assert analysis.generate_notebook is False


def test_analysis_normalize_copies_template_when_template_notebook_exists(monkeypatch):
    monkeypatch.setattr(Analysis, 'normalize', lambda *_args: None)
    template = analysis_module.DtuJupyterAnalysisTemplate(
        template_notebook='template.ipynb'
    )
    analysis = analysis_module.DtuJupyterAnalysis(
        template=template,
        generate_notebook=True,
    )
    copied = []
    monkeypatch.setattr(
        analysis,
        'copy_from_template',
        lambda *_args: copied.append(True),
    )

    analysis.normalize(_archive(_MemoryContext()), _logger())

    assert copied == [True]
    assert analysis.generate_notebook is False
