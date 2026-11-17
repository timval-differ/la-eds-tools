from nomad.config.models.plugins import ExampleUploadEntryPoint

example_upload_entry_point = ExampleUploadEntryPoint(
    title='LAEDS .sp0 spectra',
    category='Examples',
    description='Two Iridium .sp0 EDS spectra (light on / light off).',
    path='example_uploads/laeds_sp0',
)
