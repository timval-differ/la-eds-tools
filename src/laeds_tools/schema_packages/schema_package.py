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

import numpy as np
import plotly.graph_objects as go
from nomad.datamodel.data import ArchiveSection, EntryData
from nomad.datamodel.metainfo.annotations import ELNAnnotation, ELNComponentEnum
from nomad.datamodel.metainfo.plot import PlotlyFigure, PlotSection
from nomad.metainfo import JSON, Quantity, SchemaPackage, Section, SubSection

from laeds_tools.parsers.sp0_reader import Sp0Spectrum, parse_sp0_bytes

m_package = SchemaPackage()


def _num(unit: str | None = None) -> ELNAnnotation:
    props = {'defaultDisplayUnit': unit} if unit else None
    return ELNAnnotation(component=ELNComponentEnum.NumberEditQuantity, props=props)


class RunConditions(ArchiveSection):
    """Experimental conditions that are not stored in the .sp0 file.

    Filled in manually after parsing; the filename is not used because it is
    typed by hand and not reliable.
    """

    m_def = Section(label='Run conditions (manual)')

    acquisition_time = Quantity(
        type=np.float64, unit='s', a_eln=_num('s'), description='Acquisition time.'
    )
    distance = Quantity(
        type=np.float64,
        unit='cm',
        a_eln=_num('cm'),
        description='Distance (the "d" value in the filename convention).',
    )
    filament_current = Quantity(
        type=np.float64, unit='A', a_eln=_num('A'), description='Filament current.'
    )
    pressure = Quantity(
        type=np.float64, unit='mbar', a_eln=_num('mbar'), description='Pressure.'
    )
    light_on = Quantity(
        type=bool,
        a_eln=ELNAnnotation(component=ELNComponentEnum.BoolEditQuantity),
        description='Whether the light was on during the acquisition.',
    )


class Sp0Settings(ArchiveSection):
    """Settings stored in the .sp0 header (read-only, from the file)."""

    m_def = Section(label='Spectrum file settings')

    software_version = Quantity(type=str)
    spectrum_name = Quantity(type=str)
    accelerating_voltage = Quantity(type=np.float64, unit='kV')
    beam_current = Quantity(type=np.float64, unit='nA')
    live_time = Quantity(type=np.float64, unit='s')
    takeoff_angle = Quantity(type=np.float64, unit='deg')
    incidence_angle = Quantity(type=np.float64, unit='deg')
    elevation_angle = Quantity(type=np.float64, unit='deg')
    time_constant = Quantity(
        type=np.float64,
        description='Pulse processor time constant as written by Iridium (unit not '
        'stated in the file).',
    )
    pulse_processor_gain = Quantity(type=np.float64)
    calibration_zero = Quantity(
        type=np.float64, unit='eV', description='Energy of channel 0 (CalZero).'
    )
    calibration_gain = Quantity(
        type=np.float64, unit='eV', description='Energy width per channel (CalGain).'
    )
    number_of_channels = Quantity(type=int)
    raw_header = Quantity(
        type=JSON, description='All header values exactly as found in the file.'
    )

    @classmethod
    def from_spectrum(cls, spec: Sp0Spectrum) -> 'Sp0Settings':
        s, p = spec.settings, spec.parameters
        cal = spec.blocks.get('EnergyCalibrationInformation', {})
        return cls(
            software_version=spec.software_version,
            spectrum_name=s.get('Name'),
            accelerating_voltage=s.get('kV'),
            beam_current=s.get('nA'),
            live_time=s.get('Live'),
            takeoff_angle=s.get('Takeoff'),
            incidence_angle=s.get('Incid'),
            elevation_angle=s.get('Elev'),
            time_constant=p.get('Time Constant'),
            pulse_processor_gain=p.get('Pulse Processor Gain'),
            calibration_zero=cal.get('CalZero'),
            calibration_gain=cal.get('CalGain', p.get('eV per Channel')),
            number_of_channels=spec.number_of_channels,
            raw_header={
                'preamble': spec.preamble,
                'settings': s,
                'blocks': spec.blocks,
                'parameters': p,
            },
        )


class LaedsSpectrum(PlotSection, EntryData):
    """EDS spectrum from an Iridium ``.sp0`` file plus manual run conditions."""

    m_def = Section(label='LAEDS spectrum (.sp0)')

    data_file = Quantity(
        type=str,
        a_eln=ELNAnnotation(component=ELNComponentEnum.FileEditQuantity),
        description='The .sp0 file. Data and settings are re-read when it changes.',
    )
    run_conditions = SubSection(section_def=RunConditions)
    settings = SubSection(section_def=Sp0Settings)
    channel = Quantity(type=np.int64, shape=['*'])
    energy = Quantity(
        type=np.float64,
        shape=['*'],
        unit='eV',
        description='calibration_zero + channel * calibration_gain.',
    )
    counts = Quantity(type=np.int64, shape=['*'])

    def read_file(self, content: bytes, source: str) -> None:
        spec = parse_sp0_bytes(content, source=source)
        path = source
        self.settings = Sp0Settings.from_spectrum(spec)
        zero = self.settings.calibration_zero
        gain = self.settings.calibration_gain
        if gain is None:
            raise ValueError(f'{path}: no energy calibration gain in header')
        self.channel = np.arange(spec.number_of_channels)
        self.energy = (zero if zero is not None else 0) + self.channel * gain
        self.counts = np.asarray(spec.counts, dtype=np.int64)

    def normalize(self, archive: 'EntryArchive', logger: 'BoundLogger') -> None:
        if self.data_file:
            # Read via the handle: on a server this is an fsspec/zip stream that
            # has no usable OS path.
            with archive.m_context.raw_file(self.data_file, 'rb') as f:
                self.read_file(f.read(), source=self.data_file)
        if self.run_conditions is None:
            self.run_conditions = RunConditions()

        if self.counts is not None and self.energy is not None:
            fig = go.Figure(
                go.Scatter(
                    x=self.energy.to('keV').magnitude, y=self.counts, mode='lines'
                )
            )
            fig.update_layout(
                xaxis_title='Energy (keV)',
                yaxis_title='Counts',
                template='plotly_white',
            )
            self.figures = [
                PlotlyFigure(label='Spectrum', index=0, figure=fig.to_plotly_json())
            ]

        super().normalize(archive, logger)


m_package.__init_metainfo__()
