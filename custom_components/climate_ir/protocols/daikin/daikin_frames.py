"""Daikin 35-byte frames, sent as three bursts.

Protocol facts were read from the `DaikinHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.

Deviation from the reference: it assigns sentinel temperatures for dry and
fan-only that its own range check then discards, leaving the byte at a
default. That looks unintended, so the setpoint is encoded the same way in
every mode here.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_360
HEADER_SPACE_US: Final = 1_760
BIT_MARK_US: Final = 360
ZERO_SPACE_US: Final = 520
ONE_SPACE_US: Final = 1_370
MESSAGE_SPACE_US: Final = 32_300

MIN_TEMPERATURE: Final = 18
MAX_TEMPERATURE: Final = 30

TEMPLATE: Final = (
    # First header
    0x11, 0xDA, 0x27, 0x00, 0xC5, 0x00, 0x00, 0xD7,
    # Second header; the remote puts its wall clock in bytes 12 and 13
    0x11, 0xDA, 0x27, 0x00, 0x42, 0x49, 0x05, 0xA2,
    # Payload
    0x11, 0xDA, 0x27, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x06, 0x60, 0x00, 0x00, 0xC0,
    0x00, 0x00, 0x00,
)
#: Byte ranges of the three bursts.
BURSTS: Final = ((0, 8), (8, 16), (16, 35))
#: The payload checksum covers bytes 16..33 and lands in byte 34.
CHECKSUM_RANGE: Final = (16, 34)

MODE_CODES: Final = {
    "heat_cool": 0x00,
    "heat": 0x40,
    "cool": 0x30,
    "dry": 0x20,
    "fan_only": 0x60,
}
POWER_ON: Final = 0x01
POWER_OFF: Final = 0x00

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_VERY_HIGH = "Very High"
FAN_MAX = "Max"
FAN_CODES: Final = {
    FAN_AUTO: 0xA0,
    FAN_LOW: 0x30,
    FAN_MEDIUM: 0x40,
    FAN_HIGH: 0x50,
    FAN_VERY_HIGH: 0x60,
    FAN_MAX: 0x70,
}


class DaikinCommand(Command):
    """Raw 35-byte Daikin command, sent as three bursts."""

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
    """Return the 35-byte frame for the requested state."""

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")

    frame = bytearray(TEMPLATE)
    frame[21] = MODE_CODES[mode] | (POWER_ON if power_on else POWER_OFF)
    frame[22] = (temperature_c << 1) & 0xFF
    frame[24] = FAN_CODES[fan_mode]

    start, end = CHECKSUM_RANGE
    frame[34] = sum(frame[start:end]) & 0xFF

    return bytes(frame)


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
) -> DaikinCommand:
    """Build an IR command for the HA infrared platform."""

    return DaikinCommand(
        frame_to_timings(build_frame_bytes(mode, temperature_c, power_on, fan_mode))
    )


def frame_to_timings(frame: bytes) -> list:
    """Convert a frame to signed timings across its three bursts."""

    timings: list = []
    for index, (start, end) in enumerate(BURSTS):
        if index:
            timings.append(BIT_MARK_US)
            timings.append(-MESSAGE_SPACE_US)
        timings.append(HEADER_MARK_US)
        timings.append(-HEADER_SPACE_US)
        for byte in frame[start:end]:
            for position in range(8):
                timings.append(BIT_MARK_US)
                timings.append(
                    -ONE_SPACE_US if (byte >> position) & 1 else -ZERO_SPACE_US
                )
    timings.append(BIT_MARK_US)
    return timings
