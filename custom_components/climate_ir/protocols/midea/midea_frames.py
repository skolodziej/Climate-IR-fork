"""Midea three-byte frames, each byte followed by its complement.

Protocol facts were read from the `MideaHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 4_420
HEADER_SPACE_US: Final = 4_300
BIT_MARK_US: Final = 620
ZERO_SPACE_US: Final = 480
ONE_SPACE_US: Final = 1_560
MESSAGE_SPACE_US: Final = 5_100

MIN_TEMPERATURE: Final = 17
MAX_TEMPERATURE: Final = 30

LEAD_BYTE: Final = 0x4D
#: The whole message when the unit is switched off.
OFF_FRAME: Final = (0x4D, 0xDE, 0x07)

MODE_CODES: Final = {
    "heat_cool": 0x10,
    "heat": 0x30,
    "cool": 0x00,
    "dry": 0x20,
    "fan_only": 0x60,
}

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_CODES: Final = {
    FAN_AUTO: 0x02,
    FAN_LOW: 0x06,
    FAN_MEDIUM: 0x05,
    FAN_HIGH: 0x03,
}

#: The setpoint is not encoded linearly; this table is indexed by
#: temperature - 17 and covers 17..30 degrees.
TEMPERATURE_CODES: Final = (0, 8, 12, 4, 6, 14, 10, 2, 3, 11, 9, 1, 5, 13)


class MideaCommand(Command):
    """Raw Midea command: three payload bytes, sent twice."""

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
    """Return the three payload bytes for the requested state."""

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")

    if not power_on:
        return bytes(OFF_FRAME)

    if mode == "fan_only":
        # Fan-only rides on the dry code with every temperature bit set.
        payload = MODE_CODES["dry"] | 0x07
    else:
        payload = (
            MODE_CODES[mode] | TEMPERATURE_CODES[temperature_c - MIN_TEMPERATURE]
        )

    return bytes((LEAD_BYTE, ~FAN_CODES[fan_mode] & 0xFF, payload))


def build_command(
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
) -> MideaCommand:
    """Build an IR command for the HA infrared platform."""

    return MideaCommand(
        frame_to_timings(build_frame_bytes(mode, temperature_c, power_on, fan_mode))
    )


def frame_to_timings(frame: bytes) -> list:
    """Convert a frame to signed timings.

    Every byte is followed by its complement, and the whole message is sent
    twice.
    """

    timings: list = []
    for burst in range(2):
        if burst:
            timings.append(BIT_MARK_US)
            timings.append(-MESSAGE_SPACE_US)
        timings.append(HEADER_MARK_US)
        timings.append(-HEADER_SPACE_US)
        for byte in frame:
            for value in (byte, ~byte & 0xFF):
                for position in range(8):
                    timings.append(BIT_MARK_US)
                    timings.append(
                        -ONE_SPACE_US if (value >> position) & 1 else -ZERO_SPACE_US
                    )
    timings.append(BIT_MARK_US)
    return timings
