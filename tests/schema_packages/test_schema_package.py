import os.path

from nomad.client import normalize_all, parse


def test_schema_package():
    test_file = os.path.join(
        os.path.dirname(__file__), os.pardir, 'data', 'test.archive.yaml'
    )
    entry_archive = parse(test_file)[0]
    normalize_all(entry_archive)

    data = entry_archive.data
    assert len(data.counts) == 4096  # noqa: PLR2004
    assert int(data.counts.sum()) == 873943  # noqa: PLR2004
    assert data.energy[1].to('eV').magnitude == 5.0  # noqa: PLR2004
    assert data.settings.accelerating_voltage.to('kV').magnitude == 30  # noqa: PLR2004
    calibration = data.settings.raw_header['blocks']['EnergyCalibrationInformation']
    assert calibration['CalGain'] == 5  # noqa: PLR2004
    # manual fields are present but empty
    assert data.run_conditions is not None
    assert data.run_conditions.pressure is None
    assert len(data.figures) == 1
