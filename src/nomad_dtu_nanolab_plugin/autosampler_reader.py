# -------------Packages-------------------
import csv
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy import signal
from sklearn.linear_model import LinearRegression

# -----------------Globals-------------------

POLARISATION_DICT = {
    '0': 's',
    '90': 'p',
    'None': 'unpolarized(p-biased)',
}

# Constants for the calculation of the absorption coefficient

# Threshold for the transmission values: any value below zero threshold is set
# to the threshold value
T_THRESHOLD = 1e-10

# maximum value for the absorption coefficient, any value above this value is set
# to the maximum value
MAX_ALPHA = 8

# minimum alpha value for the bandgap estimation, if all the alpha values are
# above this value, the bandgap estimation is not performed
MIN_ALPHA_BANDGAP = 1

# default wavelength range on which the standard treatment is performed
WV_START = 500
WV_END = 800

# default method to calculate the absorption coefficient
ALPHA_METHOD = '1fr'

# default method to calculate the tauc plot
TAUC_METHOD = 'direct'

# maximum energy value for the bandgap estimation
MAX_ENERGY = 3.5  # eV
# window size for the smoothing of the alpha values for the bandgap estimation
WINDOW_SIZE = 21

# window size for the bandgap estimation using the intercept method
WINDOW_SIZE_INTERCEPT = 10

WINDOW_SIZE_THRESHOLD = 10
ALPHA_THRESHOLD = 0.05


# Minimum r value for the bandgap estimation using the intercept method
MIN_R = 0.9

# Number of parts expected in measurement label when split by "__"
MEASUREMENT_LABEL_PARTS = 4

# -----------------Classes------------------


# class for single UV-vis-NIR measurement collected by
# the Agilent Cary 7000 UMS
class SingleMeasurement:
    def __init__(self, measurement_label):
        # Initialize the measurement with the label
        self.measurement_label = measurement_label
        self.sample_name = None

        # Initialize the data (Refl or Trans vs. Wv), the metadata
        # (measurement conditions, uma sequence, etc.) and
        #  config (points where the measurement was taken)

        self.data = pd.DataFrame()  # List of tuples (Wv, E, %T or %R)
        self.raw_metadata = []  # Dictionary for metadata
        self.metadata = {}  # Dictionary for processes metadata
        self.config = {}  # Dictionary for config

        # Parse the measurement label if it has the correct format
        if len(measurement_label.split('__')) == MEASUREMENT_LABEL_PARTS:
            self.sample_name = self.measurement_label.split('__')[0]
            polarisation_angle = self.measurement_label.split('__')[1]
            self.metadata['PolarizationAngle'] = polarisation_angle
            self.metadata['Polarization'] = POLARISATION_DICT.get(
                polarisation_angle, 'custom'
            )
            self.metadata['SampleAngle'] = self.measurement_label.split('__')[2]
            self.metadata['DetectorAngle'] = self.measurement_label.split('__')[3]

    def add_data(self, wavelength, value, column_name):
        self.data['Wavelength'] = wavelength
        self.data['Energy'] = 1239.84 / wavelength
        self.data[column_name] = value
        self.data['Intensity'] = value
        # remove '%' from the column name
        meas_type = re.sub(r'[%]', '', column_name)
        self.metadata['MeasurementType'] = meas_type

    def add_raw_metadata(self, metadata):
        self.raw_metadata = metadata
        for row in metadata:
            if 'SampleAngle' in row[0]:
                self.metadata['SampleAngle'] = float(row[1])
            if 'PolarizationAngle' in row[0]:
                if len(row) == 1:
                    polarisation_angle = 'None'
                else:
                    polarisation_angle = row[1]
                self.metadata['PolarizationAngle'] = polarisation_angle
                self.metadata['Polarization'] = POLARISATION_DICT.get(
                    polarisation_angle, 'custom'
                )
            if 'DetectorAngle' in row[0]:
                self.metadata['DetectorAngle'] = float(row[1])
            if 'Collection Time' in row[0]:
                self.metadata['Collection Time'] = pd.to_datetime(
                    row[0].split(': ')[1], format='%d-%b-%y %I:%M:%S %p'
                )

    def add_config(self, config):
        self.config = config
        self.metadata['Sample Name'] = config['Sample Name']
        self.sample_name = config['Sample Name']

    def export_to_csv(self, file_name):
        # Create a DataFrame with Wavelength and Intensity
        df_to_export = self.data[['Wavelength', 'Energy', 'Intensity']].copy()

        # Add single values for the other quantities
        df_to_export['Xsample'] = self.config['Xsample']
        df_to_export['Ysample'] = self.config['Ysample']
        df_to_export['Sample Name'] = self.sample_name
        df_to_export['Sample Angle'] = self.metadata['SampleAngle']
        df_to_export['Polarization Angle'] = self.metadata['PolarizationAngle']
        df_to_export['Polarization'] = self.metadata['Polarization']
        df_to_export['Detector Angle'] = self.metadata['DetectorAngle']
        df_to_export['Measurement Type'] = self.metadata['MeasurementType']

        # for the single values only keep the first value
        # and drop the rest as None
        for column in [
            'Xsample',
            'Ysample',
            'Sample Name',
            'Sample Angle',
            'Polarization Angle',
            'Polarization',
            'Detector Angle',
            'Measurement Type',
        ]:
            df_to_export.loc[1:, column] = None

        # Export to CSV
        df_to_export.to_csv(f'{file_name}.csv', index=False)


