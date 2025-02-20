#
# Copyright The NOMAD Authors.
#
# This file is part of NOMAD. See https://nomad-lab.eu for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import re
from typing import TYPE_CHECKING

import nbformat
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    ActivityStep,
    Analysis,
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.metainfo.metainfo import Reference, SectionProxy
from nomad_analysis.utils import create_entry_with_api
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


FIRST_CODE_CELL = """from nomad.client import ArchiveQuery
from nomad.config import client

analysis_id = "%s"
a_query = ArchiveQuery(
    query={'entry_id:any': [analysis_id]},
    required='*',
    url=client.url,
)
entry_list = a_query.download()
analysis = entry_list[0].data"""

def replace_analysis_id(
        notebook: nbformat.notebooknode.NotebookNode,
        analysis_id: str) -> nbformat.notebooknode.NotebookNode|None:
    first_cell_pattern = re.compile(
        re.escape(FIRST_CODE_CELL.strip()).replace('%s', '(.*)')
    )
    for cell in notebook.cells:
        if cell.cell_type == 'code':
            match = first_cell_pattern.match(cell.source)
            if match:
                cell.source = FIRST_CODE_CELL % analysis_id
                return notebook
    return


m_package = Package()


class DtuJupyterAnalysisTemplate(Analysis, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Jupyter Analysis Template',
    )
    template_notebook = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
        a_browser=BrowserAnnotation(adaptor=BrowserAdaptors.RawFileAdaptor),
    )
    from_analysis = Quantity(
        type=Reference(SectionProxy('DtuJupyterAnalysis')),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    generate_notebook = Quantity(
        type=bool,
        description='Generate a Jupyter notebook',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
        ),
    )

    def copy_from_analysis(self, archive: 'EntryArchive', logger: 'BoundLogger') -> str:
        context = self.from_analysis.m_context
        with context.raw_file(self.from_analysis.notebook, 'r') as src_file:
            source_notebook = nbformat.read(src_file, as_version=4)

        template_notebook = replace_analysis_id(source_notebook, 'THE_ANALYSIS_ID')
        if template_notebook is None:
            logger.error('Standard Analysis query block is not found in the notebook.')
            return self.template_notebook
        
        new_notebook_path = archive.metadata.mainfile.split('.')[0] + '.ipynb'
        if archive.m_context.raw_path_exists(new_notebook_path):
            logger.error(f'Notebook {new_notebook_path} already exists.')
            return self.template_notebook
        
        with archive.m_context.raw_file(new_notebook_path, 'w') as dest_file:
            nbformat.write(template_notebook, dest_file)

        return new_notebook_path

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        if (
            self.generate_notebook 
            and self.from_analysis 
            and self.from_analysis.notebook
        ):
            self.template_notebook = self.copy_from_analysis(archive, logger)
            self.generate_notebook = False


class DtuAnalysisStep(ActivityStep, PlotSection):
    pass


