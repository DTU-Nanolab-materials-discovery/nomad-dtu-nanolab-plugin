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

from typing import TYPE_CHECKING, Any

import numpy as np
import plotly.graph_objects as go
from fairmat_readers_xrd import read_rigaku_rasx
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad_measurements.utils import merge_sections
from nomad_measurements.xrd.schema import (
    XRayDiffraction,
    XRayTubeSource,
    XRDResult1D,
    XRDSettings,
)
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    MappingMeasurement,
    MappingResult,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU XRD measurement schema')


class XRDMappingResult(MappingResult, XRDResult1D):
    m_def = Section()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `XRDMappingResult` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class DTUXRDMeasurement(XRayDiffraction, MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='XRD Measurement',
    )
    data_files = Quantity(
        type=str,
        shape=['*'],
        description='Data files containing the diffractograms',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
        ),
    )
    results = SubSection(
        section_def=XRDMappingResult,
        description='The XRD results.',
        repeats=True,
    )

    def plot(self) -> None:
        fig = go.Figure()
        result: XRDMappingResult
        for result in self.results:
            fig.add_trace(
                go.Scatter(
                    x=result.two_theta.to('deg').magnitude,
                    y=result.intensity.magnitude,
                    mode='lines',
                    name=(
                        f'({result.x_absolute.to("mm").magnitude:.1f}, '
                        f'{result.y_absolute.to("mm").magnitude:.1f})'
                    ),
                )
            )

        # Update layout
        fig.update_layout(
            title='XRD Patterns',
            xaxis_title='2<i>θ</i> / °',
            yaxis_title='Intensity',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
            ),
            yaxis=dict(
                fixedrange=False,
                type='log',
            ),
        )

        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
        )
        self.figures.append(
            PlotlyFigure(
                label='Patterns',
                figure=plot_json,
            )
        )

    def write_xrd_data(
        self,
        xrd_dicts: list[dict[str, Any]],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """
        Write method for populating the `ELNXRayDiffraction` section from a dict.

        Args:
            xrd_dict (Dict[str, Any]): A dictionary with the XRD data.
            archive (EntryArchive): The archive containing the section.
            logger (BoundLogger): A structlog logger.
        """
        results = []
        source_dict = {}
        for xrd_dict in xrd_dicts:
            metadata_dict: dict = xrd_dict.get('metadata', {})
            new_source_dict: dict = metadata_dict.get('source', {})
            if source_dict and source_dict != new_source_dict:
                logger.warning('Different sources in the same measurement')
            source_dict = new_source_dict

            scan_type = metadata_dict.get('scan_type', None)
            if scan_type != 'line':
                logger.error(f'Unsupported scan type: "{scan_type}"')
            result = XRDMappingResult(
                intensity=xrd_dict.get('intensity', None),
                two_theta=xrd_dict.get('2Theta', None),
                omega=xrd_dict.get('Omega', None),
                chi=xrd_dict.get('Chi', None),
                phi=xrd_dict.get('Phi', None),
                scan_axis=metadata_dict.get('scan_axis', None),
                integration_time=xrd_dict.get('countTime', None),
                x_absolute=xrd_dict.get('X', None)[0],
                y_absolute=xrd_dict.get('Y', None)[0],
            )
            result.normalize(archive, logger)
            results.append(result)

        source = XRayTubeSource(
            xray_tube_material=source_dict.get('anode_material', None),
            kalpha_one=source_dict.get('kAlpha1', None),
            kalpha_two=source_dict.get('kAlpha2', None),
            ratio_kalphatwo_kalphaone=source_dict.get('ratioKAlpha2KAlpha1', None),
            kbeta=source_dict.get('kBeta', None),
            xray_tube_voltage=source_dict.get('voltage', None),
            xray_tube_current=source_dict.get('current', None),
        )
        source.normalize(archive, logger)

        xrd_settings = XRDSettings(source=source)
        xrd_settings.normalize(archive, logger)

        samples = []

        xrd = DTUXRDMeasurement(
            results=results,
            xrd_settings=xrd_settings,
            samples=samples,
        )
        merge_sections(self, xrd, logger)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUXRDMeasurement` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.data_files:
            file_data = []
            for file_path in self.data_files:
                with archive.m_context.raw_file(file_path) as file:
                    file_data.append(read_rigaku_rasx(file.name, logger))
            self.write_xrd_data(file_data, archive, logger)
            self.figures = []
            self.plot()
        if self.sample_alignment:
            for result in self.results:
                if result.x_absolute is None or result.y_absolute is None:
                    continue
                x, y = self.sample_alignment.affine_transformation.transform_vector(
                    np.array(
                        [
                            result.x_absolute.to('m').magnitude,
                            result.y_absolute.to('m').magnitude,
                        ]
                    )
                )
                result.x_relative = x
                result.y_relative = y
                result.normalize(archive, logger)
        super().normalize(archive, logger)


m_package.__init_metainfo__()
