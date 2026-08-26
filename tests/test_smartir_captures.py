"""Check encoders against independently recorded captures.

The frames here were decoded from SmartIR's Broadlink code database, which is
MIT licensed. They are recordings of a physical remote made by someone with
no connection to this project, so reproducing them is real evidence that an
encoder is right -- much stronger than agreeing with the reference
description it was written from.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from ha_stubs import HVACMode, protocols  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


class SmartIRCaptureTest(unittest.TestCase):
    """Every capture must come back byte for byte."""

    def test_mhi_zj_matches_recorded_remote(self) -> None:
        fixture = _load("mhi_zj_smartir.json")
        profile = protocols.get_profile(fixture["profile"])
        self.assertEqual(profile.key, fixture["profile"], "profile went missing")

        for capture in fixture["captures"]:
            with self.subTest(
                mode=capture["mode"],
                fan=capture["fan_mode"],
                temperature=capture["temperature_c"],
            ):
                self._assert_frame(
                    profile,
                    capture,
                    fixture["swing_horizontal_mode"],
                )

    def test_mhi_zj_forces_the_auto_fan_in_dry(self) -> None:
        """The captures show the remote overriding the fan speed in dry."""

        profile = protocols.get_profile("mhi_zj")
        state = protocols.EntityState(
            hvac_mode=HVACMode.DRY,
            temperature=24,
            fan_mode="High",
            preset_mode="none",
            swing_mode="Up",
        )
        profile.adjust_state(state)

        self.assertEqual(state.fan_mode, "Auto")

    def _assert_frame(self, profile, capture: dict, swing_h: str) -> None:
        """Build the frame the way the entity does, reconcile included."""

        entity_state = protocols.EntityState(
            hvac_mode=HVACMode(capture["mode"]),
            temperature=capture["temperature_c"],
            fan_mode=capture["fan_mode"],
            preset_mode=profile.default_preset_mode,
            swing_mode=capture["swing_mode"],
            swing_horizontal_mode=swing_h,
        )
        profile.adjust_state(entity_state)

        command = profile.build_command(
            protocols.ClimateState(
                mode=capture["mode"],
                temperature=entity_state.temperature,
                power_on=True,
                fan_mode=entity_state.fan_mode,
                preset_mode=entity_state.preset_mode,
                swing_mode=entity_state.swing_mode,
                swing_horizontal_mode=entity_state.swing_horizontal_mode,
            )
        )
        self.assertEqual(
            _frame_hex(command.get_raw_timings()), capture["frame"]
        )


def _frame_hex(timings: list) -> str:
    """Decode our own timings back to frame bytes, least significant bit first."""

    bits = [1 if abs(space) > 800 else 0 for space in timings[3::2]]
    return bytes(
        sum(bit << index for index, bit in enumerate(bits[offset:offset + 8]))
        for offset in range(0, len(bits) // 8 * 8, 8)
    ).hex().upper()


if __name__ == "__main__":
    unittest.main()
