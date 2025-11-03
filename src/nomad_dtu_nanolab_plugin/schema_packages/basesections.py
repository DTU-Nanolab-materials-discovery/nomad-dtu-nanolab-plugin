import re
from typing import TYPE_CHECKING

from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
)
from nomad.metainfo import Package
from nomad_measurements.mapping.schema import MappingMeasurement

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package()


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
