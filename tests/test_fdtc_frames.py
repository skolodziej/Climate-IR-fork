"""Regression tests for the Mitsubishi Heavy FD-series (PJZ502A030D) frames.

Every expected value is a capture of the original remote, taken from
``docs/fd-series-protocol.md``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import re
import sys
from types import ModuleType
import unittest


class _Command:
    """Minimal stand-in for infrared_protocols.commands.Command."""

    def __init__(self, **kwargs: int) -> None:
        self.modulation = kwargs.get("modulation")
        self.repeat_count = kwargs.get("repeat_count")


infrared_protocols = ModuleType("infrared_protocols")
commands = ModuleType("infrared_protocols.commands")
commands.Command = _Command
infrared_protocols.commands = commands
sys.modules.setdefault("infrared_protocols", infrared_protocols)
sys.modules.setdefault("infrared_protocols.commands", commands)

PROTOCOL_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "climate_ir"
    / "protocols"
    / "mitsubishi_heavy"
    / "fdtc_frames.py"
)
SPEC = importlib.util.spec_from_file_location("mhi_fd_protocol_under_test", PROTOCOL_PATH)
assert SPEC is not None and SPEC.loader is not None
fd_protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fd_protocol)

BLOCK5 = "01000000101111110000000000000000"

# (label, builder kwargs, expected block 1, expected block 3)
CAPTURES = (
    (
        "off, 18C, auto, fan auto, louver up",
        dict(mode="heat_cool", temperature_c=18, power_on=False, swing_mode="Up"),
        "10110000000000000100000000000000",
        "00100000100000000010100000000000",
    ),
    (
        "on, 19C, cool",
        dict(mode="cool", temperature_c=19, power_on=True, swing_mode="Up"),
        "10110000000000001100010100000000",
        "00100000100000000010100000000000",
    ),
    (
        "on, 19C, heat",
        dict(mode="heat", temperature_c=19, power_on=True, swing_mode="Up"),
        "10110000000000001100001100000000",
        "00100000100000000010100000000000",
    ),
    (
        "on, 19C, dry",
        dict(mode="dry", temperature_c=19, power_on=True, swing_mode="Up"),
        "10110000000000001100100100000000",
        "00100000100000000010100000000000",
    ),
    (
        "on, 19C, fan only",
        dict(mode="fan_only", temperature_c=19, power_on=True, swing_mode="Up"),
        "10110000000000001100110100000000",
        "00100000100000000010100000000000",
    ),
    (
        "fan speed 2",
        dict(
            mode="fan_only",
            temperature_c=19,
            power_on=True,
            fan_mode="Low",
            swing_mode="Up",
        ),
        "10110000000000001100110100000000",
        "10000000100000000010100000000000",
    ),
    (
        "fan speed 4",
        dict(
            mode="fan_only",
            temperature_c=19,
            power_on=True,
            fan_mode="High",
            swing_mode="Up",
        ),
        "10110000000000001100110100000000",
        "11000000100000000010100000000000",
    ),
    (
        "louver down",
        dict(mode="fan_only", temperature_c=19, power_on=True, swing_mode="Down"),
        "10110000000000001100110100001100",
        "00100000100000000010100000000000",
    ),
    (
        "swing on, last louver down",
        dict(
            mode="fan_only",
            temperature_c=19,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000101100110100001100",
        "00100000100000000010100000000000",
    ),
    (
        "18C, fan only, swing, down, silent",
        dict(
            mode="fan_only",
            temperature_c=18,
            power_on=True,
            silent=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100100110100001100",
        "00100000100000010010100000000000",
    ),
    (
        # Silent stays set from the previous capture: the unit treats the two
        # as independent bits.
        "night setback with silent, power off",
        dict(
            mode="fan_only",
            temperature_c=18,
            power_on=False,
            silent=True,
            night_setback=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100100110000001100",
        "00100000100000010010100010000000",
    ),
    (
        "30C, fan only, swing, down",
        dict(
            mode="fan_only",
            temperature_c=30,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100111110100001100",
        "00100000100000000010100000000000",
    ),
    (
        "filter reset",
        dict(
            mode="fan_only",
            temperature_c=30,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
            filter_reset=True,
        ),
        "10110000000000110111110100001100",
        "00100000100000000010100000000000",
    ),
    (
        "cool, high power forces 16C",
        dict(
            mode="cool",
            temperature_c=25,
            power_on=True,
            high_power=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100000010100001100",
        "00100000100000000010101000000000",
    ),
    (
        "cool, eco forces 28C",
        dict(
            mode="cool",
            temperature_c=25,
            power_on=True,
            eco=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100011010100001100",
        "00100000100000000010100100000000",
    ),
    (
        "cool, eco off keeps 28C",
        dict(
            mode="cool",
            temperature_c=28,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100011010100001100",
        "00100000100000000010100000000000",
    ),
    (
        "heat, 28C",
        dict(
            mode="heat",
            temperature_c=28,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100011001100001100",
        "00100000100000000010100000000000",
    ),
    (
        "heat, eco forces 22C",
        dict(
            mode="heat",
            temperature_c=28,
            power_on=True,
            eco=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100110001100001100",
        "00100000100000000010100100000000",
    ),
    (
        "heat, eco off keeps 22C",
        dict(
            mode="heat",
            temperature_c=22,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100110001100001100",
        "00100000100000000010100000000000",
    ),
    (
        "auto, eco forces 25C",
        dict(
            mode="heat_cool",
            temperature_c=20,
            power_on=True,
            eco=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000101001000100001100",
        "00100000100000000010100100000000",
    ),
    (
        "auto, eco off keeps 25C",
        dict(
            mode="heat_cool",
            temperature_c=25,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000101001000100001100",
        "00100000100000000010100000000000",
    ),
    (
        "cool, 25C, high power off",
        dict(
            mode="cool",
            temperature_c=25,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000101001010100001100",
        "00100000100000000010100000000000",
    ),
    (
        "heat, high power forces 30C",
        dict(
            mode="heat",
            temperature_c=25,
            power_on=True,
            high_power=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000100111001100001100",
        "00100000100000000010101000000000",
    ),
    (
        "heat, 25C, high power off",
        dict(
            mode="heat",
            temperature_c=25,
            power_on=True,
            swing_mode="Swing",
            louver_position="Down",
        ),
        "10110000000000101001001100001100",
        "00100000100000000010100000000000",
    ),
)


def _invert(bits: str) -> str:
    return "".join("1" if bit == "0" else "0" for bit in bits)


class FDFrameEncodingTest(unittest.TestCase):
    """Verify the FD frame builder against the captured remote frames."""

    def test_captured_frames_match(self) -> None:
        for label, kwargs, block1, block3 in CAPTURES:
            with self.subTest(capture=label):
                bits = fd_protocol.build_frame_bits(**kwargs)

                self.assertEqual(len(bits), 160)
                self.assertEqual(bits[0:32], block1)
                self.assertEqual(bits[32:64], _invert(block1))
                self.assertEqual(bits[64:96], block3)
                self.assertEqual(bits[96:128], _invert(block3))
                self.assertEqual(bits[128:160], BLOCK5)

    def test_temperature_table_is_mode_independent(self) -> None:
        for mode in ("cool", "fan_only"):
            for temperature in range(18, 31):
                with self.subTest(mode=mode, temperature=temperature):
                    bits = fd_protocol.build_frame_bits(
                        mode,
                        temperature,
                        True,
                        swing_mode="Up",
                    )
                    field = bits[16:20]
                    value = sum(
                        int(bit) << index for index, bit in enumerate(field)
                    )
                    self.assertEqual(value + 16, temperature)

    def test_fan_speed_order(self) -> None:
        expected = {
            "Very Low": 0,
            "Low": 1,
            "Medium": 2,
            "High": 3,
            "Auto": 4,
        }
        for fan_mode, value in expected.items():
            with self.subTest(fan_mode=fan_mode):
                bits = fd_protocol.build_frame_bits(
                    "cool",
                    24,
                    True,
                    fan_mode=fan_mode,
                    swing_mode="Up",
                )
                field = bits[64:67]
                decoded = sum(int(bit) << index for index, bit in enumerate(field))
                self.assertEqual(decoded, value)

    def test_louver_positions(self) -> None:
        expected = {"Up": 0, "Up-Middle": 1, "Down-Middle": 2, "Down": 3}
        for swing_mode, value in expected.items():
            with self.subTest(swing_mode=swing_mode):
                bits = fd_protocol.build_frame_bits(
                    "cool", 24, True, swing_mode=swing_mode
                )
                self.assertEqual(bits[14], "0")
                field = bits[28:30]
                decoded = sum(int(bit) << index for index, bit in enumerate(field))
                self.assertEqual(decoded, value)

    def test_swing_keeps_last_louver_position(self) -> None:
        bits = fd_protocol.build_frame_bits(
            "cool",
            24,
            True,
            swing_mode="Swing",
            louver_position="Down-Middle",
        )

        self.assertEqual(bits[14], "1")
        self.assertEqual(bits[28:30], "01")

    def test_preset_normalization_is_case_insensitive(self) -> None:
        for value in ("Eco", "ECO", "eco"):
            with self.subTest(value=value):
                self.assertEqual(
                    fd_protocol.normalize_preset_mode(value), "eco"
                )
        self.assertEqual(
            fd_protocol.normalize_preset_mode("night setback"), "Night Setback"
        )
        with self.assertRaises(ValueError):
            fd_protocol.normalize_preset_mode("turbo")

    def test_timings_round_trip_through_decoder(self) -> None:
        bits = fd_protocol.build_frame_bits(
            "cool", 24, True, silent=True, swing_mode="Swing"
        )
        timings = fd_protocol.bits_to_timings(bits)

        self.assertEqual(len(timings), 325)
        self.assertEqual(timings[0], 6_000)
        self.assertEqual(timings[1], -7_500)
        self.assertEqual(timings[-3:], [500, -7_500, 500])
        self.assertEqual(fd_protocol.decode_frame_bits(timings), bits)

    def test_command_uses_36_khz_carrier(self) -> None:
        command = fd_protocol.build_fd_ir_command("cool", 24, True)

        self.assertEqual(command.modulation, 36_000)
        self.assertEqual(command.repeat_count, 0)
        self.assertEqual(len(command.get_raw_timings()), 325)

    def test_capture_table_matches_the_protocol_document(self) -> None:
        """The table here and the one in the docs must not drift apart."""

        document = (
            Path(__file__).parents[1] / "docs" / "fd-series-protocol.md"
        ).read_text()
        row = re.compile(
            r"^\|\s*(\d+)\s*\|[^|]+\|\s*`([01]{32})`\s*\|\s*`([01]{32})`\s*\|",
            re.M,
        )
        documented = [
            (int(number), block1, block3)
            for number, block1, block3 in row.findall(document)
        ]

        self.assertEqual(
            [number for number, _, _ in documented],
            list(range(1, len(documented) + 1)),
            "captures in the document must be numbered without gaps",
        )
        self.assertEqual(
            [(block1, block3) for _, block1, block3 in documented],
            [(block1, block3) for _, _, block1, block3 in CAPTURES],
        )

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            fd_protocol.build_frame_bits("turbo", 24, True)
        with self.assertRaises(ValueError):
            fd_protocol.build_frame_bits("cool", 15, True)
        with self.assertRaises(ValueError):
            fd_protocol.build_frame_bits("cool", 32, True)
        with self.assertRaises(ValueError):
            fd_protocol.build_frame_bits("cool", 24, True, fan_mode="Turbo")
        with self.assertRaises(ValueError):
            fd_protocol.build_frame_bits("cool", 24, True, swing_mode="Sideways")


# Bit masks taken from ToniA/arduino-heatpumpir's MitsubishiHeavyFDTCHeatpumpIR,
# which drives FDTCxxVF units with the older PJA502A704AA remote. It is an
# independent implementation of the same frame, so pinning the encoding to it
# guards against a systematic misreading of our own captures.
TONIA_MODE_MASKS = {
    "heat_cool": 0x00,
    "dry": 0x10,
    "cool": 0x20,
    "heat": 0x40,
    "fan_only": 0x30,
}
TONIA_LOUVER_MASKS = {
    "Up": 0x00,
    "Up-Middle": 0x10,
    "Down-Middle": 0x20,
    "Down": 0x30,
}
TONIA_MODE_FIELD = 0x70
TONIA_POWER_MASK = 0x80
TONIA_TEMPERATURE_FIELD = 0x0F
TONIA_LOUVER_FIELD = 0x30
TONIA_SWING_MASK = 0x40
TONIA_FILTER_MASK = 0x80


def _block1_bytes(bits: str) -> list:
    """Return block 1 as ToniA sees it: four bytes, each transmitted LSB first."""

    return [
        sum(int(bit) << index for index, bit in enumerate(bits[offset:offset + 8]))
        for offset in range(0, 32, 8)
    ]


class ToniACrossCheckTest(unittest.TestCase):
    """Check the encoding against a second, independent implementation."""

    def _bytes(self, **kwargs) -> list:
        kwargs.setdefault("mode", "cool")
        kwargs.setdefault("temperature_c", 24)
        kwargs.setdefault("power_on", True)
        kwargs.setdefault("swing_mode", "Up")
        return _block1_bytes(fd_protocol.build_frame_bits(**kwargs))

    def test_mode_field_matches(self) -> None:
        for mode, mask in TONIA_MODE_MASKS.items():
            with self.subTest(mode=mode):
                byte2 = self._bytes(mode=mode)[2]
                self.assertEqual(byte2 & TONIA_MODE_FIELD, mask)

    def test_power_bit_matches(self) -> None:
        self.assertEqual(self._bytes(power_on=True)[2] & TONIA_POWER_MASK, 0x80)
        self.assertEqual(self._bytes(power_on=False)[2] & TONIA_POWER_MASK, 0x00)

    def test_temperature_nibble_matches(self) -> None:
        for temperature in range(18, 31):
            with self.subTest(temperature=temperature):
                byte2 = self._bytes(temperature_c=temperature)[2]
                self.assertEqual(
                    byte2 & TONIA_TEMPERATURE_FIELD,
                    (temperature - 16) & 0x0F,
                )

    def test_louver_field_matches(self) -> None:
        for swing_mode, mask in TONIA_LOUVER_MASKS.items():
            with self.subTest(swing_mode=swing_mode):
                byte3 = self._bytes(swing_mode=swing_mode)[3]
                self.assertEqual(byte3 & TONIA_LOUVER_FIELD, mask)

    def test_swing_and_filter_bits_match(self) -> None:
        idle = self._bytes()[1]
        self.assertEqual(idle & TONIA_SWING_MASK, 0x00)
        self.assertEqual(idle & TONIA_FILTER_MASK, 0x00)

        swinging = self._bytes(swing_mode="Swing", louver_position="Up")[1]
        self.assertEqual(swinging & TONIA_SWING_MASK, TONIA_SWING_MASK)

        filtering = self._bytes(filter_reset=True)[1]
        self.assertEqual(filtering & TONIA_FILTER_MASK, TONIA_FILTER_MASK)

    def test_model_identifier_byte(self) -> None:
        """The document records 0x0D for this remote, 0x0A/0x0B for ToniA's."""

        self.assertEqual(self._bytes()[0], 0x0D)

    def test_legacy_fan_speed_field_is_left_alone(self) -> None:
        """This remote never writes the older fan field in bits 13-14."""

        for fan_mode in fd_protocol.FAN_MODES:
            with self.subTest(fan_mode=fan_mode):
                self.assertEqual(self._bytes(fan_mode=fan_mode)[1] & 0x30, 0x00)


if __name__ == "__main__":
    unittest.main()
