"""Entity-state tests for the Eco and Boost 3D Auto rules."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).parent))

from ha_stubs import HVACMode, HomeAssistantError, climate  # noqa: E402


class EcoClimateEntityTest(unittest.IsolatedAsyncioTestCase):
    """Verify Eco availability, persistence, and swing conflicts."""

    def _entity(self):
        entry = SimpleNamespace(unique_id="test", entry_id="test")
        data = {
            "config": {
                climate.CONF_EMITTER_ENTITY_ID: "infrared.test",
                climate.CONF_BASE_FRAME_HEX: (
                    "52aec31ae5f609f807ff004db25aa5ff007f80"
                ),
                "name": "Test AC",
            }
        }
        entity = climate.MHIIRClimateEntity(object(), entry, data)
        entity._async_send_current_state = AsyncMock()
        return entity

    async def test_eco_availability_and_no_timeout(self) -> None:
        for hvac_mode in (
            HVACMode.COOL,
            HVACMode.HEAT,
            HVACMode.DRY,
            HVACMode.HEAT_COOL,
        ):
            with self.subTest(hvac_mode=hvac_mode):
                entity = self._entity()
                entity._attr_hvac_mode = hvac_mode
                await entity.async_set_preset_mode("Eco")
                self.assertEqual(entity._attr_preset_mode, "eco")
                self.assertIsNone(entity._cancel_boost_reset)

        for hvac_mode in (HVACMode.OFF, HVACMode.FAN_ONLY):
            with self.subTest(hvac_mode=hvac_mode):
                entity = self._entity()
                entity._attr_hvac_mode = hvac_mode
                with self.assertRaises(HomeAssistantError):
                    await entity.async_set_preset_mode("Eco")
                self.assertEqual(entity._attr_preset_mode, "none")
                entity._async_send_current_state.assert_not_awaited()

    async def test_eco_survives_supported_mode_and_clears_in_fan_only(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL
        entity._attr_swing_mode = "Stop"
        entity._attr_swing_horizontal_mode = "Stop"
        await entity.async_set_preset_mode("Eco")

        await entity.async_set_hvac_mode(HVACMode.DRY)
        self.assertEqual(entity._attr_preset_mode, "eco")
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        self.assertEqual(entity._attr_preset_mode, "eco")
        await entity.async_set_hvac_mode(HVACMode.FAN_ONLY)
        self.assertEqual(entity._attr_preset_mode, "none")

        entity._attr_hvac_mode = HVACMode.COOL
        await entity.async_set_preset_mode("eco")
        await entity.async_set_hvac_mode(HVACMode.OFF)
        self.assertEqual(entity._attr_preset_mode, "none")

    async def test_eco_preserves_selected_fan_mode_in_entity_state(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL
        entity._attr_fan_mode = "High"

        await entity.async_set_preset_mode("eco")
        self.assertEqual(entity._attr_fan_mode, "High")

        await entity.async_set_fan_mode("Low")
        self.assertEqual(entity._attr_fan_mode, "Low")
        self.assertEqual(entity._attr_preset_mode, "eco")

    async def test_enabling_eco_or_boost_exits_3d_auto(self) -> None:
        for preset_mode in ("eco", "boost"):
            with self.subTest(preset_mode=preset_mode):
                entity = self._entity()
                entity._attr_hvac_mode = HVACMode.COOL
                entity._last_swing_mode = "30 Deg"
                entity._last_swing_horizontal_mode = "Left"

                await entity.async_set_preset_mode(preset_mode)

                self.assertEqual(entity._attr_swing_mode, "30 Deg")
                self.assertEqual(entity._attr_swing_horizontal_mode, "Left")
                if preset_mode == "boost":
                    self.assertIsNotNone(entity._cancel_boost_reset)
                else:
                    self.assertIsNone(entity._cancel_boost_reset)

    async def test_enabling_conflicting_preset_falls_back_to_stop(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL

        await entity.async_set_preset_mode("eco")

        self.assertEqual(entity._attr_swing_mode, "Stop")
        self.assertEqual(entity._attr_swing_horizontal_mode, "Stop")

    async def test_3d_auto_requests_are_rejected_without_sending(self) -> None:
        for preset_mode in ("eco", "boost"):
            with self.subTest(preset_mode=preset_mode):
                entity = self._entity()
                entity._attr_hvac_mode = HVACMode.COOL
                entity._attr_preset_mode = preset_mode
                entity._attr_swing_mode = "30 Deg"
                entity._attr_swing_horizontal_mode = "Left"

                with self.assertRaises(HomeAssistantError):
                    await entity.async_set_swing_mode("3D Auto")
                with self.assertRaises(HomeAssistantError):
                    await entity.async_set_swing_horizontal_mode("3D Auto")

                self.assertEqual(entity._attr_swing_mode, "30 Deg")
                self.assertEqual(entity._attr_swing_horizontal_mode, "Left")
                entity._async_send_current_state.assert_not_awaited()

    async def test_restored_eco_in_dry_mode_is_retained_and_reconciled(self) -> None:
        entity = self._entity()
        previous_state = SimpleNamespace(
            state="dry",
            attributes={
                "temperature": 24,
                "fan_mode": "Low",
                "preset_mode": "Eco",
                "swing_mode": "3D Auto",
                "swing_horizontal_mode": "3D Auto",
            },
        )
        entity.async_get_last_state = AsyncMock(return_value=previous_state)

        await entity._async_restore_previous_state()

        self.assertEqual(entity._attr_hvac_mode, HVACMode.DRY)
        self.assertEqual(entity._attr_preset_mode, "eco")
        self.assertEqual(entity._attr_swing_mode, "Stop")
        self.assertEqual(entity._attr_swing_horizontal_mode, "Stop")
        self.assertIsNone(entity._cancel_boost_reset)


if __name__ == "__main__":
    unittest.main()