class DtuJupyterAnalysis(Analysis, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Jupyter Analysis',
    )
    template = Quantity(
        type=DtuJupyterAnalysisTemplate,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    notebook = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
        a_browser=BrowserAnnotation(adaptor=BrowserAdaptors.RawFileAdaptor),
    )
    generate_notebook = Quantity(
        type=bool,
        description='Generate a Jupyter notebook',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
        ),
    )
    libraries = Quantity(
        type=DTUCombinatorialLibrary,
        shape=['*'],
        description='Libraries used in the analysis.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )
    steps = SubSection(
        section_def=DtuAnalysisStep,
        repeats=True,
    )

    def create_notebook(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        filename = archive.metadata.mainfile.split('.')[0] + '.ipynb'
        if archive.m_context.raw_path_exists(filename):
            logger.error(f'Notebook {filename} already exists.')
            return
        self.notebook = filename
        user = 'Unknown user'
        if archive.metadata.main_author:
            user = archive.metadata.main_author.name

        nb = nbformat.v4.new_notebook()

        nb.cells.extend(
            [
                nbformat.v4.new_markdown_cell(
                    source=f"""<div style="
    background-color: #f7f7f7;
    background-image: url('data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjxzdmcKICAgd2lkdGg9IjcyIgogICBoZWlnaHQ9IjczIgogICB2aWV3Qm94PSIwIDAgNzIgNzMiCiAgIGZpbGw9Im5vbmUiCiAgIHZlcnNpb249IjEuMSIKICAgaWQ9InN2ZzEzMTkiCiAgIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyIKICAgeG1sbnM6c3ZnPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CiAgPGRlZnMKICAgICBpZD0iZGVmczEzMjMiIC8+CiAgPHBhdGgKICAgICBkPSJNIC0wLjQ5OTk4NSwxNDUgQyAzOS41MzMsMTQ1IDcyLDExMi41MzIgNzIsNzIuNSA3MiwzMi40Njc4IDM5LjUzMywwIC0wLjQ5OTk4NSwwIC00MC41MzI5LDAgLTczLDMyLjQ2NzggLTczLDcyLjUgYyAwLDQwLjAzMiAzMi40NjcxLDcyLjUgNzIuNTAwMDE1LDcyLjUgeiIKICAgICBmaWxsPSIjMDA4YTY3IgogICAgIGZpbGwtb3BhY2l0eT0iMC4yNSIKICAgICBpZD0icGF0aDEzMTciIC8+Cjwvc3ZnPgo='), url('data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0iVVRGLTgiIHN0YW5kYWxvbmU9Im5vIj8+CjxzdmcKICAgd2lkdGg9IjIxNyIKICAgaGVpZ2h0PSIyMjMiCiAgIHZpZXdCb3g9IjAgMCAyMTcgMjIzIgogICBmaWxsPSJub25lIgogICB2ZXJzaW9uPSIxLjEiCiAgIGlkPSJzdmcxMTA3IgogICB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciCiAgIHhtbG5zOnN2Zz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxkZWZzCiAgICAgaWQ9ImRlZnMxMTExIiAvPgogIDxwYXRoCiAgICAgZD0ibSAyMi4wNDIsNDUuMDEwOSBjIDIxLjM2MjUsMjEuMjc1NyA1NS45NzYsMjEuMjc1NyA3Ny41MTkyLDAgQyAxMTkuNTU4LDI1LjA4IDE1MS41MDIsMjMuNzM1MiAxNzIuODY0LDQxLjM3OCBjIDEuMzQ1LDEuNTI1NCAyLjY5LDMuMjUxNiA0LjIzNiw0Ljc5NzEgMjEuMzYzLDIxLjI3NTYgMjEuMzYzLDU1Ljc5ODkgMCw3Ny4yNTQ5IC0yMS4zNjIsMjEuMjc2IC0yMS4zNjIsNTUuNzk4IDAsNzcuMjU1IDIxLjM2MywyMS40NTYgNTUuOTc2LDIxLjI3NSA3Ny41MiwwIDIxLjU0MywtMjEuMjc2IDIxLjM2MiwtNTUuNzk5IDAsLTc3LjI1NSAtMjEuMzYzLC0yMS4yNzYgLTIxLjM2MywtNTUuNzk4NiAwLC03Ny4yNTQ5IDEyLjY4OSwtMTIuNjQ1IDE3Ljg4OSwtMzAuMTA3MSAxNS4zOTksLTQ2LjU4NTc2IC0xLjU0NiwtMTEuNTAwOTQgLTYuNzI2LC0yMi44MjExNCAtMTUuNTgsLTMxLjYzMjU0IC0yMS4zNjMsLTIxLjI3NTYgLTU1Ljk3NiwtMjEuMjc1NiAtNzcuNTE5LDAgLTIxLjM2MywyMS4yNzU3IC01NS45NzYsMjEuMjc1NyAtNzcuNTE5NCwwIC0yMS4zNjI1LC0yMS4yNzU2IC01NS45NzYxLC0yMS4yNzU2IC03Ny41MTkyLDAgQyAwLjY3OTU2NSwtMTAuNzg3NiAwLjY3OTU5NiwyMy43MzUyIDIyLjA0Miw0NS4wMTA5IFoiCiAgICAgZmlsbD0iIzJhNGNkZiIKICAgICBzdHJva2U9IiMyYTRjZGYiCiAgICAgc3Ryb2tlLXdpZHRoPSIxMiIKICAgICBzdHJva2UtbWl0ZXJsaW1pdD0iMTAiCiAgICAgaWQ9InBhdGgxMTA1IiAvPgogIDxwYXRoCiAgICAgZD0ibSA1MS45OTUyMTIsMjIyLjczMDEzIGMgMjguMzU5MSwwIDUxLjM1ODM5OCwtMjIuOTk5OSA1MS4zNTgzOTgsLTUxLjM1ODQgMCwtMjguMzU4NiAtMjIuOTk5Mjk4LC01MS4zNTg1OSAtNTEuMzU4Mzk4LC01MS4zNTg1OSAtMjguMzU5MSwwIC01MS4zNTg2MDIsMjIuOTk5OTkgLTUxLjM1ODYwMiw1MS4zNTg1OSAwLDI4LjM1ODUgMjIuOTk5NTAyLDUxLjM1ODQgNTEuMzU4NjAyLDUxLjM1ODQgeiIKICAgICBmaWxsPSIjMTkyZTg2IgogICAgIGZpbGwtb3BhY2l0eT0iMC4zNSIKICAgICBpZD0icGF0aDE5MzciIC8+Cjwvc3ZnPgo=') ;
    background-position: left bottom, right top;
    background-repeat: no-repeat,  no-repeat;
    background-size: auto 60px, auto 160px;
    border-radius: 5px;
    box-shadow: 0px 3px 1px -2px rgba(0, 0, 0, 0.2), 0px 2px 2px 0px rgba(0, 0, 0, 0.14), 0px 1px 5px 0px rgba(0,0,0,.12);">

<h1 style="
    color: #2a4cdf;
    font-style: normal;
    font-size: 2.25rem;
    line-height: 1.4em;
    font-weight: 600;
    padding: 30px 200px 0px 30px;"> 
        {self.name}</h1>
<p style="font-size: 1.25em; font-style: italic; padding: 5px 200px 30px 30px;">
    {user}</p>
</div>"""  # noqa: E501
                ),
                nbformat.v4.new_markdown_cell(source='### Import data from NOMAD'),
                nbformat.v4.new_markdown_cell(
                    source='Query for the analysis entry associated with this notebook:'
                ),
                nbformat.v4.new_code_cell(
                    source=FIRST_CODE_CELL % archive.metadata.entry_id
                ),
                nbformat.v4.new_markdown_cell(source='### Analysis'),
                nbformat.v4.new_markdown_cell(
                    source="""Add your analysis code here.
You can use the `analysis` variable to access the data.
You can add figures and steps to the `analysis` variable and save them by calling 
`analysis.save()`.

The steps and figures from any previous runs will already be in the `analysis` variable.
If you want to start over, you can clear the steps and figures by calling:
"""
                ),
                nbformat.v4.new_code_cell(
                    source="""analysis.steps = []
analysis.figures = []"""
                ),
                nbformat.v4.new_markdown_cell(
                    source="""For example, you can add a step with a plot like this:"""
                ),
                nbformat.v4.new_code_cell(
                    source="""import datetime
import plotly.graph_objects as go
from nomad.datamodel.metainfo.plot import PlotlyFigure
from nomad_dtu_nanolab_plugin.schema_packages.analysis import DtuAnalysisStep

fig = go.Figure()
fig.add_trace(go.Scatter(x=[1, 2, 3], y=[4, 1, 2]))

plot_json = fig.to_plotly_json()
plot_json['config'] = dict(
    scrollZoom=False,
)

analysis.steps.append(
    DtuAnalysisStep(
        name='Step name',
        start_time=datetime.datetime.now(),
        comment='Description of the step',
        figures=[PlotlyFigure(
            label='My plot',
            figure=plot_json,
        )],
    )
)

analysis.save()"""
                ),
            ]
        )

        nb['metadata']['trusted'] = True

        with archive.m_context.raw_file(self.notebook, 'w') as nb_file:
            nbformat.write(nb, nb_file)
        archive.m_context.process_updated_raw_file(self.notebook, allow_modify=True)

    def copy_from_template(self, archive: 'EntryArchive', logger: 'BoundLogger') -> str:
        context = self.template.m_context
        with context.raw_file(self.template.template_notebook, 'r') as src_file:
            source_notebook = nbformat.read(src_file, as_version=4)

        template_notebook = replace_analysis_id(
            source_notebook, archive.metadata.entry_id)
        if template_notebook is None:
            logger.error('Standard Analysis query block is not found in the notebook.')
            return
        
        new_notebook_path = archive.metadata.mainfile.split('.')[0] + '.ipynb'
        if archive.m_context.raw_path_exists(new_notebook_path):
            logger.error(f'Notebook {new_notebook_path} already exists.')
            return
        
        with archive.m_context.raw_file(new_notebook_path, 'w') as dest_file:
            nbformat.write(template_notebook, dest_file)

        self.notebook = new_notebook_path

    def save(self):
        archive = self.m_parent
        create_entry_with_api(
            section=self,
            base_url=archive.m_context.installation_url,
            upload_id=archive.metadata.upload_id,
            file_name=archive.metadata.mainfile,
        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        if self.generate_notebook:
            if self.template and self.template.template_notebook:
                self.copy_from_template(archive, logger)
            else:
                self.create_notebook(archive, logger)
            self.generate_notebook = False
