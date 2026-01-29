# Cleave Combinatorial Libraries

This guide explains how to cleave (divide) your combinatorial libraries into smaller pieces in NOMAD Oasis, enabling you to track each piece's position and dedicate quarters to different characterization techniques.

## Overview

After sputtering deposition, you'll physically cleave your silicon substrates into smaller pieces (typically quarters). NOMAD's cleaving process creates "child libraries" that maintain their relationship to the parent library and original composition gradient.

## Why Cleave?

Different characterization techniques often require:

- **Dedicated samples** - Destructive or incompatible measurements
- **Different facilities** - Sending pieces to various instruments
- **Parallel processing** - Measuring multiple pieces simultaneously
- **Sample preservation** - Keeping pieces for archival or future analysis

Cleaving in NOMAD ensures:

- ✓ Child libraries know their position in the parent
- ✓ Composition coordinates transfer correctly
- ✓ Measurements link to the right part of the gradient
- ✓ Data remains traceable and reproducible

## Prerequisites

Before cleaving, you need:

- **Completed sputtering upload** with combinatorial libraries created
- **Decision on cleaving pattern** (typically "Four Quarters")
- **Knowledge of which library** to cleave (BL, BR, FL, FR position)

## Step 1: Access Your Upload

1. Navigate to your **sputtering upload** containing the combinatorial libraries

2. Click **"Create from schema"** to start a new entry

## Step 2: Create Cleaving Entry

### 2.1 Name Your Entry

Follow the naming convention:

```
username_####_Material(s)_Position_Breaking
```

Examples:

- `amazing_researcher_0042_CuZn_BL_Breaking`
- `username_0123_BaZr_FR_Breaking`

!!! tip"Naming Convention"
    "Breaking" is the standard suffix indicating this is a cleaving operation. Some groups also use "Cleaving".

### 2.2 Select Schema

From the dropdown menu, select **"Library Cleaving"** schema.

Click **"Create"**.

## Step 3: Select Parent Library

### 3.1 Choose the Combinatorial Library

In the cleaving entry, you'll see a field to select the parent library.

**Click the selector** and choose the specific combinatorial library you're cleaving:

Examples:

- `amazing_researcher_0042_CuZn_BL` (back left)
- `amazing_researcher_0042_CuZn_BR` (back right)
- etc.

!!! info "Finding Your Library"
    Use the "Only this upload" filter to show only libraries from your current sputtering upload.

### 3.2 Set Library Dimensions

Two options:

1. **Auto-fill**: Click **"Fetch library size"** to automatically retrieve dimensions from the parent library

2. **Manual entry**: Enter dimensions if the auto-fetch doesn't work:
   - Typical values: 50 mm × 50 mm for standard substrates
   - Units are usually in millimeters

## Step 4: Choose Cleaving Pattern

### 4.1 Select Pattern from Dropdown

Common patterns:

- **Four Quarters** (most common) - Divides into 2×2 pieces
- **Sixteen pieces** - Divides into 4×4 pieces
- **Custom patterns** - May be available for specific needs

Select **"Four Quarters"** for standard cleaving.

### 4.2 Confirm Piece Count

The interface shows how many pieces will be created (typically **4** for Four Quarters pattern).

Note this number - you'll verify it later.

## Step 5: Generate and Verify Pattern

### 5.1 Generate the Pattern

Click **"Generate pattern"** to create the cleaving visualization.

### 5.2 Review the Visual Pattern

A figure appears showing:

- The parent library outline
- Division lines indicating cleaving positions
- Labels for each resulting piece
- Relative positions of child libraries

![Cleaving pattern visualization](../assets/nomad-cleaving-manual.md)

**Verify the pattern**:

- ✓ Number of pieces matches expectation
- ✓ Division lines are where you'll physically cleave
- ✓ Piece orientations match your lab practice
- ✓ Labels are clear and unambiguous

!!! warning "Check Before Proceeding"
    Ensure the pattern matches your intended physical cleaving! Once child libraries are created, reorganizing them is complex.

## Step 6: Create Child Libraries

### 6.1 Generate Child Entries

Click **"Create child libraries"** to generate individual combinatorial library entries for each piece.

NOMAD will:

1. Create new library entries (one per piece)
2. Name them systematically (e.g., `_Q1`, `_Q2`, `_Q3`, `_Q4` suffixes)
3. Transfer composition gradient information
4. Link them to the parent library
5. Assign relative positions

