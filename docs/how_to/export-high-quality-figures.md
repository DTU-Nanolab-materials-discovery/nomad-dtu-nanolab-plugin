# Export High-Quality Figures from Python

This guide shows you how to export publication-quality figures from Python using Plotly, ensuring your plots are crisp and professional for papers, presentations, and posters.

## Overview

Default Plotly exports are often too low-resolution for publications. This guide explains how to configure high-quality exports for:

- **PNG format** - Raster images for presentations and web
- **SVG format** - Vector graphics for publications and posters

## The Problem

When you click the camera icon in a Plotly figure, the default export:

- Uses low resolution (often 72-96 DPI)
- May appear pixelated when printed
- Doesn't meet journal requirements (typically 300+ DPI)

## The Solution

Configure Plotly's export settings before displaying your figure.

## Quick Start

Here's the complete code to enable high-quality exports:

```python
# Define the Plotly configuration
PLOTLY_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',  # Export format: 'png' or 'svg'
        'scale': 10,      # Scale factor (multiplies default resolution)
    }
}

# Show your figure with the configuration
fig.show(config=PLOTLY_CONFIG)
```

After running this, the camera icon in the Plotly figure will export high-quality images!

## Step-by-Step Instructions

### Step 1: Import Required Libraries

Make sure you have Plotly installed:

```python
import plotly.graph_objects as go
import plotly.express as px
```

### Step 2: Create Your Figure

Create your plot as usual:

```python
# Example figure
fig = go.Figure(data=go.Scatter(
    x=[1, 2, 3, 4],
    y=[10, 11, 12, 13]
))

fig.update_layout(
    title="My High-Quality Plot",
    xaxis_title="X Axis",
    yaxis_title="Y Axis"
)
```

### Step 3: Define Export Configuration

**For PNG (Raster) Export:**

```python
PLOTLY_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',    # PNG format
        'scale': 10,        # 10x resolution (very high quality)
    }
}
```

**For SVG (Vector) Export:**

```python
PLOTLY_CONFIG = {
    'toImageButtonOptions': {
        'format': 'svg',    # SVG format (scalable vector)
        'scale': 1,         # Scale factor (less important for vectors)
    }
}
```

### Step 4: Display with Configuration

Instead of:

```python
fig.show()  # Default low quality
```

Use:

```python
fig.show(config=PLOTLY_CONFIG)  # High quality!
```

### Step 5: Export theimage

1. The Plotly figure appears in your Jupyter notebook
2. **Hover over the figure** - controls appear in the top-right corner
3. **Click the camera icon** (📷)
4. The high-quality image downloads to your browser's download folder

## Configuration Options

### Format Selection

**PNG** - Raster format:

- ✅ Good for presentations and posters
- ✅ Smaller file sizes with high scale factors
- ✅ Widely compatible
- ❌ Can pixelate when zoomed
- ❌ Fixed resolution

**SVG** - Vector format:

- ✅ Perfect for publications
- ✅ Scales infinitely without quality loss
- ✅ Editable in Illustrator/Inkscape
- ❌ Larger file sizes for complex plots
- ❌ May have font rendering issues in some viewers

### Scale Factors

The `scale` parameter multiplies the default resolution:

| Scale | Output Quality | Use Case |
|-------|----------------|----------|
| 1 | ~96 DPI | Screen viewing only |
| 2 | ~192 DPI | Web graphics |
| 5 | ~480 DPI | Presentations |
| **10** | **~960 DPI** | **Publications, posters** |

!!! tip "Recommended: scale=10"
    For publication quality, use `scale=10` with PNG format. This ensures crisp prints even on large posters.

### Additional Options

You can add more configuration options:

```python
PLOTLY_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',
        'scale': 10,
        'width': 1920,    # Set explicit width (pixels)
        'height': 1080,   # Set explicit height (pixels)
        'filename': 'my_figure',  # Default filename
    },
    'displayModeBar': True,      # Always show toolbar
    'displaylogo': False,        # Hide Plotly logo
}
```

