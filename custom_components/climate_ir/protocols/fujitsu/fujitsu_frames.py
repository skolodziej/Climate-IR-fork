"""Fujitsu 16-byte frames, with a short message for power off.

Protocol facts were read from the `FujitsuHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_210
HEADER_SPACE_US: Final = 1_680
BIT_MARK_US: Final = 410
ZERO_SPACE_US: Final = 440
ONE_SPACE_US: Final = 1_230

MIN_TEMPERATURE: Final = 16
MAX_TEMPERATURE: Final = 30

TEMPLATE: Final = (
    0x14, 0x63, 0x00, 0x10, 0x10, 0xFE, 0x09, 0x30,
    0x80, 0x04, 0x00, 0x00, 0x00, 0x00, 0x20, 0x00,
)
#: Switching off is a message of its own rather than a flag in the frame.
OFF_FRAME: Final = (0x14, 0x63, 0x00, 0x10, 0x10, 0x02, 0xFD)
CHECKSUM_SEED: Final = 0x9E

MODE_CODES: Final = {
    "heat_cool": 0x00,
    "heat": 0x04,
    "cool": 0x01,
    "dry": 0x02,
    "fan_only": 0x03,
}

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_CODES: Final = {
    FAN_AUTO: 0x00,
    FAN_LOW: 0x04,
    FAN_MEDIUM: 0x03,
    FAN_HIGH: 0x02,
}

SWING_OFF = "Off"
SWING_ON = "Swing"
SWING_CODES: Final = {SWING_OFF: 0x00, SWING_ON: 0x10}
SWING_H_CODES: Final = {SWING_OFF: 0x00, SWING_ON: 0x20}

PRESET_NONE = "none"
PRESET_ECO = "eco"
PRESET_MODES: Final = (PRESET_NONE, PRESET_ECO)
ECO_CODES: Final = {PRESET_NONE: 0x20, PRESET_ECO: 0x00}


class FujitsuCommand(Command):
    """Raw Fujitsu command."""

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
    preset_mode: str = PRESET_NONE,
) -> bytes:
    """Return the frame for the requested state."""

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
    if preset_mode not in ECO_CODES:
        raise ValueError(f"Unknown preset mode: {preset_mode}")

    if not power_on:
        return bytes(OFF_FRAME)

    frame = bytearray(TEMPLATE)
    # The least significant bit of the temperature byte stays set.
    frame[8] = ((temperature_c - 16) << 4) | 0x01
    frame[9] = MODE_CODES[mode]
    frame[10] = (
        FAN_CODES[fan_mode]
        + SWING_CODES[swing_mode]
        + SWING_H_CODES[swing_horizontal_mode]
    )
    frame[14] = ECO_CODES[preset_mode]
    frame[15] = (CHECKSUM_SEED - sum(frame[:15])) & 0xFF

    return bytes(frame)


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
    preset_mode: str = PRESET_NONE,
) -> FujitsuCommand:
    """Build an IR command for the HA infrared platform."""

    return FujitsuCommand(
        frame_to_timings(
            build_frame_bytes(
                mode,
                temperature_c,
                power_on,
                fan_mode,
                swing_mode,
                swing_horizontal_mode,
                preset_mode=preset_mode,
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
