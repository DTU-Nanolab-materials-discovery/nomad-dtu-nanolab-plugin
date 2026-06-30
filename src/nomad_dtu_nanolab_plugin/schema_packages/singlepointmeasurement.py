from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.metainfo import Quantity, Section

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    pass


class SinglePointMeasurement(DtuNanolabMeasurement):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Single point measurement',
        properties=SectionProperties(
            order=[
                'technique',
                'raw_file',
            ],
            visible=Filter(
                exclude=['steps', 'methode', 'around_barycenter'],
            ),
        ),
    )
    technique = Quantity(
        type=str,
        description='The technique used for the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.TextEditQuantity),
    )
    extracted_value = Quantity(
        type=np.float64,
        description='The extracted value from the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    raw_file = Quantity(
        type=str,
        shape=['*'],
        description='The raw data file of the measurement.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
    )
