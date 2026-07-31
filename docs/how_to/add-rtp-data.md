# Add RTP Data

This guide explains how to add Rapid Thermal Processing (RTP) data to NOMAD Oasis. RTP is used for thermal annealing, crystallization, or other heat treatments of your samples.

## Overview

RTP entries document:

- Thermal processing steps (heating, annealing, cooling)
- Temperature profiles and ramp rates
- Atmosphere and gas flows
- Input samples and their positions
- Links to processed combinatorial libraries

## Prerequisites

Before starting, you need:

- **RTP logfiles** from the RTP system
- **Completed sputtering upload** or **cleaved libraries** that were processed
- **Process details**:
  - Number of thermal steps
  - Temperature profiles
  - Gas atmospheres
  - Sample positions
  - Material systems

## Step 1: Create RTP Upload

### 1.1 Create New Upload

1. Click **"New Upload"** in NOMAD Oasis

2. **Name the upload** following your lab's RTP naming convention:
   ```
   username_####_RTP
   ```
   Example: `amazingresearcher_0042_RTP`

3. **Share with group**:
   - Click "Edit upload members"
   - Add "Thin-Film Materials Discovery" as co-author
   - Add other collaborators as needed

4. Click **"Save"**

## Step 2: Create RTP Entry

### 2.1 Start Schema Creation

In your RTP upload, click **"Create from schema"**.

### 2.2 Name and Select Schema

**Entry name**: Use the same naming as the upload
```
username_####_RTP
```

**Schema selection**: Choose **"RTP"** or **"Rapid Thermal Processing"** from built-in schemas

Click **"Create"**.

## Step 3: Upload Logfiles

If your RTP system generates logfiles:

1. **Drag and drop** the logfiles into the designated field

2. NOMAD will parse:
   - Temperature vs. time profiles
   - Gas flows
   - Pressure history
   - Ramp rates

3. **Click "Save"** after upload

!!! tip "Logfile Support"
    Check with your group which logfile formats are supported by the parser. Manual entry is also possible.

## Step 4: Fill in Overview Information

### 4.1 Basic Process Data

Fill in the main entry fields:

- **Process name/description** - Brief summary of the RTP purpose
- **Date and time** - When the process occurred
- **Operator** - Who performed the RTP

### 4.2 Material Space

Press the arrow next to **"Overview"** subsection to expand.

Fill in the **"Material space:**

- Enter the target materials used in deposition with hyphens between them
- Example: `Ba-Zr` for barium-zirconium system
- Example: `Cu-Zn-Sn-S` for quaternary system

This helps identify what materials were processed.

!!! info "Why Material Space?"
    Material space enables searching across related processes (sputtering + RTP) for the same material system.

## Step 5: Add Thermal Steps

RTP processes typically consist of multiple thermal steps (heating, hold, cooling).

### 5.1 Determine Number of Steps

Count your thermal steps. Common sequences:

- **3 steps**: Heat → Anneal → Cool
- **2 steps**: Heat/Anneal → Cool
- **5+ steps**: Multi-stage annealing with plateaus

### 5.2 Create Step Entries

1. Click the **"+" icon** next to "Steps"

2. Add one step entry for each thermal stage

3. For each step:
   - Give it a **descriptive name** (e.g., "Heating", "Annealing", "Cooling")
   - Click to open the **step overview**

### 5.3 Fill Step Details

For each step, expand the overview and fill in:

- **Temperature** - Target or maximum temperature (with units)
- **Duration** - How long at this temperature
- **Ramp rate** - Rate of temperature change (K/min or °C/min)
- **Gas atmosphere** - N₂, O₂, forming gas, vacuum, etc.
- **Gas flow rate** - If applicable
- **Pressure** - Chamber pressure during step

Example:

**Step 1: Heating**

- Temperature: 600 °C
- Duration: 10 min
- Ramp rate: 30 °C/min
- Atmosphere: N₂

**Step 2: Annealing**

- Temperature: 600 °C
- Duration: 60 min
- Ramp rate: 0 °C/min (isothermal)
- Atmosphere: N₂

**Step 3: Cooling**

- Temperature: 25 °C
- Duration: 20 min
- Ramp rate: -30 °C/min
- Atmosphere: N₂

## Step 6: Add Input Samples

Link the combinatorial libraries or samples that underwent RTP.

### 6.1 Determine Number of Input Samples

Count how many separate samples were processed in this RTP run.

### 6.2 Create Sample Entries

