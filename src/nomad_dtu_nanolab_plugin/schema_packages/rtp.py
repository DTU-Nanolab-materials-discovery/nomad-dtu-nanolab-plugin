import logging
import re
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAdaptors,
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.datamodel.results import Material, Results
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_material_processing.general import (
    ThinFilm,
    ThinFilmReference,
)
from nomad_material_processing.vapor_deposition.cvd.general import (
    ChemicalVaporDeposition,
    CVDSource,
    CVDStep,
)
from nomad_measurements.utils import create_archive

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.rtp_log_reader import parse_rtp_logfiles
from nomad_dtu_nanolab_plugin.schema_packages.sample import (
    DTUCombinatorialLibrary,
    DtuLibraryReference,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

    from nomad_dtu_nanolab_plugin.schema_packages import RTPEntryPoint

from nomad.config import config

configuration: 'RTPEntryPoint' = config.get_plugin_entry_point(
    'nomad_dtu_nanolab_plugin.schema_packages:rtp'
)

m_package = Package(name='DTU RTP schema')
logger = logging.getLogger(__name__)

# volume fraction in the respective gas mixture (the complementary gas is Ar)
RTP_GAS_FRACTION = {
    'Ar': 1,
    'N2': 1,
    'PH3': 0.1,
    'NH3': 0.1,
    'H2S': 0.1,
}
# How far past the detected end-of-process point the temperature/gas/pressure
# plots are extended, so the cooldown tail is visible instead of cutting off
# exactly at the moment gas flow stops.
POST_END_PROCESS_WINDOW_S = 30.0
# Flows below this are treated as "off" when scanning for gas shutoff timing
# (handles sensor noise/baseline drift rather than requiring an exact zero).
MIN_USED_GAS_FLOW_SCCM = 1.0
# Conversion factor: 1 torr = 133.322368421 pascals.
TORR_TO_PA = 133.322368421
# Conversion factor: 1 sccm (standard cm^3/min) = 1e-6 m^3 / 60 s.
SCCM_TO_M3_S = 1e-6 / 60
# Offset to convert between Celsius and Kelvin (0 °C = 273.15 K).
CELSIUS_TO_KELVIN_OFFSET = 273.15


def _warn_once(obj, key: str, logger, message: str) -> None:
    """Emit a warning only once per object instance for a given key."""
    if getattr(obj, key, False):
        return
    logger.warning(message)
    setattr(obj, key, True)


def _to_seconds(value) -> float:
    if hasattr(value, 'to'):
        return float(value.to('s').magnitude)
    return float(getattr(value, 'magnitude', value))


def _sanitize_log_path_value(path_value: str) -> str:
    """Strip quoting/whitespace and normalize path separators to '/'."""
    raw = str(path_value).strip().strip('"').strip("'")
    raw = raw.replace('\r', '/').replace('\n', '/').replace('\t', '/')
    return raw.replace('\\', '/')


def _candidate_log_paths(path_value: str) -> list[str]:
    """Return unique, plausible raw-file paths in lookup order."""
    normalized = _sanitize_log_path_value(path_value)
    candidates = [normalized]
    if normalized.startswith('./'):
        candidates.append(normalized[2:])
    if normalized.startswith('/'):
        candidates.append(normalized.lstrip('/'))
    if '/raw/' in normalized:
        candidates.append(normalized.split('/raw/', 1)[1])
    if normalized.startswith('raw/'):
        candidates.append(normalized[4:])

    filename = normalized.rsplit('/', 1)[-1]
    if filename:
        candidates.append(filename)
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _get_log_path_base_dirs() -> list[Path]:
    """Return project and processing roots used for filesystem fallbacks."""
    package_root = Path(__file__).resolve()
    return [
        Path.cwd(),
        package_root.parents[5],
        package_root.parents[4],
        package_root.parents[3],
        package_root.parents[4] / 'nomad-FAIR',
    ]


def _resolve_raw_log_path(
    archive, path_value: str
) -> tuple[str | None, Exception | None]:
    last_exc = None
    for candidate in _candidate_log_paths(path_value):
        try:
            with archive.m_context.raw_file(candidate, 'r'):
                return candidate, None
        except Exception as exc:
            last_exc = exc
    return None, last_exc


def _resolve_filesystem_log_path(path_value: str, base_dirs: list[Path]) -> str | None:
    candidates = _candidate_log_paths(path_value)
    candidates.insert(0, _sanitize_log_path_value(path_value))
    for candidate in candidates:
        try:
            path = Path(candidate)
            if path.is_file():
                return str(path)
            if path.is_absolute():
                continue
            for base in base_dirs:
                resolved = (base / path).resolve()
                if resolved.is_file():
                    return str(resolved)
        except Exception:
            continue
    return None


def _find_staged_log_path(filename: str, base_dirs: list[Path]) -> str | None:
    for base in base_dirs:
        try:
            staging_root = (base / '.volumes' / 'fs' / 'staging').resolve()
            if not staging_root.exists():
                continue
            for hit in staging_root.rglob(filename):
                if hit.is_file() and 'raw' in hit.parts:
                    return str(hit)
        except Exception:
            continue
    for base in base_dirs:
        try:
            fs_root = (base / '.volumes' / 'fs').resolve()
            if not fs_root.exists():
                continue
            for hit in fs_root.rglob(filename):
                if hit.is_file():
                    return str(hit)
        except Exception:
            continue
    return None


def _find_log_path_by_extension(
    expected_suffix: str, base_dirs: list[Path]
) -> str | None:
    suffix = expected_suffix.lower().lstrip('.')
    for base in base_dirs:
        try:
            fs_root = (base / '.volumes' / 'fs').resolve()
            if not fs_root.exists():
                continue
            candidates = [
                hit
                for hit in fs_root.rglob(f'*.{suffix}')
                if hit.is_file() and 'raw' in hit.parts
            ]
            if not candidates:
                continue
            if suffix == 'csv':
                preferred = [
                    path
                    for path in candidates
                    if 'recording set' in path.name.lower()
                    or '_rtp_' in path.name.lower()
                ]
            else:
                preferred = [
                    path
                    for path in candidates
                    if 'logfile' in path.name.lower() or '_rtp_' in path.name.lower()
                ]
            newest = max(preferred or candidates, key=lambda path: path.stat().st_mtime)
            return str(newest)
        except Exception:
            continue
    return None


def _resolve_log_input_path(
    archive, path_value: str, expected_suffix: str
) -> tuple[str, str]:
    """Resolve a saved log reference to NOMAD raw storage or a filesystem path."""
    raw_path, last_exc = _resolve_raw_log_path(archive, path_value)
    if raw_path is not None:
        return 'raw', raw_path

    base_dirs = _get_log_path_base_dirs()
    filesystem_path = _resolve_filesystem_log_path(path_value, base_dirs)
    if filesystem_path is not None:
        return 'fs', filesystem_path

    filename = _sanitize_log_path_value(path_value).rsplit('/', 1)[-1]
    if filename:
        staged_path = _find_staged_log_path(filename, base_dirs)
        if staged_path is not None:
            return 'fs', staged_path
    extension_path = _find_log_path_by_extension(expected_suffix, base_dirs)
    if extension_path is not None:
        return 'fs', extension_path
    if last_exc is not None:
        raise last_exc
    raise FileNotFoundError(path_value)


def _parse_resolved_log_files(
    archive,
    logger,
    eklipse_ref: tuple[str, str],
    diagnostics_refs: list[tuple[str, str]],
):
    """Materialize raw-file references while parsing all resolved log files."""
    eklipse_kind, eklipse_path = eklipse_ref
    with ExitStack() as stack:

        def materialize_raw_to_temp(raw_ref: str, suffix: str) -> str:
            raw_handle = stack.enter_context(archive.m_context.raw_file(raw_ref, 'r'))
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                delete=False,
                suffix=suffix,
                newline='',
            )
            try:
                temp_file.write(raw_handle.read())
            finally:
                temp_file.close()
            stack.callback(lambda p=temp_file.name: Path(p).unlink(missing_ok=True))
            return temp_file.name

        if eklipse_kind == 'raw':
            suffix = '.csv' if eklipse_path.lower().endswith('.csv') else '.txt'
            eklipse_path = materialize_raw_to_temp(eklipse_path, suffix)

        diagnostics_paths = []
        for kind, raw_reference in diagnostics_refs:
            reference = raw_reference
            if kind == 'raw':
                suffix = '.txt' if reference.lower().endswith('.txt') else '.csv'
                reference = materialize_raw_to_temp(reference, suffix)
            diagnostics_paths.append(reference)

        return parse_rtp_logfiles(
            eklipse_csv_path=eklipse_path,
            cx_thermo_diagnostics_txt_paths=diagnostics_paths,
            logger=logger,
        )


