from typing import TYPE_CHECKING

import numpy as np
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.basesections import (
    CompositeSystemReference,
    Experiment,
    ExperimentStep,
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import MEnum, Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.mapping.schema import (
    MappingResult,
    RectangularSampleAlignment,
)
from nomad_measurements.utils import create_archive

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    DtuNanolabMeasurement,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package(name='DTU RT measurement schema')


class RTSpectrum(ArchiveSection):
    """
    A single reflection or transmission spectrum measured at a specific configuration.
    """

    m_def = Section(
        description='Single R or T spectrum with measurement geometry information.',
    )

    spectrum_type = Quantity(
        type=MEnum('Reflection', 'Transmission'),
        description='Type of spectrum: Reflection (R) or Transmission (T).',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
        ),
    )

    wavelength = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        unit='nm',
        description='Wavelength array in nanometers.',
    )

    intensity = Quantity(
        type=np.dtype(np.float64),
        shape=['*'],
        description='Intensity values (%R or %T).',
    )

    detector_angle = Quantity(
        type=np.float64,
        unit='degree',
        description='Detector angle in degrees.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    sample_angle = Quantity(
        type=np.float64,
        unit='degree',
        description='Sample angle in degrees.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
        ),
    )

    polarization = Quantity(
        type=MEnum('s', 'p', 'unpolarized(p-biased)'),
        description='Polarization state of the measurement.',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.EnumEditQuantity,
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `RTSpectrum` class.
        """
        super().normalize(archive, logger)


class RTResult(MappingResult):
    """
    Results from a single spatial position containing multiple R/T spectra.
    """

    m_def = Section(
        description='RT measurement results at a specific position on the sample.',
    )

    spectra = SubSection(
        section_def=RTSpectrum,
        repeats=True,
        description='List of R and/or T spectra measured at this position.',
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        Normalizes the results data for the RT measurement.
        """
        super().normalize(archive, logger)
        # TODO: Add code for calculating the relative positions of the measurements.


class DTUSampleAlignment(RectangularSampleAlignment):
    m_def = Section(
        description='The alignment of the sample on the stage.',
    )


class DtuAutosamplerMeasurement(Experiment, Schema):
    """
    Base Experiment class for Agilent Cary autosampler measurements.

    This class handles the parsing of data and config files from the Agilent Cary
    7000 UMS autosampler and creates individual measurement archives for each
    sample/library found in the data.
    """

    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Autosampler Measurement',
        description='Experiment container for autosampler R/T measurements',
    )

    data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Data file (CSV with R/T spectra)',
        },
        description='CSV file containing all R and T spectra for different samples and positions',
    )

    config_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Config/Grid file (CSV)',
        },
        description='CSV file containing the grid/position metadata mapping',
    )

    raw_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'Raw instrument batch file (.bsw)',
        },
        description="""
            Raw binary file from the Agilent Cary 7000 UMS instrument
            (for bookkeeping and data provenance).
        """
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `DtuAutosamplerMeasurement` class.

        This method:
        1. Parses the data and config files using autosampler_reader
        2. Groups data by sample/library
        3. Creates separate RTMeasurement archives for each library
        4. Adds them as steps to this experiment
        """
        super().normalize(archive, logger)

        if not self.data_file or not self.config_file:
            logger.warning(
                'Both data_file and config_file are required for autosampler measurements.'
            )
            return

        # Import here to avoid circular dependencies
        from nomad_dtu_nanolab_plugin import autosampler_reader

        try:
            # Parse files using autosampler_reader
            with archive.m_context.raw_file(self.data_file) as data_f:
                with archive.m_context.raw_file(self.config_file) as config_f:
                    collects = autosampler_reader.parse_file(
                        data_f.name, config_f.name
                    )

            # Group measurements by sample
            samples = autosampler_reader.group_samples(collects)

            # Group measurements by position for each sample
            library_data = autosampler_reader.group_measurements_position(samples)

            measurements: list[ExperimentStep] = []

            # Create a measurement archive for each library
            for library_id, position_data in library_data.items():
                # Create RTMeasurement instance
                measurement = RTMeasurement(
                    name=f'{library_id} RT Measurement',
                )

                # Create results for each position
                results = []
                for position_key, multi_measurement in position_data.items():
                    result = RTResult(
                        name=f'Position {position_key}',
                    )

                    # Add position coordinates
                    if multi_measurement.position_x is not None:
                        result.position_x = multi_measurement.position_x * ureg('mm')
                    if multi_measurement.position_y is not None:
                        result.position_y = multi_measurement.position_y * ureg('mm')

                    # Create spectra from measurements
                    spectra = []
                    for single_meas in multi_measurement.measurements:
                        # Determine spectrum type from metadata
                        meas_type = single_meas.metadata.get('MeasurementType', 'Unknown')
                        if meas_type == 'T':
                            spectrum_type = 'Transmission'
                        elif meas_type == 'R':
                            spectrum_type = 'Reflection'
                        else:
                            logger.warning(f'Unknown measurement type: {meas_type}')
                            continue

                        spectrum = RTSpectrum(
                            spectrum_type=spectrum_type,
                            wavelength=single_meas.data['Wavelength'].values * ureg('nm'),
                            intensity=single_meas.data['Intensity'].values,
                        )

                        # Extract measurement geometry from metadata
                        if 'DetectorAngle' in single_meas.metadata:
                            spectrum.detector_angle = (
                                float(single_meas.metadata['DetectorAngle']) * ureg('degree')
                            )
                        if 'SampleAngle' in single_meas.metadata:
                            spectrum.sample_angle = (
                                float(single_meas.metadata['SampleAngle']) * ureg('degree')
                            )
                        if 'Polarization' in single_meas.metadata:
                            spectrum.polarization = single_meas.metadata['Polarization']

                        spectra.append(spectrum)

                    result.spectra = spectra
                    results.append(result)

                measurement.results = results

                # Link to sample using lab_id
                measurement.samples = [CompositeSystemReference(lab_id=library_id)]

                # Create archive
                measurement_ref = create_archive(
                    measurement,
                    archive,
                    f'{library_id}_rt_measurement.archive.json',
                )

                measurements.append(
                    ExperimentStep(
                        name=f'{library_id} measurement',
                        activity=measurement_ref,
                    )
                )

            self.steps = measurements

            logger.info(
                f'Created {len(measurements)} RT measurement archives from autosampler data.'
            )

        except Exception as e:
            logger.error(f'Error parsing autosampler data: {e}', exc_info=True)


class RTMeasurement(DtuNanolabMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='RT Measurement',
    )

    results = SubSection(
        section_def=RTResult,
        repeats=True,
    )
    sample_alignment = SubSection(
        section_def=DTUSampleAlignment,
        description='The alignment of the sample.',
    )

    def plot(self) -> None:
        """
        add a plot of the RT measurement results.
        """
        # TODO: Implement plotting of R/T spectra
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
