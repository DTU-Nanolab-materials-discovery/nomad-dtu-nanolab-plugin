# Add Autosampler Reflection/Transmission Measurements

This guide explains how to upload Agilent UMA autosampler Reflection/Transmission (RT) experiments to NOMAD.

## Overview

The upload uses the `DtuAutosamplerMeasurement` schema, which parses autosampler files and creates `RTMeasurement` entries for each sample/library automatically.

This document follows the full high-throughput protocol: safety, optical setup, sample mounting, grid generation, method/profile setup, measurement run, data export, and NOMAD upload.

You need:

- A measured autosampler data export (`.csv`)
- The matching grid/config file (`*_grid.csv`)
- The native batch file (`.bsw`) from the run

## Important File Roles

The grid-generator notebook creates two CSV files:

- `*_grid.csv`: sample mapping/configuration file used by NOMAD parser
- `*_polar.csv`: instrument coordinate file used by the autosampler software

Only `*_grid.csv` is uploaded as the **config file** in `DtuAutosamplerMeasurement`.

The grid generator can be opened from a NOMAD Analysis template with the same name as the notebook filename stem (filename without extension).

Example:

- Notebook file: `Autosampler_GridGenerator_Analysis_Template_V1.ipynb`
- Template name to search/select: `Autosampler_GridGenerator_Analysis_Template_V1`

## Safety and Things Not To Do

- Never unplug or plug electronics while the instrument is ON.
- Never look into the beam or place eyes in the optical plane.
- Never manipulate optics/components without opening the base-tool lid (not UMA lid only).
- Avoid reflective jewelry near the optical path.
- Never touch optics without proper gloves.
- Never send the direct beam into the detector.
- Never drop any object that can hit the detector.
- Never run UMA Autosampler Scan app and Autosampler Setup app at the same time.

## Prerequisites

Before uploading, make sure:

- Your samples/libraries already exist in the upload (for linking)
- The autosampler run was executed with the `*_polar.csv` generated from the same grid
- You exported the measurement data to `.csv` from the Agilent software
- Data and config files belong to the same run
- The corresponding `.bsw` batch file was saved from that same run

## Step 0: Set Up Optics and Start Up Instrument

1. Open the lid behind the measurement chamber and verify optics state.
2. For standard high-throughput workflows, do not use the polarizer.
3. If polarizer state must be changed, do it only with instrument power OFF.
4. Set slits according to your validated lab setup (typical high-throughput set: 1 deg, 1 deg, 3 deg in V/V/H slots).
5. Power on instrument at least 30-60 min in advance for lamp stabilization.
6. Reboot sequence: power OFF for ~10 s, then ON again.
7. Wait until boot completes and mechanical movement/noise stops.

## Step 1: Mount Samples on Holder

1. Use the designated autosampler holder (for example, 6 glass-form + 6 square slots).
2. Open holder sandwich and place samples in the numbered slots.
3. Keep sample orientation consistent with slot direction labels.
4. Place samples face down with film toward the measurement side.
5. Reassemble holder and align screw holes/grooves before tightening.
6. Record which sample was mounted in each slot.

Consistent sample orientation is critical so grid coordinates map correctly to sample coordinates.

## Step 2: Generate Grid Files

Create the map from the grid-generator notebook/template:

1. Set `GRID_NAME` and sample/slot mapping.
2. Define `SAMPLES` either with holder templates (for standard holders) or explicit sample geometry tuples.
3. Keep `ADD_BASELINE_CENTER = True` when using holders with center access for baseline.
4. Set `MAX_RADIUS` to instrument limits (or leave default autosampler radius).
5. Generate outputs.
6. Keep both generated files:
   - `*_grid.csv` for NOMAD parsing
   - `*_polar.csv` for autosampler execution

If you run this through NOMAD Analysis, search for the template using the notebook filename without `.ipynb`.

Recommended run-folder convention: create a dated folder (for example `<user>_YYMMDD`) and store both grid files there.

## Step 3: Set Measurement Method in Cary WinUV

1. Open UMA Autosampler Scan software from the Cary WinUV folder and wait for full initialization.
2. Wait until software is idle before clicking setup (typical cues: green status light, setup no longer greyed out).
3. Load autosampler method (typically no polarizer variant), usually from `Data (D:)/Methods`.
4. In setup, adjust only intended run parameters:
   - Wavelength range (typical max range 250-2500 nm)
   - Measurement speed/step in UV-vis and IR ranges
   - Baseline mode (100% + 0% or 100% only, per protocol)
4. Keep validated optical-beam-shaping parameters unchanged unless explicitly needed:
   - SBW ratio
   - Double beam mode
   - Reduced beam height
5. Confirm setup, acknowledge baseline warning if shown (baseline not yet measured at this stage is expected).
6. Save method copy in the run folder.

## Step 4: Configure UMA Autosampler Setup Profile