# class to store multiple measurements at the same sample position
class MultiMeasurement:
    def __init__(self, sample_name, verbose=False):
        self.sample_name = sample_name
        self.position_x = None
        self.position_y = None
        self.measurements = []
        self.avg_sp_measurements = []
        self.derived_data = {}
        self.verbose = verbose

    def calc_avg_transmission_refl(self, wv_start=None, wv_end=None):
        if self.avg_sp_measurements is not None:
            measurements = self.avg_sp_measurements
        else:
            measurements = self.measurements

        if wv_start is None and wv_end is None:
            wv_start = measurements[0].data['Wavelength'].min()
            wv_end = measurements[0].data['Wavelength'].max()

        for measurement in measurements:
            data = measurement.data
            mask = (data['Wavelength'] >= wv_start) & (data['Wavelength'] <= wv_end)
            avg = data['Intensity'][mask].mean()
            self.derived_data[
                f'avg_{measurement.metadata["MeasurementType"]}_{wv_start}_{wv_end}'
            ] = avg

    def find_max_transmission_refl(self, wv_start=None, wv_end=None):
        """
        method to find the wave
        """
        if self.avg_sp_measurements is not None:
            measurements = self.avg_sp_measurements
        else:
            measurements = self.measurements

        if wv_start is None:
            wv_start = measurements[0].data['Wavelength'].min()
        if wv_end is None:
            wv_end = measurements[0].data['Wavelength'].max()

        for measurement in measurements:
            data = measurement.data
            mask = (data['Wavelength'] >= wv_start) & (data['Wavelength'] <= wv_end)
            max_val = data['Intensity'][mask].max()
            max_wv = data['Wavelength'][data['Intensity'] == max_val].values[0]

            self.derived_data[
                f'max_{measurement.metadata["MeasurementType"]}_{wv_start}_{wv_end}'
            ] = max_val
            self.derived_data[
                f'max_{measurement.metadata["MeasurementType"]}_wv_{wv_start}_{wv_end}'
            ] = max_wv

    def avg_sp_pol(self):
        # we first check that all the measurements have been performed with
        # the polarizer (PolarizationAngle is not None)
        for measurement in self.measurements:
            if measurement.metadata['PolarizationAngle'] == 'None':
                self.avg_sp_measurements = self.measurements
                return

        # Group measurements by detector and sample angles
        grouped_measurements = {}
        for measurement in self.measurements:
            key = (
                measurement.metadata['DetectorAngle'],
                measurement.metadata['SampleAngle'],
            )
            if key not in grouped_measurements:
                grouped_measurements[key] = {'s': [], 'p': []}
            polarization = measurement.metadata['Polarization']
            if polarization in grouped_measurements[key]:
                grouped_measurements[key][polarization].append(measurement)

        # Average the measurements in pairs of s and p polarization
        averaged_measurements = []
        for key, pol_measurements in grouped_measurements.items():
            s_measurements = pol_measurements['s']
            p_measurements = pol_measurements['p']
            if len(s_measurements) == len(p_measurements):
                for s_measurement, p_measurement in zip(s_measurements, p_measurements):
                    avg_measurement = self._average_measurements(
                        s_measurement, p_measurement
                    )
                    averaged_measurements.append(avg_measurement)
            else:
                if self.verbose:
                    print(
                        f'Warning (point X={self.position_x}, '
                        f'Y={self.position_y}): Unequal number of s and p '
                        f'measurements'
                    )

        self.avg_sp_measurements = averaged_measurements

    def _average_measurements(self, s_measurement, p_measurement):
        avg_measurement = SingleMeasurement(s_measurement.measurement_label)
        avg_measurement.data = (s_measurement.data + p_measurement.data) / 2
        avg_measurement.metadata = s_measurement.metadata.copy()
        avg_measurement.metadata['Polarization'] = 'avg'
        return avg_measurement

    def calc_alpha(self, method='1fr', wv_start=None, wv_end=None):
        """
        method to calculate the unitless absorption coefficient
        alpha based on  R and T, and the following methods:

        method "1fr" :
            alpha = -ln(T/(1-R))
            # only considers 1st front reflection
        method "1fbr :
            alpha = -ln(T/(1-R)^2)
            #only considers 1st front reflection and 1st back reflection
        method "infr" :
            alpha = -ln(-(R^2+sqrt(R^4 + 4T^2R^2 - 4R^3 + 6R^2
                          - 4R + 1) - 2R - 1)/(2R^2T))
            # considers all reflections
        """

        def format_R_T(R, T):
            R[R > 1] = 1
            T[T < 0] = T_THRESHOLD
            return R, T

        # define the different methods to calculate the absorption coefficient
        def method_1fr(T, R):
            R, T = format_R_T(R, T)
            return -np.log(T / (1 - R))

        def method_1fbr(T, R):
            R, T = format_R_T(R, T)
            return -np.log(T / (1 - R) ** 2)

        def method_infr(T, R):
            R, T = format_R_T(R, T)
            return -np.log(
                -(
                    R**2
                    + np.sqrt(R**4 + 4 * T**2 * R**2 - 4 * R**3 + 6 * R**2 - 4 * R + 1)
                    - 2 * R
                    - 1
                )
                / (2 * R**2 * T)
            )

        # dictionary to store the methods
        method_dict = {
            '1fr': method_1fr,
            '1fbr': method_1fbr,
            'infr': method_infr,
        }
        # first group the measurements by the measurement type
        rt_grouped_measurements = {}
        for measurement in self.avg_sp_measurements:
            key = measurement.metadata['MeasurementType']
            if key not in rt_grouped_measurements:
                rt_grouped_measurements[key] = []
            rt_grouped_measurements[key].append(measurement)
        # and check there is a single R and T measurement
        for key, measurements in rt_grouped_measurements.items():
            if len(measurements) != 1:
                if self.verbose:
                    print(
                        f'Warning (point X={self.position_x}, '
                        f'Y={self.position_y}): {len(measurements)} {key} '
                        f'measurements found'
                    )
                return
        # check that both R and T measurements are present
        if 'T' not in rt_grouped_measurements or 'R' not in rt_grouped_measurements:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): T or R measurement missing'
                )
            return
        # filter the measurements to the specified wavelength range if provided
        if wv_start is not None and wv_end is not None:
            for key, measurements in rt_grouped_measurements.items():
                mask = (measurements[0].data['Wavelength'] >= wv_start) & (
                    measurements[0].data['Wavelength'] <= wv_end
                )
                measurements[0].data = measurements[0].data[mask].reset_index(drop=True)
        elif wv_start is not None:
            for key, measurements in rt_grouped_measurements.items():
                mask = measurements[0].data['Wavelength'] >= wv_start
                measurements[0].data = measurements[0].data[mask].reset_index(drop=True)
        elif wv_end is not None:
            for key, measurements in rt_grouped_measurements.items():
                mask = measurements[0].data['Wavelength'] <= wv_end
                measurements[0].data = measurements[0].data[mask].reset_index(drop=True)

        # calculate the absorption coefficient
        for key, measurements in rt_grouped_measurements.items():
            if key == 'T':
                T = measurements[0].data['Intensity'] / 100
                T_raw = measurements[0].data['Intensity']
                T_wavelength = measurements[0].data['Wavelength']
                T_energy = measurements[0].data['Energy']
            if key == 'R':
                R = measurements[0].data['Intensity'] / 100
                R_raw = measurements[0].data['Intensity']
                R_wavelength = measurements[0].data['Wavelength']
                R_energy = measurements[0].data['Energy']

        # Create R and T dataframes
        T_df = pd.DataFrame()
        T_df['Wavelength'] = T_wavelength
        T_df['Energy'] = T_energy
        T_df['T'] = T_raw

        R_df = pd.DataFrame()
        R_df['Wavelength'] = R_wavelength
        R_df['Energy'] = R_energy
        R_df['R'] = R_raw

        # format the absorption coefficient into a dataframe
        alpha_df = pd.DataFrame()
        alpha_df['Wavelength'] = measurements[0].data['Wavelength']
        alpha_df['Energy'] = measurements[0].data['Energy']
        alpha_df['alpha'] = method_dict[method](T, R)
        alpha_df.loc[alpha_df['alpha'] > MAX_ALPHA, 'alpha'] = MAX_ALPHA
        # normalize the absorption coefficient between 0 and 1
        normalized_alpha_df = alpha_df.copy()
        normalized_alpha_df['normalized_alpha'] = (
            alpha_df['alpha'] - alpha_df['alpha'].min()
        ) / (alpha_df['alpha'].max() - alpha_df['alpha'].min())
        # drop the alpha column to avoid confusion
        normalized_alpha_df.drop(columns=['alpha'], inplace=True)

        # Store all derived data
        self.derived_data['T'] = T_df
        self.derived_data['R'] = R_df
        self.derived_data['alpha'] = alpha_df
        self.derived_data['normalized_alpha'] = normalized_alpha_df
        self.derived_data['alpha_method'] = method

    def calc_tauc(self, method='direct'):
        """
        method to calculate the tauc plot from the absorption coefficient
        method "direct" :
            tauc = (alpha * energy)^2
        method "indirect" :
            tauc = sqrt(alpha * energy)
        """
        # check that the alpha data is present, by chekcing  that one of the
        # derived data dict key starts with alpha
        if 'alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Alpha data missing'
                )

        alpha_df = self.derived_data['alpha']
        alpha = alpha_df['alpha']
        energy = alpha_df['Energy']
        if method == 'direct':
            tauc = (alpha * energy) ** 2
        elif method == 'indirect':
            tauc = np.sqrt(alpha * energy)

        tauc_df = pd.DataFrame()
        tauc_df['Wavelength'] = alpha_df['Wavelength']
        tauc_df['Energy'] = alpha_df['Energy']
        tauc_df['tauc'] = tauc

        self.derived_data['tauc'] = tauc_df
        self.derived_data['tauc_method'] = method

    def estimate_bandgap_inflection(
        self,
        max_energy=None,
        # Ensure this is smaller than the length of the data
        window_size=WINDOW_SIZE_INTERCEPT,
        min_alpha=MIN_ALPHA_BANDGAP,
        edge_points_to_remove=None,  # New parameter to control edge removal
    ):
        """
        Method to estimate the bandgap from the absorption plot
        using the inflection point method, working with wavelengths.
        Edge points are removed to avoid derivative artifacts.
        """
        # Check that the alpha data is present
        if 'alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Alpha data missing'
                )
            return
            return

        alpha_df = self.derived_data['alpha']

        # In case max_energy is provided,
        # we only consider the data up to that energy
        if max_energy is not None:
            filtered_data = alpha_df[alpha_df['Energy'] <= max_energy]
        else:
            filtered_data = alpha_df

        # Extract relevant columns
        wavelength = filtered_data['Wavelength'].values  # Use wavelength directly
        alpha = filtered_data['alpha'].values

        # Avoid log or derivative issues
        alpha[alpha < T_THRESHOLD] = T_THRESHOLD

        # Handle NaN values in alpha
        alpha[np.isnan(alpha)] = 0

        # Set default edge removal based on window size if not specified
        if edge_points_to_remove is None:
            edge_points_to_remove = window_size // 2

        # Calculate spacing between wavelength values
        wavelength_diff = np.diff(wavelength)
        evenly_spaced = np.allclose(wavelength_diff, wavelength_diff[0])

        if evenly_spaced:
            # Use Savitzky–Golay smoothing and derivatives
            smooth_alpha = signal.savgol_filter(alpha, window_size, 2)
            first_derivative = signal.savgol_filter(
                smooth_alpha, window_size, 2, deriv=1, mode='mirror'
            )
            second_derivative = signal.savgol_filter(
                smooth_alpha, window_size, 2, deriv=2, mode='mirror'
            )
        else:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x},'
                    f' Y={self.position_y}): '
                    'Wavelength values are not evenly spaced. Using rolling'
                    ' average smoothing instead.'
                )

            # Rolling average smoothing
            kernel = np.ones(window_size) / window_size
            smooth_alpha = np.convolve(alpha, kernel, mode='same')

            # Approximate derivatives with finite differences
            first_derivative = np.gradient(smooth_alpha, wavelength)
            second_derivative = np.gradient(first_derivative, wavelength)

        # Remove edge points to avoid derivative artifacts
        if len(wavelength) > 2 * edge_points_to_remove:
            # Create slices excluding edge points
            valid_slice = slice(edge_points_to_remove, -edge_points_to_remove)

            wavelength_trimmed = wavelength[valid_slice]
            smooth_alpha_trimmed = smooth_alpha[valid_slice]
            first_derivative_trimmed = first_derivative[valid_slice]
            second_derivative_trimmed = second_derivative[valid_slice]

            if self.verbose:
                print(
                    f'Info (point X={self.position_x}, Y={self.position_y}): '
                    f'Removed {edge_points_to_remove} points from each edge. '
                    f'Working with {len(wavelength_trimmed)} points instead '
                    f'of {len(wavelength)}.'
                )
        else:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, Y={self.position_y}): '
                    f'Not enough data points to remove edges safely. '
                    f'Using all {len(wavelength)} points.'
                )
            wavelength_trimmed = wavelength
            smooth_alpha_trimmed = smooth_alpha
            first_derivative_trimmed = first_derivative
            second_derivative_trimmed = second_derivative

        # Inflection point: index of maximum |first derivative| (in trimmed data)
        inflection_idx_trimmed = np.argmax(np.abs(first_derivative_trimmed))

        # Find zero crossing of second derivative around inflection point
        zero_crossings = np.where(np.diff(np.sign(second_derivative_trimmed)))[0]
        if len(zero_crossings) > 0:
            bandgap_idx_trimmed = min(
                zero_crossings, key=lambda x: abs(x - inflection_idx_trimmed)
            )
        else:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): No zero crossing found. Using'
                    ' inflection point as bandgap.'
                )
            bandgap_idx_trimmed = inflection_idx_trimmed

        bandgap_wavelength = wavelength_trimmed[bandgap_idx_trimmed]
        bandgap_energy = 1239.84 / bandgap_wavelength

        # Normalize the alpha values between 0 and 1 (using trimmed data)
        normalized_smoothed_alpha_trimmed = (
            smooth_alpha_trimmed - np.min(smooth_alpha_trimmed)
        ) / (np.max(smooth_alpha_trimmed) - np.min(smooth_alpha_trimmed))

        # Store results in derived_data (using trimmed arrays)
        self.derived_data['normalized_smoothed_alpha'] = pd.DataFrame(
            {
                'Wavelength': wavelength_trimmed,
                'Energy': 1239.84 / wavelength_trimmed,
                'normalized_smoothed_alpha': normalized_smoothed_alpha_trimmed,
            }
        )

        self.derived_data['smoothed_alpha'] = pd.DataFrame(
            {
                'Wavelength': wavelength_trimmed,
                'Energy': 1239.84 / wavelength_trimmed,
                'smoothed_alpha': smooth_alpha_trimmed,
            }
        )

        self.derived_data['1st_deriv_alpha'] = pd.DataFrame(
            {
                'Wavelength': wavelength_trimmed,
                'Energy': 1239.84 / wavelength_trimmed,
                '1st_deriv_alpha': first_derivative_trimmed,
            }
        )

        self.derived_data['2nd_deriv_alpha'] = pd.DataFrame(
            {
                'Wavelength': wavelength_trimmed,
                'Energy': 1239.84 / wavelength_trimmed,
                '2nd_deriv_alpha': second_derivative_trimmed,
            }
        )

        # Before splitting the data, we check that not all smoothed alpha values
        # are above a certain threshold, if they are we return NaN
        if np.all(smooth_alpha_trimmed > min_alpha):
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, Y={self.position_y}): '
                    f'All smoothed alpha values are above {min_alpha}. '
                    f'Bandgap estimation impossible.'
                )
            bandgap_energy = np.nan
            bandgap_wavelength = np.nan

        self.derived_data['bandgap_inflection_energy'] = bandgap_energy
        self.derived_data['bandgap_inflection_wavelength'] = bandgap_wavelength
        self.derived_data['bandgap_inflection_method'] = {
            'max_energy': max_energy,
            'window_size': window_size,
            'edge_points_removed': edge_points_to_remove,
        }

    def estimate_bandgap_threshold(
        self,
        threshold=ALPHA_THRESHOLD,
        window_size=WINDOW_SIZE_THRESHOLD,
        method='normalized',
        min_alpha=MIN_ALPHA_BANDGAP,
    ):
        """
        this method is used to extract a bandgap based on the threshold method.
        We simply take the first group of consecutive points (of size
        window_size) where the absorption coefficient is above a certain
        threshold, and we take the average of the energy values of this group
        as the bandgap.
        the default takes as input the raw absorption coefficient, while the
        'normalized' method takes the normalized absorption coefficient as input.
        """
        # Check that the alpha data is present
        if 'alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Alpha data missing'
                )
            return

        if 'smoothed_alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Smoothed alpha data missing'
                )
            return

        # if all the alpha values are above the threshold, we return np.nan
        # and print a warning
        if all(self.derived_data['smoothed_alpha']['smoothed_alpha'] > min_alpha):
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): All alpha values are above the '
                    f'threshold. Bandgap estimation impossible.'
                )
            self.derived_data['bandgap_threshold_energy'] = np.nan
            self.derived_data['bandgap_threshold_wavelength'] = np.nan
            return

        if method == 'normalized':
            alpha_df = self.derived_data['normalized_alpha']
            alpha = alpha_df['normalized_alpha'].values
        elif method == 'default':
            alpha_df = self.derived_data['alpha']
            alpha = alpha_df['alpha'].values
        else:
            raise ValueError(
                f"Unknown method: {method}. Use 'normalized' or 'default'."
            )

        energy = alpha_df['Energy'].values

        # Slide a window across the data
        for i in range(len(energy) - window_size):
            # Take a window of size 'window_size'
            E_window = energy[i : i + window_size]
            alpha_window = alpha[i : i + window_size]

            # Check if all alpha values are above the threshold
            if all(alpha_window > threshold):
                # if the very first window has all values above the threshold
                # we say that the bandgap is np.nan
                if i == 0:
                    if self.verbose:
                        print(
                            f'Warning (point X={self.position_x}, '
                            f'Y={self.position_y}): All alpha values are above the '
                            f'threshold. Bandgap estimation impossible.'
                        )
                    E_g = np.nan
                else:
                    # Calculate the average energy value of the window
                    E_g = np.mean(E_window)
                break
        else:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): No suitable region found for '
                    f'bandgap estimation.'
                )
            E_g = np.nan

        # Store results in derived_data
        self.derived_data['bandgap_threshold_energy'] = E_g
        self.derived_data['bandgap_threshold_wavelength'] = 1239.84 / E_g
        self.derived_data['bandgap_threshold_method'] = {
            'threshold': threshold,
            'window_size': window_size,
        }

    def estimate_bandgap_tauc(
        self, window_size=10, max_energy=None, min_r=MIN_R, min_slope=1
    ):
        """
        Method to estimate the bandgap from the absorption plot
        using the intercept method, working with wavelengths..
        """
        # Check that the alpha data is present
        if 'alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Alpha data missing'
                )
            return

        alpha_df = self.derived_data['alpha']

        # in case max_energy is provided,
        # we only consider the data up to that energy
        if max_energy is not None:
            alpha_filtered_data = alpha_df[alpha_df['Energy'] <= max_energy]
        else:
            alpha_filtered_data = alpha_df
        # Extract relevant columns
        alpha = alpha_filtered_data['alpha'].values

        tauc_df = self.derived_data['tauc']

        if max_energy is not None:
            filtered_data = tauc_df[tauc_df['Energy'] <= max_energy]
        else:
            filtered_data = tauc_df

        # Extract relevant columns
        energy = filtered_data['Energy'].values
        tauc = filtered_data['tauc'].values

        best_r = -1
        best_region = None
        best_region_center = None
        best_fit = None

        # Slide a window across the data
        for i in range(len(energy) - window_size):
            # Take a window of size 'window_size'
            E_window = energy[i : i + window_size]
            tauc_window = tauc[i : i + window_size]

            # Perform linear regression on the window
            model = LinearRegression()
            model.fit(E_window.reshape(-1, 1), tauc_window)

            # Calculate correlation coefficient (r)
            r = np.corrcoef(E_window, tauc_window)[0, 1]

            # Get the slope of the linear regression
            slope = model.coef_[0]

            # If the correlation coefficient is higher than previous best
            # AND the slope is greater than 1, update best region
            if r > best_r and slope > min_slope:
                best_r = r
                best_region = (i, i + window_size)
                best_region_center = 0.5 * (best_region[0] + best_region[1])
                best_fit = model

        if best_fit is None:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): No suitable region found for '
                    f'bandgap estimation (r>{min_r} and slope>{min_slope}).'
                )
            E_g = np.nan
            best_r = np.nan
            best_region = np.nan
            best_region_center = np.nan
        elif best_r < min_r:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Best region correlation '
                    f'coefficient below {min_r}. Bandgap estimation impossible.'
                )
            E_g = np.nan
        elif all(alpha > MIN_ALPHA_BANDGAP):
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): All alpha values are above '
                    f'{MIN_ALPHA_BANDGAP}. Bandgap estimation impossible.'
                )
            E_g = np.nan
            best_r = np.nan
            best_region = np.nan
            best_region_center = np.nan
        else:
            # Extrapolate the best region to the x-axis
            # y = mx + b, solve for x when y=0
            intercept = best_fit.intercept_
            # Solve for E when y = 0 (intercept = 0)
            E_g = -intercept / best_fit.coef_[0]

        # Store results in derived_data
        self.derived_data['intercept_best_r'] = best_r
        self.derived_data['intercept_best_region_center'] = best_region_center
        self.derived_data['bandgap_intercept_energy'] = E_g
        self.derived_data['bandgap_intercept_wavelength'] = 1239.84 / E_g
        self.derived_data['bandgap_intercept_method'] = {
            'window_size': window_size,
            'max_energy': max_energy,
            'min_r': min_r,
            'min_slope': min_slope,
        }

        # Also store the slope of the best fit
        if best_fit is not None:
            self.derived_data['intercept_best_slope'] = best_fit.coef_[0]

        return best_region, best_r

    def standard_treatment(  # noqa: PLR0913
        self,
        wv_start=WV_START,
        wv_end=WV_END,
        alpha_method=ALPHA_METHOD,
        tauc_method=TAUC_METHOD,
        max_energy=MAX_ENERGY,
        window_size=WINDOW_SIZE,
        window_size_intercept=WINDOW_SIZE_INTERCEPT,
        window_size_threshold=WINDOW_SIZE_THRESHOLD,
        alpha_threshold=ALPHA_THRESHOLD,
        method='normalized',
        min_r=MIN_R,
        min_slope=1,  # Add this parameter with default value
    ):
        """
        method to perform the standard treatment of the data
        """
        self.avg_sp_pol()
        self.calc_avg_transmission_refl(wv_start=wv_start, wv_end=wv_end)
        self.find_max_transmission_refl(wv_start=wv_start, wv_end=wv_end)
        self.calc_alpha(method=alpha_method, wv_start=wv_start, wv_end=wv_end)
        self.calc_tauc(method=tauc_method)
        self.estimate_bandgap_inflection(max_energy=max_energy, window_size=window_size)
        self.estimate_bandgap_tauc(
            window_size=window_size_intercept,
            max_energy=max_energy,
            min_r=min_r,
            min_slope=min_slope,  # Add this parameter
        )
        self.estimate_bandgap_threshold(
            threshold=alpha_threshold,
            window_size=window_size_threshold,
            method=method,
        )

    def add_measurement(self, measurement):
        self.measurements.append(measurement)


