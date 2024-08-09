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

from typing import TYPE_CHECKING

import numpy as np
import pint
from nomad.datamodel.datamodel import ArchiveSection, EntryArchive
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import Measurement, MeasurementResult
from nomad.metainfo import Quantity, Section, SubSection
from structlog.stdlib import BoundLogger

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger


class MappingResult(MeasurementResult):
    """A class representing the result of a mapping measurement."""

    m_def = Section()
    x_relative = Quantity(
        type=np.float64,
        description="""
        The x position of the measurement relative to the center of mass of the whole
        sample.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_relative = Quantity(
        type=np.float64,
        description="""
        The y position of the measurement relative to the center of mass of the whole
        sample.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    x_absolute = Quantity(
        type=np.float64,
        description="""
        The absolute x position of the measurement in the coordinate system of the
        measurement stage.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_absolute = Quantity(
        type=np.float64,
        description="""
        The absolute y position of the measurement in the coordinate system of the
        measurement stage.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `MappingResult` class.
        Will set the name of the section to the relative position of the measurement in
        mm.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if isinstance(self.x_relative, pint.Quantity) and isinstance(
            self.y_relative, pint.Quantity
        ):
            self.name = (
                f'({self.x_relative.to("mm").magnitude:.1f}, '
                f'{self.y_relative.to("mm").magnitude:.1f})'
            )


class AffineTransformation(ArchiveSection):
    m_def = Section()
    v1_before = Quantity(
        type=np.float64,
        description='The v1 vector of the sample before the transformation.',
        shape=[2],
    )
    v2_before = Quantity(
        type=np.float64,
        description='The v2 vector of the sample before the transformation.',
        shape=[2],
    )
    v3_before = Quantity(
        type=np.float64,
        description='The v3 vector of the sample before the transformation.',
        shape=[2],
    )
    v1_after = Quantity(
        type=np.float64,
        description='The v1 vector of the sample after the transformation.',
        shape=[2],
    )
    v2_after = Quantity(
        type=np.float64,
        description='The v2 vector of the sample after the transformation.',
        shape=[2],
    )
    v3_after = Quantity(
        type=np.float64,
        description='The v3 vector of the sample after the transformation.',
        shape=[2],
    )
    transformation_matrix = Quantity(
        type=np.float64,
        description='The transformation matrix.',
        shape=[2, 2],
    )
    translation_vector = Quantity(
        type=np.float64,
        description='The translation vector.',
        shape=[2],
    )

    def calculate_affine_transformation(self) -> None:
        """
        Calculate the affine transformation matrix and translation vector from the
        sample alignment.
        """
        # Construct the matrix A and vector b for the system of equations
        a_matrix = np.array(
            [
                [self.v1_before[0], self.v1_before[1], 1, 0, 0, 0],
                [0, 0, 0, self.v1_before[0], self.v1_before[1], 1],
                [self.v2_before[0], self.v2_before[1], 1, 0, 0, 0],
                [0, 0, 0, self.v2_before[0], self.v2_before[1], 1],
                [self.v3_before[0], self.v3_before[1], 1, 0, 0, 0],
                [0, 0, 0, self.v3_before[0], self.v3_before[1], 1],
            ]
        )

        b_vector = np.array(
            [
                self.v1_after[0],
                self.v1_after[1],
                self.v2_after[0],
                self.v2_after[1],
                self.v3_after[0],
                self.v3_after[1],
            ]
        )

        # Solve for the transformation parameters
        params = np.linalg.solve(a_matrix, b_vector)

        # Extract the transformation matrix and translation vector
        self.transformation_matrix = np.array(
            [[params[0], params[1]], [params[3], params[4]]]
        )

        self.translation_vector = np.array([params[2], params[5]])

    def transform_vector(self, vector: np.ndarray) -> np.ndarray:
        """
        Apply the affine transformation to a vector.

        Args:
            vector (np.ndarray): The vector before the transformation.

        Returns:
            np.ndarray: The vector after the transformation.
        """
        return self.transformation_matrix @ vector + self.translation_vector


class SampleAlignment(ArchiveSection):
    """A class representing the alignment of a sample."""

    m_def = Section()
    affine_transformation = SubSection(
        section_def=AffineTransformation,
        description='The affine transformation of the sample.',
    )


class RectangularSampleAlignment(SampleAlignment):
    """A class representing the alignment of a rectangular sample."""

    m_def = Section()
    width = Quantity(
        type=np.float64,
        description='The width of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    height = Quantity(
        type=np.float64,
        description='The height of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    x_upper_left = Quantity(
        type=np.float64,
        description='The x position of the upper left corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_upper_left = Quantity(
        type=np.float64,
        description='The y position of the upper left corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    x_bottom_right = Quantity(
        type=np.float64,
        description='The x position of the bottom right corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    y_bottom_right = Quantity(
        type=np.float64,
        description='The y position of the bottom right corner of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )

    def calculate_bottom_left(self) -> np.ndarray:
        """
        Calculate the position of the bottom left corner of the sample.

        Returns:
            np.ndarray: The position of the bottom left corner of the sample.
        """
        if None in (
            self.width,
            self.height,
            self.x_upper_left,
            self.y_upper_left,
            self.x_bottom_right,
            self.y_bottom_right,
        ):
            return None
        a = np.array([self.x_upper_left, self.y_upper_left])
        b = np.array([self.x_bottom_right, self.y_bottom_right])
        ab = b - a
        d = np.linalg.norm(ab)
        dy = self.height * (ab[0] * self.width - ab[1] * self.height) / d**2
        dx = self.height * (ab[1] * self.width + ab[0] * self.height) / d**2
        return a + np.array([dx, -dy])

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RectangularSampleAlignment` class.
        Will calculate the affine transformation from the sample alignment.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.affine_transformation is None:
            t = AffineTransformation(
                v1_before=np.array([self.x_upper_left, self.y_upper_left]),
                v2_before=self.calculate_bottom_left(),
                v3_before=np.array([self.x_bottom_right, self.y_bottom_right]),
                v1_after=np.array([-self.width / 2, self.height / 2]),
                v2_after=np.array([-self.width / 2, -self.height / 2]),
                v3_after=np.array([self.width / 2, -self.height / 2]),
            )
            t.calculate_affine_transformation()
            self.affine_transformation = t

        super().normalize(archive, logger)


class MappingMeasurement(Measurement):
    """A class representing a mapping measurement."""

    m_def = Section()
    sample_alignment = SubSection(
        section_def=SampleAlignment,
        description='The alignment of the sample.',
    )
    results = SubSection(
        section_def=MappingResult,
        repeats=True,
    )
