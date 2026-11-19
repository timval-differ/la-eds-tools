import json
import os.path
import shutil

import pytest
from nomad.client import normalize_all, parse

EXAMPLE = os.path.join(
    os.path.dirname(__file__), os.pardir, 'data', 'example_light-on.sp0'
)


def test_parse_creates_eln_entry(tmp_path):
    sp0 = tmp_path / 'example_light-on.sp0'
    shutil.copy(EXAMPLE, sp0)

    archives = parse(str(sp0))
    assert archives, 'Sp0Parser did not match the .sp0 file'
    assert archives[0].metadata.entry_name == 'example_light-on.sp0'

    eln_file = tmp_path / 'example_light-on.archive.json'
    content = json.loads(eln_file.read_text())
    assert content['data'] == {
        'm_def': 'laeds_tools.schema_packages.schema_package.LaedsSpectrum',
        'data_file': 'example_light-on.sp0',
    }

    eln = parse(str(eln_file))[0]
    normalize_all(eln)
    assert int(eln.data.counts.sum()) == 873943  # noqa: PLR2004


def test_parse_malformed_sp0_fails_without_eln_entry(tmp_path):
    with open(EXAMPLE, encoding='ascii') as f:
        lines = f.read().splitlines()
    bad = tmp_path / 'short.sp0'
    bad.write_text('\n'.join(lines[:-10]) + '\n')

    with pytest.raises(ValueError, match='4096 channels but found 4086'):
        parse(str(bad))
    assert not (tmp_path / 'short.archive.json').exists()


def test_parse_keeps_existing_eln_entry(tmp_path):
    sp0 = tmp_path / 'example_light-on.sp0'
    shutil.copy(EXAMPLE, sp0)
    eln_file = tmp_path / 'example_light-on.archive.json'
    edited = '{"data": {"m_def": "laeds_tools.schema_packages.schema_package.LaedsSpectrum", "data_file": "example_light-on.sp0", "run_conditions": {"pressure": 1e-8}}}'
    eln_file.write_text(edited)

    parse(str(sp0))

    assert eln_file.read_text() == edited
