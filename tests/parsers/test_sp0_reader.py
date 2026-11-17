import os.path

import pytest

from laeds_tools.parsers.sp0_reader import read_sp0

EXAMPLE = os.path.join('tests', 'data', 'example_light-on.sp0')


def test_read_example():
    spec = read_sp0(EXAMPLE)

    assert spec.software_version == 'Iridium V5.13'
    assert spec.number_of_channels == 4096  # noqa: PLR2004
    assert sum(spec.counts) == 873943  # noqa: PLR2004
    assert max(spec.counts) == 32441  # noqa: PLR2004
    assert spec.settings['kV'] == 30  # noqa: PLR2004
    assert spec.settings['nA'] == 0.1  # noqa: PLR2004
    # ",Incid" in the file and repeated "High" names are cleaned up
    assert spec.settings['Incid'] == 45  # noqa: PLR2004
    assert 'NormHigh' in spec.settings
    assert spec.blocks['EnergyCalibrationInformation'] == {
        'CalZero': 0,
        'CalGain': 5,
        'LowestEnergy': 0.4,
    }
    assert spec.parameters['Number of Channels'] == 4096  # noqa: PLR2004


def test_rejects_non_iridium(tmp_path):
    bad = tmp_path / 'bad.sp0'
    bad.write_text('something else\n')
    with pytest.raises(ValueError, match='not an Iridium'):
        read_sp0(str(bad))


def test_rejects_channel_count_mismatch(tmp_path):
    with open(EXAMPLE, encoding='ascii') as f:
        lines = f.read().splitlines()
    truncated = tmp_path / 'short.sp0'
    truncated.write_text('\n'.join(lines[:-10]) + '\n')
    with pytest.raises(ValueError, match='4096 channels but found 4086'):
        read_sp0(str(truncated))