1. Open UMA Autosampler Setup application.
2. Create a **new profile** immediately to avoid modifying old profiles.
3. Save profile into current run folder.
4. Click the profile edit button (gear icon).
5. In the Baseline settings, enable baseline on the first point.
6. In the Points tab, choose manual entry/import mode.
7. Click **Import from spreadsheet**.
8. Select the `*_polar.csv` file generated by the grid notebook.
   - The file should contain two columns only: `R` and `Theta`.
   - Keep the original order of rows from the grid generator.
9. Confirm import and verify that points are displayed in the blue autosampler reach circle.
   - The software view can appear rotated by ~180 degrees relative to physical holder orientation.
10. In the output/batch settings tab, set the batch output destination to the current run folder so the `.bsw` file is saved there.
11. Right-click the center point (baseline point) and set it as the reference point.
12. Click the point-test/move icon (P button) and verify movement by clicking several points.
13. Specifically test the farthest points near the map boundary before running the sequence.

If points are unreachable or motors stall near edges, regenerate grid with tighter radius/margins.

## Step 5: Mount Holder on Autosampler

1. Turn on autosampler control unit.
2. Initialize motor from setup software and wait for all motion to end.
   - The software may report completion before motion stops; wait for full stop before continuing.
3. Use load/unload position.
4. Align holder notch with autosampler alignment pin.
5. Seat holder gently and tighten thumbscrews without over-torquing.
6. Close Autosampler Setup app before starting scan sequence.

## Step 6: Run Measurement Sequence

1. Ensure Autosampler Setup app is closed.
2. In Scan software, open autosampler pop-up and verify map.
   - If map is not loaded, browse and load the generated map for this run.
3. Set output folder to same run folder.
4. Run baseline sequence (including 0% baseline step if enabled).
   - For 0% baseline prompt, place an opaque blocker in front of detector, then continue.
5. Start measurement run.

## Step 7: Export Data from Agilent Software

1. Keep raw data intact; only clean graph display (do not delete measurement data records).
2. Remove graph views as needed and create a fresh graph view for export.
3. In trace preferences, show all traces (Select All -> Display).
4. Hide baseline traces (100% and 0%) and keep collect traces (for example Collect1/Collect2).
5. Save exported data as `.csv` into run folder.
6. Keep run folder complete with:
   - `*_grid.csv`
   - `*_polar.csv`
   - exported measurement `.csv`
   - autosampler profile/method files
   - `.bsw` batch file

## Critical Operational Notes

- Do not keep UMA Autosampler Setup and Autosampler Scan App open at the same time.
- Always initialize motors and verify edge points are reachable before starting the sequence.
- Keep a dedicated run folder containing method/profile, `*_grid.csv`, `*_polar.csv`, exported data `.csv`, and `.bsw`.

## Step 8: Prepare Files for NOMAD Upload

From your autosampler experiment folder, collect:

1. Data export CSV from Agilent software (contains spectra + metadata)
2. Grid CSV generated by notebook (`*_grid.csv`)
3. Raw `.bsw` batch file

Keep all files together and use a consistent run name/date.

When exporting data from Agilent software, export only the measurement traces (typically Collect traces) and exclude baseline traces from the final CSV export.

## Step 9: Create Autosampler Entry in NOMAD

1. Open the target upload in NOMAD Oasis
2. Click **Create from schema**
3. Select **Autosampler Measurement** (`DtuAutosamplerMeasurement`)
4. Create the entry

Suggested naming pattern:

`<username>_<date>_<project>_autosampler`

Example:

`eugbe_20260317_oxide_screen_autosampler`

## Step 10: Upload the Required Files

In the created entry:

1. Upload **Data file** with the measurement `.csv`
2. Upload **Config/Grid file** with `*_grid.csv`
3. Upload **Raw instrument batch file** with `.bsw`
4. Click **Save**

After save/normalization, NOMAD parses the autosampler data and creates per-sample RT measurement archives.

## Step 11: Verify Generated RT Measurements

Open the generated `RTMeasurement` entries and confirm:

- Expected sample/library names are present
- Position-resolved spectra are present (R/T traces)
- Coordinates look correct for mapped positions
- Plot section contains spectra and map visualizations

## Step 12: Common Checks if Parsing Looks Wrong

If results are missing or mismatched:

- Confirm you uploaded `*_grid.csv` (not `*_polar.csv`) as config
- Confirm data CSV and grid CSV are from the same run
- Confirm `.bsw` is from the same run and uploaded in the raw file field
- Check sample names in grid file match your expected naming
- Ensure data export includes all required metadata columns

## Minimal Checklist

- [ ] Entry type is `DtuAutosamplerMeasurement`
- [ ] Data `.csv` uploaded
- [ ] Config `*_grid.csv` uploaded
- [ ] `.bsw` uploaded
- [ ] Entry saved and normalized
- [ ] Generated `RTMeasurement` entries verified

## Related Documentation

- [RT Reference](../reference/rt.md)
- [Schema Reference Overview](../reference/index.md)
- [Characterization Techniques](../explanation/characterization.md)
