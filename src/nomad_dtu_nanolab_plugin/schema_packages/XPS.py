from typing import TYPE_CHECKING

import pandas as pd
from nomad.datamodel.data import Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from nomad_measurements.utils import merge_sections
from structlog.stdlib import BoundLogger

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory
from nomad_dtu_nanolab_plugin.schema_packages.basesections import (
    MappingMeasurement,
    MappingResult,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import EntryArchive
    from structlog.stdlib import BoundLogger

m_package = Package()  # fill out later

class XPSfittedPeak(Schema):
    m_def = Section()

    origin = Quantity(
        type=str,
        description='The peak type',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Peak',
        ),
    )
    be_position = Quantity(
        type=float,
        unit='(kg*m^2)/(s^2)',
        description='The position of the peak in binding energy',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Position',
            defaultDisplayUnit='eV',
        ),
    )
    intensity = Quantity(
        type=float,
        unit='1/s',
        description='The intensity of the peak',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Intensity',
            defaultDisplayUnit='cps',
        ),
    )
    fwhm = Quantity(
        type=float,
        description='The full width at half maximum of the peak',
        unit='(kg*m^2)/(s^2)',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='FWHM',
            defaultDisplayUnit='eV',
        ),
    )
    area = Quantity(
        type=float,
        description='The area of the peak',
        unit='(kg*m^2)/(s^3)',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Area',
            defaultDisplayUnit='cps*eV',
        ),
    )
    atomic_percent = Quantity(
        type=float,
        description='The atomic percent of the peak',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Atomic %',
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

class XPS_derived_composition(Schema):
    m_def = Section()

    element = Quantity(
        type=str,
        description='The element of the composition',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Element',
        ),
    )
    atomic_percent = Quantity(
        type=float,
        description='The atomic percent of the element',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Atomic %',
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

class XPSMappingResult(MappingResult, Schema):
    m_def = Section()

    position = Quantity(
        type=str,
        description='The position of the XPS spectrum',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.StringEditQuantity,
            label='Position',
        ),
    )
    peaks= SubSection(
        section_def=XPSfittedPeak,
        description='The fitted peaks of the XPS spectrum',
        repeats=True,
    )
    composition = SubSection(
        section_def=XPS_derived_composition,
        description='The composition according to the XPS analysis by element',
        repeats=True,
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


class XPSMetadata(Schema):
    m_def = Section()

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalizer for the `PLMetadata` class.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """

        super().normalize(archive, logger)


class DTUXPSMeasurement(MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='XRD Measurement',
    )
    native_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'native file'},
    )
    spectra_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={'component': 'FileEditQuantity', 'label': 'exported spectra text file'},
    )
    analysis_file = Quantity(
        type=str,
        a_browser=BrowserAnnotation(adaptor='RawFileAdaptor'),
        a_eln={
            'component': 'FileEditQuantity',
            'label': 'exported analysis text file',
        },
    )
    metadata = SubSection(
        section_def=XPSMetadata,
        description='The metadata of the ellipsometry measurement',
        # need the native file and a way to open it to extract the metadata
    )
    results = SubSection(
        section_def=XPSMappingResult,
        description='The PL results.',
        repeats=True,
        # add the spectra here
    )

    def read_XPS_analysis(self, filename: str) -> None:
        '''"Read data and coordinates from an XPS datafile.
          The file should be an csv (.txt) file."'''
        # read the file
        file = pd.read_csv(filename,
                           encoding = 'ANSI',
                           engine='python',
                           sep='delimiter',
                           header = None,
                           skiprows = 29)
        file.drop(file.iloc[4::7].index, inplace=True)
        file.reset_index(drop = True)

        # get amount of peaks
        peaknumb = []
        for i in range(0, len(file), 6):
            peaknumb.append(int(file.iloc[i][0].split()[8].replace(";","")))

        # remove useless rows
        file.drop(file.iloc[0::6].index, inplace=True)
        file.reset_index(drop = True)

        # get data from remaining rows
        full_peaklist = []
        peaklist = []
        coordlist = []
        datalist = []
        for i in range(0, len(file), 5):
            # load peak type and coordinates and fix formatting
            split_string = file.iloc[i][0].split()
            relevant_part = ' '.join(split_string[5:])
            cleaned_part = relevant_part.replace("VALUE='", "").replace("';", "")
            peaktype = cleaned_part
            # Process x-coordinate
            xcoord_str = file.iloc[i+1][0].split()[5]
            xcoord_cleaned = xcoord_str.replace("VALUE=", "").replace(";", "")
            xcoord = float(xcoord_cleaned)

            # Process y-coordinate
            ycoord_str = file.iloc[i+2][0].split()[5]
            ycoord_cleaned = ycoord_str.replace("VALUE=", "").replace(";", "")
            ycoord = float(ycoord_cleaned)
            coords = [xcoord, ycoord]

            # load data
            data = file.iloc[i+3][0].split()[2::]
            data.append(file.iloc[i+4][0].split()[2::][0])
            # fix data formatting
            data = [j.replace(",","") for j in data]
            data = [round(float(j),3) for j in data]

            full_peaklist.append(peaktype)
            peaklist.append(peaktype.split()[0])
            coordlist.append(coords)
            datalist.append(data)
        unique_coords = list(set(tuple(coord) for coord in coordlist))

        # create data dataframe
        dataframe = pd.DataFrame(datalist, columns = ['Intensity (counts)',
                                                      'Atomic %',
                                                      'Area (counts*eV)',
                                                      'FWHM (eV)',
                                                      'Peak BE (eV)'])

        # modify some values
        # convert KE to BE (KE of machine X-rays is 1486.68 eV)
        dataframe['Peak BE (eV)'] = 1486.68 - dataframe['Peak BE (eV)']
        # reorder columns to be similar to Avantage
        columnorder = ['Peak BE (eV)',
                       'Intensity (counts)',
                       'FWHM (eV)',
                       'Area (counts*eV)',
                       'Atomic %']
        dataframe = dataframe.reindex(columnorder, axis=1)
        # create peak dataframe
        peaks = pd.DataFrame(peaklist, columns = ['Peak'])
        # add peak dataframe to front of data dataframe
        dataframe = pd.concat([peaks, dataframe], axis = 1)

        #handle coordinates
        coordframe = pd.DataFrame(coordlist, columns = ['X','Y'])
        coordframe['X'] = coordframe['X'] - max(coordframe['X'])/2
        coordframe['Y'] = coordframe['Y'] - max(coordframe['Y'])/2
        coordframe = coordframe/1000
        coordframe['Y'] = coordframe['Y'].values[::-1]

        unique_coords = list(set(tuple(row) for row in coordframe[['X', 'Y']].values))

        # Concatenate the two DataFrames along the columns
        merged_frame = pd.concat([coordframe, dataframe], axis=1)

        return merged_frame, unique_coords

    def write_XPS_analysis(self,
                            dataframe: pd.DataFrame,
                            coords_list: list
                              ) -> None:
        '''"Write data and coordinates to the XPS class
        with respect to the coordinates"'''
        #filter by coordinates and create small dfs
        for coord in coords_list:
            mask = dataframe.apply(lambda row: (row['X'], row['Y']) == coord, axis=1)
            coord_data = dataframe[mask]
            self.results.append(XPSMappingResult(
                position = f'{coord[0]:.3f}, {coord[1]:.3f}',
            ))

            for index, row in coord_data.iterrows():

                peak_info = XPSfittedPeak(
                    origin= ureg.Quantity(row['Peak'], 'eV'),
                    be_position= ureg.Quantity(row['Peak BE (eV)'], 'eV'),
                    intensity= ureg.Quantity(row['Intensity (counts)'], '1/s'),
                    fwhm= ureg.Quantity(row['FWHM (eV)'], 'eV'),
                    area= ureg.Quantity(row['Area (counts*eV)'], 'cps*eV'),
                    atomic_percent= row['Atomic %'],
                )
                merge_sections(self.results[-1].peaks, peak_info)







    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUXRDMeasurement` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.analysis_file is not None:
            dataframe, coords_list = self.read_XPS_analysis(self.analysis_file)
            self.write_XPS_analysis(dataframe, coords_list)



        super().normalize(archive, logger)
m_package.__init_metainfo__()
