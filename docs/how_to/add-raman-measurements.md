# Add Raman Measurements

This guide explains how to add Raman spectroscopy measurements to your combinatorial library in NOMAD Oasis.

## Overview

Raman spectroscopy provides structural and compositional information through vibrational modes. This guide shows you how to:

- Create a Raman measurement entry
- Upload Renishaw .wdf data files
- Review auto-generated plots
- Clean up invalid data points

## Prerequisites

Before starting, you need:

- **Completed synthesis upload** with combinatorial libraries that you have characterized
- **Raman .wdf files** - Renishaw WiRE format files from your measurements
- **Knowledge of which quarter** you measured (BL, BR, FL, FR)

!!! info "File Format"
    Your .wdf files are the native Renishaw format containing position coordinates, Raman spectra, optional optical microscopy image and measurement metadata.

## Step 1: Navigate to Your Upload

1. Go to the **sputtering upload** where your combinatorial libraries were created

2. Click on the upload to open it

!!! tip "Finding Your Upload"
    Use the search function, sputtering app or filter by your username to quickly locate your uploads.

## Step 2: Create Raman Measurement Entry

### 2.1 Start Schema Creation

Click **"Create from schema"** in your upload.

### 2.2 Name and Select Schema

Follow the naming convention:

```
username_####_Material_Quarter_Raman
```

Examples:

- `amazingresearcher_0042_Cu-Zn_BR_Raman` (back right quarter)
- `username_0123_BaZr_FL_Raman` (front left quarter)

**Select the schema:**

- Choose **"Raman Measurement"** from the Built-in schemas dropdown

Click **"Create"**.

## Step 3: Upload Raman Data

### 3.1 Locate the File Upload Field

Scroll down to find the **"Raman file"** field.

### 3.2 Upload Your .wdf File

1. Click the upload area or drag and drop your Renishaw .wdf file

2. **IMPORTANT: Click "Save"** immediately after the file uploads

!!! danger "Must Save!"
    Failing to save after uploading will result in data loss. Always click "Save" after file uploads.

!!! info "Processing Time"
    NOMAD processes the file and extracts:

    - Measurement positions (x, y coordinates)
    - Raman spectra at each point
    - Wavenumber ranges and intensities
    - Relationships to the combinatorial library geometry
    - Optical microscopy image if available in the file

## Step 4: Review Results

### 4.1 Navigate to Results Subsection

Scroll down to find the **"Results"** subsection and expand it.

### 4.2 Examine Auto-Generated Plots

NOMAD automatically generates visualizations showing:

- Raman spectra at different positions
- Peak intensities vs. position
- Spectral features across the measured area
- Individual data points overlaid on the sample geometry

All measurement points from your .wdf file are displayed in the graphs.

## Step 5: Configure Sample Alignment

To properly map your Raman measurements to the combinatorial library geometry, you need to define how your sample was positioned on the Raman stage.

### 5.1 Navigate to Sample Alignment

Scroll down to find the **"Sample Alignment"** subsection and expand it.

### 5.2 Enter Sample Dimensions

Define the physical size of the measured quarter:

1. **Sample width** - Enter the width of your sample quarter (typically in mm)

2. **Sample height** - Enter the height of your sample quarter (typically in mm)

!!! info "Typical Values"
    For a standard quarter:

    - Width: ~40 mm
    - Height: ~40 mm

### 5.3 Define Corner Positions

To align the Raman coordinate system with your sample, specify the positions of **two diagonal corners**:

1. **Top-left corner position**:
   - X coordinate: Enter the stage X position of the top-left corner
   - Y coordinate: Enter the stage Y position of the top-left corner

2. **Bottom-right corner position**:
   - X coordinate: Enter the stage X position of the bottom-right corner
   - Y coordinate: Enter the stage Y position of the bottom-right corner

!!! tip "Finding Corner Positions"
    - In most Raman measurements, the stage origin (X = 0, Y = 0) is set at the bottom-left corner of the sample.
    - For a well-aligned sample, the top-left X coordinate and the bottom-right Y coordinate are both close to 0.
    - The top-left Y coordinate should be approximately equal to the sample height, and the bottom-right X coordinate should be approximately equal to the sample width.
### 5.4 Save the Alignment

**Click "Save"** after entering all alignment parameters.

!!! warning "Critical for Accurate Mapping"
    The sample alignment information is essential for:

    - Correctly overlaying Raman data on the library geometry
    - Correlating measurements with composition gradients
    - Combining data from multiple characterization techniques

### 5.5 Verify Alignment

After saving, check that:

- Sample dimensions match your physical quarter
- Corner coordinates form a diagonal across the sample
- The coordinate system matches your Raman stage orientation

## Step 6: Clean Invalid Data Points

