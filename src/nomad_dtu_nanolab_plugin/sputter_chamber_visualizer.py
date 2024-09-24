# ------------------PACKAGES AND DEFINITIONS-------------------

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import patches
from matplotlib.transforms import Affine2D
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar

# from nomad_dtu_nanolab_plugin.sputtering import DTUsamples, GunOverview
# from nomad_dtu_nanolab_plugin.substrate import DTUSubstrate
# from nomad_dtu_nanolab_plugin.target import DTUTarget


# ----DEFINE GRAPHICAL PARAMETERS, SPUTTER CHAMBER AND platen ----------

# Define the default grapihcal parameters
DEFAULT_FONTSIZE = 10
DEFAULT_LINEWIDTH = 1
GUN_TO_PLATEN = 1.4

X_LIM = (-130, 130)
Y_LIM = (-110, 110)

# Define the platen geometry
PLATEN_POS, PLATEN_DIAM, PLATEN_CENTER_DIAM = (0, 0), 75, 2

MIDDLE_SCREW_POS, MIDDLE_SCREW_DIAM = (0, 15), 3

TOXIC_GAS_INLET_ANGLE = np.radians(-58)

# Define a dictionary to map names to their colors and locations
GUN_PROPERTIES = {
    'SCracker': {'color': 'red', 'location': np.radians(180)},
    'Taurus': {'color': 'green', 'location': np.radians(90)},
    'Magkeeper3': {'color': 'blue', 'location': np.radians(315)},
    'Magkeeper4': {'color': 'magenta', 'location': np.radians(45)},
}

# ---------CLASSES-------------


# Very simples classes to store the samples and guns information
class Sample:
    # Note that sample positions are the position of the center of
    # the square samples. sub_size=40 is assumed by default.
    def __init__(self, label, pos_x, pos_y, sub_size=40, mat='cSi'):
        self.label = label
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.sub_size = sub_size
        self.pos_x_bl = pos_x - sub_size / 2
        self.pos_y_bl = pos_y - sub_size / 2
        self.mat = mat


class Gun:
    def __init__(
        self,
        name,
        mat,
        pos_x=None,
        pos_y=None,
    ):
        self.name = name
        self.mat = mat
        self.pos_x = pos_x
        self.pos_y = pos_y
        self.gcolor = GUN_PROPERTIES[name]['color']
        self.location = GUN_PROPERTIES[name]['location']


# ----------HELPERS FUNCTIONS----------------


# Function to go back in forth between polar and cartesian
def polar(x, y):
    r = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    return r, theta


def cartesian(r, theta):
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return x, y


# function to read samples number and their position from the logbook
def read_samples(sample_list: list):
    samples = []
    for sample_obj in sample_list:
        label = sample_obj.relative_position
        pos_x = sample_obj.Substrate_position_x
        pos_y = sample_obj.Substrate_position_y
        # size = sample_obj.reference.SIZE?
        sample = Sample(label, pos_x, pos_y)
        samples.append(sample)
    return samples


# Function to read the gun used from the logbook
def read_guns(gun_list: list, gun_names: str):
    guns = []
    for gun_obj, name in zip(gun_list, gun_names):
        # Where do i get where the gun is aiming at ?
        gun = Gun(name, gun_obj.target_material)
        guns.append(gun)
    return guns


