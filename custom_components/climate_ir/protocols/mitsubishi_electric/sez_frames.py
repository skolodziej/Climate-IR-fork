"""Mitsubishi Electric SEZ-KDXX 17-byte frames.

Protocol facts were read from the `MitsubishiSEZKDXXHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_060
HEADER_SPACE_US: Final = 1_580
BIT_MARK_US: Final = 350
ZERO_SPACE_US: Final = 390
ONE_SPACE_US: Final = 1_150

MIN_TEMPERATURE: Final = 16
MAX_TEMPERATURE: Final = 31

TEMPLATE: Final = (
    0x23, 0xCB, 0x26, 0x21, 0x00, 0x40, 0x00, 0x00, 0x04,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
)

POWER_ON: Final = 0x40
POWER_OFF: Final = 0x00

MODE_CODES: Final = {
    "heat_cool": 0x03,
    "heat": 0x02,
    "cool": 0x01,
    "dry": 0x05,
    "fan_only": 0x00,
}

FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_CODES: Final = {
    FAN_LOW: 0x32,
    FAN_MEDIUM: 0x34,
    FAN_HIGH: 0x36,
}


class MitsubishiElectricSEZCommand(Command):
    """Raw 17-byte Mitsubishi Electric SEZ-KDXX command."""

    def __init__(
        self,
        timings: list,
        *,
        modulation: int = DEFAULT_CARRIER_FREQUENCY,
        repeat_count: int = 0,
    ) -> None:
        """Initialize the command."""

        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._timings = timings

    def get_raw_timings(self) -> list:
        """Return signed raw timings in microseconds."""

        return list(self._timings)


def build_frame_bytes(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
) -> bytes:
    """Return the 17-byte frame for the requested state."""

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")

    frame = bytearray(TEMPLATE)
    frame[5] = POWER_ON if power_on else POWER_OFF
    frame[6] = ((temperature_c - 16) << 4) | MODE_CODES[mode]
    frame[7] = FAN_CODES[fan_mode]

    # Bytes 11..16 carry the inverse of bytes 5..10.
    for offset in range(6):
        frame[11 + offset] = ~frame[5 + offset] & 0xFF

    return bytes(frame)


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
) -> MitsubishiElectricSEZCommand:
    """Build an IR command for the HA infrared platform."""

    frame = build_frame_bytes(mode, temperature_c, power_on, fan_mode)
    return MitsubishiElectricSEZCommand(frame_to_timings(frame))


def frame_to_timings(frame: bytes) -> list:
    """Convert a frame to signed raw timings, least significant bit first."""

    timings = [HEADER_MARK_US, -HEADER_SPACE_US]
    for byte in frame:
        for position in range(8):
            timings.append(BIT_MARK_US)
            timings.append(
                -ONE_SPACE_US if (byte >> position) & 1 else -ZERO_SPACE_US
            )
    timings.append(BIT_MARK_US)
    return timings
