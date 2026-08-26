"""Hitachi 28-byte frames.

Protocol facts were read from the `HitachiHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_436
HEADER_SPACE_US: Final = 1_640
BIT_MARK_US: Final = 420
ZERO_SPACE_US: Final = 500
ONE_SPACE_US: Final = 1_250

MIN_TEMPERATURE: Final = 16
MAX_TEMPERATURE: Final = 32

TEMPLATE: Final = (
    0x01, 0x10, 0x30, 0x40, 0xBF, 0x01, 0xFE, 0x11, 0x12, 0x08,
    0x00, 0x00, 0x00, 0x00, 0x06, 0x06, 0x00, 0x80, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x80, 0x01, 0x00, 0x00, 0x00,
)
#: The checksum counts down from this seed.
CHECKSUM_SEED: Final = 1086

MODE_CODES: Final = {
    "heat_cool": 0x02,
    "heat": 0x03,
    "cool": 0x04,
    "dry": 0x05,
    "fan_only": 0x0C,
}
POWER_ON: Final = 0x80
POWER_OFF: Final = 0x00

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_VERY_HIGH = "Very High"
FAN_CODES: Final = {
    FAN_AUTO: 0x01,
    FAN_LOW: 0x02,
    FAN_MEDIUM: 0x03,
    FAN_HIGH: 0x04,
    FAN_VERY_HIGH: 0x05,
}

SWING_OFF = "Off"
SWING_ON = "Swing"
SWING_CODES: Final = {SWING_OFF: 0x00, SWING_ON: 0x01}
SWING_H_CODES: Final = {SWING_OFF: 0x00, SWING_ON: 0x01}


class HitachiCommand(Command):
    """Raw 28-byte Hitachi command."""

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
    swing_horizontal_mode: str,
) -> bytes:
    """Return the 28-byte frame for the requested state."""

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
    if swing_horizontal_mode not in SWING_H_CODES:
        raise ValueError(
            f"Unknown horizontal swing mode: {swing_horizontal_mode}"
        )

    frame = bytearray(TEMPLATE)
    if temperature_c == MIN_TEMPERATURE:
        # The lowest setpoint needs its own marker byte.
        frame[9] = 0x09
    frame[10] = MODE_CODES[mode]
    frame[11] = (temperature_c << 1) & 0xFF
    frame[13] = FAN_CODES[fan_mode]
    frame[14] |= SWING_CODES[swing_mode]
    frame[15] |= SWING_H_CODES[swing_horizontal_mode]
    frame[17] = POWER_ON if power_on else POWER_OFF

    frame[27] = (CHECKSUM_SEED - sum(frame[:27])) & 0xFF

    return bytes(frame)


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
) -> HitachiCommand:
    """Build an IR command for the HA infrared platform."""

    return HitachiCommand(
        frame_to_timings(
            build_frame_bytes(
                mode,
                temperature_c,
                power_on,
                fan_mode,
                swing_mode,
                swing_horizontal_mode,
            )
        )
    )


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
