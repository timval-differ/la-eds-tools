"""Reader for EDAX/Iridium ASCII ``.sp0`` spectrum files.

Kept free of NOMAD imports so it can be used and tested on its own.

File layout (as written by Iridium V5.13)::

    Iridium V5.13                 <- software/version line
    Spectrum
    <blank>
    OriginalSpectrum
    NoProcessedSpectrum
    "Name","HDist",...            <- CSV row of setting names
    "Untitled",0,...              <- CSV row of setting values
    "***DetectorInformation***",1 <- start of a named block
    "Z",0                         <- "key",value pairs
    "***EndDetectorInformation***"
    ...
    "Number of Channels",4096
     0                            <- one count per channel
     ...
"""

import csv
from dataclasses import dataclass, field

BLOCK_START = '***'
BLOCK_END_PREFIX = '***End'


@dataclass
class Sp0Spectrum:
    software_version: str
    preamble: list[str]
    settings: dict[str, object]
    blocks: dict[str, dict[str, object]]
    parameters: dict[str, object]
    counts: list[int] = field(default_factory=list)

    @property
    def number_of_channels(self) -> int:
        return len(self.counts)


def _to_value(text: str) -> object:
    """Convert a CSV field to int, float or str (strings keep their text)."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _dedupe_names(names: list[str]) -> list[str]:
    """Make the settings header row usable as dict keys.

    Iridium writes ranges as e.g. "NormLow","High"; a bare "High" is renamed
    to the preceding "...Low" name with "Low" -> "High". Stray characters such
    as the leading comma in ",Incid" are stripped. Remaining duplicates get a
    numeric suffix.
    """
    out: list[str] = []
    for raw in names:
        name = raw.strip().lstrip(',').strip()
        if name == 'High' and out and out[-1].endswith('Low'):
            name = out[-1][: -len('Low')].rstrip() + 'High'
        base, i = name, 2
        while name in out:
            name = f'{base}_{i}'
            i += 1
        out.append(name)
    return out


def _csv_row(line: str) -> list[str]:
    return next(csv.reader([line]))


def read_sp0(path: str) -> Sp0Spectrum:
    """Parse an ``.sp0`` file on disk. Raises ``ValueError`` on malformed content."""
    with open(path, 'rb') as f:
        return parse_sp0_bytes(f.read(), source=path)


def parse_sp0_bytes(content: bytes, source: str = '<sp0>') -> Sp0Spectrum:
    """Parse ``.sp0`` content. Use this with file handles that have no OS path,
    such as NOMAD's ``m_context.raw_file`` on a server.

    Decoded as latin-1 so a stray non-ASCII byte (e.g. a degree sign in a name)
    does not make the whole spectrum unreadable.
    """
    return _parse_lines(content.decode('latin-1').splitlines(), source)


def _parse_lines(lines: list[str], path: str) -> Sp0Spectrum:
    if not lines or not lines[0].startswith('Iridium'):
        raise ValueError(f'{path}: not an Iridium .sp0 file (first line: {lines[:1]})')

    software_version = lines[0].strip()

    # Settings name/value rows: the first two lines starting with a quote.
    first_quoted = next(
        (i for i, line in enumerate(lines) if line.startswith('"')), None
    )
    if first_quoted is None or first_quoted + 1 >= len(lines):
        raise ValueError(f'{path}: settings rows not found')
    preamble = [line.strip() for line in lines[1:first_quoted] if line.strip()]
    names = _dedupe_names(_csv_row(lines[first_quoted]))
    values = _csv_row(lines[first_quoted + 1])
    if len(names) != len(values):
        raise ValueError(
            f'{path}: settings header has {len(names)} names but {len(values)} values'
        )
    settings = {n: _to_value(v) for n, v in zip(names, values)}

    blocks: dict[str, dict[str, object]] = {}
    parameters: dict[str, object] = {}
    current: dict[str, object] | None = None
    i = first_quoted + 2
    while i < len(lines) and lines[i].startswith('"'):
        row = _csv_row(lines[i])
        key = row[0]
        if key.startswith(BLOCK_END_PREFIX):
            current = None
        elif key.startswith(BLOCK_START):
            block_name = key.strip('*')
            current = blocks.setdefault(block_name, {})
        else:
            if len(row) != 2:  # noqa: PLR2004
                raise ValueError(f'{path}:{i + 1}: expected "key",value, got {row}')
            target = current if current is not None else parameters
            target[key] = _to_value(row[1])
        i += 1

    try:
        counts = [int(line) for line in lines[i:] if line.strip()]
    except ValueError as e:
        raise ValueError(f'{path}: non-integer value in channel data: {e}') from e

    expected = parameters.get('Number of Channels')
    if expected is not None and expected != len(counts):
        raise ValueError(
            f'{path}: header says {expected} channels but found {len(counts)} counts'
        )

    return Sp0Spectrum(
        software_version=software_version,
        preamble=preamble,
        settings=settings,
        blocks=blocks,
        parameters=parameters,
        counts=counts,
    )
