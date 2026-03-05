import re
from typing import TYPE_CHECKING

from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
)
from nomad.metainfo import Package, Quantity, Section
from nomad_measurements.mapping.schema import (
    MappingMeasurement,
    RectangularSampleAlignment,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package()


class DtuNanolabMeasurement(MappingMeasurement):
    m_def = Section()

    around_barycenter = Quantity(
        type=bool,
        default=False,
        description=(
            'If checked, the sample alignment is automatically computed '
            'assuming the measurement map was performed around the center '
            'of the sample. Width and height are read from the referenced '
            'combinatorial library substrate geometry.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Center around barycenter',
        ),
    )

    def _get_sample_dimensions(
        self, logger: 'BoundLogger'
    ) -> tuple[float, float] | None:
        """Get width and height (in meters) from the referenced library geometry.

        Follows the chain: samples[0].reference -> geometry (or substrate geometry).

        Returns:
            (width_m, height_m) or None if dimensions cannot be determined.
        """
        if not self.samples:
            logger.warning('Cannot determine sample dimensions: no sample reference.')
            return None

        sample_ref = self.samples[0]
        library = getattr(sample_ref, 'reference', None)
        if library is None:
            logger.warning(
                'Cannot determine sample dimensions: sample reference not resolved.'
            )
            return None

        # Try library.geometry first, then substrate.reference.geometry
        geometry = getattr(library, 'geometry', None)
        if geometry is None:
            substrate_ref = getattr(library, 'substrate', None)
            if substrate_ref is not None:
                substrate = getattr(substrate_ref, 'reference', None)
                if substrate is not None:
                    geometry = getattr(substrate, 'geometry', None)

        if geometry is None:
            logger.warning(
                'Cannot determine sample dimensions: '
                'no geometry found on library or substrate.'
            )
            return None

        width = getattr(geometry, 'width', None)
        length = getattr(geometry, 'length', None)
        if width is None or length is None:
            logger.warning(
                'Cannot determine sample dimensions: '
                'geometry has no width or length.'
            )
            return None

        width_m = (
            width.to('m').magnitude if hasattr(width, 'to') else float(width)
        )
        height_m = (
            length.to('m').magnitude if hasattr(length, 'to') else float(length)
        )
        return width_m, height_m

    def _compute_alignment_from_barycenter(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        """Compute sample_alignment from the barycenter of measurement positions.

        Uses width/height from the library substrate geometry and centers the
        alignment on the bounding-box center of the actual measurement positions.
        """
        if not self.results:
            logger.warning(
                'Cannot center around barycenter: no results available.'
            )
            return

        dims = self._get_sample_dimensions(logger)
        if dims is None:
            return
        width_m, height_m = dims

        x_positions = []
        y_positions = []
        for result in self.results:
            if hasattr(result, 'x_absolute') and result.x_absolute is not None:
                x_val = (
                    result.x_absolute.to('m').magnitude
                    if hasattr(result.x_absolute, 'to')
                    else result.x_absolute
                )
                x_positions.append(x_val)
            if hasattr(result, 'y_absolute') and result.y_absolute is not None:
                y_val = (
                    result.y_absolute.to('m').magnitude
                    if hasattr(result.y_absolute, 'to')
                    else result.y_absolute
                )
                y_positions.append(y_val)

        if not x_positions or not y_positions:
            logger.warning(
                'Cannot center around barycenter: '
                'no valid x/y positions found in results.'
            )
            return

        x_center = (min(x_positions) + max(x_positions)) / 2
        y_center = (min(y_positions) + max(y_positions)) / 2

        alignment = RectangularSampleAlignment(
            width=width_m,
            height=height_m,
            x_upper_left=x_center - width_m / 2,
            y_upper_left=y_center + height_m / 2,
            x_lower_right=x_center + width_m / 2,
            y_lower_right=y_center - height_m / 2,
        )
        alignment.normalize(archive, logger)
        self.sample_alignment = alignment

        logger.info(
            'Auto-centered sample alignment around barycenter: '
            f'center=({x_center:.6f}, {y_center:.6f}) m, '
            f'width={width_m:.6f} m, height={height_m:.6f} m'
        )

        # Append flag to description
        flag = '[auto-centered around barycenter]'
        if not self.description:
            self.description = flag
        elif flag not in self.description:
            self.description = f'{self.description}\n{flag}'

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        if self.around_barycenter:
            self._compute_alignment_from_barycenter(archive, logger)
        super().normalize(archive, logger)

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
