from nomad.config.models.plugins import SchemaPackageEntryPoint
from pydantic import Field


class MySchemaPackageEntryPoint(SchemaPackageEntryPoint):
    parameter: int = Field(0, description='Custom configuration parameter')

    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.mypackage import m_package

        return m_package


mypackage = MySchemaPackageEntryPoint(
    name='MyPackage',
    description='Schema package defined using the new plugin mechanism.',
)


class SputteringEntryPoint(SchemaPackageEntryPoint):

    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.sputtering import m_package

        return m_package


sputtering = MySchemaPackageEntryPoint(
    name='Sputtering',
    description='Schema package defined for sputtering.',
)


class GasEntryPoint(SchemaPackageEntryPoint):

    def load(self):
        from nomad_dtu_nanolab_plugin.schema_packages.gas import m_package

        return m_package


gas = MySchemaPackageEntryPoint(
    name='Gas',
    description='Schema package defined for gas.',
)
