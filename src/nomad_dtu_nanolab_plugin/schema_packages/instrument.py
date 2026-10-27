from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    ELNAnnotation,
    ELNComponentEnum,
    Filter,
    SectionProperties,
)
from nomad.datamodel.metainfo.basesections import Instrument
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Datetime, MEnum, Package, Quantity, Section, SubSection

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.target import DTUTarget

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU customised Instrument scheme')


class ExternalInstrument(Instrument, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='external Instrument',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'lab_id',
                    'method',
                    'web_reference',
                    'responsible_person_instrument',
                    'responsible_person_group',
                    'description',
                ],
                visible=Filter(
                    exclude=[
                        'datetime',
                    ]
                ),
            )
        ),
    )
    method = Quantity(
        type=str,
        shape=['*'],
        description='The measurement method of this instrument.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(
                suggestions=[
                    'EDX',
                    'XRD',
                    'XPS',
                    'R/T',
                    'Ellipsometry',
                    'Raman',
                    'PL',
                    'Other',
                ]
            ),
        ),
    )
    responsible_person_instrument = Quantity(
        type=str,
        shape=['*'],
        description="""
        The external person responsible for this Instrument.
        Please add Email
        """,
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    responsible_person_group = Quantity(
        type=str,
        shape=['*'],
        description='The group responsible for this Instrument.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    web_reference = Quantity(
        type=str,
        shape=['*'],
        description='Web reference for this Instrument. If possible Labadvisor',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUInstrument` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)


class GasInlet(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'gas_inlet_position',
                    'gas_inlet_direction_vector',
                    'gas_inlet_pipe_diameter',
                    'description',
                ],
            ),
        ),
    )
    gas_inlet_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    gas_inlet_direction_vector = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    gas_inlet_pipe_diameter = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
        ),
        unit='m',
    )


class SputterSource(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'source_type',
                    'date_of_installation',
                    'height_of_source',
                    'set_angle',
                    'rotation',
                    'pointed_towards',
                    'distance_to_substrate',
                    'base_position',
                ],
            ),
        ),
    )
    base_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    date_of_installation = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    source_type = Quantity(
        type=str,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(suggestions=['Taurus', 'Magkeeper', 'Other']),
        ),
    )
    pointed_towards = Quantity(
        type=np.float64,
        shape=(2,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    height_of_source = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    distance_to_substrate = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    set_angle = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )
    rotation = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree',
        ),
        unit='rad',
    )


class OptixMeasurement(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'optix_position',
                    'description',
                ],
            ),
        ),
    )
    optix_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )


class OesMeasurement(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'oes_identifier',
                    'oes_position',
                    'description',
                ],
            ),
        ),
    )
    oes_identifier = Quantity(
        type=str,
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    oes_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )


class SCrackerSource(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_installation',
                    'S_cracker_extension_into_chamber',
                    'S_cracker_mounting_height',
                    'nozzle_position',
                    'pointed_towards',
                    'distance_to_substrate',
                    'base_position',
                    'description',
                ],
            ),
        ),
    )
    base_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    date_of_installation = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    nozzle_position = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    pointed_towards = Quantity(
        type=np.float64,
        shape=(2,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    distance_to_substrate = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    S_cracker_extension_into_chamber = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    S_cracker_mounting_height = Quantity(
        type=np.float64,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )


class ChamberGeometry(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date',
                    'chamber_size_3D',
                    'chamber_picture',
                    'aluminum_covers',
                    'description',
                    'source',
                    'sulfur_cracker',
                    'Inert_gas_inlet',
                    'Reactive_gas_inlet',
                ],
            ),
        ),
    )
    date = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    chamber_size_3D = Quantity(
        type=np.float64,
        shape=(3,),
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='cm',
        ),
        unit='m',
    )
    chamber_picture = Quantity(
        type=str,
        description='A picture of the chamber geometry.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
    )
    aluminum_covers = Quantity(
        type=bool,
        description='Whether aluminum covers are used in the chamber.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source = SubSection(
        section_def=SputterSource,
        repeats=True,
    )
    sulfur_cracker = SubSection(
        section_def=SCrackerSource,
        repeats=False,
    )
    optix = SubSection(
        section_def=OptixMeasurement,
        repeats=False,
    )
    OES = SubSection(
        section_def=OesMeasurement,
        repeats=True,
    )
    Inert_gas_inlet = SubSection(
        section_def=GasInlet,
        repeats=False,
    )
    Reactive_gas_inlet = SubSection(
        section_def=GasInlet,
        repeats=False,
    )


class StatusChangeSputtersystem(ArchiveSection):
    m_def = Section()
    date_of_change = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    comment_about_change = Quantity(
        type=str,
        a_eln=ELNAnnotation(component=ELNComponentEnum.RichTextEditQuantity),
    )


class PurgeAndCleaning(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'number_of_purge_cycles',
                    'time_per_purge_cycles',
                    'pressure_during_purge',
                    'detector_alarm',
                    'sulfur_cracker_refilled',
                    'comment_about_change',
                    'description',
                ],
            ),
        ),
    )
    sulfur_cracker_refilled = Quantity(
        type=bool,
        description='Whether the sulfur cracker was refilled.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    number_of_purge_cycles = Quantity(
        type=np.float64,
        description='Number of purge cycles automatically performed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity),
    )
    time_per_purge_cycles = Quantity(
        type=np.float64,
        description='Time per purge cycle.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity, defaultDisplayUnit='minute'
        ),
        unit='s',
    )
    detector_alarm = Quantity(
        type=bool,
        description='Whether the detector alarm went off during purge.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    pressure_during_purge = Quantity(
        type=np.float64,
        description='Maximum pressure during purge.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mbar',
        ),
        unit='kg/(m*s^2)',
    )


class QuickCleaning(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'vacuumed',
                    'other_cleaning_methods',
                    'comment_about_change',
                ],
            ),
        ),
    )
    vacuumed = Quantity(
        type=bool,
        description='Whether the chamber was vacuumed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    other_cleaning_methods = Quantity(
        type=str,
        description='Other cleaning methods used.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RichTextEditQuantity),
    )


class TargetChange(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'source_1_changed',
                    'source_1_target',
                    'source_3_changed',
                    'source_3_target',
                    'source_4_changed',
                    'source_4_target',
                    'comment_about_change',
                ],
            ),
        ),
    )
    source_1_changed = Quantity(
        type=bool,
        description='Whether the target in source 1 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_3_changed = Quantity(
        type=bool,
        description='Whether the target in source 3 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_4_changed = Quantity(
        type=bool,
        description='Whether the target in source 4 was changed.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    source_1_target = Quantity(
        type=DTUTarget,
        description='A reference to a NOMAD Target entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='composite system reference',
        ),
    )
    source_4_target = Quantity(
        type=DTUTarget,
        description='A reference to a NOMAD Target entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='composite system reference',
        ),
    )
    source_3_target = Quantity(
        type=DTUTarget,
        description='A reference to a NOMAD Target entry.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='composite system reference',
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)

        instrument = self.m_parent
        if not isinstance(instrument, DtuSputterInstrument):
            logger.warning(
                'Cannot update mounted target history: target change is not '
                'attached to a sputter instrument.'
            )
            return

        mounted_targets = instrument.mountedTargets
        if mounted_targets is None:
            mounted_targets = []
            instrument.mountedTargets = mounted_targets

        previous_entries = [
            entry
            for entry in mounted_targets
            if self.date_of_change is None
            or entry.date is None
            or entry.date <= self.date_of_change
        ]
        if previous_entries:
            dated_entries = [
                entry for entry in previous_entries if entry.date is not None
            ]
            previous_entry = (
                max(dated_entries, key=lambda entry: entry.date)
                if dated_entries
                else previous_entries[-1]
            )
        else:
            previous_entry = None

        updated_targets = {}
        for source_number in (1, 3, 4):
            changed = getattr(self, f'source_{source_number}_changed')
            new_target = getattr(self, f'source_{source_number}_target')
            previous_target = (
                getattr(previous_entry, f'source_{source_number}_target')
                if previous_entry is not None
                else None
            )

            if changed is True and new_target is None:
                logger.warning(
                    'Cannot update mounted target history: Source %s is marked '
                    'changed but has no target reference.',
                    source_number,
                )
                return

            updated_targets[f'source_{source_number}_target'] = (
                new_target if changed is True else previous_target
            )

        if any(
            entry.date == self.date_of_change
            and all(
                getattr(entry, field) == target
                for field, target in updated_targets.items()
            )
            for entry in mounted_targets
        ):
            return

        mounted_targets.append(
            MountedTarget(
                date=self.date_of_change,
                **updated_targets,
            )
        )


class MountedTarget(ArchiveSection):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date',
                    'source_1_target',
                    'source_3_target',
                    'source_4_target',
                ],
            ),
        ),
    )
    date = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(component=ELNComponentEnum.DateTimeEditQuantity),
    )
    source_1_target = Quantity(
        type=DTUTarget,
        description='The target mounted on source 1.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='Source 1 target',
        ),
    )
    source_3_target = Quantity(
        type=DTUTarget,
        description='The target mounted on source 3.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='Source 3 target',
        ),
    )
    source_4_target = Quantity(
        type=DTUTarget,
        description='The target mounted on source 4.',
        a_eln=ELNAnnotation(
            component='ReferenceEditQuantity',
            label='Source 4 target',
        ),
    )


class PlattenCleaning(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'platen_cleaned',
                    'comment_about_change',
                ],
            ),
        ),
    )
    platen_cleaned = Quantity(
        type=str,
        description='The relative position of the substrate on the platen.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
            props=dict(suggestions=['A', 'B', 'C']),
        ),
    )
    method_of_cleaning = Quantity(
        type=MEnum(
            'sanding',
            'other',
        ),
        description='The cleaning method for the platen.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.RadioEnumEditQuantity),
        default='sanding',
    )


class ThermalCleaning(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'temperature',
                    'duration',
                    'comment_about_change',
                ],
            ),
        ),
    )
    temperature = Quantity(
        type=np.float64,
        description='The temperature used for thermal cleaning.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='degree_Celsius',
        ),
        unit='K',
    )
    duration = Quantity(
        type=np.float64,
        description='The duration of the thermal cleaning.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
        ),
        unit='s',
    )


class QcmMaintenance(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'qcm_1_replaced',
                    'qcm_2_replaced',
                    'comment_about_change',
                ],
            ),
        ),
    )
    qcm_1_replaced = Quantity(
        type=bool,
        description='Whether the QCM was cleaned.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )
    qcm_2_replaced = Quantity(
        type=bool,
        description='Whether the QCM was replaced.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
    )


class BigMaintainance(StatusChangeSputtersystem):
    m_def = Section(
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'date_of_change',
                    'copy_old_chamber_geometry',
                    'geometry',
                    'transfer_geometry_now',
                    'comment_about_change',
                ],
            ),
        ),
    )
    copy_old_chamber_geometry = Quantity(
        type=bool,
        description=(
            'Whether the chamber geometry was copied from the geometry history.'
        ),
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity, default=True),
    )
    geometry = SubSection(
        section_def=ChamberGeometry,
        repeats=False,
    )
    transfer_geometry_now = Quantity(
        type=bool,
        description=(
            'Append the geometry above to the sputter instrument geometry history.'
        ),
        a_eln=ELNAnnotation(
            component='ActionEditQuantity',
            label='Transfer geometry NOW',
        ),
    )

    def copy_previous_chamber_geometry(self, logger: 'BoundLogger') -> None:
        """Copy the latest geometry from the instrument's geometry history."""
        if self.copy_old_chamber_geometry is False or self.geometry is not None:
            return

        geometry_history = getattr(self.m_parent, 'geometry', None)
        if not geometry_history:
            logger.warning('Cannot copy chamber geometry: geometry history is empty.')
            return

        dated_geometries = [
            geometry
            for geometry in geometry_history
            if geometry.date is not None
            and (self.date_of_change is None or geometry.date <= self.date_of_change)
        ]
        if dated_geometries:
            previous_geometry = max(
                dated_geometries, key=lambda geometry: geometry.date
            )
        else:
            undated_geometries = [
                geometry for geometry in geometry_history if geometry.date is None
            ]
            if undated_geometries:
                previous_geometry = undated_geometries[-1]
            elif self.date_of_change is None:
                previous_geometry = geometry_history[-1]
            else:
                logger.warning(
                    'Cannot copy chamber geometry: no geometry predates this entry.'
                )
                return

        self.geometry = ChamberGeometry.m_from_dict(previous_geometry.m_to_dict())

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        super().normalize(archive, logger)
        if self.copy_old_chamber_geometry is not False and self.geometry is None:
            self.copy_previous_chamber_geometry(logger)
        if self.transfer_geometry_now:
            try:
                self.transfer_geometry_to_instrument(logger)
            finally:
                self.transfer_geometry_now = False

    def transfer_geometry_to_instrument(self, logger: 'BoundLogger') -> None:
        """Update the latest geometry or append a new dated history entry."""
        instrument = self.m_parent
        if not isinstance(instrument, DtuSputterInstrument):
            logger.warning(
                'Cannot transfer chamber geometry: maintenance is not attached '
                'to a sputter instrument.'
            )
            return
        if self.geometry is None:
            logger.warning('Cannot transfer chamber geometry: no geometry is set.')
            return
        if self.date_of_change is None:
            logger.warning(
                'Cannot transfer chamber geometry: no maintenance date is set.'
            )
            return

        geometry_entry = ChamberGeometry.m_from_dict(self.geometry.m_to_dict())
        geometry_entry.date = self.date_of_change

        geometry_history = instrument.geometry
        if geometry_history is None:
            geometry_history = []
            instrument.geometry = geometry_history

        dated_geometries = [
            (index, entry)
            for index, entry in enumerate(geometry_history)
            if entry.date is not None
        ]
        if dated_geometries:
            latest_index, latest_geometry = max(
                dated_geometries, key=lambda item: item[1].date
            )
            if latest_geometry.date.date() == geometry_entry.date.date():
                logger.warning(
                    'Overwriting the latest chamber geometry: a geometry change '
                    'already exists on %s.',
                    geometry_entry.date.date(),
                )
                geometry_history[latest_index] = geometry_entry
                return

        geometry_history.append(geometry_entry)


class DtuSputterInstrument(Instrument, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Sputter System',
        a_eln=ELNAnnotation(
            properties=SectionProperties(
                order=[
                    'name',
                    'update',
                    'time_used_chamber',
                    'latest_base_pressure',
                    'lab_id',
                    'datetime',
                    'lab_location',
                    'manufacturer',
                    'description',
                    'status_of_system',
                    'geometry',
                    'mountedTargets',
                ],
            )
        ),
    )
    datetime = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.DateTimeEditQuantity,
            label='Date of purchase',
        ),
    )
    update = Quantity(
        type=Datetime,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.DateTimeEditQuantity,
            label='Date of last update',
        ),
    )
    time_used_chamber = Quantity(
        type=np.float64,
        description="""
        The total time the chamber has been used for sputtering as of today.
          """,
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='minute',
        ),
        unit='s',
    )
    lab_location = Quantity(
        type=str,
        description='The location of the lab where this Instrument is located.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    manufacturer = Quantity(
        type=str,
        description='The manufacturer of this Instrument.',
        a_eln=ELNAnnotation(component=ELNComponentEnum.StringEditQuantity),
    )
    latest_base_pressure = Quantity(
        type=np.float64,
        shape=(),
        description='The base pressure of the sputtering chamber over time.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mbar',
        ),
        unit='kg/(m*s^2)',
    )
    status_of_system = SubSection(
        section_def=StatusChangeSputtersystem,
        repeats=True,
    )
    geometry = SubSection(
        section_def=ChamberGeometry,
        repeats=True,
    )
    mountedTargets = SubSection(
        section_def=MountedTarget,
        repeats=True,
    )

    def plot_status_timeline(self) -> None:
        """Create a timeline of the instrument and its status changes."""
        from html import escape

        import plotly.graph_objects as go

        status_entries = []
        for status_change in self.status_of_system or []:
            if status_change.date_of_change is None:
                continue
            status_entries.append(status_change)

        if not status_entries:
            return

        figure = go.Figure()
        event_positions = [
            0.92 - index * 0.84 / max(len(status_entries) - 1, 1)
            for index in range(len(status_entries))
        ]
        figure.add_shape(
            type='line',
            xref='paper',
            yref='paper',
            x0=0.5,
            x1=0.5,
            y0=0.08,
            y1=0.92,
            line={'color': '#506784', 'width': 4},
        )
        figure.add_trace(
            go.Scatter(
                x=[0.5] * len(status_entries),
                y=event_positions,
                mode='markers',
                marker={
                    'size': 12,
                    'color': '#d95f59',
                    'line': {'color': 'white', 'width': 2},
                },
                hovertemplate=(
                    '<b>%{customdata[0]}</b><br>%{customdata[1]}<extra></extra>'
                ),
                customdata=[
                    [
                        status_change.m_def.name,
                        status_change.comment_about_change or 'No comment',
                    ]
                    for status_change in status_entries
                ],
            )
        )
        for position, status_change in zip(event_positions, status_entries):
            date_text = status_change.date_of_change.strftime('%Y-%m-%d')
            status_type = escape(status_change.m_def.name)
            comment = escape(status_change.comment_about_change or 'No comment')
            figure.add_annotation(
                x=0.44,
                y=position,
                xref='paper',
                yref='paper',
                text=date_text,
                showarrow=False,
                xanchor='right',
                align='right',
                font={'size': 12, 'color': '#334155'},
            )
            figure.add_annotation(
                x=0.56,
                y=position,
                xref='paper',
                yref='paper',
                text=f'<b>{status_type}</b><br>{comment}',
                showarrow=False,
                xanchor='left',
                align='left',
                bgcolor='#f8fafc',
                bordercolor='#cbd5e1',
                borderwidth=1,
                borderpad=8,
                font={'size': 12, 'color': '#1e293b'},
            )
        figure.update_layout(
            title='Sputter system status timeline',
            xaxis={'visible': False, 'range': [0, 1]},
            yaxis={'visible': False, 'range': [0, 1]},
            height=max(400, 150 * len(status_entries)),
            margin={'l': 110, 'r': 300, 't': 70, 'b': 30},
            plot_bgcolor='white',
        )
        self.figures.append(
            PlotlyFigure(label='Status timeline', figure=figure.to_plotly_json())
        )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DTUInstrument` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        super().normalize(archive, logger)
        self.figures = []
        self.plot_status_timeline()


m_package.__init_metainfo__()
