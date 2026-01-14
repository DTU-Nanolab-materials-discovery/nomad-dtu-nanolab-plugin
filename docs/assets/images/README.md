# Documentation Assets

This directory contains images and media files for the DTU Nanolab plugin documentation.

## Screenshots Needed

Please add the following screenshots manually:

1. **jupyter-analysis-eln-form.png**
   - Screenshot of the ELN form showing:
     - `name` field
     - `template` reference field
     - `libraries` repeating reference field
     - `generate_notebook` checkbox
   - Should show the form interface users interact with to create analysis entries

2. **jupyter-analysis-api-query-cell.png**
   - Screenshot of the generated API query code cell showing:
     ```python
     from nomad.client import ArchiveQuery
     from nomad.config import client
     
     analysis_id = "THE_ANALYSIS_ID"
     a_query = ArchiveQuery(
         query={'entry_id:any': [analysis_id]},
         required='*',
         url=client.url,
     )
     entry_list = a_query.download()
     analysis = entry_list[0].data
     ```
   - Should clearly show this is a Jupyter notebook cell

Once these screenshots are added, the documentation will render correctly with all visual aids.