### 6.2 View the Schematic

After creation, **scroll down** to see the schematic showing:

- All cleaved pieces laid out geometrically
- Position labels for each piece
- Parent-child relationships
- Composition gradient indicators

!!! success "Child Libraries Created"
    Each child library is now a separate entry that can be independently measured and analyzed!

## Step 7: Verify Child Libraries

### 7.1 Check Upload Entries

Navigate to your upload's entry list and verify:

- ✓ Parent library still exists
- ✓ Four child library entries created (or your expected number)
- ✓ Child libraries are named systematically
- ✓ Links between parent and children are established

### 7.2 Verify Nomenclature

Child libraries should be named:

```
ParentName_QuarterID
```

Examples:

- `amazing_researcher_0042_CuZn_BL_Q1`
- `amazing_researcher_0042_CuZn_BL_Q2`
- `amazing_researcher_0042_CuZn_BL_Q3`
- `amazing_researcher_0042_CuZn_BL_Q4`

## Understanding Positions

### Quarter Identifiers

After cleaving into quarters, pieces are typically labeled:

- **Q1** - Top-left quarter
- **Q2** - Top-right quarter
- **Q3** - Bottom-left quarter
- **Q4** - Bottom-right quarter

(Or your lab's specific convention - document this!)

### Relative Positions

Each child library knows its position relative to:

- The parent library coordinates
- The original sputtering targets
- The compositional gradient directions

This enables:

- Accurate composition assignment
- Gradient reconstruction from multiple measurements
- Cross-technique correlation

## Best Practices

### Physical vs. Digital Cleaving

!!! important "Synchronize Physical and Digital"
    **In the lab**: Use a diamond scribe and mark pieces clearly
    
    **In NOMAD**: Create child libraries matching your physical pieces
    
    **Label pieces**: Mark physical samples to match NOMAD nomenclature

### Timing

- **Before cleaving**: Create the cleaving entry and review the pattern
- **After cleaving**: Verify child libraries exist, then proceed with measurements
- **Document immediately**: Don't let unlabeled physical pieces and NOMAD diverge

### Organization

- Keep one cleaving entry per parent library
- Name children systematically for easy identification
- Document orientation if non-standard

## Troubleshooting

### Can't find parent library

**Problem**: Library doesn't appear in the selector

**Solutions**:

- Verify the library exists in your upload
- Check if you're in the correct upload
- Use "Only this upload" filter
- Ensure library was created by sputtering upload process

### Pattern doesn't generate

**Problem**: Clicking "Generate pattern" does nothing or shows errors

**Solutions**:

- Verify library dimensions are set
- Check that parent library is selected
- Try manually entering dimensions
- Refresh the page and try again

### Wrong number of child libraries created

**Problem**: Expected 4 pieces but got a different number

**Solutions**:

- Check which pattern was selected
- Verify the pattern actually generates expected piece count
- Contact admin if child libraries are missing
- May need to delete and recreate the cleaving entry

### Child libraries have wrong positions

**Problem**: Position labels don't match physical pieces

**Solutions**:

- Document the actual positions in free-text fields
- Create a mapping in your lab notebook
- Consider recreating the cleaving entry if caught early
- Contact NOMAD support for renaming assistance

### Can't delete cleaving entry

**Problem**: Want to redo cleaving but can't delete

**Solutions**:

- Check if child libraries are already being used in measurements (can't delete if referenced)
- May need to delete dependent measurements first
- Contact administrator for help with complex deletions

## After Cleaving

Once child libraries are created:

1. **Physically cleave** your substrates to match the pattern
2. **Label pieces** clearly with their child library names
3. **Store pieces** systematically (labeled containers)
4. **Proceed with measurements** on individual child libraries:
   - [Add EDX Measurements](add-edx-measurements.md)
   - [Add XRD Measurements](add-xrd-measurements.md)
   - Other characterization techniques

## Related Resources

- [Upload Sputtering Data](upload-sputtering-data.md) - Create parent libraries
- [Combinatorial Libraries](../explanation/combinatorial-libraries.md) - Understanding the data model
- [Library Cleaving Reference](../reference/cleaving.md) - Detailed schema documentation
- [Tutorial](../tutorial/tutorial.md) - Complete workflow example

## Need Help?

If you encounter issues:

- Ask colleagues who have cleaved libraries before
- Review successful cleaving examples in your group
- Check if your lab has specific cleaving conventions
- Contact DTU Nanolab NOMAD support
