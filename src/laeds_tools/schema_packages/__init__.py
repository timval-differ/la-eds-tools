from nomad.config.models.plugins import SchemaPackageEntryPoint


class LaedsSchemaPackageEntryPoint(SchemaPackageEntryPoint):
    def load(self):
        from laeds_tools.schema_packages.schema_package import m_package

        return m_package


schema_package_entry_point = LaedsSchemaPackageEntryPoint(
    name='LaedsSchemaPackage',
    description='Schema for LAEDS .sp0 spectra with manual run conditions.',
)
