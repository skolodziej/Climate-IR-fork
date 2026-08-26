"""Toshiba nine-byte frames.

Protocol facts were read from the `ToshibaHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 4_400
HEADER_SPACE_US: Final = 4_400
BIT_MARK_US: Final = 550
ZERO_SPACE_US: Final = 550
ONE_SPACE_US: Final = 1_600

MIN_TEMPERATURE: Final = 17
MAX_TEMPERATURE: Final = 30

TEMPLATE: Final = (0x4F, 0xB0, 0xC0, 0x3F, 0x80, 0x00, 0x00, 0x00, 0x00)

MODE_CODES: Final = {
    "heat_cool": 0x00,
    "heat": 0xC0,
    "cool": 0x80,
    "dry": 0x40,
    # This family has no fan-only code of its own; dry is the closest.
    "fan_only": 0x40,
}
MODE_OFF: Final = 0xE0

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_VERY_HIGH = "Very High"
FAN_MAX = "Max"
FAN_CODES: Final = {
    FAN_AUTO: 0x00,
    FAN_LOW: 0x02,
    FAN_MEDIUM: 0x06,
    FAN_HIGH: 0x01,
    FAN_VERY_HIGH: 0x05,
    FAN_MAX: 0x03,
}


class ToshibaCommand(Command):
    """Raw nine-byte Toshiba command."""

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


def _reverse_nibble(value: int) -> int:
    """Return the low nibble with its bits reversed."""

    return int(f"{value & 0x0F:04b}"[::-1], 2)


def build_frame_bytes(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
) -> bytes:
    """Return the nine-byte frame for the requested state."""

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")

    frame = bytearray(TEMPLATE)
    frame[5] |= _reverse_nibble(temperature_c - MIN_TEMPERATURE)
    frame[6] |= (MODE_OFF if not power_on else MODE_CODES[mode]) | FAN_CODES[fan_mode]

    checksum = 0x00
    for byte in frame[:8]:
        checksum ^= byte
    frame[8] = checksum

    return bytes(frame)


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
) -> ToshibaCommand:
    """Build an IR command for the HA infrared platform."""

    return ToshibaCommand(
        frame_to_timings(build_frame_bytes(mode, temperature_c, power_on, fan_mode))
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