#################### DEFINE INPUT_SAMPLES (SUBSECTION) ######################
class DtuRTPInputSampleMounting(ArchiveSection):
    """
    Section containing information about the mounting of the combinatiorial libraries
    (input samples) on the susceptor.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'input_combi_lib',
                    'relative_position',
                    'position_x',
                    'position_y',
                    'rotation',
                ],
            )
        ),
    )
    name = Quantity(
        type=str,
        description='The name of the input sample.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    input_combi_lib = Quantity(
        type=DTUCombinatorialLibrary,
        description='The input sample (combinatorial library) that is used.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.ReferenceEditQuantity,
        ),
    )

    relative_position = Quantity(
        type=str,
        description='The relative position of the input sample on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(
                suggestions=[
                    'bl',
                    'br',
                    'fl',
                    'fr',
                    'm',
                    'ha',
                    'hb',
                    'hc',
                    'hd',
                    'va',
                    'vb',
                    'vc',
                    'vd',
                ]
            ),
        ),
    )
    position_x = Quantity(
        type=np.float64,
        description='The center x-coordinate of the input sample on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    position_y = Quantity(
        type=np.float64,
        description='The center y-coordinate of the input sample on the susceptor.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    rotation = Quantity(
        type=np.float64,
        description="""
            MANUAL INPUT. The angle between the initial position in the "mother" sample
            and the position on the susceptor.
        """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuRTPInputSampleMounting` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        if self.position_x is None or self.position_y is None:
            # Hardcoded susceptor layout (in meters): predefined mounting
            # slots, named by their position. 'bl'/'br'/'fl'/'fr'/'m' are the
            # five square slots (back-left, back-right, front-left,
            # front-right, middle); 'ha'-'hd' are horizontal-rectangle slots
            # and 'va'-'vd' are vertical-rectangle slots, ordered from one
            # edge of the susceptor to the other.
            positions = {
                'bl': (-0.0125, 0.0125),
                'br': (0.0125, 0.0125),
                'fl': (-0.0125, -0.0125),
                'fr': (0.0125, -0.0125),
                'm': (0, 0),
                'ha': (0, 0.015),
                'hb': (0, 0.005),
                'hc': (0, -0.005),
                'hd': (0, -0.015),
                'va': (-0.015, 0),
                'vb': (-0.005, 0),
                'vc': (0.005, 0),
                'vd': (0.015, 0),
            }
            if self.relative_position in positions:
                self.position_x, self.position_y = positions[self.relative_position]
            elif self.position_x is None or self.position_y is None:
                logger.warning(
                    f'Sample mounting position coordinates could not be determined '
                    f'(relative_position={self.relative_position} not recognized, '
                    f'position_x={self.position_x}, position_y={self.position_y})'
                )

        if self.relative_position is not None:
            self.name = self.relative_position
        elif self.position_x is not None and self.position_y is not None:
            # Fall back to a coordinate-based name when no relative_position
            # is set. The decimal point is replaced with 'p' since '.' is not
            # a safe character in lab IDs/filenames (e.g. "x1.2y-0.5" ->
            # "x1p2yp0p5").
            self.name = (
                f'x{self.position_x.to("cm").magnitude:.1f}'
                f'y{self.position_y.to("cm").magnitude:.1f}'
            ).replace('.', 'p')


#################### HUMAN READABLE OVERVIEW (SUBSECTION) ######################
class RTPOverview(ArchiveSection):
    """
    Section containing a human readable overview of the RTP process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'material_space',
                    'no_dwell_steps',
                    'annealing_temperature',
                    'total_heating_time',
                    'annealing_time',
                    'total_cooling_time',
                    'annealing_pressure',
                    'annealing_ar_flow',
                    'annealing_n2_flow',
                    'annealing_ph3_in_ar_flow',
                    'annealing_nh3_in_ar_flow',
                    'annealing_h2s_in_ar_flow',
                    'end_of_process_temperature',
                    'annealing_h2s_partial_pressure',
                    'annealing_ph3_partial_pressure',
                    'annealing_nh3_partial_pressure',
                    'annealing_n2_partial_pressure',
                    'annealing_ar_partial_pressure',
                ],
            )
        ),
    )
    material_space = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Material space',
        ),
        description='The elements present in your film before and/or after '
        'the RTP process.',
    )
    no_dwell_steps = Quantity(
        type=int,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Number of dwell steps',
        ),
        description='Number of dwell steps (plateaus) in the RTP process.',
    )
    annealing_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='torr',
            label='Annealing Pressure',
        ),
        unit='Pa',
        description='Pressure (average) in the RTP chamber during the annealing '
        'plateau',
    )
    annealing_time = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Annealing Time',
        ),
        unit='s',
        description='Time spent at the annealing plateau of the RTP process.',
    )
    annealing_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='Annealing Temperature',
        ),
        unit='K',
        description=(
            'Temperature (average) during the annealing plateau of the RTP process.'
        ),
    )
    annealing_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Annealing Ar Flow',
        ),
        unit='m**3/s',
        description='Argon flow (average) used during the annealing plateau of the'
        ' RTP process. The unit "cm^3/minute" is used and equal to sccm.',
    )
    annealing_n2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Annealing N2 Flow',
        ),
        unit='m**3/s',
        description='Nitrogen flow (average) used during the annealing plateau of the'
        ' RTP process. The unit "cm^3/minute" is used and equal to sccm.',
    )
    annealing_ph3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Annealing PH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Phosphine flow (average) used during the annealing plateau of'
        ' the RTP process. The unit "cm^3/minute" is used and equal to sccm.',
    )
    annealing_nh3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Annealing NH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Ammonia flow (average) used during the annealing plateau of'
        ' the RTP process. The unit "cm^3/minute" is used and equal to sccm.',
    )
    annealing_h2s_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Annealing H2S in Ar Flow',
        ),
        unit='m**3/s',
        description='H2S flow (average) used during the annealing plateau of the'
        ' RTP process. The unit "cm^3/minute" is used and equal to sccm.',
    )
    total_heating_time = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Total heating up time',
        ),
        unit='s',
        description='Total time spent until maximum temperature '
        '(main annealing plateau) is reached.',
    )
    total_cooling_time = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Total cooling down time',
        ),
        unit='s',
        description='Total time spent between the end of the main annealing plateau '
        'until the samples are cooled down to room temperature.',
    )
    end_of_process_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='End of process temperature',
        ),
        unit='K',
        description='Temperature during the cooling phase of the RTP process '
        'at which gas flows are shut off and the final pump-purge procedure '
        'is initiated before removing the samples from the chamber.',
    )
    annealing_ph3_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Annealing PH3 Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure of PH3 (average) during the annealing plateau '
            'of the RTP process.'
        ),
    )
    annealing_nh3_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Annealing NH3 Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure of NH3 (average) during the annealing plateau '
            'of the RTP process.'
        ),
    )
    annealing_h2s_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Annealing H2S Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure of H2S (average) during the annealing plateau '
            'of the RTP process.'
        ),
    )
    annealing_n2_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Annealing N2 Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure of N2 (average) during the annealing plateau '
            'of the RTP process.'
        ),
    )
    annealing_ar_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Annealing Ar Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure of Ar (average) during the annealing plateau '
            'of the RTP process.'
        ),
    )

    def calc_partial_pressure(self):
        """
        Convert the annealing gas flows into partial pressures using Dalton's
        law: each gas's partial pressure equals its mole fraction of the
        total flow, multiplied by the total chamber pressure.

        PH3, NH3, and H2S are delivered pre-diluted in Ar (see
        RTP_GAS_FRACTION), so only RTP_GAS_FRACTION of their flow is the
        active gas; the remainder is carrier Ar. The Ar partial pressure
        therefore accounts for both the dedicated Ar line and the Ar
        carrier fraction of every diluted gas line (the "(1 - fraction)"
        terms below).
        """
        annealing_ar_flow = (
            self.annealing_ar_flow.magnitude
            if self.annealing_ar_flow is not None
            else 0
        )
        annealing_n2_flow = (
            self.annealing_n2_flow.magnitude
            if self.annealing_n2_flow is not None
            else 0
        )
        annealing_nh3_in_ar_flow = (
            self.annealing_nh3_in_ar_flow.magnitude
            if self.annealing_nh3_in_ar_flow is not None
            else 0
        )
        annealing_h2s_in_ar_flow = (
            self.annealing_h2s_in_ar_flow.magnitude
            if self.annealing_h2s_in_ar_flow is not None
            else 0
        )
        annealing_ph3_in_ar_flow = (
            self.annealing_ph3_in_ar_flow.magnitude
            if self.annealing_ph3_in_ar_flow is not None
            else 0
        )
        total_flow = (
            annealing_ar_flow
            + annealing_h2s_in_ar_flow
            + annealing_n2_flow
            + annealing_nh3_in_ar_flow
            + annealing_ph3_in_ar_flow
        )

        if total_flow == 0:
            logger.warning(
                'Total annealing gas flow is zero. '
                'Partial pressures cannot be meaningfully calculated.'
            )
            return

        if self.annealing_pressure is None:
            logger.warning(
                'Annealing pressure is None. Partial pressures cannot be calculated.'
            )
            return

        total_pressure = self.annealing_pressure.magnitude

        annealing_h2s_partial_pressure = ureg.Quantity(
            annealing_h2s_in_ar_flow
            * RTP_GAS_FRACTION['H2S']
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_h2s_partial_pressure = annealing_h2s_partial_pressure

        annealing_ph3_partial_pressure = ureg.Quantity(
            annealing_ph3_in_ar_flow
            * RTP_GAS_FRACTION['PH3']
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_ph3_partial_pressure = annealing_ph3_partial_pressure

        annealing_nh3_partial_pressure = ureg.Quantity(
            annealing_nh3_in_ar_flow
            * RTP_GAS_FRACTION['NH3']
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_nh3_partial_pressure = annealing_nh3_partial_pressure

        annealing_n2_partial_pressure = ureg.Quantity(
            annealing_n2_flow * RTP_GAS_FRACTION['N2'] / total_flow * total_pressure,
            'Pa',
        )
        self.annealing_n2_partial_pressure = annealing_n2_partial_pressure

        # Ar partial pressure = dedicated Ar line + the Ar-carrier remainder
        # of each diluted gas line (1 - that gas's active-gas fraction).
        annealing_ar_partial_pressure = ureg.Quantity(
            (
                annealing_h2s_in_ar_flow * (1 - RTP_GAS_FRACTION['H2S'])
                + annealing_ph3_in_ar_flow * (1 - RTP_GAS_FRACTION['PH3'])
                + annealing_nh3_in_ar_flow * (1 - RTP_GAS_FRACTION['NH3'])
                + annealing_ar_flow * RTP_GAS_FRACTION['Ar']
            )
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.annealing_ar_partial_pressure = annealing_ar_partial_pressure

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTPOverview` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)
        flows = [
            self.annealing_ar_flow,
            self.annealing_n2_flow,
            self.annealing_ph3_in_ar_flow,
            self.annealing_nh3_in_ar_flow,
            self.annealing_h2s_in_ar_flow,
        ]
        if any(
            flow is not None and getattr(flow, 'magnitude', flow) != 0 for flow in flows
        ):
            self.calc_partial_pressure()
        else:
            _warn_once(
                self,
                '_warned_no_annealing_gas_flows',
                logger,
                'No detectable annealing gas flows. '
                'Partial pressures will not be calculated.',
            )


##################### STEPS (SUBSECTION) ######################################
class RTPStepOverview(ArchiveSection):
    """
    Section containing a human readable overview of a certain step of the RTP process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'duration',
                    'initial_temperature',
                    'final_temperature',
                    'pressure',
                    'step_ar_flow',
                    'step_n2_flow',
                    'step_ph3_in_ar_flow',
                    'step_nh3_in_ar_flow',
                    'step_h2s_in_ar_flow',
                    'temperature_ramp',
                    'step_ar_partial_pressure',
                    'step_n2_partial_pressure',
                    'step_ph3_partial_pressure',
                    'step_nh3_partial_pressure',
                    'step_h2s_partial_pressure',
                ],
            )
        ),
    )
    duration = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
            label='Duration',
        ),
        unit='s',
        description='Duration of the step.',
    )
    pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='torr',
            label='Pressure',
        ),
        unit='Pa',
        description='Pressure (average) in the RTP chamber during the step.',
    )
    step_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='Ar Flow',
        ),
        unit='m**3/s',
        description='Argon flow rate (average) used during the step.'
        'The unit "cm^3/minute" is used and equal to sccm.',
    )
    step_n2_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='N2 Flow',
        ),
        unit='m**3/s',
        description='Nitrogen flow rate (average) used during the step. '
        'The unit "cm^3/minute" is used and equal to sccm.',
    )
    step_ph3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='PH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Phosphine flow rate (average) used during the step.'
        'The unit "cm^3/minute" is used and equal to sccm.',
    )
    step_nh3_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='NH3 in Ar Flow',
        ),
        unit='m**3/s',
        description='Ammonia flow rate (average) used during the step.'
        'The unit "cm^3/minute" is used and equal to sccm.',
    )
    step_h2s_in_ar_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm^3/minute',
            label='H2S in ArFlow',
        ),
        unit='m**3/s',
        description='H2S flow rate (average) used during the step.'
        'The unit "cm^3/minute" is used andequal to sccm.',
    )
    initial_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='Initial Temperature',
        ),
        unit='K',
        description='Temperature at the start of the step.',
    )
    final_temperature = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='celsius',
            label='Final Temperature',
        ),
        unit='K',
        description='Temperature at the end of the step.',
    )
    temperature_ramp = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='celsius/minute',
            label='Temperature ramp rate. ',
        ),
        unit='K/s',
        description='Rate of temperature increase/decrease during the step.',
    )
    step_ph3_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='PH3 Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure (average) of PH3 during the annealing plateau '
            'of the RTP process.'
        ),
    )
    step_nh3_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='NH3 Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure (average) of NH3 during the annealing plateau '
            'of the RTP process.'
        ),
    )
    step_h2s_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='H2S Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure (average) of H2S during the annealing plateau '
            'of the RTP process.'
        ),
    )
    step_n2_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='N2 Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure (average) of N2 during the annealing plateau '
            'of the RTP process.'
        ),
    )
    step_ar_partial_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            defaultDisplayUnit='torr',
            label='Ar Partial Pressure',
        ),
        unit='Pa',
        description=(
            'Partial pressure (average) of Ar during the annealing plateau '
            'of the RTP process.'
        ),
    )

    def calc_ramp(self):
        """
        Calculate the temperature ramp rate based on the initial and final temperatures
        and the duration of the step.
        """
        if (
            self.initial_temperature is None
            or self.final_temperature is None
            or self.duration is None
        ):
            logger.warning(
                'Cannot calculate temperature ramp: initial_temperature,'
                ' final_temperature, or duration is missing.'
            )
            return

        initial_temperature = self.initial_temperature.magnitude
        final_temperature = self.final_temperature.magnitude
        duration = self.duration.magnitude

        temperature_ramp = ureg.Quantity(
            ((final_temperature - initial_temperature) / duration),
            'K/s',
        )
        self.temperature_ramp = temperature_ramp

    def calc_partial_pressure(self):
        """
        Same Dalton's-law mole-fraction model as
        `RTPOverview.calc_partial_pressure`, applied to a single step's
        flows/pressure instead of the annealing-plateau averages.
        """
        step_ar_flow = (
            self.step_ar_flow.magnitude if self.step_ar_flow is not None else 0
        )
        step_n2_flow = (
            self.step_n2_flow.magnitude if self.step_n2_flow is not None else 0
        )
        step_nh3_in_ar_flow = (
            self.step_nh3_in_ar_flow.magnitude
            if self.step_nh3_in_ar_flow is not None
            else 0
        )
        step_h2s_in_ar_flow = (
            self.step_h2s_in_ar_flow.magnitude
            if self.step_h2s_in_ar_flow is not None
            else 0
        )
        step_ph3_in_ar_flow = (
            self.step_ph3_in_ar_flow.magnitude
            if self.step_ph3_in_ar_flow is not None
            else 0
        )
        total_flow = (
            step_ar_flow
            + step_h2s_in_ar_flow
            + step_n2_flow
            + step_ph3_in_ar_flow
            + step_nh3_in_ar_flow
        )

        if total_flow == 0:
            logger.warning(
                'Total gas flow is zero in step. '
                'Partial pressures cannot be meaningfully calculated.'
            )
            return

        if self.pressure is None:
            logger.warning(
                'Step pressure is None. Partial pressures cannot be calculated.'
            )
            return

        total_pressure = self.pressure.magnitude

        step_h2s_partial_pressure = ureg.Quantity(
            step_h2s_in_ar_flow * RTP_GAS_FRACTION['H2S'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_h2s_partial_pressure = step_h2s_partial_pressure

        step_ph3_partial_pressure = ureg.Quantity(
            step_ph3_in_ar_flow * RTP_GAS_FRACTION['PH3'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_ph3_partial_pressure = step_ph3_partial_pressure

        step_nh3_partial_pressure = ureg.Quantity(
            step_nh3_in_ar_flow * RTP_GAS_FRACTION['NH3'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_nh3_partial_pressure = step_nh3_partial_pressure

        step_n2_partial_pressure = ureg.Quantity(
            step_n2_flow * RTP_GAS_FRACTION['N2'] / total_flow * total_pressure,
            'Pa',
        )
        self.step_n2_partial_pressure = step_n2_partial_pressure

        # Ar partial pressure = dedicated Ar line + the Ar-carrier remainder
        # of each diluted gas line (see RTPOverview.calc_partial_pressure).
        step_ar_partial_pressure = ureg.Quantity(
            (
                step_h2s_in_ar_flow * (1 - RTP_GAS_FRACTION['H2S'])
                + step_ph3_in_ar_flow * (1 - RTP_GAS_FRACTION['PH3'])
                + step_nh3_in_ar_flow * (1 - RTP_GAS_FRACTION['NH3'])
                + step_ar_flow * RTP_GAS_FRACTION['Ar']
            )
            / total_flow
            * total_pressure,
            'Pa',
        )
        self.step_ar_partial_pressure = step_ar_partial_pressure

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUSteps` class.

        Args:
        archive (EntryArchive): The archive containing the section that is being
        normalized.
        logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        flows = [
            self.step_ar_flow,
            self.step_n2_flow,
            self.step_ph3_in_ar_flow,
            self.step_nh3_in_ar_flow,
            self.step_h2s_in_ar_flow,
        ]
        if any(
            flow is not None and getattr(flow, 'magnitude', flow) != 0 for flow in flows
        ):
            self.calc_partial_pressure()
        else:
            _warn_once(
                self,
                '_warned_no_step_gas_flows',
                logger,
                'No detectable step gas flows. '
                'Partial pressures will not be calculated.',
            )

        # Check if parent step is an annealing step
        parent_step = getattr(self, 'm_parent', None)
        parent_step_name = getattr(parent_step, 'name', '') if parent_step else ''
        # Matches names starting with "anneal" or "annealing" (case
        # insensitive), e.g. "Annealing", "anneal 1", "Anneal: H2S" - but not
        # names where "anneal" appears mid-string.
        is_annealing = (
            re.match(r'^\s*anneal(?:ing)?\b', parent_step_name, re.IGNORECASE)
            is not None
        )

        if (
            self.initial_temperature is not None
            and self.final_temperature is not None
            and self.initial_temperature != self.final_temperature
            and not is_annealing
        ):
            self.calc_ramp()
        elif is_annealing and self.initial_temperature != self.final_temperature:
            # Annealing steps are expected to be isothermal (held at a
            # constant plateau temperature). If the logged initial/final
            # temperatures differ anyway, that's logged as a warning rather
            # than silently computing a ramp rate that wouldn't be
            # meaningful for a plateau step.
            _warn_once(
                self,
                '_annealing_ramp_warning_emitted',
                logger,
                f'Step "{parent_step_name}" identified as annealing: '
                'skipping temperature_ramp calculation '
                '(annealing steps are isothermal by definition)',
            )


class DtuRTPSources(CVDSource, ArchiveSection):
    """
    Information regarding the sources (gases) used in the RTP process.
    """

    sources = Quantity(
        type=str,
        shape=['*'],
        description=(
            'Automatically generated list of used sources (gases) during this step.'
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)


class DTURTPSteps(CVDStep, ArchiveSection):
    """
    Class representing each step in the RTP process.
    """

    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'creates_new_thin_film',
                    'step_overview',
                    'sources',
                    'comment',
                ],
                visible=Filter(
                    exclude=[
                        'start_time',
                        'duration',
                        'step_index',
                        'environment',
                        'sample_parameters',
                    ]
                ),
            )
        ),
    )
    step_overview = SubSection(
        section_def=RTPStepOverview,
    )
    sources = SubSection(
        section_def=DtuRTPSources,
        repeats=True,
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTURTPSteps` class.

        Note: per-step source syncing is intentionally NOT duplicated here.
        The parent `DtuRTP.normalize()` already syncs step sources from
        `used_gases` in a single explicit pass
        (`_sync_step_sources_from_used_gases`), so this method only handles
        derived `step_overview` quantities (ramps and partial pressures).

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        # Ensure derived step_overview values (temperature ramp and partial
        # pressures) are always computed during step normalization.
        if self.step_overview is not None:
            self.step_overview.normalize(archive, logger)


###################### 1ST LEVEL CLASS (RTP) #################################
class DtuRTP(ChemicalVaporDeposition, PlotSection, Schema):
    """
    A synthesis method where a rapidly heated substrate is exposed to one or more
    volatile precursors, which react or decompose on the surface to produce a deposit.
    [database_cross_reference: https://orcid.org/0000-0002-0640-0422]

    Synonyms:
    - rapid thermal chemical vapor deposition
    - rapid thermal CVD
    - RTCVD
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='RTP',
        links=['http://purl.obolibrary.org/obo/CHMO_0001328'],
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'datetime',
                    'lab_id',
                    'location',
                    'log_file_eklipse',
                    'log_file_CXThermoDiagnostics',
                    'log_files_CXThermoDiagnostics',
                    'process_log_files',
                    'overwrite_existing_data',
                    'samples_susceptor_before',
                    'samples_susceptor_after',
                    'base_pressure',
                    'base_pressure_ballast',
                    'rate_of_rise',
                    'chiller_flow',
                    'used_gases',
                    'overview',
                    'steps',
                    'input_samples',
                    'samples',
                    'figures',
                ],
                visible=Filter(exclude=['end_time', 'instruments', 'method']),
            )
        ),
    )
    lab_id = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Run ID',
        ),
        description='The ID of the run. Format: user_number_RTP.',
    )
    location = Quantity(
        type=str,
        default='DTU; IDOL Lab',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
        ),
    )
    log_file_eklipse = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity, label='Gas/Pressure log file'
        ),
        description=(
            'MANUAL INPUT. Cell to upload the gas/pressure log file '
            'obtained with Eklipse.'
        ),
    )
    log_files_CXThermoDiagnostics = Quantity(
        type=str,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.FileEditQuantity,
            label='Temperature log files',
        ),
        description=(
            'MANUAL INPUT. Temperature log files obtained with CX-Thermo. '
            'If one file is provided, it is used directly. '
            'If multiple files are provided, '
            'they are stacked by timestamp before merging with pressure data.'
        ),
    )
    process_log_files = Quantity(
        type=bool,
        default=True,
        description=(
            'MANUAL INPUT. Boolean to indicate if the RTP log files should '
            'be processed.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Process log files',
        ),
    )
    overwrite_existing_data = Quantity(
        type=bool,
        default=True,
        description=(
            'MANUAL INPUT. Boolean to indicate if the data present in the '
            'entry should be overwritten by data incoming from the log files.'
        ),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.BoolEditQuantity,
            label='Overwrite existing data ?',
        ),
    )
    samples_susceptor_before = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of the samples on susceptor before the RTP process.',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description=(
            'MANUAL INPUT. Cell to upload the image of the samples on '
            'susceptor before the RTP process.'
        ),
    )
    samples_susceptor_after = Quantity(
        type=str,
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Image of the samples on susceptor after the RTP process.',
        },
        a_browser=BrowserAnnotation(
            adaptor=BrowserAdaptors.RawFileAdaptor,
        ),
        description=(
            'MANUAL INPUT. Cell to upload the image of the samples on '
            'susceptor after the RTP process.'
        ),
    )
    used_gases = Quantity(
        type=str,
        shape=['*'],
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Used gases',
        ),
        description='Gases used in the RTP process.',
    )
    #################### GENERAL CHECKS ######################
    base_pressure = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Base Pressure without ballast',
            defaultDisplayUnit='mtorr',
        ),
        unit='Pa',
        description='RTP chamber base pressure when ballast is OFF.',
    )
    base_pressure_ballast = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Base Pressure with ballast',
            defaultDisplayUnit='mtorr',
        ),
        unit='Pa',
        description='RTP chamber base pressure when ballast is ON.',
    )
    rate_of_rise = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mtorr/minute',
            label='Rate of Rise',
        ),
        unit='Pa/s',
        description='Rate of rise of the pressure in the RTP chamber during static '
        'vacuum conditions.',
    )
    chiller_flow = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='l/minute',
            label='Chiller Flow',
        ),
        unit='m**3/s',
        description='MANUAL INPUT. Chiller flow rate during the RTP process.',
    )
    ############################## SUBSECTIONS ########################################
    input_samples = SubSection(
        section_def=DtuRTPInputSampleMounting,
        repeats=True,
    )
    overview = SubSection(
        section_def=RTPOverview,
    )
    steps = SubSection(
        section_def=DTURTPSteps,
        repeats=True,
    )

    ####### MATERIAL SPACE, SOURCES AND RTP SAMPLE LIBRARY FUNCTIONS #################
    def _sync_step_sources_from_used_gases(self, overwrite: bool = False) -> None:
        """Populate each RTP step's `sources` from the process-level `used_gases`.

        This helper keeps the per-step `sources` entries aligned with the gases
        recorded in `self.used_gases`. For every step, it creates one
        `DtuRTPSources` object per gas and stores it in `step.sources`.

        Behavior:
        - If no gases are defined in `self.used_gases`, nothing is done.
        - Existing `step.sources` are preserved unless `overwrite=True`.
        - Each created source entry uses the gas name both as `source.name`
          and as the only element in `source.sources`.

        This is intended as a convenience/default synchronization step when
        step-specific source information is not entered manually.
        """
        # Ignore empty gas entries and work only with defined gases.
        gases = [gas for gas in (self.used_gases or []) if gas]
        if not gases:
            return

        # Update each step unless existing sources should be preserved.
        for step in getattr(self, 'steps', []) or []:
            if not overwrite and (step.sources or []):
                continue

            step.sources = []
            for gas in gases:
                source = DtuRTPSources()
                source.sources = [gas]
                source.name = gas
                step.sources.append(source)

    def _get_input_sample_material_elements(self) -> list[str]:
        """Collect elements from input samples in their inherited composition order.

        Returns elements in order: those from input samples (in order of appearance),
        maintaining the sequence as they appear in the elemental composition.
        """
        ordered_elements: list[str] = []

        def _append_symbol(raw_symbol) -> None:
            if raw_symbol is None:
                return
            symbol = str(raw_symbol).strip()
            if symbol and symbol not in ordered_elements:
                ordered_elements.append(symbol)

        for rtp_sample in getattr(self, 'input_samples', []) or []:
            origin = getattr(rtp_sample, 'input_combi_lib', None)
            if origin is None:
                continue

            layer_ref = (
                origin.layers[0].reference if getattr(origin, 'layers', None) else None
            )
            layer_comp = getattr(layer_ref, 'elemental_composition', None)
            if layer_comp is None:
                layer_comp = getattr(origin, 'elemental_composition', None)

            if not layer_comp:
                continue

            for elem in layer_comp:
                _append_symbol(getattr(elem, 'element', elem))

        return ordered_elements

    def _autofill_material_space(self) -> None:
        """Always recompute material_space from input-sample composition + gas elements.

        - No input samples with composition -> material_space is cleared to None.
        - Input samples present -> their elements are used, with gas-derived elements
          (PH3->P, H2S->S) inserted to maintain order: metals first (e.g. Sn),
          then P, then S.
        """
        if self.overview is None:
            self.overview = RTPOverview()

        ordered_elements = self._get_input_sample_material_elements()
        if not ordered_elements:
            self.overview.material_space = None
            return

        # Add gas-derived elements in the desired order: P before S, N after S
        # This maintains the pattern: input elements (metal), then P, then S, then N
        gas_to_element = {'PH3': 'P', 'H2S': 'S', 'N2': 'N', 'NH3': 'N'}
        for gas in ['PH3', 'H2S', 'N2', 'NH3']:  # Maintain explicit order: P before S
            if gas in (self.used_gases or []):
                symbol = gas_to_element[gas]
                if symbol not in ordered_elements:
                    ordered_elements.append(symbol)

        # Keep all non-P/S/N elements first, then force P then S then N at the end.
        ordered_elements = [
            element for element in ordered_elements if element not in {'P', 'S', 'N'}
        ] + [element for element in ['P', 'S', 'N'] if element in ordered_elements]

        self.overview.material_space = '-'.join(ordered_elements)

    def add_libraries(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        samples = []
        rtp_name = self.name
        rtp_datetime = self.datetime
        rtp_materialspace = self.overview.material_space
        if not rtp_materialspace:
            return
        for rtp_sample in self.input_samples:
            # Get the input sample and its origin (pre-RTP) sample/layer
            origin = rtp_sample.input_combi_lib
            origin_layer = origin.layers[0].reference if origin.layers else None

            # Get elemental compositions
            origin_elements = [e.element for e in origin.elemental_composition]
            rtp_elements = [e for e in rtp_materialspace.split('-') if e]

            # Merge for library: the post-RTP library should contain every
            # element the input sample already had, plus any new elements
            # introduced by the RTP process (e.g. P/S from PH3/H2S gas).
            # If the sets already match, reuse origin's composition as-is
            # rather than rebuilding equivalent objects.
            if set(rtp_elements) == set(origin_elements):
                elemental_composition = origin.elemental_composition
            else:
                merged_elements = origin_elements + [
                    e for e in rtp_elements if e not in origin_elements
                ]
                elemental_composition = [
                    type(origin.elemental_composition[0])(element=e)
                    for e in merged_elements
                ]

            # Merge for the layer: same logic as above, applied to the
            # origin layer's composition specifically (the layer and the
            # library it belongs to are tracked separately).
            if (
                origin_layer is not None
                and origin_layer.elemental_composition is not None
            ):
                layer_origin_elements = [
                    e.element for e in origin_layer.elemental_composition
                ]
                merged_layer_elements = layer_origin_elements + [
                    e for e in rtp_elements if e not in layer_origin_elements
                ]
                layer_elemental_composition = [
                    type(origin_layer.elemental_composition[0])(element=e)
                    for e in merged_layer_elements
                ]
            else:
                logger.warning(
                    f'Could not determine elemental composition for the '
                    f"new layer of sample '{rtp_sample.name}'. "
                    'No origin layer or missing elemental composition in origin'
                    ' layer.'
                )

            # Create new layer and library only if an input sample has been specified
            # and overview is filled (to get material space -> elemental composition)
            if rtp_sample.name is not None:
                # Create a new ThinFilm layer for this sample
                layer = ThinFilm(
                    elemental_composition=layer_elemental_composition,
                    lab_id=f'{rtp_name} {rtp_sample.name}-Layer'.replace(' ', '_'),
                )
                layer_ref = create_archive(
                    layer,
                    archive,
                    f'{layer.lab_id}.archive.json',
                    overwrite=configuration.overwrite_layers,
                )
                # Create new library
                library = DTUCombinatorialLibrary(
                    name=f'{rtp_name} {rtp_sample.name}',
                    datetime=rtp_datetime,
                    lab_id=f'{rtp_name} {rtp_sample.name}'.replace(' ', '_'),
                    description=f'RTP library for {rtp_name} {rtp_sample.name}',
                    elemental_composition=elemental_composition,
                    layers=[
                        ThinFilmReference(
                            name='Main Layer',
                            reference=layer_ref,
                            lab_id=layer.lab_id,
                        )
                    ],
                    geometry=origin.geometry,
                    substrate=origin.substrate,
                    process_parameter_overview=origin.process_parameter_overview,
                    parent_library=DtuLibraryReference(
                        reference=origin.m_proxy_value,
                        name=origin.name,
                        lab_id=origin.lab_id,
                    ),
                )
                samples.append(library)
        if configuration.overwrite_libraries:
            # The layer archives created just above are written
            # asynchronously by NOMAD's processing pipeline. When
            # overwrite_libraries is enabled, the library archives created
            # right below this need those layers to have finished
            # processing first (so they resolve correctly), but there's no
            # synchronous "wait until processed" API available here - hence
            # the fixed delay as a pragmatic (if fragile) workaround.
            time.sleep(5)
        self.samples = [
            CompositeSystemReference(
                name=f'Sample {library.name}',
                reference=create_archive(
                    library,
                    archive,
                    f'{library.lab_id}.archive.json',
                    overwrite=configuration.overwrite_libraries,
                ),
                lab_id=library.lab_id,
            )
            for library in samples
        ]
        if not samples:
            logger.warning(
                'No RTP sample libraries were created. '
                'Check that input_samples have valid input_combi_lib and name and'
                'that overview.material_space is filled.'
            )

    ############################## PLOTS #################################
    def _find_temperature_end_time(
        self,
        time_s: list,
        temperature_c: list,
        cooling_start: float,
        cooling_end: float,
        end_temp_c: float | None,
    ) -> float | None:
        if end_temp_c is None:
            return None
        for raw_time, temperature in zip(time_s, temperature_c):
            time_value = float(raw_time)
            if time_value < cooling_start:
                continue
            if time_value > cooling_end:
                break
            if np.isfinite(temperature) and float(temperature) <= end_temp_c:
                return time_value
        return None

    def _find_gas_shutoff_time(
        self, time_s: list, cooling_start: float, cooling_end: float
    ) -> float | None:
        flows = [
            getattr(self, '_log_ar_flow_sccm', []) or [],
            getattr(self, '_log_n2_flow_sccm', []) or [],
            getattr(self, '_log_ph3_flow_sccm', []) or [],
            getattr(self, '_log_h2s_flow_sccm', []) or [],
        ]
        if any(len(flow) != len(time_s) for flow in flows):
            return None

        had_gas_on = False
        for samples in zip(time_s, *flows):
            time_value = float(samples[0])
            if time_value < cooling_start:
                continue
            if time_value > cooling_end:
                break
            gas_on = any(
                np.isfinite(flow) and abs(float(flow)) > MIN_USED_GAS_FLOW_SCCM
                for flow in samples[1:]
            )
            if gas_on:
                had_gas_on = True
            elif had_gas_on:
                return time_value
        return None

    def _get_cooling_end_time(self, cooling_segment) -> float:
        cooling_start = _to_seconds(cooling_segment[1])
        cooling_end = _to_seconds(cooling_segment[2])
        time_s = getattr(self, '_log_time_s', []) or getattr(self, '_time', [])
        temperature_c = getattr(self, '_log_temperature_c', []) or getattr(
            self, '_temperature_profile', []
        )
        if not time_s or not temperature_c or len(time_s) != len(temperature_c):
            return cooling_end

        end_temp = None
        if self.overview is not None:
            end_temp = getattr(self.overview, 'end_of_process_temperature', None)
        if hasattr(end_temp, 'to'):
            end_temp_c = float(end_temp.to('celsius').magnitude)
        elif end_temp is not None:
            end_temp_c = float(end_temp) - CELSIUS_TO_KELVIN_OFFSET
        else:
            end_temp_c = None

        reached_time = self._find_temperature_end_time(
            time_s, temperature_c, cooling_start, cooling_end, end_temp_c
        )
        if reached_time is None:
            reached_time = self._find_gas_shutoff_time(
                time_s, cooling_start, cooling_end
            )
        if reached_time is None:
            return cooling_end
        return min(float(time_s[-1]), reached_time + POST_END_PROCESS_WINDOW_S)

    def _get_full_plot_time_range(self) -> tuple[float, float] | None:
        """Return plot range from heating start to 30 s after process end temp.

        Falls back to full available range when phase labels or temperature
        samples are missing.
        """
        series = getattr(self, '_log_time_s', []) or getattr(self, '_time', []) or []
        if not series:
            return None

        start_time = _to_seconds(series[0])
        end_time = _to_seconds(series[-1])
        segments = getattr(self, '_phase_segments', []) or []
        if segments:
            heating_segment = next(
                (segment for segment in segments if 'heat' in segment[0].lower()),
                None,
            )
            if heating_segment is not None:
                start_time = _to_seconds(heating_segment[1])
            cooling_segment = next(
                (segment for segment in segments if 'cool' in segment[0].lower()),
                None,
            )
            if cooling_segment is not None:
                end_time = self._get_cooling_end_time(cooling_segment)
            end_time = min(end_time, _to_seconds(segments[-1][2]))

        return start_time, max(end_time, start_time)

    def _build_phase_segments(self) -> list[tuple[str, float, float]]:
        """Build (name, start_s, end_s) segments from step durations.

        Used as a fallback when log-file-derived segments (with real
        timestamps) aren't available - e.g. when reconstructing a process
        timeline purely from step definitions rather than parsed logs.
        Segments are laid out back-to-back starting at t=0, in step order.
        """
        # Prefer log-file-derived boundaries (actual timestamps) when available.
        log_segs = getattr(self, '_log_phase_segments', None)
        if log_segs:
            return log_segs

        segments: list[tuple[str, float, float]] = []
        cursor = 0.0
        for step in getattr(self, 'steps', []) or []:
            step_overview = getattr(step, 'step_overview', None)
            if step_overview is None or step_overview.duration is None:
                continue
            duration = step_overview.duration
            duration_s = (
                float(duration.to('s').magnitude)
                if hasattr(duration, 'to')
                else float(getattr(duration, 'magnitude', duration))
            )
            if duration_s <= 0:
                continue
            name = (step.name or '').strip() or 'Step'
            segments.append((name, cursor, cursor + duration_s))
            cursor += duration_s
        return segments

    def _add_phase_delimiters(self, fig: go.Figure) -> None:
        """Shade each process phase (heating/annealing/cooling/etc.) as a
        background rectangle on the plot, with a centered text label."""
        segments = getattr(self, '_phase_segments', []) or []
        if not segments:
            return
        # Used below to keep phase labels centered within the visible
        # (trimmed) plot window rather than the full segment - otherwise a
        # label could be centered outside the actual plotted x-range and
        # appear to be missing/off to the side.
        x_trim = self._get_full_plot_time_range()

        # Color scheme: orange for heating, blue for cooling, gray for
        # annealing, and a neutral gray fallback for any other phase name.
        def _phase_fill_color(name: str) -> str:
            n = name.lower()
            if 'heat' in n:
                return 'rgba(255, 160, 60, 0.18)'
            if 'cool' in n:
                return 'rgba(60, 140, 255, 0.18)'
            if 'anneal' in n:
                return 'rgba(150, 150, 150, 0.18)'
            return 'rgba(120, 120, 120, 0.10)'

        # Matching (more saturated/opaque) text colors for the phase labels.
        def _phase_font_color(name: str) -> str:
            n = name.lower()
            if 'heat' in n:
                return 'rgba(200, 100, 0, 1)'
            if 'cool' in n:
                return 'rgba(0, 80, 200, 1)'
            return 'rgba(80, 80, 80, 1)'

        for name, start, end in segments:
            start_f = float(start)
            end_f = float(end)
            fig.add_vrect(
                x0=start_f,
                x1=end_f,
                fillcolor=_phase_fill_color(name),
                opacity=1.0,
                layer='below',
                line_width=0,
            )

            # Clamp the label's centering window to the visible plot range
            # (x_trim) so labels for segments that extend beyond the
            # plotted window are still centered within what's actually
            # shown, rather than off-screen.
            if x_trim is not None:
                trimmed_start = max(start_f, float(x_trim[0]))
                trimmed_end = min(end_f, float(x_trim[1]))
            else:
                trimmed_start = start_f
                trimmed_end = end_f

            if trimmed_end <= trimmed_start:
                # The trimmed window collapsed (segment falls entirely
                # outside the visible range) - fall back to centering on
                # the segment's full (untrimmed) extent.
                label_x = 0.5 * (start_f + end_f)
            else:
                label_x = 0.5 * (trimmed_start + trimmed_end)

            fig.add_annotation(
                x=label_x,
                y=0.96,
                xref='x',
                yref='paper',
                text=name,
                showarrow=False,
                font=dict(size=13, color=_phase_font_color(name)),
                xanchor='center',
                yanchor='top',
            )

    # Set up temperature profile plot
    def plot_temperature_profile(self) -> None:
        time_s = getattr(self, '_log_time_s', []) or getattr(self, '_time', []) or []
        temperature_c = (
            getattr(self, '_log_temperature_c', [])
            or getattr(self, '_temperature_profile', [])
            or []
        )
        setpoint_c = getattr(self, '_temperature_setpoint_profile', []) or []
        lamp_power = getattr(self, '_lamp_power_profile', []) or []

        if not time_s or not temperature_c:
            _warn_once(
                self,
                '_warned_missing_temperature_timeseries_plot_data',
                logger,
                'Temperature timeseries plot cannot be created: '
                'time or temperature data missing from process logs',
            )
            return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=time_s,
                y=temperature_c,
                mode='lines',
                name='Actual Temperature',
            )
        )
        if setpoint_c and len(setpoint_c) == len(time_s):
            fig.add_trace(
                go.Scatter(
                    x=time_s,
                    y=setpoint_c,
                    mode='lines',
                    name='Temperature Setpoint',
                    line=dict(dash='dash'),
                )
            )
        if lamp_power and len(lamp_power) == len(time_s):
            fig.add_trace(
                go.Scatter(
                    x=time_s,
                    y=lamp_power,
                    mode='lines',
                    name='Lamp Power',
                    yaxis='y2',
                )
            )
        self._add_phase_delimiters(fig)

        x_range = self._get_full_plot_time_range()
        fig.update_xaxes(
            automargin=True
        )  # fix for bug with the axis not visible when 1st time the plot is created
        fig.update_yaxes(automargin=True)  # same fix for the y axis
        fig.update_layout(
            title='RTP Temperature and Lamp Power',
            height=500,
            autosize=True,
            margin=dict(l=85, r=85, t=60, b=70),
            xaxis_title='Time / s',
            yaxis_title='Temperature / °C',
            yaxis2=dict(
                title='Lamp Power / %',
                overlaying='y',
                side='right',
                showgrid=False,
            ),
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.25,
                xanchor='center',
                x=0.5,
            ),
            xaxis=dict(
                fixedrange=False,
                autorange=False if x_range is not None else True,
                showline=True,
                showgrid=True,
                zeroline=True,
                range=list(x_range) if x_range is not None else None,
            ),
            yaxis=dict(
                fixedrange=False,
                showline=True,
                showgrid=True,
                zeroline=True,
            ),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(
            scrollZoom=False,
            responsive=True,
        )
        self.figures.append(
            PlotlyFigure(
                label='Temperature Profile',
                figure=plot_json,
            )
        )

    # Set up gas flows profile plot
    def plot_gas_flows_profile(self) -> None:
        time_s = getattr(self, '_log_time_s', []) or []
        if not time_s:
            return

        flow_series = {
            'Ar Flow': getattr(self, '_log_ar_flow_sccm', []),
            'N2 Flow': getattr(self, '_log_n2_flow_sccm', []),
            'PH3 in Ar Flow': getattr(self, '_log_ph3_flow_sccm', []),
            'H2S in Ar Flow': getattr(self, '_log_h2s_flow_sccm', []),
        }

        fig = go.Figure()
        plotted = False
        for name, values in flow_series.items():
            if values and len(values) == len(time_s):
                plotted = True
                fig.add_trace(
                    go.Scatter(
                        x=time_s,
                        y=values,
                        mode='lines',
                        name=name,
                    )
                )

        if not plotted:
            return

        self._add_phase_delimiters(fig)
        x_range = self._get_full_plot_time_range()

        fig.update_layout(
            title='RTP Gas Flows Evolution',
            xaxis_title='Time / s',
            yaxis_title='Flow / sccm',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='top',
                y=-0.15,
                xanchor='center',
                x=0.5,
            ),
            xaxis=dict(
                fixedrange=False,
                autorange=False if x_range is not None else True,
                showline=True,
                showgrid=True,
                zeroline=True,
                range=list(x_range) if x_range is not None else None,
            ),
            yaxis=dict(
                fixedrange=False,
                showline=True,
                showgrid=True,
                zeroline=True,
            ),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False, responsive=True)
        self.figures.append(
            PlotlyFigure(
                label='Gas Flows Evolution',
                figure=plot_json,
            )
        )

    # Set up pressure profile plot
    def plot_pressure_profile(self) -> None:
        time_s = getattr(self, '_log_time_s', []) or []
        pressure_torr = getattr(self, '_log_pressure_torr', []) or []
        if not time_s or not pressure_torr or len(pressure_torr) != len(time_s):
            _warn_once(
                self,
                '_warned_missing_pressure_profile_data',
                logger,
                'Pressure profile plot cannot be created: '
                'time or pressure data missing or mismatched in length',
            )
            return
        pressure_arr = np.asarray(pressure_torr, dtype=float)
        if not np.isfinite(pressure_arr).any():
            _warn_once(
                self,
                '_warned_invalid_pressure_profile_values',
                logger,
                'Pressure profile plot cannot be created: '
                'all pressure values are NaN or infinite',
            )
            return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=time_s,
                y=pressure_torr,
                mode='lines',
                name='Chamber Pressure',
            )
        )
        self._add_phase_delimiters(fig)
        x_range = self._get_full_plot_time_range()
        fig.update_layout(
            title='RTP Pressure Evolution',
            xaxis_title='Time / s',
            yaxis_title='Pressure / torr',
            template='plotly_white',
            hovermode='closest',
            dragmode='zoom',
            xaxis=dict(
                fixedrange=False,
                autorange=False if x_range is not None else True,
                showline=True,
                showgrid=True,
                zeroline=True,
                range=list(x_range) if x_range is not None else None,
            ),
            yaxis=dict(
                fixedrange=False,
                showline=True,
                showgrid=True,
                zeroline=True,
            ),
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False, responsive=True)
        self.figures.append(
            PlotlyFigure(
                label='Pressure Evolution',
                figure=plot_json,
            )
        )

    def _get_sample_dimensions(self, input_sample, rel_pos) -> tuple[float, float]:
        geometry = getattr(input_sample.input_combi_lib, 'geometry', None)
        if geometry is not None:
            width = getattr(geometry, 'width', 10)
            length = getattr(geometry, 'length', 10)
            if hasattr(width, 'magnitude'):
                width = width.to('mm').magnitude
            if hasattr(length, 'magnitude'):
                length = length.to('mm').magnitude
        else:
            # No geometry recorded on the sample: fall back to nominal sizes
            # (in mm) based on the slot's naming convention, matching the
            # same slot groupings used in
            # DtuRTPInputSampleMounting.normalize() - square slots are
            # 20x20, horizontal-rectangle slots are wide (40x9.5), vertical
            # ones are tall (9.5x40), and anything unrecognized defaults to
            # a small 10x10 placeholder.
            square_positions = {'bl', 'br', 'fl', 'fr', 'm'}
            rectangle_horizontal = {'ha', 'hb', 'hc', 'hd'}
            rectangle_vertical = {'va', 'vb', 'vc', 'vd'}
            if rel_pos in square_positions:
                width, length = 20, 20
            elif rel_pos in rectangle_horizontal:
                width, length = 40, 9.5
            elif rel_pos in rectangle_vertical:
                width, length = 9.5, 40
            else:
                width, length = 10, 10
        return width, length

    def _get_sample_position(self, input_sample) -> tuple[float, float]:
        x = getattr(input_sample, 'position_x', None)
        y = getattr(input_sample, 'position_y', None)
        if x is None or y is None:
            x = 0
            y = 0
        if hasattr(x, 'magnitude'):
            x = x.to('mm').magnitude
        if hasattr(y, 'magnitude'):
            y = y.to('mm').magnitude
        return x, y

    def _get_sample_rotation(self, input_sample) -> float:
        rotation = getattr(input_sample, 'rotation', None)
        if rotation is None:
            logger.warning(
                f"Input sample '{getattr(input_sample, 'name', 'Unnamed')}' "
                'has no rotation specified; defaulting to 0 radians.'
            )
            return 0.0
        if hasattr(rotation, 'to'):
            return float(rotation.to('rad').magnitude)
        return float(rotation)

    # Helper function to plot a sample on the susceptor. It is called in the next.
    def plot_sample_on_susceptor(self, fig, input_sample):
        rel_pos = getattr(input_sample, 'relative_position', None)
        raw_x = getattr(input_sample, 'position_x', None)
        raw_y = getattr(input_sample, 'position_y', None)
        if rel_pos is None and raw_x is None and raw_y is None:
            logger.warning(
                f"Input sample '{getattr(input_sample, 'name', 'Unnamed')}'"
                ' has no relative position, x, or y set.'
                ' It will be placed at the center by default.'
            )
        width, length = self._get_sample_dimensions(input_sample, rel_pos)
        x, y = self._get_sample_position(input_sample)
        angle_rad = self._get_sample_rotation(input_sample)

        # Build the sample's rectangle in its own local coordinate frame
        # (centered on the origin), then rotate and translate it into place
        # on the susceptor using a standard 2D rotation matrix:
        #   x' = x*cos(a) - y*sin(a)
        #   y' = x*sin(a) + y*cos(a)
        # followed by translation to (x, y).
        half_w, half_l = width / 2, length / 2
        local_corners = [
            (-half_w, -half_l),
            (half_w, -half_l),
            (half_w, half_l),
            (-half_w, half_l),
        ]
        cos_a = float(np.cos(angle_rad))
        sin_a = float(np.sin(angle_rad))
        rotated_corners = [
            (
                x + (cx * cos_a - cy * sin_a),
                y + (cx * sin_a + cy * cos_a),
            )
            for cx, cy in local_corners
        ]
        # Build an SVG path string tracing the four rotated corners:
        # "M x0,y0 L x1,y1 L x2,y2 L x3,y3 Z" (M = move to start, L = line
        # to each subsequent corner, Z = close the path back to the start).
        path = 'M ' + ' L '.join(f'{px},{py}' for px, py in rotated_corners) + ' Z'
        fig.add_shape(
            type='path',
            path=path,
            line=dict(color='blue', width=2),
            fillcolor='rgba(100,100,255,0.3)',
        )
        label = rel_pos if rel_pos else input_sample.name
        fig.add_annotation(
            x=x,
            y=y,
            text=label,
            showarrow=False,
            font=dict(color='black', size=12),
            bgcolor='white',
        )

    # Set up the sample-on-susceptor graphical visualization
    def plot_susceptor(self) -> None:
        fig = go.Figure()

        # Draw susceptor outline (square 50x50 mm centered at 0,0)
        susceptor_size = 50  # mm
        half_susceptor = susceptor_size / 2
        fig.add_shape(
            type='rect',
            x0=-half_susceptor,
            y0=-half_susceptor,
            x1=half_susceptor,
            y1=half_susceptor,
            line=dict(color='black', width=3),
            fillcolor='rgba(200,200,200,0.1)',
            layer='below',
        )
        # Add 'chamber' label to the left side. By convention, the RTP
        # chamber's interior/door side is oriented to the left and the
        # operator ("User") side is oriented to the bottom of this diagram,
        # giving a fixed, consistent frame of reference for interpreting
        # relative_position values (bl/br/fl/fr etc.) across plots.
        fig.add_annotation(
            x=-half_susceptor - 2,  # 2 mm left of the susceptor edge
            y=0,
            text='RTP chamber',
            showarrow=False,
            font=dict(color='black', size=16),
            xanchor='right',
            yanchor='middle',
            textangle=-90,  # Rotate text to be vertical
        )
        # Add 'user' label to the bottom side
        fig.add_annotation(
            x=0,
            y=-half_susceptor - 2,  # 2 mm below the susceptor edge
            text='User',
            showarrow=False,
            font=dict(color='black', size=16),
            xanchor='center',
            yanchor='top',
        )
        # Loop through input_samples and plot them, using the helper function.
        for input_sample in getattr(self, 'input_samples', []):
            self.plot_sample_on_susceptor(fig, input_sample)
        fig.update_layout(
            title='Samples on Susceptor',
            xaxis=dict(
                # Extra left/right padding (15mm) leaves room for the
                # vertical "RTP chamber" label outside the susceptor outline.
                range=[-half_susceptor - 15, half_susceptor + 15],
                scaleanchor='y',
                scaleratio=1,
                showgrid=False,
                zeroline=False,
                visible=False,
            ),
            yaxis=dict(
                # Smaller padding (5mm) here since the "User" label is a
                # single line and doesn't need as much clearance.
                range=[-half_susceptor - 5, half_susceptor + 5],
                showgrid=False,
                zeroline=False,
                visible=False,
            ),
            width=500,
            height=500,
            plot_bgcolor='white',
        )
        plot_json = fig.to_plotly_json()
        plot_json['config'] = dict(scrollZoom=False, responsive=True)
        self.figures.append(
            PlotlyFigure(
                label='Samples-on-Susceptor Map',
                figure=plot_json,
            )
        )

    def _store_log_series(
        self, attribute, timeseries, overwrite, series_config
    ) -> None:
        preferred_key, fallback_key, conversion, factor = series_config
        if not overwrite and getattr(self, attribute, []):
            return
        if preferred_key in timeseries:
            values = timeseries.get(preferred_key, [])
            if conversion is not None:
                values = [
                    self._convert_log_value(value, conversion, factor)
                    for value in values
                ]
        elif fallback_key is not None:
            values = timeseries.get(fallback_key, [])
        else:
            values = []
        setattr(self, attribute, values)

    @staticmethod
    def _convert_log_value(value, conversion, factor):
        if not np.isfinite(value):
            return float('nan')
        if conversion == 'subtract':
            return float(value) - factor
        return float(value) / factor

    def _store_log_timeseries(self, parsed, overwrite) -> None:
        timeseries = parsed.timeseries or {}
        series = [
            ('_log_time_s', ('time_s', None, None, 0.0)),
            (
                '_log_temperature_c',
                (
                    'temperature_k',
                    'temperature_c',
                    'subtract',
                    CELSIUS_TO_KELVIN_OFFSET,
                ),
            ),
            (
                '_temperature_setpoint_profile',
                (
                    'temperature_setpoint_k',
                    'temperature_setpoint_c',
                    'subtract',
                    CELSIUS_TO_KELVIN_OFFSET,
                ),
            ),
            ('_lamp_power_profile', ('lamp_power', None, None, 0.0)),
            (
                '_log_pressure_torr',
                ('pressure_pa', 'pressure_torr', 'divide', TORR_TO_PA),
            ),
            (
                '_log_ar_flow_sccm',
                ('ar_flow_m3_s', 'ar_flow_sccm', 'divide', SCCM_TO_M3_S),
            ),
            (
                '_log_n2_flow_sccm',
                ('n2_flow_m3_s', 'n2_flow_sccm', 'divide', SCCM_TO_M3_S),
            ),
            (
                '_log_ph3_flow_sccm',
                (
                    'ph3_in_ar_flow_m3_s',
                    'ph3_in_ar_flow_sccm',
                    'divide',
                    SCCM_TO_M3_S,
                ),
            ),
            (
                '_log_h2s_flow_sccm',
                (
                    'h2s_in_ar_flow_m3_s',
                    'h2s_in_ar_flow_sccm',
                    'divide',
                    SCCM_TO_M3_S,
                ),
            ),
        ]
        for attribute, series_config in series:
            self._store_log_series(
                attribute,
                timeseries,
                overwrite,
                series_config,
            )

        if overwrite or not getattr(self, '_log_phase_segments', []):
            self._log_phase_segments = [
                (step.name, step.start_time_s, step.end_time_s)
                for step in parsed.steps
                if step.start_time_s is not None and step.end_time_s is not None
            ]

    def _set_overview_fields(self, parsed, overwrite, fields) -> None:
        for attribute in fields:
            if overwrite or getattr(self.overview, attribute) is None:
                setattr(
                    self.overview,
                    attribute,
                    parsed.overview.get(attribute),
                )

    def _store_log_overview(self, parsed, has_detected_annealing, overwrite) -> None:
        if self.overview is None:
            self.overview = RTPOverview()
        annealing_fields = (
            'annealing_pressure',
            'annealing_time',
            'annealing_temperature',
            'annealing_ar_flow',
            'annealing_n2_flow',
            'annealing_ph3_in_ar_flow',
            'annealing_nh3_in_ar_flow',
            'annealing_h2s_in_ar_flow',
        )
        if has_detected_annealing:
            if overwrite or self.overview.no_dwell_steps is None:
                self.overview.no_dwell_steps = sum(
                    1
                    for step in parsed.steps
                    if re.match(
                        r'^\s*(?:\d+(?:st|nd|rd|th)\s+)?(?:dwell|anneal(?:ing)?)\b',
                        str(step.name or '').lower(),
                    )
                )
            self._set_overview_fields(
                parsed,
                overwrite,
                (*annealing_fields, 'total_heating_time', 'total_cooling_time'),
            )
        else:
            if overwrite or self.overview.no_dwell_steps is None:
                self.overview.no_dwell_steps = 0
            if overwrite:
                for attribute in annealing_fields:
                    setattr(self.overview, attribute, None)

        self._set_overview_fields(
            parsed,
            overwrite,
            ('total_heating_time', 'total_cooling_time', 'end_of_process_temperature'),
        )

    def _create_step_from_log(self, parsed_step):
        step = DTURTPSteps(name=parsed_step.name)
        step.step_overview = RTPStepOverview(
            duration=parsed_step.duration_s,
            step_ar_flow=parsed_step.ar_flow_m3_s,
            step_n2_flow=parsed_step.n2_flow_m3_s,
            step_ph3_in_ar_flow=parsed_step.ph3_in_ar_flow_m3_s,
            step_nh3_in_ar_flow=parsed_step.nh3_in_ar_flow_m3_s,
            step_h2s_in_ar_flow=parsed_step.h2s_in_ar_flow_m3_s,
            initial_temperature=parsed_step.initial_temperature_k,
            final_temperature=parsed_step.final_temperature_k,
        )
        if parsed_step.pressure_pa is not None:
            step.step_overview.pressure = parsed_step.pressure_pa
        return step

    def _store_log_steps(self, parsed, logger, overwrite) -> None:
        if not (overwrite or not self.steps):
            return
        for parsed_step in parsed.steps:
            initial_c = parsed_step.initial_temperature_k - CELSIUS_TO_KELVIN_OFFSET
            final_c = parsed_step.final_temperature_k - CELSIUS_TO_KELVIN_OFFSET
            logger.warning(
                f'Parsed RTP step "{parsed_step.name}": '
                f'initial_temperature={initial_c:.1f} °C, '
                f'final_temperature={final_c:.1f} °C, '
                f'duration={parsed_step.duration_s:.1f} s'
            )
        self.steps = []
        for parsed_step in parsed.steps:
            self.steps.append(self._create_step_from_log(parsed_step))

    def parse_log_files(
        self,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        overwrite: bool = False,
    ) -> None:
        """Parse RTP gas and diagnostics log files and populate RTP quantities."""
        # Collect configured CX-Thermo diagnostics log paths and remove any
        # empty values.
        diagnostics_inputs = [
            path for path in (self.log_files_CXThermoDiagnostics or []) if path
        ]

        # Preserve original order while removing duplicates.
        deduped_diagnostics_inputs = []
        for path in diagnostics_inputs:
            if path not in deduped_diagnostics_inputs:
                deduped_diagnostics_inputs.append(path)

        # Both the Eklipse gas log and at least one diagnostics log are required.
        if not self.log_file_eklipse or not deduped_diagnostics_inputs:
            return

        try:
            # Resolve the primary Eklipse log and all diagnostics logs to either
            # NOMAD raw references or concrete filesystem paths.
            eklipse_kind, eklipse_ref = _resolve_log_input_path(
                archive, self.log_file_eklipse, 'csv'
            )
            resolved_diagnostics_refs = [
                _resolve_log_input_path(archive, path, 'txt')
                for path in deduped_diagnostics_inputs
            ]

            parsed = _parse_resolved_log_files(
                archive,
                logger,
                (eklipse_kind, eklipse_ref),
                resolved_diagnostics_refs,
            )
            has_detected_annealing = getattr(parsed, 'has_detected_annealing', False)

        except Exception as exc:
            # Parsing is optional enrichment: failures are logged but do not
            # abort normal processing of the archive entry.
            logger.warning(f'Failed to parse RTP log files: {exc}')
            return

        # Keep explicitly entered values by default; optionally overwrite.
        if overwrite or self.used_gases in (None, []):
            self.used_gases = parsed.used_gases
        if not self.used_gases:
            logger.warning(
                'No process gases detected in RTP logs. All used_gases are empty.'
            )

        for attribute, value in (
            ('base_pressure', parsed.base_pressure_pa),
            ('base_pressure_ballast', parsed.base_pressure_ballast_pa),
            ('rate_of_rise', parsed.rate_of_rise_pa_s),
        ):
            if (overwrite or getattr(self, attribute) is None) and value is not None:
                setattr(self, attribute, value)

        self._store_log_timeseries(parsed, overwrite)
        self._store_log_overview(parsed, has_detected_annealing, overwrite)
        self._store_log_steps(parsed, logger, overwrite)

    def _reconstruct_temperature_profile(self, logger) -> None:
        times, temps, current_time = [], [], 0
        steps_list = getattr(self, 'steps', []) or []
        for step in steps_list:
            step_overview = getattr(step, 'step_overview', None)
            if (
                step_overview is not None
                and isinstance(step_overview.initial_temperature, ureg.Quantity)
                and isinstance(step_overview.final_temperature, ureg.Quantity)
                and isinstance(step_overview.duration, ureg.Quantity)
            ):
                temps.append(step_overview.initial_temperature.to('celsius').magnitude)
                times.append(current_time)
                current_time += step_overview.duration or 0
                temps.append(step_overview.final_temperature.to('celsius').magnitude)
                times.append(current_time)
        if not times or not temps:
            _warn_once(
                self,
                '_warned_empty_reconstructed_temperature_profile',
                logger,
                'No valid steps found to construct temperature profile. '
                'Temperature profile will be empty.',
            )
        self._time = times
        self._temperature_profile = temps

    def _normalize_temperature_profile(self, logger) -> None:
        log_time_s = getattr(self, '_log_time_s', []) or []
        log_temp_c = getattr(self, '_log_temperature_c', []) or []
        if log_time_s and log_temp_c and len(log_time_s) == len(log_temp_c):
            self._time = log_time_s
            self._temperature_profile = log_temp_c
            return
        if not log_time_s or not log_temp_c:
            _warn_once(
                self,
                '_warned_reconstruct_temperature_profile',
                logger,
                'Temperature timeseries data from logs not available '
                'or incomplete. Reconstructing profile from step '
                'definitions.',
            )
        self._reconstruct_temperature_profile(logger)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTP` class.

        Order of operations, and why:
          1. Parse log files first - everything else (steps, overview fields,
             timeseries arrays) is derived from this.
          2. Generic schema normalization (base-class bookkeeping).
          3. Explicitly normalize subsections that NOMAD's base normalize()
             does not reliably cascade into: steps (ramps + partial
             pressures) and overview (annealing partial pressures). These
             are grouped together since they're the same kind of operation.
          4. lab_id default.
          5. Phase segments + temperature array fallback - these depend on
             steps already being parsed/normalized above (step 1 and 3).
          6. RTP-specific derived state: step source syncing, material space
             autofill, library creation.
          7. Plotting - depends on phase segments, temperature/gas/pressure
             arrays, and overview.end_of_process_temperature all being
             settled by this point.
          8. Results population for periodic-table filtering.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        # 1. Parse log files (populates used_gases, base pressures, overview
        # fields, raw timeseries arrays, and rebuilds self.steps).
        has_temperature_input = bool(self.log_files_CXThermoDiagnostics)
        if self.log_file_eklipse and has_temperature_input and self.process_log_files:
            self.parse_log_files(
                archive,
                logger,
                overwrite=bool(self.overwrite_existing_data),
            )

        # 2. Generic schema normalization.
        super().normalize(archive, logger)

        # 3. Explicit subsection normalization. NOMAD's base normalize() does
        # not reliably cascade into these, so they're invoked directly here,
        # right next to each other since they're the same kind of operation
        # (compute derived quantities for a subsection that was just
        # populated with raw values in step 1).
        for step in getattr(self, 'steps', []) or []:
            step.normalize(archive, logger)
        if self.overview is not None:
            self.overview.normalize(archive, logger)

        # 4. Populate lab_id according to generated name.
        if self.lab_id is None:
            self.lab_id = self.name.replace(' ', '_')

        # 5. Phase segments + temperature profile fallback.
        # Depends on parse_log_files() (step rebuild + _log_phase_segments)
        # and the step.normalize() loop above having already run.
        self._phase_segments = self._build_phase_segments()
        self._normalize_temperature_profile(logger)

        # 6. RTP-specific derived state: source syncing, material space,
        # library creation.
        self._sync_step_sources_from_used_gases(
            overwrite=bool(self.overwrite_existing_data)
        )
        self._autofill_material_space()
        if self.overview is not None:
            self.overview.normalize(archive, logger)
            self.add_libraries(archive, logger)

        # 7. Plotting. Depends on phase segments (step 5), the timeseries
        # arrays (step 1/5), and overview.end_of_process_temperature (step 1)
        # all being settled.
        self.figures = []
        self.plot_temperature_profile()
        self.plot_gas_flows_profile()
        self.plot_pressure_profile()
        self.plot_susceptor()

        # 8. Populate results with material elements for periodic table
        # filtering.
        if self.overview is not None and self.overview.material_space:
            if archive.results is None:
                archive.results = Results()
            if archive.results.material is None:
                archive.results.material = Material()
            elements = self.overview.material_space.split('-')
            archive.results.material.elements = elements
