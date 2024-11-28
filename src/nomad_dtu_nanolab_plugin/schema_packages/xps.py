import re
from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, Schema
from nomad.datamodel.datamodel import EntryArchive
from nomad.datamodel.metainfo.annotations import (
    BrowserAnnotation,
    ELNAnnotation,
    ELNComponentEnum,
)
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import Package, Quantity, Section, SubSection
from nomad.units import ureg
from scipy.interpolate import griddata
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


class XpsFittedPeak(ArchiveSection):
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
            component=ELNComponentEnum.NumberEditQuantity,
            label='Position',
            defaultDisplayUnit='eV',
        ),
    )
    intensity = Quantity(
        type=float,
        unit='1/s',
        description='The intensity of the peak',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Intensity',
            defaultDisplayUnit='cps',
        ),
    )
    fwhm = Quantity(
        type=float,
        description='The full width at half maximum of the peak',
        unit='(kg*m^2)/(s^2)',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='FWHM',
            defaultDisplayUnit='eV',
        ),
    )
    area = Quantity(
        type=float,
        description='The area of the peak',
        unit='(kg*m^2)/(s^3)',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
            label='Area',
            defaultDisplayUnit='cps*eV',
        ),
    )
    atomic_percent = Quantity(
        type=float,
        description='The atomic percent of the peak',
        a_eln=ELNAnnotation(
            component=ELNComponentEnum.NumberEditQuantity,
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


class XpsDerivedComposition(ArchiveSection):
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
            component=ELNComponentEnum.NumberEditQuantity,
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


class XpsMappingResult(MappingResult):
    m_def = Section()

    peaks = SubSection(
        section_def=XpsFittedPeak,
        description='The fitted peaks of the XPS spectrum',
        repeats=True,
    )
    composition = SubSection(
        section_def=XpsDerivedComposition,
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


class XpsMetadata(ArchiveSection):
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


class DTUXpsMeasurement(MappingMeasurement, PlotSection, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='XPS Measurement',
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
        section_def=XpsMetadata,
        description='The metadata of the ellipsometry measurement',
        # need the native file and a way to open it to extract the metadata
    )
    results = SubSection(
        section_def=XpsMappingResult,
        description='The PL results.',
        repeats=True,
        # add the spectra here
    )

    def read_XPS_analysis(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        '''"Read data and coordinates from an XPS datafile.
        The file should be an csv (.txt) file."'''
        self.add_sample_reference(self.analysis_file, archive, logger)
        # read the file
        with archive.m_context.raw_file(self.analysis_file, 'rb') as xps:
            file = pd.read_csv(
                xps,
                encoding='latin1',
                engine='python',
                sep='delimiter',
                header=None,
                skiprows=29,
            )
        file.drop(file.iloc[4::7].index, inplace=True)
        file.reset_index(drop=True)

        # get amount of peaks
        peaknumb = []
        for i in range(0, len(file), 6):
            peaknumb.append(int(file.iloc[i][0].split()[8].replace(';', '')))

        # remove useless rows
        file.drop(file.iloc[0::6].index, inplace=True)
        file.reset_index(drop=True)

        # get data from remaining rows
        full_peaklist = []
        peaklist = []
        coordlist = []
        datalist = []
        for i in range(0, len(file), 5):
            # load peak type and coordinates and fix formatting
            split_string = file.iloc[i][0].split()
            relevant_part = ' '.join(split_string[5:])
            cleaned_part = relevant_part.replace("VALUE='", '').replace("';", '')
            peaktype = cleaned_part

            # Process x-coordinate
            xcoord_str = file.iloc[i + 1][0].split()[5]
            xcoord_cleaned = xcoord_str.replace('VALUE=', '').replace(';', '')
            xcoord = float(xcoord_cleaned)

            # Process y-coordinate
            ycoord_str = file.iloc[i + 2][0].split()[5]
            ycoord_cleaned = ycoord_str.replace('VALUE=', '').replace(';', '')
            ycoord = float(ycoord_cleaned)
            coords = [xcoord, ycoord]

            # load data
            data = file.iloc[i + 3][0].split()[2::]
            data.append(file.iloc[i + 4][0].split()[2::][0])
            # fix data formatting
            data = [j.replace(',', '') for j in data]
            data = [round(float(j), 3) for j in data]

            full_peaklist.append(peaktype)
            peaklist.append(peaktype.split()[0])
            coordlist.append(coords)
            datalist.append(data)
        unique_coords = list(set(tuple(coord) for coord in coordlist))

        # create data dataframe
        dataframe = pd.DataFrame(
            datalist,
            columns=[
                'Intensity (counts)',
                'Atomic %',
                'Area (counts*eV)',
                'FWHM (eV)',
                'Peak BE (eV)',
            ],
        )

        # modify some values
        # convert KE to BE (KE of machine X-rays is 1486.68 eV)
        dataframe['Peak BE (eV)'] = 1486.68 - dataframe['Peak BE (eV)']
        # reorder columns to be similar to Avantage
        columnorder = [
            'Peak BE (eV)',
            'Intensity (counts)',
            'FWHM (eV)',
            'Area (counts*eV)',
            'Atomic %',
        ]
        dataframe = dataframe.reindex(columnorder, axis=1)
        # create peak dataframe
        peaks = pd.DataFrame(peaklist, columns=['Peak'])
        # add peak dataframe to front of data dataframe
        dataframe = pd.concat([peaks, dataframe], axis=1)

        # handle coordinates
        coordframe = pd.DataFrame(coordlist, columns=['X', 'Y'])
        coordframe['X'] = coordframe['X'] - max(coordframe['X']) / 2
        coordframe['Y'] = coordframe['Y'] - max(coordframe['Y']) / 2
        coordframe = coordframe / 1000
        coordframe['Y'] = coordframe['Y'].values[::-1]

        unique_coords = list(set(tuple(row) for row in coordframe[['X', 'Y']].values))

        # Concatenate the two DataFrames along the columns
        merged_frame = pd.concat([coordframe, dataframe], axis=1)

        return merged_frame, unique_coords

    def write_XPS_analysis(self, dataframe: pd.DataFrame, coords_list: list) -> None:
        '''"Write data and coordinates to the XPS class
        with respect to the coordinates"'''
        # filter by coordinates and create small dfs
        results = []

        for coord in coords_list:
            mask = dataframe.apply(lambda row: (row['X'], row['Y']) == coord, axis=1)
            coord_data = dataframe[mask]
            mapping_result = XpsMappingResult(
                x_relative=ureg.Quantity(coord[0], 'mm'),
                y_relative=ureg.Quantity(coord[1], 'mm'),
            )
            peaks = []
            coord_data = coord_data.assign(Element=coord_data['Peak'])

            for index, row in coord_data.iterrows():
                peak_info = XpsFittedPeak(
                    origin=ureg.Quantity(row['Peak'], 'eV'),
                    be_position=ureg.Quantity(row['Peak BE (eV)'], 'eV'),
                    intensity=ureg.Quantity(row['Intensity (counts)'], '1/s'),
                    fwhm=ureg.Quantity(row['FWHM (eV)'], 'eV'),
                    area=ureg.Quantity(row['Area (counts*eV)'], 'cps*eV'),
                    atomic_percent=row['Atomic %'],
                )

                peaks.append(peak_info)

                # figure out whiche element the peak is from
                current_element = row['Peak']
                match = re.split(r'\d', current_element, maxsplit=1)
                current_element = match[0]
                coord_data.loc[index, 'Element'] = current_element

            mapping_result.peaks = peaks

            # take info from previous loop, reduce df and add to composition
            composition = []
            grouped_df = coord_data.groupby('Element', as_index=False)['Atomic %'].sum()
            for index, row in grouped_df.iterrows():
                element_info = XpsDerivedComposition(
                    element=row['Element'],
                    atomic_percent=row['Atomic %'],
                )
                composition.append(element_info)

            mapping_result.composition = composition

            results.append(mapping_result)
        # merge_sections(self.results, results)
        self.results = results

    def plot(self) -> None:
        x, y = [], []
        quantifications = defaultdict(list)
        # ratios = defaultdict(list)
        result: XpsMappingResult
        for result in self.results:
            if isinstance(result.x_relative, ureg.Quantity) and isinstance(
                result.y_relative, ureg.Quantity
            ):
                x.append(result.x_relative.to('mm').magnitude)
                y.append(result.y_relative.to('mm').magnitude)
                x_title = 'X Sample Position (mm)'
                y_title = 'Y Sample Position (mm)'
            elif isinstance(result.x_absolute, ureg.Quantity) and isinstance(
                result.y_absolute, ureg.Quantity
            ):
                x.append(result.x_absolute.to('mm').magnitude)
                y.append(result.y_absolute.to('mm').magnitude)
                x_title = 'X Stage Position (mm)'
                y_title = 'Y Stage Position (mm)'
            else:
                continue

            quantification: XpsDerivedComposition
            for quantification in result.composition:
                quantifications[quantification.element].append(
                    quantification.atomic_percent
                )

            # Calculate and append the fractions of all elements with each other
            # test to see if this works or there is another errror
        #     quantification_i: XpsDerivedComposition
        #     for quantification_i in result.composition:
        #         quantification_j: XpsDerivedComposition
        #         for quantification_j in result.composition:
        #             if quantification_i.element == quantification_j.element:
        #                 continue
        #             ratio = (
        #                 quantification_i.atomic_percent
        #                 / quantification_j.atomic_percent
        #             )
        #             ratios[
        #                 f'{quantification_i.element}/{quantification_j.element}'
        #             ].append(ratio)
        #             # processed_pairs.add(pair)

        # combined_data = {**quantifications, **ratios}
        combined_data = quantifications

        for q, data in combined_data.items():
            # Create a grid for the heatmap
            xi = np.linspace(min(x), max(x), 100)
            yi = np.linspace(min(y), max(y), 100)
            xi, yi = np.meshgrid(xi, yi)
            zi = griddata((x, y), data, (xi, yi), method='linear')

            # Create a scatter plot
            scatter = go.Scatter(
                x=x,
                y=y,
                mode='markers',
                marker=dict(
                    size=15,
                    color=data,  # Set color to atomic fraction values
                    colorscale='Viridis',  # Choose a colorscale
                    # colorbar=dict(title=f'{q} Atomic Fraction'),  # Add a colorbar
                    showscale=False,  # Hide the colorbar for the scatter plot
                    line=dict(
                        width=2,  # Set the width of the border
                        color='DarkSlateGrey',  # Set the color of the border
                    ),
                ),
                customdata=data,  # Add atomic fraction data to customdata
                hovertemplate=f'<b>Atomic fraction of {q}:</b> %{{customdata}}',
            )

            # Create a heatmap
            heatmap = go.Heatmap(
                x=xi[0],
                y=yi[:, 0],
                z=zi,
                colorscale='Viridis',
                colorbar=dict(title=f'{q} Atomic Fraction'),
            )

            # Combine scatter plot and heatmap
            fig = go.Figure(data=[heatmap, scatter])

            # Update layout
            fig.update_layout(
                title=f'{q} Atomic Fraction Colormap',
                xaxis_title=x_title,
                yaxis_title=y_title,
                template='plotly_white',
                hovermode='closest',
                dragmode='zoom',
                xaxis=dict(
                    fixedrange=False,
                ),
                yaxis=dict(
                    fixedrange=False,
                ),
            )

            plot_json = fig.to_plotly_json()
            plot_json['config'] = dict(
                scrollZoom=False,
            )
            self.figures.append(
                PlotlyFigure(
                    label=f'{q} Atomic Fraction',
                    figure=plot_json,
                )
            )

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        """
        The normalize function of the `DTUXRDMeasurement` section.

        Args:
            archive (EntryArchive): The archive containing the section that is being
            normalized.
            logger (BoundLogger): A structlog logger.
        """
        if self.analysis_file is not None:
            dataframe, coords_list = self.read_XPS_analysis(archive, logger)
            self.write_XPS_analysis(dataframe, coords_list)

        super().normalize(archive, logger)
        self.figures = []
        self.plot()


m_package.__init_metainfo__()