# -----------------Reading Data-------------------


def group_samples(collects):
    samples = {}
    for collect in collects:
        if collect.sample_name in samples:
            samples[collect.sample_name].append(collect)
        else:
            samples[collect.sample_name] = [collect]

    return samples


def estimate_bandgap_tauc_map(
    map_meas, window_size=WINDOW_SIZE_INTERCEPT, max_energy=MAX_ENERGY, verbose=False
):
    """
    Method to estimate the bandgap from the absorption plot
    using the intercept method. The main different with the estimate_bandgap_tauc
    method is that it first scans for all the measurements in the map_meas and finds
    the region with the highest avg correlation coefficient over the whole map_meas.
    Then it uses this region to estimate the bandgap for each point in the map_meas.
    """
    best_r_dict = {}
    best_region_dict = {}
    max_region = None
    min_region = None

    for position_key, multi_measurement in map_meas.items():
        best_region, best_r = multi_measurement.estimate_bandgap_tauc(
            window_size=window_size, max_energy=max_energy
        )
        if isinstance(best_region, tuple):
            best_r_dict[position_key] = best_r
            best_region_dict[position_key] = best_region

    # let us compute the average of the regions tuples,
    best_region_avg = np.mean([np.mean(region) for region in best_region_dict.values()])
    for position_key, region in best_region_dict.items():
        if max_region is None:
            max_region = region[1]
            min_region = region[0]
        max_region = max(max_region, region[1])
        min_region = min(min_region, region[0])

    if verbose:
        print(f'Max region: {max_region}')
        print(f'Min region: {min_region}')
        print(f'Average best region: {best_region_avg}')

    # TODO: fit the tauc data to a line in the average best region and
    # find the intersection with the x-axis


