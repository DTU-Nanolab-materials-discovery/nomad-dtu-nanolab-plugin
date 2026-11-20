---
name: nomad-ternary-composition-analysis
description: Build and interpret read-only NOMAD compositional ternary plots, including measured sample clouds, candidate phase markers, oxygen overlays, and clearly qualified geometric nearest-composition regions.
---

# NOMAD ternary composition analysis

Use this skill when creating or reviewing a NOMAD analysis that maps measured
compositions to ternary diagrams, compares samples with stoichiometric phases,
or explores composition-space neighborhoods.

## Data access

- Query NOMAD read-only with `owner: visible`. Use the repository's
  `notebooks/oasis_trends/oasis_helpers.py` and `oasis_auth.py` when available.
- Request only `lab_id`, `deposition.material_space`, and
  `elemental_composition` for combinatorial samples. Paginate, report server and
  fetched counts, and state that results reflect the token's permissions.
- Never execute notebooks or code downloaded from NOMAD. Do not write data back
  to the Oasis or commit downloaded archives/tokens.
- Keep extracted analysis data and exported figures out of the repository
  unless the user explicitly requests committed artifacts.

## Composition handling

- Normalize phase formula counts to atomic fractions and verify they sum to one.
- Inspect the original measured fraction sums before renormalizing. For
  correlations between elemental atomic fractions, test sensitivity to closure
  by comparing with a ratio to explicitly named matrix elements and by
  excluding implausible fraction sums. Treat that ratio as a sensitivity, not
  as proof of a substitution mechanism.
- Parse material-space labels conservatively; normalize element order
  deterministically (for example by electronegativity, then symbol).
- For a ternary projection, explicitly state whether samples must have an exact
  three-element material space or whether lower-dimensional subspaces are
  included on ternary edges.
- If projecting a composition with extra elements (such as oxygen) onto three
  axes, renormalize only the selected three elements and preserve excluded
  fractions separately for hover data or coloring. Never imply the ternary
  projection preserves the full composition.
- Treat absent measured elements explicitly. Do not silently interpret a
  missing oxygen value as zero; if missing desired-anion values are treated as
  below detection, disclose that assumption and report coverage.
- Keep records with uncertain source/provenance flagged. Sample-grid points
  from the same combinatorial library are spatially correlated and are not
  independent experimental replicates.

## Candidate phases and "basins"

- Candidate formula, stability source, and aimed/unplanned classification must
  be user-provided or independently cited. Label user-supplied values as
  unverified until their source is checked.
- A nearest-reference/Voronoi partition in composition coordinates is only a
  geometric similarity visualization. It is not a thermodynamic or kinetic
  basin, phase diagram, stability prediction, or evidence for a theory.
- If a system has only one reference formula, every sample is necessarily
  assigned to it; show formula distances but do not describe the result as a
  basin or comparative phase preference.
- Report the distance metric, selected axes, formula set, phase-to-sample
  coverage, and any cutoff. Do not force every sample into a phase category
  without showing its distance or an explicit rejection threshold.
- A hypothesis about anion deficiency should compare the measured anion atomic
  fraction with the explicit reference stoichiometry and analyze oxygen only
  where oxygen was reported. Require or explicitly qualify coverage of all
  formula elements; do not silently treat missing composition values as zero.
  Compare within each material system/phase first; pooled correlations across
  systems can be misleading.
- For claims tied to a named theory, ask for the specific prediction and map it
  to an observable before testing it.

## Plotly conventions

- Prefer `plotly.graph_objects.Scatterternary` for explicit ternary axes and
  overlaid reference phases. Use interactive figures and
  `PLOTLY_CONFIG = {'toImageButtonOptions': {'format': 'svg', 'scale': 1}}`.
- Frame ternary axes with `showline=True` and `linecolor='black'`; label all
  axes with element and atomic-percent units. Plotly ternary axes do not support
  the Cartesian-axis `mirror` property.
- Use distinct symbols/colors for measured samples and references. Hover should
  expose sample/lab ID, actual ternary coordinates, relevant excluded-element
  quantities, nearest-reference label, and distance.
- Mention that SVG/PNG export is available using the Plotly toolbar camera.
- In Jupyter, display figures inline. Outside Jupyter, save HTML outside the
  repository and provide its path.

## Validation and reporting

- Validate notebook JSON and parse every code cell before running.
- Test ternary normalization, boundary compositions, missing/zero compositions,
  binary-on-ternary-edge handling, and phase matching with synthetic data.
- For live Oasis runs, report visible totals, fetched counts, composition/O
  coverage, joins or omissions, and any runtime/authentication limitation.
- Separate observed patterns from interpretation and causal claims. State
  uncertainties and identify the specific user inputs still needed.
