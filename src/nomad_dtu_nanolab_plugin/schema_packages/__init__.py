from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class BasesectionsEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.basesections import m_package

        return m_package


basesections = BasesectionsEntryPoint(
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


sputtering = SputteringEntryPoint(
    name='Sputtering',
    description='Schema package defined for sputtering.',
)


class RTPEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.rtp import m_package

        return m_package


rtp = RTPEntryPoint(
    name='RTP',
    description='Schema package defined for RTP.',
)


class ThermalEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.thermal import m_package

        return m_package


thermal = ThermalEntryPoint(
    name='Thermal',
    description='Schema package defined for thermal evaporation.',
)


class GasEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.gas import m_package

        return m_package


gas = GasEntryPoint(
    name='Gas',
    description='Schema package defined for gas.',
)


class TargetEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.target import m_package

        return m_package


target = TargetEntryPoint(
    name='Targets',
    description='Schema package defined for targets.',
)


class SubstrateEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.substrate import m_package

        return m_package


substrate = SubstrateEntryPoint(
    name='Substrate',
    description='Schema package defined for substrate.',
)


class InstrumentEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.instrument import m_package

        return m_package


instrument = InstrumentEntryPoint(
    name='Instrument',
    description='Schema package defined for instrument.',
)


class EDXEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.edx import m_package

        return m_package


edx = EDXEntryPoint(
    name='EDX',
    description='Schema package defined for EDX measurements.',
)


class XRDEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.xrd import m_package

        return m_package


xrd = XRDEntryPoint(
    name='XRD',
    description='Schema package defined for XRD measurements.',
)


class XPSEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.xps import m_package

        return m_package


xps = XPSEntryPoint(
    name='XPS',
    description='Schema package defined for XPS measurements.',
)


class SampleEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.sample import m_package

        return m_package


sample = SampleEntryPoint(
    name='Sample',
    description='Schema package defined for samples.',
)


class AnalysisEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.analysis import m_package

        return m_package


analysis = AnalysisEntryPoint(
    name='Analysis',
    description='Schema package defined for analysis.',
)
