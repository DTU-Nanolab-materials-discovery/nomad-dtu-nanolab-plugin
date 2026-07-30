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
import logging

import pytest
import structlog
from nomad.utils import structlogging
from structlog.testing import LogCapture

structlogging.ConsoleFormatter.short_format = True
setattr(logging, 'Formatter', structlogging.ConsoleFormatter)

DEFAULT_LOG_LEVELS = ('error', 'critical')


@pytest.fixture(name='caplog', scope='function')
def fixture_caplog():
    """
    Extracts log messages from the logger and raises an assertion error if the specified
    log levels in ('error', 'critical').
    """

    def format_record(record):
        renderer = structlog.processors.KeyValueRenderer(sort_keys=False)

        exception = record.pop('exception', None)
        rendered = renderer(None, None, record)  # render without exception

        if exception:
            rendered = f'{rendered}\nexception:\n{exception}'
            # escape chars in exeception are obeyed

        return rendered

    caplog = LogCapture()
    processors = structlog.get_config()['processors']
    old_processors = processors.copy()

    try:
        processors.clear()
        processors.append(structlog.processors.format_exc_info)
        processors.append(caplog)
        structlog.configure(processors=processors)
        yield caplog
        exceptions = []
        for record in caplog.entries:
            if record['log_level'] in DEFAULT_LOG_LEVELS:
                exceptions.append(record)
        if len(exceptions) > 0:
            formatted_exceptions = '\n\n'.join(
                format_record(record) for record in exceptions
            )
            assert False, (
                f'Found at least one normalization error:\n\n{formatted_exceptions}'
            )
    finally:
        processors.clear()
        processors.extend(old_processors)
        structlog.configure(processors=processors)
