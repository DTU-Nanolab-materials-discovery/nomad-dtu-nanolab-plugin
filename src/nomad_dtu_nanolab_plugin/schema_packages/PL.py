from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd
import plotly.express as px
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import (ELNAnnotation, ELNComponentEnum,
                                       EntryArchive)
from nomad.datamodel.metainfo.annotations import BrowserAnnotation
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.utils import merge_sections
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.basesections import (MappingMeasurement,
                                                   MappingResult)
from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger



m_package = Package(name='DTU EDX measurement schema')



class PLMappingResult(MappingResult, Schema):
    m_def = Section()

    position = Quantity(
        type=str,
        description='The position of the PL spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Position',
        ),
    )
    peak_lambda = Quantity(
        type=np.float64,
        unit='m',
        description='Peak wavelength of the PL spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Peak Lambda',
        ),
    )
    peak_intensity = Quantity(
        type=np.float64,
        unit='V',
        description='Peak intensity of the PL spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='V',
            label='Peak Intensity',
        ),
    )
    signal_intensity = Quantity(
        type=np.float64,
        description='Signal intensity of the PL spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Signal Intensity',
        ),
    )
    peak_fwhm = Quantity(
        type=np.float64,
        unit='m',
        description='Peak full width at half maximum of the PL spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Peak FWHM',
        ),
    )


    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `PLMappingResult` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)

class PLMetadata(Schema):
    m_def = Section()
    thickness = Quantity(
        type=np.float64,
        unit='m',
        description='The thickness the machine assumes for the sample',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='um',
            label='assumed Sample thickness',
        ),
    )
    wafer_diameter = Quantity(
        type=np.float64,
        unit='m',
        description='The diameter of the wafer',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
            label='wafer holder size',
        ),
    )
    scan_diameter = Quantity(
        type=np.float64,
        unit='m',
        description='The diameter of the scan',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
            label='diamer of the scan',
        ),
    )
    resolution = Quantity(
        type=np.float64,
        unit='m',
        description='The resolution of the scan',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
            label='Resolution',
        ),
    )
    scan_rate = Quantity(
        type=np.float64,
        unit='m/s',
        description='''
        The rate of the scan.
        The unit is points per second (pts/s)
        and therefore only right as long as the resolution is 1mm''',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm/s',
            label='scan rate',
        ),
    )
    used_laser = Quantity(
        type =np.float64,
        unit='m',
        description='The wavelength of the laser used',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Laser wavelength',
        ),
    )
    used_power = Quantity(
        type=np.float64,
        unit='W',
        description='The power of the laser used',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mW',
            label='Laser Power',
        ),
    )
    used_filter = Quantity(
        type=str,
        description='The filter used for the measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='used filter',
        ),
    )
    gain_factor = Quantity(
        type=np.float64,
        description='''
        The gain factor used for the measurement,
        it is unitless and scales the signal intensity
        ''',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Gain Factor',
        ),

    )
    temperature = Quantity(
        type=np.float64,
        unit='K',
        description='The temperature during the measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='C',
            label='Temperature',
        ),
    )
    center_wafelength = Quantity(
        type=np.float64,
        unit='m',
        description='The center wavelength of the measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Center Wafelength',
        ),
    )
    wavelength_range = Quantity(
        type= [np.float64],
        unit='m',
        description='The range of the wavelength',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='nm',
            label='Wafelength Range',
        ),
    )
    slit_width = Quantity(
        type=np.float64,
        unit='m',
        description='The slit width used for the measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='mm',
            label='Slit Width',
        ),
    )
    gratings = Quantity(
        type=np.float64,
        unit= 'g/m',
        description='The gratings used for the measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            defaultDisplayUnit='g/mm',
            label='Grating',
        ),
    )
    detector = Quantity(
        type=str,
        description='The detector used for the measurement',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Detector type',
        ),
    )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `PLMetadata` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)

