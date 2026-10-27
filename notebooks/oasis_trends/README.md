# Oasis trend analyses

These notebooks explore trends in records visible to the authenticated NOMAD
account. They are read-only: they query metadata and retrieve selected archives,
but do not save analysis results back to NOMAD.

## Access and scope

Never paste the token into a notebook or chat, print it, or commit it.
`owner: "visible"` respects the account's NOMAD permissions; it does not grant
access to private records belonging to other users. Ask an Oasis administrator
for the appropriate read permissions if cross-user records should be included.

The API URL is configurable through `NOMAD_BASE_URL`. Use the HTTPS URL
configured for your Oasis.

### Windows setup

From PowerShell in the repository root, run:

```powershell
python .\notebooks\oasis_trends\setup_nomad_token.py
```

The script opens the Oasis sign-in page. Sign in in your browser, then create or
copy an API access token from your NOMAD account settings. Back in the terminal,
paste the token when prompted; input is hidden. The script does **not** ask for
your password or automate the login. It encrypts the token using Windows DPAPI
for the current Windows account, outside the repository, at
`%LOCALAPPDATA%\NOMAD\oasis-token.dpapi`. It never prints the token.

Run Jupyter under the same Windows account and restart its kernel after setup.
The notebooks first look for `NOMAD_CLIENT_ACCESS_TOKEN` in the environment and
then read the encrypted DPAPI store on Windows. If the token needs to be rotated,
rerun the setup script; it replaces the saved token. To revoke a token, use the
NOMAD account settings where it was created and delete the local encrypted file.
The local file is encrypted, but the token is available in process memory while
requests are being made.

On non-Windows notebook runtimes, supply `NOMAD_CLIENT_ACCESS_TOKEN` through
that runtime's secret/environment-variable mechanism; the Windows DPAPI helper
does not apply.

## Staged plan

1. **Confirm access and data coverage.** Run a small paginated metadata search
   for the required entry types. Record counts and missing fields before fetching
   any full archives.
2. **Map the relationships.** Check how sputtering runs, substrate/sample
   libraries, EDX measurements, and target records reference one another. Keep
   unresolved joins visible rather than guessing.
3. **Explore the active questions.**
   - Exp 1: compare measured spatially averaged composition with sputtering
     target DC bias.
   - Exp 2: explore oxygen content against target material, base pressure, and
     available preceding-run context.
   - Base pressure: explore recorded chamber and process factors associated with
     sputtering base pressure.
   - Exp 7: test whether Ba-target DC bias varies with recorded target usage.
4. **Interpret and refine.** Check sample counts, missingness, confounders,
   process-history coverage, and sensitivity to aggregation choices before
   drawing conclusions.

Exp 3, 4, 5, and 6 are intentionally out of scope for now.

## Notebooks

- `exp1_exp2_composition_vs_sputtering.ipynb`
- `base_pressure_and_ba_target_bias.ipynb`

The query scopes and archive-fetch limits in each notebook are configurable.
The current defaults cover the visible metadata counts observed during setup;
the diagnostics report fetched counts, and NOMAD visibility depends on the
authenticated account. The composition notebook parses EDX archives in small
batches and fetches linked library archives only to reduce memory use. Results
are exploratory associations, not causal evidence. In particular, target age
or run order is not a direct measurement of erosion.

The notebook runtime needs Jupyter, `requests`, `pandas`, `numpy`, and `plotly`.
Charts are interactive Plotly figures.
