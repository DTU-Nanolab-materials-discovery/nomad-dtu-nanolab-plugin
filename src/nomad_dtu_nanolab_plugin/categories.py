from nomad.datamodel.data import EntryDataCategory
from nomad.metainfo.metainfo import Category


class DTUNanolabCategory(EntryDataCategory):
    m_def = Category(
        label='DTU Nanolab materials discovery', categories=[EntryDataCategory]
    )
