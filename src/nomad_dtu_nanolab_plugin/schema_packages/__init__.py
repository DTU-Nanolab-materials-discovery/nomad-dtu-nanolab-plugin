import importlib

from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class BasesectionsEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.basesections import m_package

        return m_package


basesections_entry_point = BasesectionsEntryPoint(
    name='Basesections',
    description='Schema package defined for base sections.',
)


class SputteringEntryPoint(SchemaPackageEntryPoint):
    overwrite_libraries: bool = Field(
        False,
        description='Whether to overwrite existing libraries with the same name.',
    )
    overwrite_layers: bool = Field(
        False,
        description='Whether to overwrite existing layers with the same name.',
    )

    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.sputtering import m_package

        return m_package


sputtering_entry_point = SputteringEntryPoint(
    name='Sputtering',
    description='Schema package defined for sputtering.',
)


class RTPEntryPoint(SchemaPackageEntryPoint):
    overwrite_libraries: bool = Field(
        False,
        description='Whether to overwrite existing libraries with the same name.',
    )
    overwrite_layers: bool = Field(
        False,
        description='Whether to overwrite existing layers with the same name.',
    )

    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.rtp import m_package

        return m_package


rtp_entry_point = RTPEntryPoint(
    name='RTP',
    description='Schema package defined for RTP.',
)


class ThermalEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.thermal import m_package

        return m_package


thermal_entry_point = ThermalEntryPoint(
    name='Thermal',
    description='Schema package defined for thermal evaporation.',
)


class GasEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.gas import m_package

        return m_package


gas_entry_point = GasEntryPoint(
    name='Gas',
    description='Schema package defined for gas.',
)


class TargetEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.target import m_package

        return m_package


target_entry_point = TargetEntryPoint(
    name='Targets',
    description='Schema package defined for targets.',
)


class SubstrateEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.substrate import m_package

        return m_package


substrate_entry_point = SubstrateEntryPoint(
    name='Substrate',
    description='Schema package defined for substrate.',
)


class InstrumentEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.instrument import m_package

        return m_package


instrument_entry_point = InstrumentEntryPoint(
    name='Instrument',
    description='Schema package defined for instrument.',
)


class EDXEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.edx import m_package

        return m_package


edx_entry_point = EDXEntryPoint(
    name='EDX',
    description='Schema package defined for EDX measurements.',
)


class XRDEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.xrd import m_package

        return m_package


xrd_entry_point = XRDEntryPoint(
    name='XRD',
    description='Schema package defined for XRD measurements.',
)


class XPSEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.xps import m_package

        return m_package


xps_entry_point = XPSEntryPoint(
    name='XPS',
    description='Schema package defined for XPS measurements.',
)


class PLEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.PL import m_package

        return m_package


pl_entry_point = PLEntryPoint(
    name='PL',
    description='Schema package defined for PL measurements.',
)


class EllipsometryEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.ellipsometry import m_package

        return m_package


ellipsometry_entry_point = EllipsometryEntryPoint(
    name='Ellipsometry',
    description='Schema package defined for Ellipsometry measurements.',
)


class RTEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.rt import m_package

        return m_package


rt_entry_point = RTEntryPoint(
    name='RT',
    description='Schema package defined for RT measurements.',
)


class RamanEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.raman import m_package

        return m_package


raman_entry_point = RamanEntryPoint(
    name='Raman',
    description='Schema package defined for Raman measurements.',
)


class SampleEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.sample import m_package

        return m_package


sample_entry_point = SampleEntryPoint(
    name='Sample',
    description='Schema package defined for samples.',
)


class AnalysisEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.analysis import m_package

        return m_package


analysis_entry_point = AnalysisEntryPoint(
    name='Analysis',
    description='Schema package defined for analysis.',
)


# Register and expose the RT schema package eagerly so archives that reference
# nomad_dtu_nanolab_plugin.schema_packages.rt.DtuAutosamplerMeasurement can be resolved.
rt = importlib.import_module('nomad_dtu_nanolab_plugin.schema_packages.rt')