def group_measurements_position(samples, verbose=False):
    multi_measurements = {}
    for sample_name, collects in samples.items():
        if sample_name not in multi_measurements:
            multi_measurements[sample_name] = {}
        for collect in collects:
            position_x = collect.config['Xsample']
            position_y = collect.config['Ysample']
            position_key = f'{position_x}_{position_y}'
            if position_key not in multi_measurements[sample_name]:
                multi_measurement = MultiMeasurement(sample_name, verbose=verbose)
                multi_measurement.position_x = collect.config['Xsample']
                multi_measurement.position_y = collect.config['Ysample']
                multi_measurements[sample_name][position_key] = multi_measurement
            multi_measurements[sample_name][position_key].add_measurement(collect)
    return multi_measurements


def get_uma_sequence_length(sample_names):
    sample_name_counts = {}
    for i, name in enumerate(sample_names):
        if name in sample_name_counts:
            sample_name_counts[name].append(i)
        else:
            sample_name_counts[name] = [i]
    # Determine the interval between occurrences of the same sample name
    intervals = []
    for indices in sample_name_counts.values():
        if len(indices) > 1:
            intervals.append(indices[1] - indices[0])

    # check the last interval (the reminder of the list)
    if len(intervals) > 1:
        intervals.append(len(sample_names) - sample_name_counts[sample_names[0]][-1])

    # check that all intervals are the same
    if not all(interval == intervals[0] for interval in intervals):
        raise ValueError('Intervals between collects are not consistent.')

    return intervals[0]


