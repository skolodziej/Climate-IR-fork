"""Regression tests for MHI preset frame encoding."""

from __future__ import annotations

import importlib.util
from pathlib import Path
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
    / "mhi_ir_climate"
    / "ir_protocol.py"
)
SPEC = importlib.util.spec_from_file_location(
    "mhi_ir_protocol_under_test", PROTOCOL_PATH
)
assert SPEC is not None and SPEC.loader is not None
ir_protocol = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ir_protocol)


class EcoPresetEncodingTest(unittest.TestCase):
    """Verify Eco encoding against the supplied decoder capture."""

    def _build_frame(self, fan_mode: str, preset_mode: str = "eco") -> bytes:
        return ir_protocol.build_ac_frame_bytes(
            "cool",
            24,
            True,
            ir_protocol.DEFAULT_BASE_FRAME_HEX,
            fan_mode=fan_mode,
            preset_mode=preset_mode,
            swing_ud="Stop",
            swing_lr="Stop",
        )

    def test_eco_matches_captured_frame(self) -> None:
        frame = self._build_frame("Auto")

        self.assertEqual(
            frame.hex().upper(),
            "52AEC31AE5F609F807F9063FC037C8FF007F80",
        )

    def test_eco_overrides_every_selected_fan_speed(self) -> None:
        for fan_mode in ir_protocol.FAN_MODES:
            with self.subTest(fan_mode=fan_mode):
                frame = self._build_frame(fan_mode)
                self.assertEqual(frame[ir_protocol.FAN_BYTE], 0xF9)
                self.assertEqual(frame[ir_protocol.FAN_COMP_BYTE], 0x06)
                self.assertEqual(frame[ir_protocol.PRESET_BYTE], 0xFF)
                self.assertEqual(frame[ir_protocol.PRESET_COMP_BYTE], 0x00)

    def test_eco_normalization_is_case_insensitive(self) -> None:
        self.assertEqual(ir_protocol.normalize_preset_mode("Eco"), "eco")
        self.assertEqual(ir_protocol.normalize_preset_mode("ECO"), "eco")

    def test_existing_preset_encodings_are_unchanged(self) -> None:
        boost = self._build_frame("Auto", "boost")
        silent = self._build_frame("Auto", "Silent")
        night_setback = self._build_frame("Auto", "Night Setback")

        self.assertEqual(
            (boost[ir_protocol.FAN_BYTE], boost[ir_protocol.FAN_COMP_BYTE]),
            (0xF7, 0x08),
        )
        self.assertEqual(
            (silent[ir_protocol.PRESET_BYTE], silent[ir_protocol.PRESET_COMP_BYTE]),
            (0x7F, 0x80),
        )
        self.assertEqual(
            (
                night_setback[ir_protocol.PRESET_BYTE],
                night_setback[ir_protocol.PRESET_COMP_BYTE],
            ),
            (0xBF, 0x40),
        )


if __name__ == "__main__":
    unittest.main()
