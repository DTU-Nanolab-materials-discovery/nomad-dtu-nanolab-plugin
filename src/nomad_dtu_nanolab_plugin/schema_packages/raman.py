import re
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from ase.data import chemical_symbols
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from nomad_measurements.utils import merge_sections
from scipy.interpolate import griddata

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU EDX measurement schema')






class RamanResult(MappingResult):
    m_def = Section()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        the results section of the RT measurement.
        """
        super().normalize(archive, logger)
        # TODO: Add code for calculating the relative positions of the measurements.
 


class DTUSampleAlignment(RectangularSampleAlignment):
    m_def = Section(
        description='The alignment of the sample on the stage.',
    )




class RamanMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Raman Measurement',
    )
    raman_data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'Raman file'},
    )
    
    results = SubSection(
        section_def=RamanResult,
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=DTUSampleAlignment,
        description='The alignment of the sample.',
    )

    def plot(self) -> None:
        """
        add a plot of the RT results.
        """
        pass
        
        

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTMeasurement` class.
        """

        if self.location is None:
            self.location = 'DTU Nanolab RT Measurement'

        super().normalize(archive, logger)

        self.figures = []
        if len(self.results) > 0:
            self.plot()


m_package.__init_metainfo__()
