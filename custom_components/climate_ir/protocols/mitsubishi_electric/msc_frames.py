"""Mitsubishi Electric MSC 14-byte frames.

Protocol facts were read from the `MitsubishiMSCHeatpumpIR` module of
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
    0x23, 0xCB, 0x26, 0x01, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
)

POWER_ON: Final = 0x24
POWER_OFF: Final = 0x20

MODE_CODES: Final = {
    "heat_cool": 0x08,
    "heat": 0x01,
    "cool": 0x03,
    "dry": 0x02,
    "fan_only": 0x07,
}

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_CODES: Final = {
    FAN_AUTO: 0x00,
    FAN_LOW: 0x02,
    FAN_MEDIUM: 0x03,
    FAN_HIGH: 0x05,
}

SWING_AUTO = "Auto"
SWING_SWING = "Swing"
SWING_UP = "Up"
SWING_UP_MIDDLE = "Up-Middle"
SWING_MIDDLE = "Middle"
SWING_DOWN_MIDDLE = "Down-Middle"
SWING_DOWN = "Down"
SWING_CODES: Final = {
    SWING_AUTO: 0x00,
    SWING_SWING: 0x38,
    SWING_UP: 0x08,
    SWING_UP_MIDDLE: 0x10,
    SWING_MIDDLE: 0x18,
    SWING_DOWN_MIDDLE: 0x20,
    SWING_DOWN: 0x28,
}


class MitsubishiElectricMSCCommand(Command):
    """Raw 14-byte Mitsubishi Electric MSC command."""

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
    swing_mode: str,
) -> bytes:
    """Return the 14-byte frame for the requested state."""

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")
    if swing_mode not in SWING_CODES:
        raise ValueError(f"Unknown swing mode: {swing_mode}")

    frame = bytearray(TEMPLATE)
    frame[5] = POWER_ON if power_on else POWER_OFF
    frame[6] = MODE_CODES[mode]
    # This family counts the setpoint down from 31.
    frame[7] = 31 - temperature_c
    frame[8] = FAN_CODES[fan_mode] | SWING_CODES[swing_mode]
    frame[-1] = sum(frame[:-1]) & 0xFF

    return bytes(frame)


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
) -> MitsubishiElectricMSCCommand:
    """Build an IR command for the HA infrared platform."""

    frame = build_frame_bytes(mode, temperature_c, power_on, fan_mode, swing_mode)
    return MitsubishiElectricMSCCommand(frame_to_timings(frame))


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
