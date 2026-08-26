"""Mitsubishi Heavy Industries FD-series IR command builder.

Covers the PJZ502A030D remote from the RCN-TC-5AW-E3 infrared set, as used by
the commercial FD-series cassette indoor units such as the FDTC40VH.

This is a different protocol from the ZSA/Avanti frames in ``ir_protocol``:
36 kHz carrier, 160 payload bits and a complement-block integrity scheme
instead of the 19-byte ZSA frame. See ``docs/fd-series-protocol.md`` for the
reverse-engineering notes this module is built from.
"""

from __future__ import annotations

from typing import Final, Literal

from infrared_protocols.commands import Command

Mode = Literal["cool", "heat", "dry", "fan_only", "heat_cool"]

DEFAULT_CARRIER_FREQUENCY: Final = 36_000
HEADER_MARK_US: Final = 6_000
HEADER_SPACE_US: Final = 7_500
BIT_MARK_US: Final = 500
ZERO_SPACE_US: Final = 1_500
ONE_SPACE_US: Final = 3_500
TRAILER_MARK_US: Final = BIT_MARK_US
TRAILER_SPACE_US: Final = 7_500

BLOCK_BITS: Final = 32
FRAME_BITS: Final = 5 * BLOCK_BITS

MODEL_ID_BITS: Final = "101100000000"
BLOCK5_BITS: Final = "01000000101111110000000000000000"

MIN_TEMPERATURE: Final = 18
MAX_TEMPERATURE: Final = 30
TEMPERATURE_OFFSET: Final = 16
MIN_FIELD_TEMPERATURE: Final = TEMPERATURE_OFFSET
MAX_FIELD_TEMPERATURE: Final = TEMPERATURE_OFFSET + 15

MODE_CODES: Final = {
    "heat_cool": "000",
    "cool": "010",
    "heat": "001",
    "dry": "100",
    "fan_only": "110",
}

FAN_AUTO = "Auto"
FAN_VERY_LOW = "Very Low"
FAN_LOW = "Low"
FAN_MEDIUM = "Medium"
FAN_HIGH = "High"
FAN_MODES: Final = (
    FAN_AUTO,
    FAN_VERY_LOW,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_HIGH,
)
DEFAULT_FAN_MODE: Final = FAN_AUTO
FAN_CODES: Final = {
    "auto": 4,
    "very_low": 0,
    "low": 1,
    "medium": 2,
    "med": 2,
    "high": 3,
}

SWING_SWING = "Swing"
SWING_UP = "Up"
SWING_UP_MIDDLE = "Up-Middle"
SWING_DOWN_MIDDLE = "Down-Middle"
SWING_DOWN = "Down"
SWING_MODES: Final = (
    SWING_SWING,
    SWING_UP,
    SWING_UP_MIDDLE,
    SWING_DOWN_MIDDLE,
    SWING_DOWN,
)
DEFAULT_SWING_MODE: Final = SWING_SWING
DEFAULT_LOUVER_POSITION: Final = SWING_UP
LOUVER_CODES: Final = {
    "up": 0,
    "up_middle": 1,
    "up_1": 1,
    "down_middle": 2,
    "up_2": 2,
    "down": 3,
}

PRESET_NONE = "none"
PRESET_BOOST = "boost"
PRESET_ECO = "eco"
PRESET_SILENT = "Silent"
PRESET_NIGHT_SETBACK = "Night Setback"
PRESET_MODES: Final = (
    PRESET_NONE,
    PRESET_BOOST,
    PRESET_ECO,
    PRESET_SILENT,
    PRESET_NIGHT_SETBACK,
)
DEFAULT_PRESET_MODE: Final = PRESET_NONE
PRESET_KEYS: Final = {
    "none": PRESET_NONE,
    "boost": PRESET_BOOST,
    "powerful": PRESET_BOOST,
    "high_power": PRESET_BOOST,
    "eco": PRESET_ECO,
    "silent": PRESET_SILENT,
    "night_setback": PRESET_NIGHT_SETBACK,
    "setback": PRESET_NIGHT_SETBACK,
}

# The remote refuses temperature input while High Power or Eco is active and
# writes its own setpoint into the temperature field instead.
BOOST_TEMPERATURES: Final = {
    "cool": 16,
    "heat": 30,
}
ECO_TEMPERATURES: Final = {
    "cool": 28,
    "heat": 22,
    "heat_cool": 25,
}


class MHIFDIRCommand(Command):
    """Raw FD-series IR command for the HA infrared platform."""

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


def build_fd_ir_command(
    mode: Mode,
    temperature_c: int,
    power_on: bool,
    fan_mode: str = DEFAULT_FAN_MODE,
    swing_mode: str = DEFAULT_SWING_MODE,
    louver_position: str = DEFAULT_LOUVER_POSITION,
    silent: bool = False,
    night_setback: bool = False,
    high_power: bool = False,
    eco: bool = False,
    filter_reset: bool = False,
) -> MHIFDIRCommand:
    """Build an FD-series IR command for Home Assistant's infrared helpers."""

    bits = build_frame_bits(
        mode,
        temperature_c,
        power_on,
        fan_mode=fan_mode,
        swing_mode=swing_mode,
        louver_position=louver_position,
        silent=silent,
        night_setback=night_setback,
        high_power=high_power,
        eco=eco,
        filter_reset=filter_reset,
    )
    return MHIFDIRCommand(bits_to_timings(bits))


