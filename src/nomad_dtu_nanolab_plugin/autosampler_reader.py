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


def _standard_treatment_options(args, kwargs):
    defaults = {
        'wv_start': WV_START,
        'wv_end': WV_END,
        'alpha_method': ALPHA_METHOD,
        'tauc_method': TAUC_METHOD,
        'max_energy': MAX_ENERGY,
        'window_size': WINDOW_SIZE,
        'window_size_intercept': WINDOW_SIZE_INTERCEPT,
        'window_size_threshold': WINDOW_SIZE_THRESHOLD,
        'alpha_threshold': ALPHA_THRESHOLD,
        'method': 'normalized',
        'min_r': MIN_R,
        'min_slope': 1,
    }
    names = tuple(defaults)
    if len(args) > len(names):
        raise TypeError(
            f'standard_treatment() takes {len(names)} positional arguments '
            f'but {len(args)} were given'
        )

    options = dict(zip(names, args))
    for name, value in kwargs.items():
        if name not in defaults:
            raise TypeError(
                f"standard_treatment() got an unexpected keyword argument '{name}'"
            )
        if name in options:
            raise TypeError(
                f"standard_treatment() got multiple values for argument '{name}'"
            )
        options[name] = value
    return {**defaults, **options}


def _build_alpha_dataframes(transmission, reflection, source_measurement, method):
    def format_values(reflectance, transmittance):
        reflectance[reflectance > 1] = 1
        transmittance[transmittance < 0] = T_THRESHOLD
        return reflectance, transmittance

    def one_front(transmittance, reflectance):
        reflectance, transmittance = format_values(reflectance, transmittance)
        return -np.log(transmittance / (1 - reflectance))

    def front_and_back(transmittance, reflectance):
        reflectance, transmittance = format_values(reflectance, transmittance)
        return -np.log(transmittance / (1 - reflectance) ** 2)

    def infinite_reflections(transmittance, reflectance):
        reflectance, transmittance = format_values(reflectance, transmittance)
        return -np.log(
            -(
                reflectance**2
                + np.sqrt(
                    reflectance**4
                    + 4 * transmittance**2 * reflectance**2
                    - 4 * reflectance**3
                    + 6 * reflectance**2
                    - 4 * reflectance
                    + 1
                )
                - 2 * reflectance
                - 1
            )
            / (2 * reflectance**2 * transmittance)
        )

    alpha_methods = {
        '1fr': one_front,
        '1fbr': front_and_back,
        'infr': infinite_reflections,
    }
    t_df = pd.DataFrame(
        {
            'Wavelength': transmission['wavelength'],
            'Energy': transmission['energy'],
            'T': transmission['intensity'],
        }
    )
    r_df = pd.DataFrame(
        {
            'Wavelength': reflection['wavelength'],
            'Energy': reflection['energy'],
            'R': reflection['intensity'],
        }
    )
    alpha_df = pd.DataFrame(
        {
            'Wavelength': source_measurement.data['Wavelength'],
            'Energy': source_measurement.data['Energy'],
            'alpha': alpha_methods[method](
                transmission['fraction'], reflection['fraction']
            ),
        }
    )
    alpha_df.loc[alpha_df['alpha'] > MAX_ALPHA, 'alpha'] = MAX_ALPHA
    normalized_alpha_df = alpha_df.copy()
    normalized_alpha_df['normalized_alpha'] = (
        alpha_df['alpha'] - alpha_df['alpha'].min()
    ) / (alpha_df['alpha'].max() - alpha_df['alpha'].min())
    normalized_alpha_df.drop(columns=['alpha'], inplace=True)
    return t_df, r_df, alpha_df, normalized_alpha_df


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
                str(int(float(polarisation_angle.strip()))), 'custom'
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
                if len(row) == 1 or row[1].strip() == 'None':
                    polarisation_angle = 'None'
                else:
                    polarisation_angle = row[1]
                self.metadata['PolarizationAngle'] = (
                    None
                    if polarisation_angle == 'None'
                    else float(polarisation_angle.strip())
                )
                self.metadata['Polarization'] = POLARISATION_DICT.get(
                    polarisation_angle.strip(), 'custom'
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
            elif self.verbose:
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

        rt_measurements = self._get_rt_measurements()
        if rt_measurements is None:
            return
        self._filter_rt_wavelengths(rt_measurements, wv_start, wv_end)
        transmission, reflection, source_measurement = self._get_rt_arrays(
            rt_measurements
        )
        t_df, r_df, alpha_df, normalized_alpha_df = _build_alpha_dataframes(
            transmission, reflection, source_measurement, method
        )
        self.derived_data['T'] = t_df
        self.derived_data['R'] = r_df
        self.derived_data['alpha'] = alpha_df
        self.derived_data['normalized_alpha'] = normalized_alpha_df
        self.derived_data['alpha_method'] = method

    def _get_rt_measurements(self):
        grouped = {}
        for measurement in self.avg_sp_measurements:
            key = measurement.metadata['MeasurementType']
            grouped.setdefault(key, []).append(measurement)

        for key, measurements in grouped.items():
            if len(measurements) != 1:
                if self.verbose:
                    print(
                        f'Warning (point X={self.position_x}, '
                        f'Y={self.position_y}): {len(measurements)} {key} '
                        'measurements found'
                    )
                return None

        if 'T' not in grouped or 'R' not in grouped:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): T or R measurement missing'
                )
            return None
        return grouped

    @staticmethod
    def _filter_rt_wavelengths(rt_measurements, wv_start, wv_end):
        for measurements in rt_measurements.values():
            data = measurements[0].data
            mask = pd.Series(True, index=data.index)
            if wv_start is not None:
                mask &= data['Wavelength'] >= wv_start
            if wv_end is not None:
                mask &= data['Wavelength'] <= wv_end
            if wv_start is not None or wv_end is not None:
                measurements[0].data = data[mask].reset_index(drop=True)

    @staticmethod
    def _get_rt_arrays(rt_measurements):
        values = {}
        source_measurement = None
        for key, measurements in rt_measurements.items():
            source_measurement = measurements[0]
            data = source_measurement.data
            values[key] = {
                'fraction': data['Intensity'] / 100,
                'intensity': data['Intensity'],
                'wavelength': data['Wavelength'],
                'energy': data['Energy'],
            }
        return values['T'], values['R'], source_measurement

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

        smooth_alpha, first_derivative, second_derivative = self._smooth_alpha(
            wavelength, alpha, window_size
        )
        (
            wavelength_trimmed,
            smooth_alpha_trimmed,
            first_derivative_trimmed,
            second_derivative_trimmed,
        ) = self._trim_inflection_edges(
            wavelength,
            smooth_alpha,
            first_derivative,
            second_derivative,
            edge_points_to_remove,
        )

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

        self._store_inflection_data(
            wavelength_trimmed,
            smooth_alpha_trimmed,
            first_derivative_trimmed,
            second_derivative_trimmed,
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

    def _smooth_alpha(self, wavelength, alpha, window_size):
        wavelength_diff = np.diff(wavelength)
        if np.allclose(wavelength_diff, wavelength_diff[0]):
            smooth_alpha = signal.savgol_filter(alpha, window_size, 2)
            first_derivative = signal.savgol_filter(
                smooth_alpha, window_size, 2, deriv=1, mode='mirror'
            )
            second_derivative = signal.savgol_filter(
                smooth_alpha, window_size, 2, deriv=2, mode='mirror'
            )
            return smooth_alpha, first_derivative, second_derivative

        if self.verbose:
            print(
                f'Warning (point X={self.position_x},'
                f' Y={self.position_y}): '
                'Wavelength values are not evenly spaced. Using rolling'
                ' average smoothing instead.'
            )
        kernel = np.ones(window_size) / window_size
        smooth_alpha = np.convolve(alpha, kernel, mode='same')
        first_derivative = np.gradient(smooth_alpha, wavelength)
        second_derivative = np.gradient(first_derivative, wavelength)
        return smooth_alpha, first_derivative, second_derivative

    def _trim_inflection_edges(
        self,
        wavelength,
        smooth_alpha,
        first_derivative,
        second_derivative,
        edge_points_to_remove,
    ):
        if len(wavelength) > 2 * edge_points_to_remove:
            valid_slice = slice(edge_points_to_remove, -edge_points_to_remove)
            trimmed = tuple(
                values[valid_slice]
                for values in (
                    wavelength,
                    smooth_alpha,
                    first_derivative,
                    second_derivative,
                )
            )
            if self.verbose:
                print(
                    f'Info (point X={self.position_x}, Y={self.position_y}): '
                    f'Removed {edge_points_to_remove} points from each edge. '
                    f'Working with {len(trimmed[0])} points instead '
                    f'of {len(wavelength)}.'
                )
            return trimmed

        if self.verbose:
            print(
                f'Warning (point X={self.position_x}, Y={self.position_y}): '
                f'Not enough data points to remove edges safely. '
                f'Using all {len(wavelength)} points.'
            )
        return wavelength, smooth_alpha, first_derivative, second_derivative

    def _store_inflection_data(
        self, wavelength, smooth_alpha, first_derivative, second_derivative
    ):
        energy = 1239.84 / wavelength
        normalized = (smooth_alpha - np.min(smooth_alpha)) / (
            np.max(smooth_alpha) - np.min(smooth_alpha)
        )
        self.derived_data['normalized_smoothed_alpha'] = pd.DataFrame(
            {
                'Wavelength': wavelength,
                'Energy': energy,
                'normalized_smoothed_alpha': normalized,
            }
        )
        for key, values in (
            ('smoothed_alpha', smooth_alpha),
            ('1st_deriv_alpha', first_derivative),
            ('2nd_deriv_alpha', second_derivative),
        ):
            self.derived_data[key] = pd.DataFrame(
                {
                    'Wavelength': wavelength,
                    'Energy': energy,
                    key: values,
                }
            )

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
        if not self._has_threshold_data(min_alpha):
            return

        alpha_df, alpha = self._threshold_alpha(method)
        energy = alpha_df['Energy'].values
        E_g = self._find_threshold_energy(energy, alpha, threshold, window_size)
        self.derived_data['bandgap_threshold_energy'] = E_g
        self.derived_data['bandgap_threshold_wavelength'] = 1239.84 / E_g
        self.derived_data['bandgap_threshold_method'] = {
            'threshold': threshold,
            'window_size': window_size,
        }

    def _has_threshold_data(self, min_alpha):
        if 'alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Alpha data missing'
                )
            return False
        if 'smoothed_alpha' not in self.derived_data:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Smoothed alpha data missing'
                )
            return False
        smoothed_alpha = self.derived_data['smoothed_alpha']['smoothed_alpha']
        if all(smoothed_alpha > min_alpha):
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): All alpha values are above the '
                    'threshold. Bandgap estimation impossible.'
                )
            self.derived_data['bandgap_threshold_energy'] = np.nan
            self.derived_data['bandgap_threshold_wavelength'] = np.nan
            return False
        return True

    def _threshold_alpha(self, method):
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
        return alpha_df, alpha

    def _find_threshold_energy(self, energy, alpha, threshold, window_size):
        for index in range(len(energy) - window_size):
            energy_window = energy[index : index + window_size]
            alpha_window = alpha[index : index + window_size]
            if all(alpha_window > threshold):
                if index == 0:
                    if self.verbose:
                        print(
                            f'Warning (point X={self.position_x}, '
                            f'Y={self.position_y}): All alpha values are above the '
                            'threshold. Bandgap estimation impossible.'
                        )
                    return np.nan
                return np.mean(energy_window)

        if self.verbose:
            print(
                f'Warning (point X={self.position_x}, '
                f'Y={self.position_y}): No suitable region found for '
                'bandgap estimation.'
            )
        return np.nan

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

        fit_result = self._find_tauc_fit(energy, tauc, window_size, min_slope)
        E_g, best_r, best_region, best_region_center = self._resolve_tauc_fit(
            alpha,
            fit_result,
            min_r,
            min_slope,
        )

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
        if fit_result[3] is not None:
            self.derived_data['intercept_best_slope'] = fit_result[3].coef_[0]

        return best_region, best_r

    @staticmethod
    def _find_tauc_fit(energy, tauc, window_size, min_slope):
        best_r = -1
        best_region = None
        best_region_center = None
        best_fit = None
        for index in range(len(energy) - window_size):
            energy_window = energy[index : index + window_size]
            tauc_window = tauc[index : index + window_size]
            model = LinearRegression()
            model.fit(energy_window.reshape(-1, 1), tauc_window)
            correlation = np.corrcoef(energy_window, tauc_window)[0, 1]
            if correlation > best_r and model.coef_[0] > min_slope:
                best_r = correlation
                best_region = (index, index + window_size)
                best_region_center = 0.5 * (best_region[0] + best_region[1])
                best_fit = model
        return best_r, best_region, best_region_center, best_fit

    def _resolve_tauc_fit(
        self,
        alpha,
        fit_result,
        min_r,
        min_slope,
    ):
        best_r, best_region, best_region_center, best_fit = fit_result
        if best_fit is None:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): No suitable region found for '
                    f'bandgap estimation (r>{min_r} and slope>{min_slope}).'
                )
            return np.nan, np.nan, np.nan, np.nan
        if best_r < min_r:
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): Best region correlation '
                    f'coefficient below {min_r}. Bandgap estimation impossible.'
                )
            return np.nan, best_r, best_region, best_region_center
        if all(alpha > MIN_ALPHA_BANDGAP):
            if self.verbose:
                print(
                    f'Warning (point X={self.position_x}, '
                    f'Y={self.position_y}): All alpha values are above '
                    f'{MIN_ALPHA_BANDGAP}. Bandgap estimation impossible.'
                )
            return np.nan, np.nan, np.nan, np.nan
        bandgap = -best_fit.intercept_ / best_fit.coef_[0]
        return bandgap, best_r, best_region, best_region_center

    def standard_treatment(self, *args, **kwargs):
        """
        method to perform the standard treatment of the data
        """
        options = _standard_treatment_options(args, kwargs)
        self.avg_sp_pol()
        self.calc_avg_transmission_refl(
            wv_start=options['wv_start'], wv_end=options['wv_end']
        )
        self.find_max_transmission_refl(
            wv_start=options['wv_start'], wv_end=options['wv_end']
        )
        self.calc_alpha(
            method=options['alpha_method'],
            wv_start=options['wv_start'],
            wv_end=options['wv_end'],
        )
        self.calc_tauc(method=options['tauc_method'])
        self.estimate_bandgap_inflection(
            max_energy=options['max_energy'], window_size=options['window_size']
        )
        self.estimate_bandgap_tauc(
            window_size=options['window_size_intercept'],
            max_energy=options['max_energy'],
            min_r=options['min_r'],
            min_slope=options['min_slope'],
        )
        self.estimate_bandgap_threshold(
            threshold=options['alpha_threshold'],
            window_size=options['window_size_threshold'],
            method=options['method'],
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


def read_data_block(data_path, measurement_labels, column_headers, parse_sequence=True):

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

    if parse_sequence:
        uma_sequence_length = get_uma_sequence_length(measurement_labels)
    else:
        uma_sequence_length = len(collects)

    return collects, uma_sequence_length


def read_metadata_block(reader):
    metadata_lines = []
    for row in reader:
        if isinstance(row, list):
            if len(row) == 0:
                metadata_lines = [row] + list(reader)
                break
            row_start = row[0]
        # FIX: use float() instead of isdigit() to handle decimal wavelengths
        try:
            float(row_start)
        except ValueError:
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


def parse_file(data_path, config_path=None, parse_sequence=True):
    with open(data_path, encoding='utf-8') as file:
        reader = csv.reader(file)

        # Read header lines
        measurement_labels = next(reader)  # First row
        # empty strings are removed
        measurement_labels = list(filter(None, measurement_labels))
        column_headers = next(reader)  # Second row

        # Read data block
        collects, uma_sequence_length = read_data_block(
            data_path,
            measurement_labels,
            column_headers,
            parse_sequence=parse_sequence,
        )

        # Read metadata block
        metadata_dict = read_metadata_block(reader)

        if len(collects) != len(metadata_dict):
            raise ValueError(
                f'Number of collects ({len(collects)})',
                f'and metadata blocks ({len(metadata_dict)}) do not match.',
                f'{metadata_dict.keys()}',
            )

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