def read_data_block(data_path, measurement_labels, column_headers):
    uma_sequence_length = get_uma_sequence_length(measurement_labels)

    df = pd.read_csv(data_path, skiprows=1)
    # remove non float rows
    df = df.apply(pd.to_numeric, errors='coerce')
    # remove missing values
    df = df.dropna(axis=1, how='all')
    # remove all rows after the first NaN
    df = df.dropna(subset=[df.columns[0]])

    collects = []
    for i in range(len(measurement_labels)):
        collect = SingleMeasurement(measurement_labels[i])
        wavelength = df.iloc[:, 2 * i]
        values = df.iloc[:, 2 * i + 1]
        column_name = column_headers[2 * i + 1]
        collect.add_data(wavelength, values, column_name)
        collects.append(collect)

    return collects, uma_sequence_length


def read_metadata_block(reader):
    metadata_lines = []
    for row in reader:
        if isinstance(row, list):
            if len(row) == 0:
                # Treat empty list as the start of the metadata
                metadata_lines = [row] + list(reader)
                break
            row_start = row[0]
        if not row_start.isdigit():  # Stop when metadata starts
            metadata_lines = [row] + list(reader)
            break

    # Parse metadata
    metadata_dict = {}
    current_key = None
    current_metadata = []

    for i, line in enumerate(metadata_lines):
        if not any(line):  # Detect empty row separating blocks
            if current_key:
                metadata_dict[f'{current_key}_{i}'] = (
                    current_metadata  # Store previous block
                )
                current_key = None
                current_metadata = []
            continue
        # First row after empty line (or first row of file)
        # is the sample name
        if current_key is None:
            current_key = line[0]
            current_metadata = []
        else:
            current_metadata.append(line)  # Store metadata

    # Save last block
    if current_key:
        metadata_dict[f'{current_key}_last'] = current_metadata

    for key, value in metadata_dict.items():
        metadata_dict[key] = [
            [cell for cell in row if isinstance(cell, str) and cell.strip()]
            for row in value
        ]

    return metadata_dict


