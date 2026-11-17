from datetime import UTC, datetime
from unittest.mock import Mock

from nomad.datamodel.datamodel import EntryArchive

from nomad_dtu_nanolab_plugin.schema_packages.instrument import (
    BigMaintainance,
    ChamberGeometry,
    DtuSputterInstrument,
    MountedTarget,
    StatusChangeSputtersystem,
    TargetChange,
)
from nomad_dtu_nanolab_plugin.schema_packages.target import DTUTarget


def test_big_maintenance_copies_latest_geometry_as_of_its_date():
    instrument = DtuSputterInstrument()
    instrument.geometry = [
        ChamberGeometry(
            date=datetime(2024, 1, 1, tzinfo=UTC),
            chamber_size_3D=[1.0, 2.0, 3.0],
        ),
        ChamberGeometry(
            date=datetime(2026, 1, 1, tzinfo=UTC),
            chamber_size_3D=[4.0, 5.0, 6.0],
        ),
        ChamberGeometry(
            date=datetime(2025, 1, 1, tzinfo=UTC),
            chamber_size_3D=[7.0, 8.0, 9.0],
        ),
    ]
    maintenance = BigMaintainance(date_of_change=datetime(2025, 6, 1, tzinfo=UTC))
    instrument.status_of_system = [maintenance]

    maintenance.normalize(EntryArchive(), Mock())

    assert not hasattr(StatusChangeSputtersystem(), 'geometry')
    assert maintenance.geometry.date == datetime(2025, 1, 1, tzinfo=UTC)
    assert maintenance.geometry.chamber_size_3D.to('m').magnitude.tolist() == [
        7.0,
        8.0,
        9.0,
    ]


def test_big_maintenance_transfers_edited_geometry_to_instrument_history():
    instrument = DtuSputterInstrument()
    previous_geometry = ChamberGeometry(
        date=datetime(2025, 1, 1, tzinfo=UTC),
        chamber_size_3D=[1.0, 2.0, 3.0],
    )
    instrument.geometry = [previous_geometry]
    maintenance = BigMaintainance(
        date_of_change=datetime(2025, 6, 1, tzinfo=UTC),
        geometry=ChamberGeometry(chamber_size_3D=[4.0, 5.0, 6.0]),
        transfer_geometry_now=True,
    )
    instrument.status_of_system = [maintenance]
    previous_geometry_count = len(instrument.geometry)

    maintenance.normalize(EntryArchive(), Mock())

    assert instrument.geometry[0] is previous_geometry
    assert len(instrument.geometry) == previous_geometry_count + 1
    assert instrument.geometry[-1].date == datetime(2025, 6, 1, tzinfo=UTC)
    assert instrument.geometry[-1].chamber_size_3D.to('m').magnitude.tolist() == [
        4.0,
        5.0,
        6.0,
    ]
    assert maintenance.geometry.date is None
    assert maintenance.transfer_geometry_now is False


def test_big_maintenance_overwrites_latest_geometry_from_same_day():
    instrument = DtuSputterInstrument()
    existing_geometry = ChamberGeometry(
        date=datetime(2025, 6, 1, 8, tzinfo=UTC),
        chamber_size_3D=[1.0, 2.0, 3.0],
    )
    instrument.geometry = [existing_geometry]
    maintenance = BigMaintainance(
        date_of_change=datetime(2025, 6, 1, 16, tzinfo=UTC),
        geometry=ChamberGeometry(chamber_size_3D=[4.0, 5.0, 6.0]),
        transfer_geometry_now=True,
    )
    instrument.status_of_system = [maintenance]
    logger = Mock()

    maintenance.normalize(EntryArchive(), logger)

    assert len(instrument.geometry) == 1
    assert instrument.geometry[0] is not existing_geometry
    assert instrument.geometry[0].date == datetime(2025, 6, 1, 16, tzinfo=UTC)
    assert instrument.geometry[0].chamber_size_3D.to('m').magnitude.tolist() == [
        4.0,
        5.0,
        6.0,
    ]
    logger.warning.assert_called_once()


def test_target_change_adds_complete_mounted_target_snapshot():
    instrument = DtuSputterInstrument()
    source_1_target = DTUTarget(lab_id='Ag_T_001')
    source_3_target = DTUTarget(lab_id='Au_T_002')
    source_4_target = DTUTarget(lab_id='Cu_T_003')
    updated_source_1_target = DTUTarget(lab_id='Al_T_004')
    initial_target_change = TargetChange(
        date_of_change=datetime(2025, 6, 1, tzinfo=UTC),
        source_1_changed=True,
        source_1_target=source_1_target,
        source_3_changed=True,
        source_3_target=source_3_target,
        source_4_changed=True,
        source_4_target=source_4_target,
    )
    target_change = TargetChange(
        date_of_change=datetime(2025, 7, 1, tzinfo=UTC),
        source_1_changed=True,
        source_1_target=updated_source_1_target,
        source_3_changed=False,
        source_4_changed=False,
    )
    instrument.status_of_system = [initial_target_change, target_change]
    logger = Mock()

    initial_target_change.normalize(EntryArchive(), logger)
    target_change.normalize(EntryArchive(), logger)
    target_change.normalize(EntryArchive(), logger)

    assert [
        (
            entry.source_1_target,
            entry.source_3_target,
            entry.source_4_target,
        )
        for entry in instrument.mountedTargets
    ] == [
        (source_1_target, source_3_target, source_4_target),
        (updated_source_1_target, source_3_target, source_4_target),
    ]
    assert all(
        entry.date == date
        for entry, date in zip(
            instrument.mountedTargets,
            (
                datetime(2025, 6, 1, tzinfo=UTC),
                datetime(2025, 7, 1, tzinfo=UTC),
            ),
        )
    )


def test_target_change_button_overwrites_mounted_targets_from_same_day():
    instrument = DtuSputterInstrument()
    existing_target = DTUTarget(lab_id='Ag_T_001')
    updated_target = DTUTarget(lab_id='Al_T_004')
    instrument.mountedTargets = [
        MountedTarget(
            date=datetime(2025, 6, 1, 8, tzinfo=UTC),
            source_1_target=existing_target,
        )
    ]
    target_change = TargetChange(
        date_of_change=datetime(2025, 6, 1, 16, tzinfo=UTC),
        source_1_changed=True,
        source_1_target=updated_target,
        source_3_changed=False,
        source_4_changed=False,
        transfer_targets_now=True,
    )
    instrument.status_of_system = [target_change]

    target_change.normalize(EntryArchive(), Mock())

    assert len(instrument.mountedTargets) == 1
    assert instrument.mountedTargets[0].date == datetime(2025, 6, 1, 16, tzinfo=UTC)
    assert instrument.mountedTargets[0].source_1_target == updated_target
    assert target_change.transfer_targets_now is False
