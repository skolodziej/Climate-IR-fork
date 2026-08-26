"""Panasonic 27-byte frames, shared by the DKE, JKE, NKE, LKE and EKE remotes.

One protocol carries all five models; they differ only in a handful of
template bytes. Protocol facts were read from the `PanasonicHeatpumpIR`
module of ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual
description of the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_500
HEADER_SPACE_US: Final = 1_800
BIT_MARK_US: Final = 420
ZERO_SPACE_US: Final = 470
ONE_SPACE_US: Final = 1_350
MESSAGE_SPACE_US: Final = 10_000

MIN_TEMPERATURE: Final = 16
MAX_TEMPERATURE: Final = 30

TEMPLATE: Final = (
    0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x06,
    0x02, 0x20, 0xE0, 0x04, 0x00, 0x00, 0x00, 0x80,
    0x00, 0x00, 0x00, 0x0E, 0xE0, 0x00, 0x00, 0x81,
    0x00, 0x00, 0x00,
)
#: The first burst carries bytes 0..7, the second the rest.
FIRST_BURST: Final = 8
CHECKSUM_SEED: Final = 0xF4

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

SWING_AUTO = "Auto"
SWING_UP = "Up"
SWING_UP_MIDDLE = "Up-Middle"
SWING_MIDDLE = "Middle"
SWING_DOWN_MIDDLE = "Down-Middle"
SWING_DOWN = "Down"
SWING_CODES: Final = {
    SWING_AUTO: 0x0F,
    SWING_UP: 0x01,
    SWING_UP_MIDDLE: 0x02,
    SWING_MIDDLE: 0x03,
    SWING_DOWN_MIDDLE: 0x04,
    SWING_DOWN: 0x05,
}

SWING_H_AUTO = "Auto"
SWING_H_MIDDLE = "Middle"
SWING_H_LEFT = "Left"
SWING_H_MIDDLE_LEFT = "Middle-Left"
SWING_H_MIDDLE_RIGHT = "Middle-Right"
SWING_H_RIGHT = "Right"
SWING_H_CODES: Final = {
    SWING_H_AUTO: 0x0D,
    SWING_H_MIDDLE: 0x06,
    SWING_H_LEFT: 0x09,
    SWING_H_MIDDLE_LEFT: 0x0A,
    SWING_H_MIDDLE_RIGHT: 0x0B,
    SWING_H_RIGHT: 0x0C,
}

PRESET_NONE = "none"
PRESET_BOOST = "boost"
PRESET_SILENT = "Silent"
PRESET_MODES: Final = (PRESET_NONE, PRESET_BOOST, PRESET_SILENT)
PROFILE_CODES: Final = {
    PRESET_NONE: 0x00,
    PRESET_SILENT: 0x01,
    PRESET_BOOST: 0x20,
}


class Variant:
    """One Panasonic model: the template bytes it differs in."""

    def __init__(
        self,
        key: str,
        reversed_temperature: bool = False,
        horizontal_swing: bool = False,
        fixed_bytes: dict | None = None,
    ) -> None:
        """Initialize the variant."""

        self.key = key
        # EKE transmits the temperature nibble bit-reversed.
        self.reversed_temperature = reversed_temperature
        # Only DKE lets the remote aim the horizontal louver.
        self.horizontal_swing = horizontal_swing
        self.fixed_bytes = fixed_bytes or {}


DKE: Final = Variant(
    "dke", horizontal_swing=True, fixed_bytes={23: 0x01, 25: 0x06}
)
EKE: Final = Variant("eke", reversed_temperature=True)
JKE: Final = Variant("jke")
NKE: Final = Variant("nke", fixed_bytes={17: 0x06})
LKE: Final = Variant("lke", fixed_bytes={17: 0x06, 13: 0x02})

VARIANTS: Final = {v.key: v for v in (DKE, JKE, NKE, LKE, EKE)}


class PanasonicCommand(Command):
    """Raw 27-byte Panasonic command, sent as two bursts."""

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


def _bit_reverse(value: int) -> int:
    """Reverse the bits of a byte."""

    return int(f"{value & 0xFF:08b}"[::-1], 2)


def build_frame_bytes(
    variant: Variant,
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
    preset_mode: str = PRESET_NONE,
) -> bytes:
    """Return the 27-byte frame for the requested state."""

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
    if preset_mode not in PROFILE_CODES:
        raise ValueError(f"Unknown preset mode: {preset_mode}")

    frame = bytearray(TEMPLATE)
    for index, value in variant.fixed_bytes.items():
        frame[index] = value

    temperature = (temperature_c << 1) & 0xFF
    frame[14] = _bit_reverse(temperature) if variant.reversed_temperature else temperature
    if variant.horizontal_swing:
        frame[17] = SWING_H_CODES[swing_horizontal_mode]

    frame[13] |= MODE_CODES[mode] | (POWER_ON if power_on else POWER_OFF)
    frame[16] = FAN_CODES[fan_mode] | SWING_CODES[swing_mode]
    frame[21] = PROFILE_CODES[preset_mode]
    frame[26] = (CHECKSUM_SEED + sum(frame[:26])) & 0xFF

    return bytes(frame)


def build_command(
    variant: Variant,
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
    preset_mode: str = PRESET_NONE,
) -> PanasonicCommand:
    """Build an IR command for the HA infrared platform."""

    frame = build_frame_bytes(
        variant,
        mode,
        temperature_c,
        power_on,
        fan_mode,
        swing_mode,
        swing_horizontal_mode,
        preset_mode=preset_mode,
    )
    return PanasonicCommand(frame_to_timings(frame))


def frame_to_timings(frame: bytes) -> list:
    """Convert a frame to signed timings: two bursts split after byte 8."""

    timings: list = []
    for start, end in ((0, FIRST_BURST), (FIRST_BURST, len(frame))):
        if start:
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
