from nomad.datamodel.data import Schema
from nomad.metainfo.metainfo import Package, Section
from nomad_material_processing.vapor_deposition.pvd.thermal import ThermalEvaporation

from nomad_dtu_nanolab_plugin.categories import DTUNanolabCategory

m_package = Package()


class DtuThermalEvaporation(ThermalEvaporation, Schema):
    m_def = Section(
        categories=[DTUNanolabCategory],
        label='Bell Jar Evaporator',
    )


m_package.__init_metainfo__()
