# Add Ellipsometry Measurements

This guide explains how to add ellipsometry optical characterization data to your combinatorial library in NOMAD Oasis.

## Overview

Ellipsometry provides optical properties including film thickness, refractive index (n), and extinction coefficient (k). This guide covers:

- Exporting data from CompleteEASE software
- Creating an ellipsometry measurement entry
- Uploading n&k and thickness data files
- Reviewing auto-generated plots

## Prerequisites

Before starting, you need:

- **Completed synthesis upload** with combinatorial libraries
- **Ellipsometry measurement snapshot files** - CompleteEASE `.snapshot` files
- **Knowledge of which quarter** you measured (BL, BR, FL, FR)
- **Access to CompleteEASE software** - For data export

!!! info "File Format"
    You'll need to export three files from CompleteEASE:

    - **n&k file** (`.txt`) - Refractive index and extinction coefficient vs. position
    - **Thickness file** (`.txt`) - Thickness, roughness, MSE, and other fit parameters
    - **Snapshot file** (`.snapshot`) - Original measurement file (for archival)

## Step 1: Export Data from CompleteEASE

### 1.1 Transfer Data from Instrument

1. Move the measurement data with a USB stick from the ellipsometer to a separate computer
2. Store data on the O: drive or your designated storage location

### 1.2 Open CompleteEASE Software

1. Launch the **Remote Desktop Connection** software on your PC
2. Connect to the remote computer **DTU-8CC0321MFL**
3. Open the **CompleteEASE** software

### 1.3 Load Your Snapshot

1. Go to **Analysis** → **Open Snapshot** → **Browse file system**
2. Navigate to your measurement file and open it

![CompleteEASE interface](../assets/ellipsometry-completeease.png)

### 1.4 Fit Data for All Points

1. In the software, fit the ellipsometry data for all measured points
2. Ensure all fits converge and show reasonable MSE (Mean Squared Error) values

![Fit parameters window](../assets/ellipsometry-fit-window.png)

!!! tip "Quality Check"
    Review the MSE values - lower values indicate better fits. Typical values should be < 10 for good fits.

### 1.5 Export n&k Data

To export the refractive index (n) and extinction coefficient (k):

1. **Right-click** into the fitting window
2. Select **"Graph OCs Vs. Position"**
3. Choose the optical constant type to graph:
   - Select **n** (refractive index)
   - Select **k** (extinction coefficient)
   - Or select **e1 & e2** (dielectric constants) if needed

![Edit fit parameter dialog](../assets/ellipsometry-graph-selection.png)

4. **Right-click** into the plot that appears
5. Select **"Copy Data to Clipboard"**
6. Paste the data into a new text file
7. Save with naming convention: `username_####_Material_Quarter_nk.txt`

**Example filename**: `eugbe_0020_Zr_BR_nk.txt`

This is your **n&k file** for uploading to NOMAD.

![n&k data plot](../assets/ellipsometry-nk-plot.png)

### 1.6 Export Thickness Data

To export thickness and other fit parameters:

1. **Left-click** on **Thickness** in the fitting window (or other parameters like Roughness, E inf, etc.)

![Thickness selection in fit window](../assets/ellipsometry-thickness-fit.png)

2. Click **"Copy Parameters to Clipboard"**
3. Paste the data into a new text file
4. Save with naming convention: `username_####_Material_Quarter_th.txt`

**Example filename**: `eugbe_0020_Zr_BR_th.txt`

This is your **thickness file** for uploading to NOMAD. It contains:

- Film thickness at each position
- Surface roughness
- MSE (fit quality metric)
- Other fitted parameters

### 1.7 Prepare Snapshot File

Keep the original `.snapshot` file - you'll upload this to NOMAD as well for archival purposes.

**Example filename**: `eugbe_0020_Zr_BR.snapshot`

!!! note "Snapshot Parsing"
    The snapshot file is currently uploaded for archival but not automatically parsed. Future versions may extract data directly from snapshot files.

## Step 2: Navigate to Your Upload

1. Log into **NOMAD Oasis**
2. Go to the **sputtering upload** where your combinatorial libraries were created
3. Click on the upload to open it

!!! tip "Finding Your Upload"
    Use the search function or filter by your username to quickly locate your uploads.

## Step 3: Create Ellipsometry Measurement Entry

### 3.1 Start Schema Creation

Click **"Create from schema"** in your upload.

### 3.2 Name and Select Schema

Follow the naming convention:

```
username_####_Material_Quarter_Ellipsometry
```

Examples:

- `eugbe_0020_Zr_BR_Ellipsometry` (back right quarter)
- `username_0123_BaZr_FL_Ellipsometry` (front left quarter)

**Select the schema:**

- Choose **"Ellipsometry Measurement"** from the Built-in schemas dropdown

Click **"Create"**.

## Step 4: Upload Ellipsometry Data

### 4.1 Locate the File Upload Fields

Scroll down in the ellipsometry entry to find the upload fields:

- **n&k file** - For optical constants data
- **Thickness file** - For thickness and fit parameters
- **Snapshot file** - For the original CompleteEASE file

### 4.2 Upload n&k File

1. Locate the **"n&k file"** upload field
2. Click the upload area or drag and drop your `*_nk.txt` file
3. **IMPORTANT: Click "Save"** immediately after the file uploads

!!! danger "Must Save!"
    Failing to save after uploading will result in data loss. Always click "Save" after file uploads.

### 4.3 Upload Thickness File

1. Locate the **"Thickness file"** upload field
2. Upload your `*_th.txt` file
3. **Click "Save"** immediately

### 4.4 Upload Snapshot File

1. Locate the **"Snapshot file"** upload field
2. Upload your `.snapshot` file from CompleteEASE
3. **Click "Save"** immediately

!!! info "Processing Time"
    NOMAD processes the files and extracts:

    - Optical constants (n, k) at each wavelength and position
    - Film thickness across the measured area
    - Roughness and other parameters
    - Fit quality metrics (MSE)
    - Relationships to the combinatorial library geometry

## Step 5: Review Results

### 5.1 Navigate to Results Subsection

Scroll down to find the **"Results"** subsection and expand it.

### 5.2 Examine Auto-Generated Plots

NOMAD automatically generates visualizations showing:

- Thickness vs. position (heatmap)
- Refractive index (n) vs. position
- Extinction coefficient (k) vs. position
- n and k vs. wavelength at different positions
- Roughness distribution
- MSE fit quality map

All measurement points from your data files are displayed in the graphs.

### 5.3 Verify Data Quality

Check the plots for:

- **Thickness uniformity** or expected gradients
- **Reasonable n&k values** (n typically 1.5-4 for most materials)
- **Low MSE values** (< 10 for good fits, shown in fit quality map)
- **Consistent roughness** across the sample

## Step 6: Clean Invalid Data Points (If Needed)

During ellipsometry mapping, you might have:

- Points with poor fits (high MSE)
- Measurements on bare substrate
- Edge effects
- Outliers

### 6.1 Identify Bad Points

Review the plots and identify suspicious data:

- Very high MSE values (> 20)
- Unreasonable thickness values
- Points in unmeasured regions
- Outliers inconsistent with neighbors

### 6.2 Delete Invalid Points

1. Locate the data point in the list (usually shown with coordinates)
2. Click the **trash can icon** next to the invalid point
3. **Click "Save"** after each deletion

!!! warning "Save After Each Deletion"
    Changes aren't final until you save. Always click "Save" after removing points.

## Step 7: Repeat for Additional Quarters

If you measured multiple quarters of your combinatorial library, repeat this entire process for each quarter:

1. Export n&k, thickness, and snapshot files with the appropriate quarter identifier:
   - `username_####_Material_BR_nk.txt`, `*_th.txt`, `*.snapshot`
   - `username_####_Material_BL_nk.txt`, `*_th.txt`, `*.snapshot`
   - `username_####_Material_FL_nk.txt`, `*_th.txt`, `*.snapshot`
   - `username_####_Material_FR_nk.txt`, `*_th.txt`, `*.snapshot`

2. Create new Ellipsometry Measurement entries for each quarter

3. Upload the corresponding files

4. Review results and clean data if needed

!!! tip "Mapping Strategy"
    Quarters are commonly measured individually. This allows:

    - Manageable data processing
    - Easier quality control
    - Parallel characterization workflows
    - Better organization in NOMAD

## Verification Checklist

After uploading ellipsometry data, verify:

- [ ] Entry named correctly with quarter identifier
- [ ] n&k file uploaded successfully
- [ ] Thickness file uploaded successfully
- [ ] Snapshot file uploaded successfully
- [ ] Results subsection shows plots
- [ ] Thickness values are reasonable (typically nm to hundreds of nm)
- [ ] n&k values make physical sense
- [ ] MSE values indicate good fits (< 10 preferred)
- [ ] Invalid points removed (if any)
- [ ] Final save completed

