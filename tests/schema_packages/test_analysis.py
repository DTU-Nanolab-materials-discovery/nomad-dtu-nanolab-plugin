from types import SimpleNamespace

import nbformat
import nomad.client
import pytest

from nomad_dtu_nanolab_plugin.schema_packages.analysis import (
    FIRST_CODE_CELL,
    LEGACY_FIRST_CODE_CELLS,
    DtuJupyterAnalysis,
    DtuJupyterAnalysisTemplate,
    replace_analysis_id,
)


class RawContext:
    def __init__(self, path, installation_url):
        self.path = path
        self.installation_url = installation_url
        self.updated = []

    def raw_path_exists(self, name):
        return (self.path / name).exists()

    def raw_file(self, name, mode):
        return (self.path / name).open(mode, encoding='utf-8')

    def process_updated_raw_file(self, name, allow_modify):
        self.updated.append((name, allow_modify))


def assert_query_uses_context(monkeypatch, cell, entry_id, url):
    observed = {}
    result = object()

    class FakeArchiveQuery:
        def __init__(self, **kwargs):
            observed.update(kwargs)

        def download(self):
            return [SimpleNamespace(data=result)]

    monkeypatch.setattr(nomad.client, 'ArchiveQuery', FakeArchiveQuery)
    namespace = {}
    exec(cell.source, namespace)
    assert observed == {
        'query': {'entry_id:any': [entry_id]},
        'required': '*',
        'url': url,
    }
    assert namespace['analysis'] is result


@pytest.mark.parametrize(
    'source',
    [
        FIRST_CODE_CELL % ('old-id', 'https://other.example/api'),
        *(cell % 'old-id' for cell in LEGACY_FIRST_CODE_CELLS),
        (LEGACY_FIRST_CODE_CELLS[0] % 'old-id').replace(
            'url=client.url,', "url='https://custom.example/api',"
        ),
        (LEGACY_FIRST_CODE_CELLS[1] % 'old-id').replace(
            "url='https://nomad.nanolab.dtu.dk/nomad-oasis/api',#client.url,",
            "url='https://custom.example/api',",
        ),
    ],
)
def test_replace_query_cell_preserves_other_cells(source):
    notebook = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell('Notes'),
            nbformat.v4.new_code_cell(source),
            nbformat.v4.new_code_cell('my_analysis = 42'),
        ]
    )
    url = "https://new.example/api?key=it's"

    assert replace_analysis_id(notebook, 'new-id', url) is notebook
    assert notebook.cells[1].source == FIRST_CODE_CELL % ('new-id', url)
    assert notebook.cells[0].source == 'Notes'
    assert notebook.cells[2].source == 'my_analysis = 42'
    compile(notebook.cells[1].source, '<notebook>', 'exec')


def test_replace_query_cell_does_not_replace_unrelated_code():
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("print('hello')")]
    )
    assert replace_analysis_id(notebook, 'id', 'https://example.org/api') is None
    assert notebook.cells[0].source == "print('hello')"