class DTUPLMeasurement(MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='XRD Measurement',
    )
    pl_data_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'full PL file'},
    )
    pl_overview_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'PL map file'},
    )
    metadata = SubSection(
        section_def=PLMetadata,
        description='The metadata of the PL measurement',
    )
    results = SubSection(
        section_def=PLMappingResult,
        description='The PL results.',
        repeats=True,
    )


    def write_PL_metadata(
        self,
        metadata_dict: dict[str, Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:
        metadata =metadata_dict

        entry = metadata.get('Thickness', None)
        if entry is not None and self.metadata.thickness is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            thickness = float(filtered_entry) if filtered_entry else None
            self.metadata.thickness = ureg.Quantity(thickness, 'um')

        entry = metadata.get('WaferDiam', None)
        if entry is not None and self.metadata.wafer_diameter is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            waferdiam = float(filtered_entry) if filtered_entry else None
            self.metadata.wafer_diameter = ureg.Quantity(waferdiam, 'mm')

        entry = metadata.get('ScanDiam', None)
        if entry is not None and self.metadata.scan_diameter is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            scandiam = float(filtered_entry) if filtered_entry else None
            self.metadata.scan_diameter = ureg.Quantity(scandiam, 'mm')

        entry = metadata.get('Resolution', None)
        if entry is not None and self.metadata.resolution is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            resolution = float(filtered_entry) if filtered_entry else None
            self.metadata.resolution = ureg.Quantity(resolution, 'mm')

        entry = metadata.get('ScanRate', None)
        if entry is not None and self.metadata.scan_rate is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            scanrate = float(filtered_entry) if filtered_entry else None
            self.metadata.scan_rate = ureg.Quantity(scanrate, 'mm/s')

        entry = metadata.get('Laser', None)
        if entry is not None and self.metadata.used_laser is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            laser = float(filtered_entry) if filtered_entry else None
            self.metadata.used_laser = ureg.Quantity(laser, 'nm')

        entry = metadata.get('Power', None)
        if entry is not None and self.metadata.used_power is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            power = float(filtered_entry) if filtered_entry else None
            self.metadata.used_power = ureg.Quantity(power, 'mW')

        entry = metadata.get('Filter', None)
        if entry is not None and self.metadata.used_filter is None:
            self.metadata.used_filter = entry

        entry = metadata.get('Gain', None)
        if entry is not None and self.metadata.gain_factor is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            gain = float(filtered_entry) if filtered_entry else None
            self.metadata.gain_factor = gain

        entry = metadata.get('Temperature', None)
        if entry is not None and self.metadata.temperature is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            temperature = float(filtered_entry) if filtered_entry else None
            self.metadata.temperature = ureg.Quantity(temperature, 'C')

        entry = metadata.get('Centerwavelength', None)
        if entry is not None and self.metadata.center_wafelength is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            centerwavelength = float(filtered_entry) if filtered_entry else None
            self.metadata.center_wafelength = ureg.Quantity(centerwavelength, 'nm')

        entry = metadata.get('Range', None)
        if entry is not None and self.metadata.wavelength_range is None:
            parts = entry.split('to')
            cleaned_parts = []
            for part in parts:
                filtered_chars = [c for c in part if c.isdigit() or c == '.']
                cleaned_part = ''.join(filtered_chars)
                cleaned_parts.append(cleaned_part)
            wavelength_range = [float(part) for part in cleaned_parts if part]
            wavelength_quantities = [ureg.Quantity(x, 'nm') for x in wavelength_range]
            self.metadata.wavelength_range = wavelength_quantities

        entry = metadata.get('Slitwidth', None)
        if entry is not None and self.metadata.slit_width is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            slitwidth = float(filtered_entry) if filtered_entry else None
            self.metadata.slit_width = ureg.Quantity(slitwidth, 'mm')

        entry = metadata.get('Grating', None)
        if entry is not None and self.metadata.gratings is None:
            filtered_chars = [c for c in entry if c.isdigit() or c == '.']
            filtered_entry = ''.join(filtered_chars)
            gratings = float(filtered_entry) if filtered_entry else None
            self.metadata.gratings = ureg.Quantity(gratings, 'g/mm')

        entry = metadata.get('Detector', None)
        if entry is not None and self.metadata.detector is None:
            self.metadata.detector = entry


    def write_PL_by_position(
        self,
        data_dict: dict[str, Any],
        archive: 'EntryArchive',
        logger: 'BoundLogger',
    ) -> None:

        results = self.results
        if results is None:
            results = []
            for key, values in data_dict.items():

                result = PLMappingResult(
                    position=key,
                    peak_lambda=ureg.Quantity(values[0], 'nm'),
                    peak_intensity=ureg.Quantity(values[1], 'V'),
                    signal_intensity=values[2],
                    peak_fwhm=ureg.Quantity(values[3], 'nm'),
                )
                result.normalize(archive, logger)
                results.append(result)
        else:
            result=[]
            #add the information accoring to the key to the respective subsections


    def plot_overview(self, data_df: pd.DataFrame ) -> None:
        # Sort the DataFrame by 'X' and 'Y' columns
        data_df = data_df.sort_values(by=['X', 'Y'], key=lambda col: col.astype(float))

        # Iterate over each column except 'X' and 'Y'
        for column in data_df.columns:
            if column not in ['X', 'Y']:
                fig = px.scatter(
                    data_df, x='X',
                    y='Y',
                    color=column,
                    size=None,
                    title=f'Scatter Plot of {column}'
                    )
                fig.update_traces(marker=dict(size=20))  #Set size for all markers

                plot_json = fig.to_plotly_json()
                plot_json['config'] = dict(
                    scrollZoom=False,
                )
                self.figures.append(
                    PlotlyFigure(
                        label=column,
                        figure=plot_json,
                    )
                )



    def plot_spectra(self) -> None:
        #add the plotting stuff here
        data_lines = []
        #problem : how toplot these in their subsections


    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUXRDMeasurement` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.pl_data_file:
            with archive.m_context.raw_file(self.pl_data_file) as file:
                lines = file.readlines()

            metadata_lines = []
            data_lines = []
            data_section = False

            for line in lines:
                stripped_line = line.strip()
                if stripped_line == 'DATA:':
                    data_section = True
                    continue
                if data_section:
                    data_lines.append(stripped_line)
                else:
                    metadata_lines.append(stripped_line)

            metadata_dict = {}

            # Transform metadata_lines into dictionary entries
            for line in metadata_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.replace(' ', '')
                    value = value.replace(' ', '')
                    metadata_dict[key] = value


            data_dict = {'Wavelength in nm': []}
            current_header = 'Wavelength in nm'
            data_dict[current_header] = []

            for line in data_lines:
                if line.startswith('POS:'):
                    # Extract the header from the line
                    current_header = line.split('POS:')[1].strip()
                    data_dict[current_header] = []
                else:
                    data_dict[current_header].append(line)

            data_dict = {k: v for k, v in data_dict.items() if v}



            self.write_PL_metadata(metadata_dict, archive, logger)
            #the data_dict has all the spectra information with the position as the key
            #use the dict to plot all the spectra in the respective subsections
            #do i need a write section? or just the plot section?
            self.figures =[]
            self.plot_spectra()




        if self.pl_overview_file:
            metadata_lines = []
            data_lines = []

            with archive.m_context.raw_file(self.pl_overview_file) as file:
                lines = file.readlines()

            for line in lines:
                stripped_line = line.strip()
                if not stripped_line:
                    data_section = True
                    continue
                if data_section:
                    # Split the line into columns based on ';' delimiter
                    columns = stripped_line.split(';')
                    data_lines.append(columns)
                else:
                    metadata_lines.append(stripped_line)

            metadata_dict = {}
            # Transform metadata_lines into dictionary entries
            for line in metadata_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.replace(' ', '')
                    value = value.replace(' ', '')
                    metadata_dict[key] = value

            # create a df from the data_lines (easier for plotting)
            data_df = pd.DataFrame(data_lines)
            #some cleanup of the dataframe
            data_df.columns = data_df.iloc[0]
            data_df = data_df.drop([0, 1])
            data_df.columns = data_df.columns.str.replace(' ', '').str.replace('\t', '')
            data_df = data_df.apply(pd.to_numeric, errors='ignore')

            # make a dict for writing into the subsections
            data_dict = {}
            for index, row in data_df.iterrows():
                key = f"{row['X']},{row['Y']}"
                values = row.drop(['X', 'Y']).tolist()
                data_dict[key] = values

            self.write_PL_metadata(metadata_dict, archive, logger)
            self.write_PL_by_position(data_dict, archive, logger)
            self.figures =[]
            self.plot_overview(data_df)
            #add the plots of the spectra to the subsections


        super().normalize(archive, logger)


m_package.__init_metainfo__()