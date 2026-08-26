"""Mitsubishi Electric 18-byte frame family: MSZ FD, FE, MSY, FA and KJ.

Protocol facts were read from the `MitsubishiHeatpumpIR` module of
ToniA/arduino-heatpumpir, which is GPL-2.0. Only the factual description of
the protocol is used here; the implementation is our own.

Unverified: no capture from real hardware was available.
"""

from __future__ import annotations

from typing import Final

from infrared_protocols.commands import Command

DEFAULT_CARRIER_FREQUENCY: Final = 38_000
HEADER_MARK_US: Final = 3_500
HEADER_SPACE_US: Final = 1_700
BIT_MARK_US: Final = 430
ZERO_SPACE_US: Final = 390
ONE_SPACE_US: Final = 1_250
MESSAGE_SPACE_US: Final = 17_500

MIN_TEMPERATURE: Final = 16
MAX_TEMPERATURE: Final = 31

TEMPLATE: Final = (
    0x23, 0xCB, 0x26, 0x01, 0x00, 0x20, 0x48, 0x00, 0x00,
    0x00, 0x61, 0x00, 0x00, 0x00, 0x10, 0x40, 0x00, 0x00,
)

POWER_ON: Final = 0x20
POWER_OFF: Final = 0x00

FAN_AUTO = "Auto"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_VERY_HIGH = "Very High"
FAN_QUIET = "Quiet"
FAN_CODES: Final = {
    FAN_AUTO: 0x00,
    FAN_LOW: 0x01,
    FAN_MEDIUM: 0x02,
    FAN_HIGH: 0x03,
    FAN_VERY_HIGH: 0x04,
    FAN_QUIET: 0x05,
}

SWING_AUTO = "Auto"
SWING_SWING = "Swing"
SWING_UP = "Up"
SWING_UP_MIDDLE = "Up-Middle"
SWING_MIDDLE = "Middle"
SWING_DOWN_MIDDLE = "Down-Middle"
SWING_DOWN = "Down"

SWING_H_AUTO = "Auto"
SWING_H_SWING = "Swing"
SWING_H_LEFT = "Left"
SWING_H_MIDDLE_LEFT = "Middle-Left"
SWING_H_MIDDLE = "Middle"
SWING_H_MIDDLE_RIGHT = "Middle-Right"
SWING_H_RIGHT = "Right"
SWING_H_CODES: Final = {
    SWING_H_AUTO: 0x00,
    SWING_H_SWING: 0xC0,
    SWING_H_LEFT: 0x10,
    SWING_H_MIDDLE_LEFT: 0x20,
    SWING_H_MIDDLE: 0x30,
    SWING_H_MIDDLE_RIGHT: 0x40,
    SWING_H_RIGHT: 0x50,
}

_STANDARD_MODES: Final = {
    "heat_cool": 0x20,
    "heat": 0x08,
    "cool": 0x18,
    "dry": 0x10,
    "fan_only": 0x38,
}
_FA_MODES: Final = {
    "heat_cool": 0x60,
    "heat": 0x48,
    "cool": 0x58,
    "dry": 0x50,
    "fan_only": 0x38,
}
_STANDARD_SWING: Final = {
    SWING_AUTO: 0x40,
    SWING_SWING: 0x78,
    SWING_UP: 0x48,
    SWING_UP_MIDDLE: 0x50,
    SWING_MIDDLE: 0x58,
    SWING_DOWN_MIDDLE: 0x60,
    SWING_DOWN: 0x68,
}
_FA_SWING: Final = {
    **_STANDARD_SWING,
    SWING_DOWN_MIDDLE: 0x58,
    SWING_DOWN: 0x60,
}


class Variant:
    """One MSZ model: its value tables and template tweaks."""

    def __init__(
        self,
        key: str,
        mode_codes: dict,
        swing_codes: dict,
        cleared_bytes: tuple = (),
    ) -> None:
        """Initialize the variant."""

        self.key = key
        self.mode_codes = mode_codes
        self.swing_codes = swing_codes
        # Bytes this model zeroes in the template.
        self.cleared_bytes = cleared_bytes


FD: Final = Variant("fd", _STANDARD_MODES, _STANDARD_SWING)
FE: Final = Variant("fe", _STANDARD_MODES, _STANDARD_SWING)
MSY: Final = Variant("msy", _STANDARD_MODES, _STANDARD_SWING, cleared_bytes=(14, 15))
FA: Final = Variant("fa", _FA_MODES, _FA_SWING, cleared_bytes=(10, 15))
KJ: Final = Variant("kj", _STANDARD_MODES, _STANDARD_SWING, cleared_bytes=(15,))

VARIANTS: Final = {v.key: v for v in (FD, FE, MSY, FA, KJ)}


class MitsubishiElectricMSZCommand(Command):
    """Raw 18-byte Mitsubishi Electric command, transmitted twice."""

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
) -> bytes:
    """Return the 18-byte frame for the requested state."""

    if mode not in variant.mode_codes:
        raise ValueError(f"mode must be one of {sorted(variant.mode_codes)}")
    if not MIN_TEMPERATURE <= temperature_c <= MAX_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_TEMPERATURE}..{MAX_TEMPERATURE}"
        )
    if fan_mode not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")
    if swing_mode not in variant.swing_codes:
        raise ValueError(f"Unknown swing mode: {swing_mode}")
    if swing_horizontal_mode not in SWING_H_CODES:
        raise ValueError(
            f"Unknown horizontal swing mode: {swing_horizontal_mode}"
        )

    frame = bytearray(TEMPLATE)
    for index in variant.cleared_bytes:
        frame[index] = 0x00

    frame[5] = POWER_ON if power_on else POWER_OFF
    frame[6] = variant.mode_codes[mode]
    frame[7] = temperature_c - 16
    frame[8] = SWING_H_CODES[swing_horizontal_mode]
    frame[9] = FAN_CODES[fan_mode] | variant.swing_codes[swing_mode]
    # Byte 10 carries the remote's clock. Nothing reads it back, so it stays
    # at whatever the template holds.
    frame[17] = sum(frame[:17]) & 0xFF

    return bytes(frame)


def build_command(
    variant: Variant,
    mode: str,
    temperature_c: int,
    power_on: bool,
    fan_mode: str,
    swing_mode: str,
    swing_horizontal_mode: str,
) -> MitsubishiElectricMSZCommand:
    """Build an IR command for the HA infrared platform."""

    frame = build_frame_bytes(
        variant,
        mode,
        temperature_c,
        power_on,
        fan_mode,
        swing_mode,
        swing_horizontal_mode,
    )
    return MitsubishiElectricMSZCommand(frame_to_timings(frame))


def frame_to_timings(frame: bytes) -> list:
    """Convert a frame to signed timings. The burst is sent twice."""

    timings: list = []
    for burst in range(2):
        if burst:
            timings.append(-MESSAGE_SPACE_US)
        timings.append(HEADER_MARK_US)
        timings.append(-HEADER_SPACE_US)
        for byte in frame:
            for position in range(8):
                timings.append(BIT_MARK_US)
                timings.append(
                    -ONE_SPACE_US if (byte >> position) & 1 else -ZERO_SPACE_US
                )
        timings.append(BIT_MARK_US)

    return timings