During Raman mapping, you might accidentally measure:

- Areas with no film (bare substrate)
- Wrong sample regions
- Points with poor signal quality
- Edge effects or contamination

These invalid points should be removed.

### 6.1 Identify Bad Points

Review the plots and identify suspicious data:

- Spectra with very low signal-to-noise
- Points in regions you didn't deposit
- Outliers inconsistent with neighboring points
- Substrate-only signals

### 6.2 Delete Invalid Points

1. Locate the data point in the list (usually shown with coordinates)

2. Click the **trash can icon** next to the invalid point

3. **Click "Save"** after each deletion

!!! warning "Save After Each Deletion"
    Changes aren't final until you save. Always click "Save" after removing points.

### 6.3 Re-check Plots

After removing invalid points, scroll back to the Results section to verify:

- Plots show cleaner spectral trends
- Outliers are removed
- Data makes physical sense

## Step 7: Repeat for Additional Quarters

If you measured multiple quarters of your combinatorial library, repeat this entire process for each quarter:

1. Create a new Raman Measurement entry with the appropriate quarter name:
   - `username_####_Material_BR_Raman`
   - `username_####_Material_BL_Raman`
   - `username_####_Material_FL_Raman`
   - `username_####_Material_FR_Raman`

2. Upload the corresponding .wdf file

3. Review and clean data points

!!! tip "Mapping Strategy"
    Quarters are commonly measured individually. This allows:

    - Dedicating quarters to different techniques
    - Focusing Raman on interesting structural regions
    - Parallel processing of characterization

## Verification Checklist

After uploading Raman data, verify:

- [ ] Entry named correctly with quarter identifier
- [ ] .wdf file uploaded successfully
- [ ] Results subsection shows plots
- [ ] Data points appear in expected positions
- [ ] Invalid points removed
- [ ] Final save completed
- [ ] Spectral features look reasonable

## Troubleshooting

### No plots appear in Results section

**Problem**: Results subsection is empty or shows errors

**Solutions**:

- Check .wdf file format - ensure it's from Renishaw WiRE software
- Verify file uploaded successfully (no error messages)
- Refresh the page and check again
- Confirm you clicked "Save" after upload

### Can't delete data points

**Problem**: Trash icon missing or not working

**Solutions**:

- Make sure you're in edit mode (not just viewing)
- Try refreshing the page
- Check you have write permissions on the upload
- Verify the entry isn't locked or published

### Wrong data appears in plots

**Problem**: Plots show unexpected spectra or positions

**Solutions**:

- Verify you uploaded the correct .wdf file
- Check if the file corresponds to the correct quarter
- Ensure file wasn't corrupted during transfer
- Confirm measurement positions match library geometry

### .wdf file won't upload

**Problem**: File rejected or error during upload

**Solutions**:

- Verify file is in Renishaw .wdf format
- Check file size isn't too large (typically <50 MB)
- Ensure file isn't corrupted
- Try opening in WiRE software to verify integrity
- Re-export from your Raman analysis software

## Understanding Raman Data

### What does Raman measure?

Raman spectroscopy provides:

- **Vibrational modes** characteristic of molecular bonds and crystal structures
- **Phase identification** - crystalline vs. amorphous, different polymorphs
- **Stress and strain** information from peak shifts
- **Spatial distribution** of structural features across your sample

### Measurement considerations:

- **Laser wavelength**: Different wavelengths probe different depths
- **Spatial resolution**: Typically ~1 micron lateral resolution (diffraction limited)
- **Sample sensitivity**: Some materials may degrade under laser exposure
- **Fluorescence interference**: Can mask Raman signal

### Data interpretation:

The visualizations help you:

- Identify structural phases across your library
- Locate regions with specific vibrational signatures
- Track structural gradients and phase boundaries
- Correlate structure with composition

## Next Steps

After adding Raman measurements:

1. **[Add EDX Measurements](add-edx-measurements.md)** - Add composition data
2. **[Add XRD Measurements](add-xrd-measurements.md)** - Add structural characterization
3. **[Add Other Characterization](../reference/index.md)** - XPS, PL, Ellipsometry, etc.

## Related Resources

- [Upload Sputtering Data](upload-sputtering-data.md) - Create the parent combinatorial library
- [Raman Reference](../reference/raman.md) - Detailed schema documentation
- [Tutorial](../tutorial/tutorial.md) - Complete workflow example
- [Combinatorial Libraries](../explanation/combinatorial-libraries.md) - Understanding the data model

## Need Help?

If you encounter issues:

- Ask colleagues who have successfully uploaded Raman data
- Review example uploads in your group
- Check the [Reference Documentation](../reference/raman.md)
- Contact DTU Nanolab NOMAD support