def test_generate_and_copy_notebook_with_context_urls(tmp_path, monkeypatch):
    logger = SimpleNamespace(warn=pytest.fail)
    source_context = RawContext(tmp_path, 'https://source.example/api')
    source_archive = SimpleNamespace(
        metadata=SimpleNamespace(
            mainfile='source.archive.yaml', entry_id='source-id', main_author=None
        ),
        m_context=source_context,
    )
    source = SimpleNamespace(name='Source', notebook=None)
    DtuJupyterAnalysis.create_notebook(source, source_archive, logger)
    with source_context.raw_file(source.notebook, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert notebook.cells[3].source == FIRST_CODE_CELL % (
        'source-id',
        source_context.installation_url,
    )
    assert_query_uses_context(
        monkeypatch, notebook.cells[3], 'source-id', source_context.installation_url
    )
    assert source_context.updated == [('source.ipynb', True)]

    template_context = RawContext(tmp_path, 'https://template.example/api')
    template_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='template.archive.yaml'),
        m_context=template_context,
    )
    from_analysis = SimpleNamespace(m_context=source_context, notebook=source.notebook)
    template = SimpleNamespace(from_analysis=from_analysis, template_notebook=None)
    template_path = DtuJupyterAnalysisTemplate.copy_from_analysis(
        template, template_archive, logger
    )
    with template_context.raw_file(template_path, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert notebook.cells[3].source == FIRST_CODE_CELL % (
        'THE_ANALYSIS_ID',
        template_context.installation_url,
    )

    target_context = RawContext(tmp_path, 'https://target.example/api')
    target_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='target.archive.yaml', entry_id='target-id'),
        m_context=target_context,
    )
    target = SimpleNamespace(
        template=SimpleNamespace(
            m_context=template_context, template_notebook=template_path
        ),
        notebook=None,
    )
    DtuJupyterAnalysis.copy_from_template(target, target_archive, logger)
    with target_context.raw_file(target.notebook, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert notebook.cells[3].source == FIRST_CODE_CELL % (
        'target-id',
        target_context.installation_url,
    )
    assert_query_uses_context(
        monkeypatch, notebook.cells[3], 'target-id', target_context.installation_url
    )


@pytest.mark.parametrize(
    'source',
    [
        FIRST_CODE_CELL % ('THE_ANALYSIS_ID', 'https://old.example/api'),
        *(cell % 'THE_ANALYSIS_ID' for cell in LEGACY_FIRST_CODE_CELLS),
        (LEGACY_FIRST_CODE_CELLS[0] % 'THE_ANALYSIS_ID').replace(
            'url=client.url,', "url='https://old.example/api',"
        ),
        (LEGACY_FIRST_CODE_CELLS[1] % 'THE_ANALYSIS_ID').replace(
            "url='https://nomad.nanolab.dtu.dk/nomad-oasis/api',#client.url,",
            "url='https://old.example/api',",
        ),
    ],
)
def test_template_notebook_template_notebook_cycle(tmp_path, monkeypatch, source):
    logger = SimpleNamespace(warn=pytest.fail)
    old_context = RawContext(tmp_path, 'https://old.example/api')
    original = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell('Preserved notes'),
            nbformat.v4.new_code_cell(source),
            nbformat.v4.new_code_cell('my_analysis = 42'),
        ]
    )
    with old_context.raw_file('old-template.ipynb', 'w') as file:
        nbformat.write(original, file)

    first_context = RawContext(tmp_path, 'https://first.example/api')
    first_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='first.archive.yaml', entry_id='first-id'),
        m_context=first_context,
    )
    first = SimpleNamespace(
        template=SimpleNamespace(
            m_context=old_context, template_notebook='old-template.ipynb'
        ),
        notebook=None,
    )
    DtuJupyterAnalysis.copy_from_template(first, first_archive, logger)
    with first_context.raw_file(first.notebook, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert_query_uses_context(
        monkeypatch, notebook.cells[1], 'first-id', first_context.installation_url
    )

    template_context = RawContext(tmp_path, 'https://template.example/api')
    template_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='next-template.archive.yaml'),
        m_context=template_context,
    )
    template = SimpleNamespace(
        from_analysis=SimpleNamespace(m_context=first_context, notebook=first.notebook),
        template_notebook=None,
    )
    template_path = DtuJupyterAnalysisTemplate.copy_from_analysis(
        template, template_archive, logger
    )
    with template_context.raw_file(template_path, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert notebook.cells[1].source == FIRST_CODE_CELL % (
        'THE_ANALYSIS_ID',
        template_context.installation_url,
    )

    second_context = RawContext(tmp_path, 'https://second.example/api')
    second_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='second.archive.yaml', entry_id='second-id'),
        m_context=second_context,
    )
    second = SimpleNamespace(
        template=SimpleNamespace(
            m_context=template_context, template_notebook=template_path
        ),
        notebook=None,
    )
    DtuJupyterAnalysis.copy_from_template(second, second_archive, logger)
    with second_context.raw_file(second.notebook, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert_query_uses_context(
        monkeypatch, notebook.cells[1], 'second-id', second_context.installation_url
    )
    assert notebook.cells[0].source == 'Preserved notes'
    assert notebook.cells[2].source == 'my_analysis = 42'


@pytest.mark.parametrize(
    'source',
    [
        *(cell % 'old-id' for cell in LEGACY_FIRST_CODE_CELLS),
        (LEGACY_FIRST_CODE_CELLS[0] % 'old-id').replace(
            'url=client.url,', "url='https://old.example/api',"
        ),
        (LEGACY_FIRST_CODE_CELLS[1] % 'old-id').replace(
            "url='https://nomad.nanolab.dtu.dk/nomad-oasis/api',#client.url,",
            "url='https://old.example/api',",
        ),
    ],
)
def test_legacy_notebook_to_template_to_notebook(tmp_path, monkeypatch, source):
    logger = SimpleNamespace(warn=pytest.fail)
    old_context = RawContext(tmp_path, 'https://old.example/api')
    original = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(source),
            nbformat.v4.new_code_cell('my_analysis = 42'),
        ]
    )
    with old_context.raw_file('old.ipynb', 'w') as file:
        nbformat.write(original, file)

    template_context = RawContext(tmp_path, 'https://template.example/api')
    template_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='template.archive.yaml'),
        m_context=template_context,
    )
    template = SimpleNamespace(
        from_analysis=SimpleNamespace(m_context=old_context, notebook='old.ipynb'),
        template_notebook=None,
    )
    template_path = DtuJupyterAnalysisTemplate.copy_from_analysis(
        template, template_archive, logger
    )
    with template_context.raw_file(template_path, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert notebook.cells[0].source == FIRST_CODE_CELL % (
        'THE_ANALYSIS_ID',
        template_context.installation_url,
    )

    target_context = RawContext(tmp_path, 'https://target.example/api')
    target_archive = SimpleNamespace(
        metadata=SimpleNamespace(mainfile='target.archive.yaml', entry_id='target-id'),
        m_context=target_context,
    )
    target = SimpleNamespace(
        template=SimpleNamespace(
            m_context=template_context, template_notebook=template_path
        ),
        notebook=None,
    )
    DtuJupyterAnalysis.copy_from_template(target, target_archive, logger)
    with target_context.raw_file(target.notebook, 'r') as file:
        notebook = nbformat.read(file, as_version=4)
    assert_query_uses_context(
        monkeypatch, notebook.cells[0], 'target-id', target_context.installation_url
    )
    assert notebook.cells[1].source == 'my_analysis = 42'
