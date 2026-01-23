from renishawWiRE import WDFReader
import pandas as pd
import os
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

class RamanMeas():
    def __init__(self):
        self.x_pos = 0
        self.y_pos = 0
        self.data = pd.DataFrame(columns=['wavenumber', 'intensity'])
        self.image = None  # Store the optical image for this measurement point
        self.laser_wavelength = None

class MappingRamanMeas():
    def __init__(self):
        self.raman_meas_list = []

    def read_wdf_mapping(self, folder, filename_list):
        """Read WDF file and extract both Raman spectra and optical images"""
        for filename in filename_list:
            file_path = os.path.join(folder, filename)
            reader = WDFReader(file_path)

            # Debug information
            #print(f"\n=== WDF File: {filename} ===")
            #print(f"Spectra shape: {reader.spectra.shape}")
            #print(f"Xdata shape: {reader.xdata.shape}")
            #if hasattr(reader, 'xpos') and hasattr(reader, 'ypos'):
            #    print(f"Number of positions: {len(reader.xpos)}")
            #    print(f"X positions: {reader.xpos[:5]}...")
            #    print(f"Y positions: {reader.ypos[:5]}...")

            # Get wavenumber data (should be 1D)
            wv_num = reader.xdata

            # Extract optical images first
            optical_images = self._extract_optical_images_from_reader(reader)
            #print(f"Extracted {len(optical_images)} optical images")

            # Check if we have position data
            if hasattr(reader, 'xpos') and hasattr(reader, 'ypos') and len(reader.xpos) > 1:
                # We have mapping data with positions
                #print(f"Processing {len(reader.xpos)} spectra...")

                # Handle 3D spectra array (e.g., 5x5x1015 grid)
                spectra_array = reader.spectra
                if len(spectra_array.shape) == 3:
                    # 3D array: reshape to 2D [position, wavenumber]
                    #print(f"Reshaping 3D spectra from {spectra_array.shape} to 2D")
                    original_shape = spectra_array.shape
                    spectra_array = spectra_array.reshape(-1, spectra_array.shape[-1])
                    #print(f"Reshaped to: {spectra_array.shape}")

                for i in range(len(reader.xpos)):
                    raman_meas = RamanMeas()
                    raman_meas.x_pos = -reader.xpos[i] #swap x
                    raman_meas.y_pos = reader.ypos[i]
                    raman_meas.laser_wavelength = reader.laser_length

                    # Assign optical image if available
                    if i < len(optical_images):
                        raman_meas.image = optical_images[i]

                    # Get intensity data for this position
                    if len(spectra_array.shape) == 2:
                        # 2D array: [position, wavenumber]
                        intensity = spectra_array[i]
                        if i < 3:  # Debug first few spectra
                            print(f"Spectrum {i}: pos=({raman_meas.x_pos:.2f}, {raman_meas.y_pos:.2f}), "
                                  f"intensity range {intensity.min():.2f} - {intensity.max():.2f}, "
                                  f"has_image={raman_meas.image is not None}")
                    else:
                        # 1D array: single spectrum
                        print("Warning: Only single spectrum found, but multiple positions exist")
                        intensity = spectra_array

                    # Ensure both arrays are 1D
                    wv_num_flat = np.array(wv_num).flatten()
                    intensity_flat = np.array(intensity).flatten()

                    # Make sure arrays have same length
                    min_length = min(len(wv_num_flat), len(intensity_flat))
                    wv_num_flat = wv_num_flat[:min_length]
                    intensity_flat = intensity_flat[:min_length]

                    raman_meas.data = pd.DataFrame(
                        {'wavenumber': wv_num_flat, 'intensity': intensity_flat}
                    )
                    self.raman_meas_list.append(raman_meas)
            else:
                # Single spectrum without position data
                print("Processing single spectrum...")
                raman_meas = RamanMeas()
                raman_meas.x_pos = 0
                raman_meas.y_pos = 0

                # Assign optical image if available
                if len(optical_images) > 0:
                    raman_meas.image = optical_images[0]

                # Ensure both arrays are 1D
                wv_num_flat = np.array(wv_num).flatten()
                intensity_flat = np.array(reader.spectra).flatten()

                # Make sure arrays have same length
                min_length = min(len(wv_num_flat), len(intensity_flat))
                wv_num_flat = wv_num_flat[:min_length]
                intensity_flat = intensity_flat[:min_length]

                raman_meas.data = pd.DataFrame(
                    {'wavenumber': wv_num_flat, 'intensity': intensity_flat}
                )
                self.raman_meas_list.append(raman_meas)

            print(f"Total spectra loaded: {len(self.raman_meas_list)}")

    def _extract_optical_images_from_reader(self, reader):
        """Internal method to extract optical images from WDF reader"""
        from PIL import Image
        import io

        images = []

        # Try to extract from WXDB block
        if hasattr(reader, 'file_obj') and hasattr(reader, 'block_info'):
            if 'WXDB' in reader.block_info:
                block_type, offset, size = reader.block_info['WXDB']
                reader.file_obj.seek(offset)
                wxdb_data = reader.file_obj.read(size)

                # Find all JPEG start positions
                jpeg_start = b'\xff\xd8\xff'
                jpeg_end = b'\xff\xd9'

                start_positions = []
                pos = 0
                while True:
                    pos = wxdb_data.find(jpeg_start, pos)
                    if pos == -1:
                        break
                    start_positions.append(pos)
                    pos += 1

                # Extract each JPEG
                for i, start_pos in enumerate(start_positions):
                    # Find end of this JPEG
                    end_pos = wxdb_data.find(jpeg_end, start_pos)
                    if end_pos == -1:
                        if i < len(start_positions) - 1:
                            end_pos = start_positions[i + 1]
                        else:
                            end_pos = len(wxdb_data)
                    else:
                        end_pos += 2

                    jpeg_data = wxdb_data[start_pos:end_pos]

                    try:
                        img = Image.open(io.BytesIO(jpeg_data))
                        images.append(img)
                    except Exception as e:
                        print(f"  Warning: Failed to extract image {i}: {e}")
                        images.append(None)

        return images

    def save_optical_images(self, folder, filename_prefix):
        """Save all optical images to disk"""
        from PIL import Image

        saved_count = 0
        for i, raman_meas in enumerate(self.raman_meas_list):
            if raman_meas.image is not None:
                img_path = os.path.join(folder,
                    f"{filename_prefix}_point{i}_x{raman_meas.x_pos:.0f}_y{raman_meas.y_pos:.0f}.png")
                raman_meas.image.save(img_path)
                saved_count += 1

        print(f"Saved {saved_count} optical images to {folder}")
        return saved_count

    def normalize_intensity(self, x_range:tuple = None):
        for raman_meas in self.raman_meas_list:
            if x_range is None:
                # Normalize each spectrum by its own max
                max_int = raman_meas.data['intensity'].max()
            else:
                # Filter the data based on the x_range, then get max from filtered data
                mask = (raman_meas.data['wavenumber'] >= x_range[0]) & (raman_meas.data['wavenumber'] <= x_range[1])
                filtered_data = raman_meas.data[mask]
                max_int = filtered_data['intensity'].max() if len(filtered_data) > 0 else 1

            if max_int > 0:  # Avoid division by zero
                raman_meas.data['norm_intensity'] = raman_meas.data['intensity'] / max_int
            else:
                raman_meas.data['norm_intensity'] = raman_meas.data['intensity']


    def plot_spectra(self, color_by='x_pos', method='normalize', x_range=None, max_spectra=None):
        if method == 'normalize':
            # Always normalize fresh for this plot (remove caching)
            print("Normalizing spectra...")
            self.normalize_intensity(x_range=x_range)
            y_plot = 'norm_intensity'
        elif method == 'default':
            y_plot = 'intensity'

        # Limit number of spectra to plot if specified
        spectra_to_plot = self.raman_meas_list
        if max_spectra is not None:
            spectra_to_plot = self.raman_meas_list[:max_spectra]
            print(f"Plotting first {len(spectra_to_plot)} spectra...")

        # Get the color values based on the selected attribute
        color_values = [getattr(raman_meas, color_by) for raman_meas in spectra_to_plot]

        # Create a color scale
        color_scale = px.colors.sequential.Viridis

        # Normalize the color values to the range [0, 1]
        if len(set(color_values)) > 1:  # Check if there are different values
            norm_color_values = (np.array(color_values) - np.min(color_values)) / (np.max(color_values) - np.min(color_values))
        else:
            norm_color_values = np.zeros(len(color_values))

        # Map the normalized color values to the color scale
        colors = [color_scale[int(val * (len(color_scale) - 1))] for val in norm_color_values]

        # Plot spectra with the Plotly library with the position as legend
        fig = go.Figure()
        for i, (raman_meas, color) in enumerate(zip(spectra_to_plot, colors)):
            # Filter data by x_range if specified
            if x_range is not None:
                mask = (raman_meas.data['wavenumber'] >= x_range[0]) & (raman_meas.data['wavenumber'] <= x_range[1])
                plot_data = raman_meas.data[mask]
            else:
                plot_data = raman_meas.data

            # Add some debug info for first few spectra
            if i < 3:
                intensity_range = f"{plot_data[y_plot].min():.2f}-{plot_data[y_plot].max():.2f}"
                print(f"Spectrum {i}: pos=({raman_meas.x_pos:.2f}, {raman_meas.y_pos:.2f}), intensity_range={intensity_range}, n_points={len(plot_data)}")

            fig.add_trace(go.Scatter(
                x=plot_data['wavenumber'],
                y=plot_data[y_plot],
                mode='lines',
                name=f"x={raman_meas.x_pos:.2f}, y={raman_meas.y_pos:.2f}",
                line=dict(color=color)
            ))

        fig.update_layout(
            title=f"Raman Spectra (colored by {color_by})",
            xaxis_title="Wavenumber (cm⁻¹)",
            yaxis_title="Intensity"
        )

        fig.show()
        return fig

    def create_intensity_map(self, target_wavenumber, wavenumber_tolerance=5):
        """Create a 2D intensity map at a specific wavenumber"""
        x_positions = []
        y_positions = []
        intensities = []

        for raman_meas in self.raman_meas_list:
            x_positions.append(raman_meas.x_pos)
            y_positions.append(raman_meas.y_pos)

            # Find intensity at target wavenumber
            mask = (raman_meas.data['wavenumber'] >= target_wavenumber - wavenumber_tolerance) & \
                   (raman_meas.data['wavenumber'] <= target_wavenumber + wavenumber_tolerance)
            filtered_data = raman_meas.data[mask]

            if len(filtered_data) > 0:
                intensity = filtered_data['intensity'].mean()
            else:
                intensity = 0
            intensities.append(intensity)

        return pd.DataFrame({
            'x_pos': x_positions,
            'y_pos': y_positions,
            'intensity': intensities
        })

    def plot_intensity_map(self, target_wavenumber, wavenumber_tolerance=5):
        """Plot a 2D intensity map at a specific wavenumber"""
        map_data = self.create_intensity_map(target_wavenumber, wavenumber_tolerance)

        # Create a pivot table for the heatmap
        x_unique = sorted(map_data['x_pos'].unique())
        y_unique = sorted(map_data['y_pos'].unique())

        # Create intensity matrix
        intensity_matrix = np.zeros((len(y_unique), len(x_unique)))

        for _, row in map_data.iterrows():
            x_idx = x_unique.index(row['x_pos'])
            y_idx = y_unique.index(row['y_pos'])
            intensity_matrix[y_idx, x_idx] = row['intensity']

        fig = go.Figure(data=go.Heatmap(
            z=intensity_matrix,
            x=x_unique,
            y=y_unique,
            colorscale='Viridis',
            colorbar=dict(title="Intensity")
        ))

        fig.update_layout(
            title=f"Raman Intensity Map at {target_wavenumber} cm⁻¹",
            xaxis_title="X Position (μm)",
            yaxis_title="Y Position (μm)"
        )

        fig.show()
        return fig


    def create_image_grid(self, save_path=None, spacing= (-0.4, 0.1)):
        """Create a grid showing all optical images with their positions"""
        import matplotlib.pyplot as plt
        from matplotlib.gridspec import GridSpec

        # Filter to only measurements with images
        measurements_with_images = [m for m in self.raman_meas_list if m.image is not None]

        if not measurements_with_images:
            print("No optical images available")
            return

        n_images = len(measurements_with_images)
        n_cols = 3
        n_rows = (n_images + n_cols - 1) // n_cols

        fig = plt.figure(figsize=(15, 5 * n_rows))
        gs = GridSpec(n_rows, n_cols, figure=fig, hspace=spacing[0], wspace=spacing[1])

        for i, raman_meas in enumerate(measurements_with_images):
            row = i // n_cols
            col = i % n_cols
            ax = fig.add_subplot(gs[row, col])

            ax.imshow(raman_meas.image)
            # Find original index
            orig_idx = self.raman_meas_list.index(raman_meas)
            ax.set_title(f"Point {orig_idx}\n"
                        f"X={raman_meas.x_pos:.1f} μm, Y={raman_meas.y_pos:.1f} μm",
                        fontsize=10)
            ax.axis('off')

        #plt.suptitle('Optical Images at Each Raman Measurement Point',
        #            fontsize=14, fontweight='bold')

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Grid saved to: {save_path}")

        plt.show()
        return fig