## Creating a Reusable Configuration

For consistency across all your figures, define configurations once:

```python
# At the top of your notebook
PNG_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',
        'scale': 10,
    }
}

SVG_CONFIG = {
    'toImageButtonOptions': {
        'format': 'svg',
        'scale': 1,
    }
}

# Use throughout your notebook
fig1.show(config=PNG_CONFIG)
fig2.show(config=SVG_CONFIG)
fig3.show(config=PNG_CONFIG)
```

## Best Practices

### For Publications

```python
# Vector graphics, editable
PUBLICATION_CONFIG = {
    'toImageButtonOptions': {
        'format': 'svg',
        'scale': 1,
    },
    'displaylogo': False,
}

fig.show(config=PUBLICATION_CONFIG)
```

Then:

1. Export as SVG
2. Open in vector graphics editor (Illustrator, Inkscape)
3. Adjust fonts, colors, labels as needed
4. Export final version per journal requirements

### For Presentations

```python
# High-resolution raster
PRESENTATION_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',
        'scale': 5,  # Balance quality vs file size
        'width': 1920,
        'height': 1080,
    }
}

fig.show(config=PRESENTATION_CONFIG)
```

### For Posters

```python
# Very high resolution for large prints
POSTER_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',
        'scale': 10,  # Maximum quality
    }
}

fig.show(config=POSTER_CONFIG)
```

## Troubleshooting

### Export still looks low quality

**Problem**: Image appears pixelated despite configuration

**Solutions**:

- Verify you used `fig.show(config=PLOTLY_CONFIG)` not just `fig.show()`
- Check the scale factor (`scale=10` for high quality)
- Try increasing the scale factor further
- For vectors, use SVG instead of PNG

### Export is too large

**Problem**: File size is very large

**Solutions**:

- For PNG: Reduce scale factor (try `scale=5`)
- For SVG: Simplify your plot (fewer data points)
- Consider PNG for complex plots with many points
- Use subsampling for scatter plots with thousands of points

### Camera icon doesn't appear

**Problem**: Can't find the export button

**Solutions**:

- Hover over the plot to reveal toolbar
- Add `'displayModeBar': True` to configuration
- Try `'modeBarButtonsToAdd': ['toImage']` in config
- Verify Plotly is properly installed and up to date

### SVG renders incorrectly

**Problem**: SVG file has missing elements or wrong fonts

**Solutions**:

- Try PNG export instead
- Update Plotly to latest version
- Simplify plot (remove problematic elements)
- Export PNG at high scale, then vectorize externally

### Export filename is generic

**Problem**: All exports named "newplot.png"

**Solutions**:

Add filename to configuration:

```python
PLOTLY_CONFIG = {
    'toImageButtonOptions': {
        'format': 'png',
        'scale': 10,
        'filename': 'figure_1_composition_map',
    }
}
```

## Alternative: Programmatic Export

For batch processing or automation, export programmatically:

### Install Required Package

```bash
pip install kaleido
```

### Export from Code

```python
# PNG export
fig.write_image("figure.png", scale=10)

# SVG export
fig.write_image("figure.svg")

# With size specification
fig.write_image("figure.png", width=1920, height=1080, scale=10)
```

This bypasses the GUI and generates files directly.

## Related Resources

- [Plot Combinatorial EDX Data](plot-combinatorial-edx.md) - Creating the figures to export
- [Jupyter Analysis Reference](../reference/analysis.md) - Advanced visualization techniques
- [Plotly Documentation](https://plotly.com/python/) - Official Plotly guides

## Need Help?

If you encounter export issues:

- Check Plotly version: `pip show plotly`
- Update Plotly: `pip install --upgrade plotly`
- Try programmatic export as alternative
- Ask colleagues for working configuration examples
- Consult Plotly community forums
