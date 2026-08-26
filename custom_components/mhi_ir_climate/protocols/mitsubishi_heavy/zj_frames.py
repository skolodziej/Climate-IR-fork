"""Mitsubishi Heavy 11-byte frame family: SRK ZJ, ZMP and ZEA.

Protocol facts (timings, byte layout, value codes) were read from the
`MitsubishiHeavyHeatpumpIR` module of ToniA/arduino-heatpumpir, which is
GPL-2.0. Only the factual description of the protocol is used here; the
implementation is our own.

Unverified: no capture from real hardware was available for these three
variants. The encoding follows the reference description exactly, but nobody
has confirmed a unit responds.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_200
HEADER_SPACE_US: Final = 1_600
BIT_MARK_US: Final = 400
ZERO_SPACE_US: Final = 400
ONE_SPACE_US: Final = 1_200

MIN_TEMPERATURE: Final = 18
MAX_TEMPERATURE: Final = 30

MODE_CODES: Final = {
    "heat_cool": 0x07,
    "heat": 0x03,
    "cool": 0x06,
    "dry": 0x05,
    "fan_only": 0x04,
}
POWER_ON: Final = 0x00
POWER_OFF: Final = 0x08

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_VERY_HIGH = "Very High"
FAN_ECONO = "Econo"
FAN_HI_POWER = "Hi Power"

SWING_STOP = "Stop"
SWING_SWING = "Swing"
SWING_UP = "Up"
SWING_UP_MIDDLE = "Up-Middle"
SWING_MIDDLE = "Middle"
SWING_DOWN_MIDDLE = "Down-Middle"
SWING_DOWN = "Down"

SWING_H_STOP = "Stop"
SWING_H_SWING = "Swing"
SWING_H_MIDDLE = "Middle"
SWING_H_LEFT = "Left"
SWING_H_MIDDLE_LEFT = "Middle-Left"
SWING_H_MIDDLE_RIGHT = "Middle-Right"
SWING_H_RIGHT = "Right"
SWING_H_LEFT_RIGHT = "Left-Right"
SWING_H_RIGHT_LEFT = "Right-Left"
SWING_H_3D_AUTO = "3D Auto"


class Variant:
    """One 11-byte variant: its template and its value tables."""

    def __init__(
        self,
        key: str,
        template: tuple,
        fan_codes: dict,
        swing_codes: dict,
        swing_h_codes: dict,
        clean_off: int,
        mode_overrides: dict | None = None,
        wide_swing_h: bool = False,
    ) -> None:
        """Initialize the variant."""

        self.key = key
        self.template = template
        self.fan_codes = fan_codes
        self.swing_codes = swing_codes
        self.swing_h_codes = swing_h_codes
        self.clean_off = clean_off
        self.mode_overrides = mode_overrides or {}
        # ZEA packs the horizontal direction across two nibbles.
        self.wide_swing_h = wide_swing_h


ZJ: Final = Variant(
    key="zj",
    template=(0x52, 0xAE, 0xC3, 0x26, 0xD9, 0x11, 0x00, 0x07, 0x00, 0x00, 0x00),
    fan_codes={
        FAN_AUTO: 0xE0,
        FAN_LOW: 0xA0,
        FAN_MEDIUM: 0x80,
        FAN_HIGH: 0x60,
        FAN_HI_POWER: 0x40,
        FAN_ECONO: 0x00,
    },
    swing_codes={
        SWING_STOP: 0x1A,
        SWING_SWING: 0x0A,
        SWING_UP: 0x02,
        SWING_UP_MIDDLE: 0x18,
        SWING_MIDDLE: 0x10,
        SWING_DOWN_MIDDLE: 0x08,
        SWING_DOWN: 0x00,
    },
    swing_h_codes={
        SWING_H_STOP: 0xCC,
        SWING_H_SWING: 0x4C,
        SWING_H_MIDDLE: 0x48,
        SWING_H_LEFT: 0xC8,
        SWING_H_MIDDLE_LEFT: 0x88,
        SWING_H_MIDDLE_RIGHT: 0x08,
        SWING_H_RIGHT: 0xC4,
        SWING_H_LEFT_RIGHT: 0x84,
        SWING_H_RIGHT_LEFT: 0x44,
        SWING_H_3D_AUTO: 0x04,
    },
    clean_off=0x20,
)

ZMP: Final = Variant(
    key="zmp",
    template=ZJ.template,
    fan_codes={
        FAN_AUTO: 0xE0,
        FAN_LOW: 0xA0,
        FAN_MEDIUM: 0x80,
        FAN_HIGH: 0x60,
        FAN_HI_POWER: 0x20,
        FAN_ECONO: 0x00,
    },
    swing_codes=ZJ.swing_codes,
    swing_h_codes=ZJ.swing_h_codes,
    clean_off=0x20,
    # The ZMP variant uses a different code for fan-only operation.
    mode_overrides={"fan_only": 0xD4},
)

ZEA: Final = Variant(
    key="zea",
    template=(0x52, 0xAE, 0xC3, 0x26, 0xD9, 0xDF, 0x20, 0x07, 0x00, 0x00, 0x00),
    fan_codes={
        FAN_AUTO: 0xE0,
        FAN_LOW: 0xC2,
        FAN_MEDIUM: 0xA4,
        FAN_HIGH: 0x86,
        FAN_VERY_HIGH: 0x68,
        FAN_HI_POWER: 0x2C,
        FAN_ECONO: 0x0E,
    },
    swing_codes={
        SWING_STOP: 0x32,
        SWING_SWING: 0x1A,
        SWING_UP: 0x0E,
        SWING_UP_MIDDLE: 0x31,
        SWING_MIDDLE: 0x25,
        SWING_DOWN_MIDDLE: 0x19,
        SWING_DOWN: 0x0D,
    },
    swing_h_codes={
        SWING_H_STOP: 0xF0,
        SWING_H_SWING: 0xD2,
        SWING_H_MIDDLE: 0xA5,
        SWING_H_LEFT: 0xC3,
        SWING_H_MIDDLE_LEFT: 0xB4,
        SWING_H_MIDDLE_RIGHT: 0x96,
        SWING_H_RIGHT: 0x87,
        SWING_H_LEFT_RIGHT: 0x78,
        SWING_H_RIGHT_LEFT: 0x69,
        SWING_H_3D_AUTO: 0xE1,
    },
    clean_off=0x08,
    wide_swing_h=True,
)

VARIANTS: Final = {variant.key: variant for variant in (ZJ, ZMP, ZEA)}


class MitsubishiHeavyZJCommand(Command):
    """Raw 11-byte Mitsubishi Heavy command."""

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
    variant: Variant,
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
    clean: bool = False,
) -> bytes:
    """Return the 11-byte frame for the requested state."""

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in variant.fan_codes:
        raise ValueError(f"Unknown fan mode: {fan_mode}")
    if swing_mode not in variant.swing_codes:
        raise ValueError(f"Unknown swing mode: {swing_mode}")
    if swing_horizontal_mode not in variant.swing_h_codes:
        raise ValueError(
            f"Unknown horizontal swing mode: {swing_horizontal_mode}"
        )

    frame = bytearray(variant.template)
    mode_code = variant.mode_overrides.get(mode, MODE_CODES[mode])
    fan = variant.fan_codes[fan_mode]
    swing_v = variant.swing_codes[swing_mode]
    swing_h = variant.swing_h_codes[swing_horizontal_mode]
    clean_code = 0x00 if clean else variant.clean_off
    temperature = (~((temperature_c - 17) << 4)) & 0xF0

    if variant.wide_swing_h:
        frame[5] |= (swing_h & 0xF0) | ((swing_v >> 1) & 0x01) | clean_code
        frame[7] |= (fan & 0xE0) | ((swing_v >> 1) & 0x18)
    else:
        frame[5] |= swing_h | (swing_v & 0x02) | clean_code
        frame[7] |= fan | (swing_v & 0x18)

    frame[9] |= mode_code | (POWER_ON if power_on else POWER_OFF) | temperature

    # No checksum; three bytes carry the inverse of their predecessor.
    frame[6] = ~frame[5] & 0xFF
    frame[8] = ~frame[7] & 0xFF
    frame[10] = ~frame[9] & 0xFF

    return bytes(frame)


def build_command(
    variant: Variant,
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
    clean: bool = False,
) -> MitsubishiHeavyZJCommand:
    """Build an IR command for the HA infrared platform."""

    frame = build_frame_bytes(
        variant,
        mode,
        temperature_c,
        power_on,
        fan_mode,
        swing_mode,
        swing_horizontal_mode,
        clean=clean,
    )
    return MitsubishiHeavyZJCommand(frame_to_timings(frame))


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