def main():
    global mapping
    folder = r"Z:\P110143-phosphosulfides-Andrea\Data\Samples\indiogo_0019_RTP\Raman"
    filename_list = [
        "indiogo_0019_RTP_hc_1x10s_P1_x20_map_0.wdf",
    ]

    meas_name = filename_list[0].split(".")[0]
    sample_list = meas_name.split("_")[:4]
    sample_name = "_".join(sample_list)

    mapping = MappingRamanMeas()

    # Read WDF file (this now automatically extracts and stores images)
    print("="*60)
    print("READING WDF FILE AND EXTRACTING DATA")
    print("="*60)
    mapping.read_wdf_mapping(folder, filename_list)

    # Optionally save all images to disk
    print("\n" + "="*60)
    print("SAVING OPTICAL IMAGES")
    print("="*60)
    mapping.save_optical_images(folder, meas_name)

    # Create a grid view of all images (now uses .image attribute)
    print("\n" + "="*60)
    print("CREATING IMAGE GRID")
    print("="*60)
    grid_path = os.path.join(folder, f"{meas_name}_optical_grid.png")
    mapping.create_image_grid(save_path=grid_path)

    # Plot all spectra
    print("\n" + "="*60)
    print("PLOTTING RAMAN SPECTRA")
    print("="*60)
    fig = mapping.plot_spectra(method='default', x_range=(80, 1000))
    fig.write_html(os.path.join(folder, f"{meas_name}_Raman_spectra.html"))

    # Create intensity map
    print("\n" + "="*60)
    print("CREATING INTENSITY MAP")
    print("="*60)
    map_fig = mapping.plot_intensity_map(target_wavenumber=380, wavenumber_tolerance=2)
    map_fig.write_html(os.path.join(folder, f"{meas_name}_Raman_intensity_map.html"))

    # Example: Access individual images
    print("\n" + "="*60)
    print("EXAMPLE: ACCESSING INDIVIDUAL IMAGES")
    print("="*60)
    for i, raman_meas in enumerate(mapping.raman_meas_list[:3]):
        print(f"Point {i}: x={raman_meas.x_pos:.1f}, y={raman_meas.y_pos:.1f}, "
              f"has_image={raman_meas.image is not None}, "
              f"image_size={raman_meas.image.size if raman_meas.image else 'N/A'}")

if __name__ == "__main__":
    main()