def read_config_block(config_path, collects, uma_sequence_length):
    config = pd.read_csv(config_path)

    if len(config) != len(collects) / uma_sequence_length:
        raise ValueError(
            'Inconsistency in the number of uma measurements '
            'and the measurement mapping in the config file.'
        )
    # counter to iterate through measurements in the config file
    config_counter = 0
    # counter to iterate through measurements in the uma sequence
    uma_counter = 0

    for collect in collects:
        collect.add_config(config.iloc[config_counter])
        uma_counter += 1
        if uma_counter == uma_sequence_length:
            config_counter += 1
            uma_counter = 0


def parse_file(data_path, config_path=None):
    with open(data_path, encoding='utf-8') as file:
        reader = csv.reader(file)

        # Read header lines
        measurement_labels = next(reader)  # First row
        # empty strings are removed
        measurement_labels = list(filter(None, measurement_labels))
        column_headers = next(reader)  # Second row

        # Read data block
        collects, uma_sequence_length = read_data_block(
            data_path, measurement_labels, column_headers
        )

        # Read metadata block
        metadata_dict = read_metadata_block(reader)

        if len(collects) != len(metadata_dict):
            raise ValueError('Number of collects and metadata blocks do not match.')

        # Iterate through the metadata dictionary to write the metadata
        for collect, metadata in zip(collects, metadata_dict.values()):
            collect.add_raw_metadata(metadata)

        # Read config block
        if config_path is not None:
            read_config_block(config_path, collects, uma_sequence_length)

    return collects