## Troubleshooting

### No plots appear in Results section

**Problem**: Results subsection is empty or shows errors

**Solutions**:

- Check file formats - ensure `.txt` files are properly formatted
- Verify files exported correctly from CompleteEASE
- Check that you clicked "Save"
- Refresh the page and wait for processing
- Ensure n&k and thickness files have correct column structure

### Wrong data appears in plots

**Problem**: Plots show unexpected values or positions

**Solutions**:

- Verify you uploaded files from the correct measurement
- Check that files correspond to the correct quarter
- Confirm naming convention matches the quarter being uploaded
- Re-export from CompleteEASE and verify data integrity
- Check that position coordinates in files match library geometry

### High MSE values throughout

**Problem**: Fit quality is poor (MSE > 20) for many points

**Solutions**:

- Review fits in CompleteEASE software
- Adjust fitting model or parameters
- Check measurement quality (angles, wavelengths)
- Consider if sample has rough surface or is inhomogeneous
- May need to re-measure problematic areas

### File upload rejected

**Problem**: Files won't upload or show errors

**Solutions**:

- Verify files are in plain text (`.txt`) format
- Check file size (should be < 5 MB typically)
- Ensure files aren't corrupted
- Try opening files in a text editor to verify content
- Re-export from CompleteEASE
- Check file permissions

### Thickness values seem wrong

**Problem**: Thickness much higher or lower than expected

**Solutions**:

- Verify fitting model in CompleteEASE
- Check if substrate is correctly defined
- Review layer stack configuration
- Confirm units (nm vs. Å vs. µm)
- Check if multiple layers are being summed incorrectly

### Can't delete data points

**Problem**: Trash icon missing or not working

**Solutions**:

- Ensure you're in edit mode
- Check you have write permissions on the upload
- Try refreshing the page
- Verify the entry isn't published/locked

## Understanding Ellipsometry Data

### What does ellipsometry measure?

Ellipsometry provides:

- **Film thickness** - Accurate thickness determination (Å precision)
- **Refractive index (n)** - Real part of complex refractive index
- **Extinction coefficient (k)** - Imaginary part related to absorption
- **Surface roughness** - Rms roughness of film surface
- **Layer properties** - Can characterize multi-layer stacks

### Measurement considerations:

- **Model-dependent**: Results depend on the fitting model used
- **Wavelength range**: Typically UV-visible-NIR (200-1000 nm)
- **Spot size**: ~1-3 mm (larger than EDX or Raman)
- **Substrate effects**: Must account for substrate optical properties
- **Thickness range**: Most accurate for films 10 nm - 10 µm

### Data interpretation:

Use the visualizations to:

- Map film thickness across combinatorial libraries
- Identify optical constant variations with composition
- Correlate thickness with deposition conditions
- Find composition regions with desired optical properties
- Verify film uniformity or intentional gradients

### Fit quality (MSE):

- **MSE < 5**: Excellent fit
- **MSE 5-10**: Good fit
- **MSE 10-20**: Acceptable, may need review
- **MSE > 20**: Poor fit, check model or measurement

## Next Steps

After adding ellipsometry measurements:

1. **[Add EDX Measurements](add-edx-measurements.md)** - Correlate optical properties with composition
2. **[Add XRD Measurements](add-xrd-measurements.md)** - Link optical properties to crystal structure
3. **[Add Raman Measurements](add-raman-measurements.md)** - Complement with vibrational spectroscopy
4. **[Export High-Quality Figures](export-high-quality-figures.md)** - Create publication-ready plots

## Related Resources

- [Upload Sputtering Data](upload-sputtering-data.md) - Create the parent combinatorial library
- [Ellipsometry Reference](../reference/ellipsometry.md) - Detailed schema documentation
- [Combinatorial Libraries](../explanation/combinatorial-libraries.md) - Understanding the data model
- [Characterization Overview](../explanation/characterization.md) - General characterization workflow

## Need Help?

If you encounter issues:

- Check the troubleshooting section above
- Review the [characterization explanation](../explanation/characterization.md)
- Ask in the [NOMAD Discord](https://discord.gg/Gyzx3ukUw8)
- Contact your local NOMAD administrator
- Open an issue on [GitHub](https://github.com/DTU-Nanolab-materials-discovery/nomad-dtu-nanolab-plugin/issues)
