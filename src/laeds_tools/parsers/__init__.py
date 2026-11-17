from nomad.config.models.plugins import ParserEntryPoint


class Sp0ParserEntryPoint(ParserEntryPoint):
    def load(self):
        from laeds_tools.parsers.parser import Sp0Parser

        return Sp0Parser(**self.model_dump())


parser_entry_point = Sp0ParserEntryPoint(
    name='Sp0Parser',
    description='Parser for EDAX/Iridium ASCII .sp0 spectrum files.',
    mainfile_name_re=r'(?i).*\.sp0$',
    mainfile_contents_re=r'^Iridium',
)