1. Click the **"+" icon** next to "Input samples"

2. Add one entry for each sample

### 6.3 Link Each Sample

For each input sample:

1. Give it a **name** - Use the cleaved material library name
   - Example: `amazingresearcher_0042_CuZn_BL`

2. **Choose from the list** - Select the existing combinatorial library from your sputtering upload
   - Use filters to find it quickly

3. Choose the **relative position** in the RTP chamber if applicable:
   - Center, edge, specific location
   - This helps track position-dependent effects

!!! warning "Important"
    Do NOT click "Save" until you've filled in ALL step data and ALL samples! Partial saves may cause validation errors.

## Step 7: Save Everything

Once completed:

- ✓ Overview information filled
- ✓ Material space specified
- ✓ All thermal steps added and configured
- ✓ All input samples linked

**Click the "Save" button** at the top of the page.

!!! danger "Save Only When Complete"
    The RTP schema validates relationships between steps and samples. Save only after everything is filled to avoid errors.

## Verification Checklist

After saving, verify:

- [ ] RTP entry created successfully (no error messages)
- [ ] All thermal steps are present and named
- [ ] Temperature profiles are correct
- [ ] Input samples link to correct combinatorial libraries
- [ ] Material space matches your system
- [ ] Logfiles uploaded (if applicable)

## Troubleshooting

### Can't save - validation error

**Problem**: Error message appears when trying to save

**Solutions**:

- Check that all required fields are filled
- Ensure all thermal steps have temperature and duration
- Verify input samples are properly linked (not just named)
- Make sure material space is specified
- Try filling in any empty fields marked with red indicators

### Can't find input sample in list

**Problem**: Expected combinatorial library doesn't appear in selector

**Solutions**:

- Verify the library exists in a sputtering upload
- Check if you have access permissions to that upload
- Ensure the library is from a shared upload
- Search by typing the exact library name
- Ask colleagues if library exists under different name

### Wrong sample linked

**Problem**: Linked incorrect combinatorial library

**Solutions**:

- If not saved yet: simply reselect the correct library
- If already saved: edit the RTP entry and change the link
- Verify the library name matches your physical sample

### Multiple samples from same library

**Problem**: Processed multiple quarters from the same parent library

**Solutions**:

- Add separate input sample entries for each cleaved piece
- Select the specific child library for each (e.g., `_Q1`, `_Q2`)
- Document positions if they matter for the RTP process

### Thermal steps in wrong order

**Problem**: Created steps but they're not in chronological order

**Solutions**:

- Most schemas maintain the order you created them
- Use step numbering in names (1-Heating, 2-Annealing, 3-Cooling)
- Check if the schema allows reordering
- Delete and recreate if necessary (before linking measurements)

## Understanding RTP Data

### Why document RTP?

RTP significantly affects:

- **Crystal structure** - Phase transitions, grain growth
- **Optical properties** - Bandgap, absorption
- **Electrical properties** - Conductivity, mobility
- **Compositional homogeneity** - Interdiffusion, segregation

Documenting RTP enables:

- Reproducing successful processes
- Correlating thermal history with properties
- Searching for samples with similarthermal treatment
- Understanding structure-property relationships

### Best practices:

- **Complete documentation**: Record all steps, even brief ones
- **Consistent naming**: Use systematic step names across RTPs
- **Atmosphere details**: Gas type and flow impact results
- **Position tracking**: Note sample positions if non-uniform heating
- **Link thoroughly**: Connect to both parent deposition and subsequent characterization

## Next Steps

After adding RTP data:

1. Characterize the processed samples:
   - [Add XRD Measurements](add-xrd-measurements.md) - Check for structural changes
   - [Add EDX Measurements](add-edx-measurements.md) - Verify composition stability
   - Other characterization as appropriate

2. Compare pre- and post-RTP properties

3. Use Jupyter Analysis to correlate thermal treatment with outcomes

## Related Resources

- [Upload Sputtering Data](upload-sputtering-data.md) - Create input libraries
- [Cleave Libraries](cleave-libraries.md) - Prepare samples for RTP
- [RTP Reference](../reference/rtp.md) - Detailed schema documentation
- [Materials Discovery Workflow](../explanation/workflow.md) - RTP in context

## Need Help?

If you encounter issues:

- Ask colleagues experienced with RTP documentation
- Review existing RTP uploads for examples
- Check the [Reference Documentation](../reference/rtp.md)
- Contact DTU Nanolab NOMAD support