def plot_matplotlib_chamber_config(
    samples, guns, platen_angle, plot_platen_angle=False
):
    fig, ax = plt.subplots()

    # Define the shapes
    squares = [
        patches.Rectangle(
            (sample.pos_x_bl, sample.pos_y_bl),
            sample.sub_size,
            sample.sub_size,
            linewidth=DEFAULT_LINEWIDTH,
            edgecolor='g',
            facecolor='none',
        )
        for sample in samples
    ]

    arrowsX = [
        patches.FancyArrow(
            sample.pos_x_bl + sample.sub_size / 10,
            sample.pos_y_bl + sample.sub_size / 10,
            sample.sub_size / 4,
            0,
            width=1,
            head_width=3,
            head_length=3,
            color='red',
        )
        for sample in samples
    ]

    for arrow in arrowsX:
        ax.add_patch(arrow)

    arrowsY = [
        patches.FancyArrow(
            sample.pos_x_bl + sample.sub_size / 10,
            sample.pos_y_bl + sample.sub_size / 10,
            0,
            sample.sub_size / 4,
            width=1,
            head_width=3,
            head_length=3,
            color='blue',
        )
        for sample in samples
    ]

    for arrow in arrowsY:
        ax.add_patch(arrow)

    circles = [
        patches.Circle(
            (gun.pos_x, gun.pos_y),
            2,
            linewidth=DEFAULT_LINEWIDTH,
            edgecolor=gun.gcolor,
            facecolor=gun.gcolor,
        )
        for gun in guns
        if gun.pos_x is not None and gun.pos_y is not None
    ]

    circle_platen = patches.Circle(
        PLATEN_POS,
        PLATEN_DIAM,
        linewidth=DEFAULT_LINEWIDTH,
        edgecolor='black',
        facecolor='none',
    )

    circle_platen_center = patches.Circle(
        PLATEN_POS,
        PLATEN_CENTER_DIAM,
        linewidth=DEFAULT_LINEWIDTH,
        edgecolor='black',
        facecolor='black',
    )

    circle_middle_screw = patches.Circle(
        MIDDLE_SCREW_POS,
        MIDDLE_SCREW_DIAM,
        linewidth=DEFAULT_LINEWIDTH,
        edgecolor='black',
        facecolor='black',
    )

    # Create a transformation to rotate around the origin
    rotation_angle = platen_angle - 90
    rotation_transform = Affine2D().rotate_deg(rotation_angle)

    # Draw the shapes and rotate around the origin when necessary
    for square in squares:
        square.set_transform(rotation_transform + ax.transData)
        ax.add_patch(square)

    for arrow in arrowsX:
        arrow.set_transform(rotation_transform + ax.transData)
        ax.add_patch(arrow)

    for arrow in arrowsY:
        arrow.set_transform(rotation_transform + ax.transData)
        ax.add_patch(arrow)

    for circle in circles:
        ax.add_patch(circle)

    circle_middle_screw.set_transform(rotation_transform + ax.transData)
    ax.add_patch(circle_middle_screw)

    ax.add_patch(circle_platen_center)

    circle_platen.set_transform(rotation_transform + ax.transData)
    ax.add_patch(circle_platen)

    # Add text labels to samples (rotating with a)
    for sample in samples:
        rotated_edge = rotation_transform.transform(
            (
                sample.pos_x_bl + 0.8 * sample.sub_size,
                sample.pos_y_bl + 0.8 * sample.sub_size,
            )
        )
        rotated_arrowX_end = rotation_transform.transform(
            (
                sample.pos_x_bl + 0.55 * sample.sub_size,
                sample.pos_y_bl + 0.15 * sample.sub_size,
            )
        )
        rotated_arrowY_end = rotation_transform.transform(
            (
                sample.pos_x_bl + 0.15 * sample.sub_size,
                sample.pos_y_bl + 0.55 * sample.sub_size,
            )
        )
        ax.text(
            rotated_edge[0],
            rotated_edge[1],
            sample.label,
            ha='center',
            va='center',
            color='black',
            fontsize=DEFAULT_FONTSIZE,
        )
        # Add legend for X
        ax.text(
            rotated_arrowX_end[0],
            rotated_arrowX_end[1],
            'X',
            ha='center',
            va='center',
            color='red',
            fontsize=DEFAULT_FONTSIZE,
            weight='bold',
        )
        # Add legend for Y
        ax.text(
            rotated_arrowY_end[0],
            rotated_arrowY_end[1],
            'Y',
            ha='center',
            va='center',
            color='blue',
            fontsize=DEFAULT_FONTSIZE,
            weight='bold',
        )

    # Add text labels to sputter chamber modules (not rotating)
    for gun in guns:
        ax.text(
            cartesian(GUN_TO_PLATEN * PLATEN_DIAM, gun.location)[0],
            cartesian(GUN_TO_PLATEN * PLATEN_DIAM, gun.location)[1],
            f'{gun.name}\n({gun.mat})',
            ha='center',
            va='center',
            color=gun.gcolor,
            fontsize=DEFAULT_FONTSIZE,
        )

    ax.text(
        0,
        Y_LIM[1] - 10,
        'Glovebox Door',
        ha='center',
        va='center',
        color='black',
        fontsize=DEFAULT_FONTSIZE,
        weight='bold',
    )

    ax.text(
        0,
        Y_LIM[0] + 10,
        'Service Door',
        ha='center',
        va='center',
        color='black',
        fontsize=DEFAULT_FONTSIZE,
        weight='bold',
    )

    ax.text(
        cartesian((GUN_TO_PLATEN + 0.2) * PLATEN_DIAM, TOXIC_GAS_INLET_ANGLE)[0],
        cartesian((GUN_TO_PLATEN + 0.2) * PLATEN_DIAM, TOXIC_GAS_INLET_ANGLE)[1],
        'Toxic\nGas',
        ha='center',
        va='center',
        color='black',
        fontsize=DEFAULT_FONTSIZE,
        weight='bold',
    )

    # Add legend
    if plot_platen_angle:
        ax.legend(
            title=f'a={platen_angle}\u00b0', loc='upper left', fontsize=DEFAULT_FONTSIZE
        )

    # Remove axis lines and ticks
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

    # Add a 50mm scale bar
    fontprops = fm.FontProperties(size=DEFAULT_FONTSIZE)
    scalebar = AnchoredSizeBar(
        ax.transData,
        50,
        '50 mm',
        'upper right',
        pad=0.1,
        color='black',
        frameon=False,
        size_vertical=1,
        fontproperties=fontprops,
    )

    ax.add_artist(scalebar)
    # Set limits and show the plot
    plt.xlim(X_LIM)
    plt.ylim(Y_LIM)
    ax.set_aspect('equal', adjustable='box')

    return fig


def main():
    # Dummy samples and guns

    samples = [
        Sample('1', -15, -15, 40),
        Sample('2', -15, 25, 40),
        Sample('3', 25, -15, 40),
        Sample('4', 25, 25, 40),
    ]

    guns = [
        Gun('Magkeeper4', 'Cu'),
    ]

    platen_angle = 80  # in degrees

    # #------------------------PLOT-----------------------------

    # Call the method in the main function
    fig = plot_matplotlib_chamber_config(samples, guns, platen_angle)
    fig.show()

    # fig = plot_plotly_chamber_config(samples, guns, platen_angle)
    # Show plotly figure
    # fig.show()

    # #-----------------------EXPORT FIGURE-----------------------------

    # fig.savefig(fig_file_path, dpi=300)


if __name__ == '__main__':
    main()