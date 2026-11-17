import os.path
from pathlib import PurePath
from typing import (
    TYPE_CHECKING,
)

if TYPE_CHECKING:
    from nomad.datamodel.datamodel import (
        EntryArchive,
    )
    from structlog.stdlib import (
        BoundLogger,
    )

from nomad.parsing.parser import MatchingParser


class Sp0Parser(MatchingParser):
    """Turns each Iridium ``.sp0`` file into an editable ``LaedsSpectrum`` entry.

    Entries parsed directly from raw files cannot be edited in the NOMAD GUI, so
    the parser writes a ``<name>.archive.json`` next to the ``.sp0`` file that
    references it. NOMAD processes that file as an ELN entry; its normalizer reads
    the spectrum, and the manual run conditions can be filled in there.
    An existing ``.archive.json`` is left alone so manual edits survive reprocessing.
    """

    def parse(
        self,
        mainfile: str,
        archive: 'EntryArchive',
        logger: 'BoundLogger',
        child_archives: dict[str, 'EntryArchive'] = None,
    ) -> None:
        from laeds_tools.parsers.sp0_reader import read_sp0
        from laeds_tools.schema_packages.schema_package import LaedsSpectrum

        # Fail this entry visibly on a malformed file. Errors raised while NOMAD
        # processes the generated ELN entry are only recorded on that entry.
        read_sp0(mainfile)

        # Upload-relative on a NOMAD server. Local `nomad.client.parse` gives an
        # absolute path instead, so make it relative to the local context root.
        raw_path = archive.metadata.mainfile
        local_dir = getattr(archive.m_context, 'local_dir', None)
        if os.path.isabs(raw_path) and local_dir:
            raw_path = os.path.relpath(raw_path, local_dir)
        raw_path = PurePath(raw_path).as_posix()  # NOMAD paths use '/'
        stem = os.path.splitext(raw_path)[0]
        eln_file = f'{stem}.archive.json'
        archive.metadata.entry_name = os.path.basename(raw_path)

        if archive.m_context.raw_path_exists(eln_file):
            logger.info('ELN entry already exists, not overwriting', file=eln_file)
            return

        entry = LaedsSpectrum(data_file=raw_path)
        with archive.m_context.update_entry(eln_file, write=True, process=True) as e:
            e['data'] = entry.m_to_dict(with_root_def=True)
