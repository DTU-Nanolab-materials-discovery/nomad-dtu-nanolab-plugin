import re
from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
)
from nomad.metainfo import Package, Quantity, Section
from nomad_measurements.mapping.schema import MappingMeasurement, RectangularSampleAlignment

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package()


class DTUBaseSampleAlignment(RectangularSampleAlignment):
    """Base class for DTU sample alignment with common functionality.

    This base class provides common sample alignment properties and functionality
    for all DTU measurement types (Raman, XRD, Ellipsometry, EDX, etc.).

    Features:
        - Standard width and height properties with default values (40mm x 40mm)
        - "Center Around Zero" button to automatically calculate corner coordinates
          by analyzing actual measurement positions (x_absolute, y_absolute) from
          results and using the user-provided width/height centered on those positions,
          so the relative map is centered at (0,0)

    Inherited from RectangularSampleAlignment:
        - x_upper_left (float with unit): X-coordinate of upper-left corner
        - y_upper_left (float with unit): Y-coordinate of upper-left corner
        - x_lower_right (float with unit): X-coordinate of lower-right corner
        - y_lower_right (float with unit): Y-coordinate of lower-right corner
    """

    m_def = Section(
        description='The alignment of the sample on the stage.',
    )

    width = Quantity(
        type=np.float64,
        default=0.04,
        description='The width of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    height = Quantity(
        type=np.float64,
        default=0.04,
        description='The height of the sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )
    center_around_zero = Quantity(
        type=bool,
        default=False,
        description=(
            'Automatically calculate corner coordinates using user-provided width/height '
            'centered on the actual measurement positions (x_absolute, y_absolute from results) '
            'to center the relative map at (0,0).'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ActionEditQuantity,
            label='Center Around Zero',
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """Normalize the sample alignment information.

        If center_around_zero is triggered, calculates corner coordinates based on
        the actual measurement positions (x_absolute, y_absolute) from the results,
        using the user-provided width/height and centering them on the measurement
        bounding box so that relative positions will be centered at (0,0).

        Args:
            archive (EntryArchive): The archive containing the section being normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)

        if self.center_around_zero:
            # Get the parent measurement section to access results
            parent = self.m_parent
            if parent and hasattr(parent, 'results') and parent.results:
                # Extract all x_absolute and y_absolute positions
                x_positions = []
                y_positions = []
                
                for result in parent.results:
                    if hasattr(result, 'x_absolute') and result.x_absolute is not None:
                        # Convert to meters if it has a unit
                        x_val = result.x_absolute.to('m').magnitude if hasattr(result.x_absolute, 'to') else result.x_absolute
                        x_positions.append(x_val)
                    if hasattr(result, 'y_absolute') and result.y_absolute is not None:
                        # Convert to meters if it has a unit
                        y_val = result.y_absolute.to('m').magnitude if hasattr(result.y_absolute, 'to') else result.y_absolute
                        y_positions.append(y_val)
                
                if x_positions and y_positions:
                    # Calculate the center of the actual measurements
                    x_min = min(x_positions)
                    x_max = max(x_positions)
                    y_min = min(y_positions)
                    y_max = max(y_positions)
                    
                    x_center = (x_min + x_max) / 2
                    y_center = (y_min + y_max) / 2
                    
                    # Use user-provided width and height, centered on the measurement center
                    if self.width is not None and self.height is not None:
                        self.x_upper_left = x_center - self.width / 2
                        self.x_lower_right = x_center + self.width / 2
                        self.y_upper_left = y_center + self.height / 2
                        self.y_lower_right = y_center - self.height / 2
                        
                        logger.info(
                            f'Calculated corner coordinates: '
                            f'measurement center=({x_center:.6f}, {y_center:.6f}) m, '
                            f'width={self.width:.6f} m, height={self.height:.6f} m, '
                            f'corners: upper-left=({self.x_upper_left:.6f}, {self.y_upper_left:.6f}), '
                            f'lower-right=({self.x_lower_right:.6f}, {self.y_lower_right:.6f})'
                        )
                    else:
                        logger.warning(
                            'Cannot center around zero: width or height is not set.'
                        )
                else:
                    logger.warning(
                        'Cannot center around zero: no valid x/y positions found in results.'
                    )
            else:
                logger.warning(
                    'Cannot center around zero: no results found in parent measurement.'
                )
            
            self.center_around_zero = False


class DtuNanolabMeasurement(MappingMeasurement):
    def set_lab_id(
        self, lab_id: str, archive: 'EntryArchive', logger: 'BoundLogger'
    ) -> None:
        from nomad.search import MetadataPagination, search

        measurement_number = 1
        while measurement_number < 1000:  # noqa: PLR2004
            test = f'{lab_id}_{measurement_number:03d}'
            search_result = search(
                owner='all',
                query={'results.eln.lab_ids': test},
                pagination=MetadataPagination(page_size=1),
                user_id=archive.metadata.main_author.user_id,
            )
            if search_result.pagination.total == 0 or (
                search_result.pagination.total == 1
                and search_result.data[0]['entry_id'] == archive.metadata.entry_id
            ):
                self.lab_id = test
                return
            measurement_number += 1
        logger.warning(f'Could not find a unique lab_id for: {lab_id}')

    def add_sample_reference(
        self,
        filename: str,
        measurement_type: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        from nomad.datamodel.context import ServerContext

        # Define the regex pattern
        pattern = r'^(?P<lab_id>([^_]*_){3}[^_.]*)'
        # Match the pattern
        match = re.match(pattern, filename)
        if not match:
            logger.warning(f'Could not match lab_id in: {filename}')
            return
        sample_id = match.group('lab_id')
        sample_ref = CompositeSystemReference(lab_id=sample_id)
        lab_id = f'{sample_id}_{measurement_type}'
        if isinstance(archive.m_context, ServerContext):
            sample_ref.normalize(archive, logger)
            if self.lab_id is None:
                self.set_lab_id(lab_id, archive, logger)
        else:
            self.lab_id = lab_id
        self.samples = [sample_ref]


m_package.__init_metainfo__()