def build_frame_bits(
    mode: Mode,
    temperature_c: int,
    power_on: bool,
    fan_mode: str = DEFAULT_FAN_MODE,
    swing_mode: str = DEFAULT_SWING_MODE,
    louver_position: str = DEFAULT_LOUVER_POSITION,
    silent: bool = False,
    night_setback: bool = False,
    high_power: bool = False,
    eco: bool = False,
    filter_reset: bool = False,
) -> str:
    """Return the 160-bit FD frame for the requested state.

    Bits are returned in transmission order, MSB of each block first.

    Silent, Night Setback, High Power and Eco are independent bits on the
    unit, and the remote does combine them, so they are taken as separate
    flags here. Mapping them onto Home Assistant's single-select preset is
    left to the profile layer.
    """

    if mode not in MODE_CODES:
        raise ValueError(f"mode must be one of {sorted(MODE_CODES)}")

    forced = forced_temperature(mode, high_power=high_power, eco=eco)
    temperature = int(temperature_c if forced is None else forced)
    if not MIN_FIELD_TEMPERATURE <= temperature <= MAX_FIELD_TEMPERATURE:
        raise ValueError(
            f"temperature_c must be {MIN_FIELD_TEMPERATURE}"
            f"..{MAX_FIELD_TEMPERATURE}"
        )

    swing, louver_code = _pick_swing_codes(swing_mode, louver_position)
    fan_code = _pick_fan_code(fan_mode)

    block1 = (
        MODEL_ID_BITS  # 1-12   model identifier
        + "00"  # 13-14  unknown
        + _bit(swing)  # 15     swing
        + _bit(filter_reset)  # 16     filter reset
        + _lsb_bits(temperature - TEMPERATURE_OFFSET, 4)  # 17-20  temperature
        + MODE_CODES[mode]  # 21-23  operating mode
        + _bit(power_on)  # 24     power
        + "0000"  # 25-28  unknown
        + _lsb_bits(louver_code, 2)  # 29-30  louver position
        + "00"  # 31-32  unknown
    )
    block3 = (
        _lsb_bits(fan_code, 3)  # 65-67  fan speed
        + "00000"  # 68-72  unknown
        + "1"  # 73     unknown
        + "000000"  # 74-79  unknown
        + _bit(silent)  # 80     silent
        + "001010"  # 81-86  unknown
        + _bit(high_power)  # 87     high power
        + _bit(eco)  # 88     eco
        + _bit(night_setback)  # 89     night setback
        + "0000000"  # 90-96  unknown
    )

    if len(block1) != BLOCK_BITS or len(block3) != BLOCK_BITS:
        raise ValueError("FD data blocks must be 32 bits each")

    return block1 + _invert(block1) + block3 + _invert(block3) + BLOCK5_BITS


def forced_temperature(
    mode: str,
    high_power: bool = False,
    eco: bool = False,
) -> int | None:
    """Return the setpoint the remote writes for High Power or Eco, if any."""

    if high_power:
        return BOOST_TEMPERATURES.get(mode)
    if eco:
        return ECO_TEMPERATURES.get(mode)
    return None


def bits_to_timings(bits: str) -> list:
    """Convert a bit string to signed raw timings in microseconds."""

    timings = [HEADER_MARK_US, -HEADER_SPACE_US]
    for bit in bits:
        timings.append(BIT_MARK_US)
        timings.append(-ONE_SPACE_US if bit == "1" else -ZERO_SPACE_US)
    timings.append(TRAILER_MARK_US)
    timings.append(-TRAILER_SPACE_US)
    timings.append(TRAILER_MARK_US)
    return timings


def decode_frame_bits(timings: list) -> str:
    """Decode received raw timings back into a bit string.

    Receiver modules shorten the mark and lengthen the space by the same
    amount, so only the space length is evaluated.
    """

    body = timings[2:]
    bits = []
    for index in range(0, len(body) - 1, 2):
        space = abs(body[index + 1])
        if space > 6_000:
            break
        bits.append("1" if space > 2_500 else "0")
    return "".join(bits)


def normalize_preset_mode(preset_mode: str) -> str:
    """Normalize a preset name to its canonical FD preset."""

    normalized = str(preset_mode).strip().lower().replace("-", "_").replace(" ", "_")
    if normalized not in PRESET_KEYS:
        raise ValueError(f"Unknown preset mode: {preset_mode}")
    return PRESET_KEYS[normalized]


def normalize_swing_mode(swing_mode: str) -> str:
    """Normalize a swing or louver name to a lookup key."""

    normalized = str(swing_mode).strip().lower()
    normalized = normalized.replace("/", "_").replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def _normalize_fan_mode(fan_mode: str) -> str:
    normalized = str(fan_mode).strip().lower()
    normalized = normalized.replace("/", "_").replace("-", "_").replace(" ", "_")
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized


def _pick_fan_code(fan_mode: str) -> int:
    normalized = _normalize_fan_mode(fan_mode)
    if normalized not in FAN_CODES:
        raise ValueError(f"Unknown fan mode: {fan_mode}")
    return FAN_CODES[normalized]


def _pick_louver_code(louver_position: str) -> int:
    normalized = normalize_swing_mode(louver_position)
    if normalized not in LOUVER_CODES:
        raise ValueError(f"Unknown louver position: {louver_position}")
    return LOUVER_CODES[normalized]


def _pick_swing_codes(swing_mode: str, louver_position: str) -> tuple:
    """Return the swing flag and the louver position it is combined with."""

    if normalize_swing_mode(swing_mode) == "swing":
        return True, _pick_louver_code(louver_position or DEFAULT_LOUVER_POSITION)

    return False, _pick_louver_code(swing_mode)


def _bit(value: object) -> str:
    return "1" if value else "0"


def _lsb_bits(value: int, width: int) -> str:
    """Return a multi-bit field, least significant bit transmitted first."""

    return "".join(str((value >> index) & 1) for index in range(width))


def _invert(bits: str) -> str:
    return "".join("1" if bit == "0" else "0" for bit in bits)