# -----------------Plotting-------------------


def print_methods(multi_meas_map, verbose=True):
    """
    Method to print the methods used for the derived data, it iterates through
    the derived data and looks for method strings or dictionaries, and prints
    them
    """

    methods = {}
    # we only check the first point of the map (first entry of the map)
    # as the methods should be the same
    first_key = list(multi_meas_map.keys())[0]
    first_measurement = multi_meas_map[first_key]

    for key, value in first_measurement.derived_data.items():
        if 'method' not in key:
            continue
        if isinstance(value, dict):
            if verbose:
                print(f'{key}:')
            for sub_key, sub_value in value.items():
                if verbose:
                    print(f'    {sub_key}: {sub_value}')
                methods[f'{key}_{sub_key}'] = sub_value

        elif isinstance(value, str):
            if verbose:
                print(f'{key}: {value}')
            methods[key] = value

    return methods


def make_heatmap(multi_meas_map):
    """
    Method to make a heatmap of the avg transmission and reflection
    vs the sample position using Plotly for a single sample
    """
    import plotly.graph_objects as go

    # Create a dictionary to store the data
    data_dict = {}
    for position_key, measurement in multi_meas_map.items():
        position_x = measurement.position_x
        position_y = measurement.position_y
        for key, value in measurement.derived_data.items():
            if not isinstance(value, float):
                continue

            if key not in data_dict:
                data_dict[key] = {'X': [], 'Y': [], 'Value': []}
            if isinstance(value, float):
                data_dict[key]['X'].append(position_x)
                data_dict[key]['Y'].append(position_y)
                data_dict[key]['Value'].append(value)

    figs = {}
    export_data = {}
    # Create a heatmap for each key in derived_data
    for key, data in data_dict.items():
        export_data[key] = pd.DataFrame(data)
        fig = go.Figure(
            data=go.Heatmap(
                x=data['X'], y=data['Y'], z=data['Value'], colorscale='Viridis'
            )
        )
        fig.update_layout(
            title=f'Heatmap of {key} vs Sample Position',
            xaxis_title='X Position',
            yaxis_title='Y Position',
            xaxis=dict(scaleanchor='y', scaleratio=1),  # Ensure equal aspect ratio
            yaxis=dict(scaleanchor='x', scaleratio=1),  # Ensure equal aspect ratio
        )
        figs[key] = fig

    return figs, export_data


def plot_derived_data(multi_meas_map, quantity='alpha', x='Energy'):
    fig = go.Figure()

    data_export = pd.DataFrame()
    y_axis_title = quantity  # default value in case loop doesn't set it

    for position_key, measurement in multi_meas_map.items():
        if quantity not in measurement.derived_data:
            continue
        quantity_df = measurement.derived_data[quantity]

        data_export[f'{position_key}_{x}'] = quantity_df[x]
        data_export[f'{position_key}_{quantity}'] = quantity_df[quantity]
        fig.add_trace(
            go.Scatter(
                x=quantity_df[x],
                y=quantity_df[quantity],
                mode='lines',
                name=position_key,
            )
        )
        y_axis_title = quantity

    fig.update_layout(
        title=f'{quantity} vs {x}',
        xaxis_title=x,
        yaxis_title=y_axis_title,
        legend_title='Position',
    )

    return fig, data_export
