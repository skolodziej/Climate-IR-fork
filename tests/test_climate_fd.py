"""Entity-state tests for the FD-series (PJZ502A030D) profile."""

from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).parent))

from ha_stubs import (  # noqa: E402
    ClimateEntityFeature,
    HVACMode,
    HomeAssistantError,
    climate,
    fd_protocol,
    infrared,
)


def _field(bits: str, start: int, width: int) -> int:
    """Decode a multi-bit field that is transmitted least significant bit first."""

    return sum(int(bit) << index for index, bit in enumerate(bits[start:start + width]))


class FDClimateEntityTest(unittest.IsolatedAsyncioTestCase):
    """Verify the FD profile drives the entity and the frames it sends."""

    def setUp(self) -> None:
        infrared.async_send_command = AsyncMock()

    def _entity(self, **overrides: object):
        entry = SimpleNamespace(unique_id="test", entry_id="test")
        data = {
            "config": {
                climate.CONF_EMITTER_ENTITY_ID: "infrared.test",
                climate.CONF_PROTOCOL: "fd",
                "name": "Cassette",
                **overrides,
            }
        }
        return climate.MHIIRClimateEntity(object(), entry, data)

    def _sent_bits(self) -> str:
        self.assertTrue(infrared.async_send_command.await_count)
        command = infrared.async_send_command.await_args.args[2]
        return fd_protocol.decode_frame_bits(command.get_raw_timings())

    async def test_entity_exposes_fd_capabilities(self) -> None:
        entity = self._entity()

        self.assertEqual(entity._attr_fan_modes, list(fd_protocol.FAN_MODES))
        self.assertEqual(entity._attr_swing_modes, list(fd_protocol.SWING_MODES))
        self.assertEqual(entity._attr_swing_horizontal_modes, [])
        self.assertIsNone(entity._attr_swing_horizontal_mode)
        self.assertNotIn(
            ClimateEntityFeature.SWING_HORIZONTAL_MODE,
            entity._attr_supported_features,
        )
        self.assertIn("FD", entity._attr_device_info["model"])
        self.assertEqual(entity._attr_min_temp, 18)
        self.assertEqual(entity._attr_max_temp, 30)

    async def test_frame_carries_mode_temperature_and_power(self) -> None:
        entity = self._entity()
        entity._attr_target_temperature = 24

        await entity.async_set_hvac_mode(HVACMode.COOL)

        bits = self._sent_bits()
        self.assertEqual(len(bits), 160)
        self.assertEqual(bits[:12], fd_protocol.MODEL_ID_BITS)
        self.assertEqual(_field(bits, 16, 4) + 16, 24)
        self.assertEqual(bits[20:23], fd_protocol.MODE_CODES["cool"])
        self.assertEqual(bits[23], "1")

    async def test_turning_off_keeps_last_mode_and_clears_power(self) -> None:
        entity = self._entity()
        await entity.async_set_hvac_mode(HVACMode.HEAT)
        await entity.async_set_hvac_mode(HVACMode.OFF)

        bits = self._sent_bits()
        self.assertEqual(bits[20:23], fd_protocol.MODE_CODES["heat"])
        self.assertEqual(bits[23], "0")

    async def test_eco_forces_the_setpoint_of_each_mode(self) -> None:
        expected = {
            HVACMode.COOL: 28,
            HVACMode.HEAT: 22,
            HVACMode.HEAT_COOL: 25,
        }
        for hvac_mode, setpoint in expected.items():
            with self.subTest(hvac_mode=hvac_mode):
                entity = self._entity()
                entity._attr_hvac_mode = hvac_mode
                entity._attr_target_temperature = 20

                await entity.async_set_preset_mode("eco")

                self.assertEqual(entity._attr_target_temperature, setpoint)
                bits = self._sent_bits()
                self.assertEqual(_field(bits, 16, 4) + 16, setpoint)
                self.assertEqual(bits[87], "1")

    async def test_eco_setpoint_survives_clearing_the_preset(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL
        entity._attr_target_temperature = 20

        await entity.async_set_preset_mode("eco")
        await entity.async_set_preset_mode("none")

        self.assertEqual(entity._attr_target_temperature, 28)
        bits = self._sent_bits()
        self.assertEqual(_field(bits, 16, 4) + 16, 28)
        self.assertEqual(bits[87], "0")

    async def test_eco_follows_a_mode_change(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL
        await entity.async_set_preset_mode("eco")

        await entity.async_set_hvac_mode(HVACMode.HEAT)

        self.assertEqual(entity._attr_preset_mode, "eco")
        self.assertEqual(entity._attr_target_temperature, 22)

    async def test_eco_and_boost_are_unavailable_in_dry_and_fan_only(self) -> None:
        for preset_mode in ("eco", "boost"):
            for hvac_mode in (HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.OFF):
                with self.subTest(preset_mode=preset_mode, hvac_mode=hvac_mode):
                    entity = self._entity()
                    entity._attr_hvac_mode = hvac_mode

                    with self.assertRaises(HomeAssistantError):
                        await entity.async_set_preset_mode(preset_mode)

                    self.assertEqual(entity._attr_preset_mode, "none")

    async def test_boost_sends_the_extreme_without_moving_the_setpoint(self) -> None:
        expected = {HVACMode.COOL: 16, HVACMode.HEAT: 30}
        for hvac_mode, frame_temperature in expected.items():
            with self.subTest(hvac_mode=hvac_mode):
                entity = self._entity()
                entity._attr_hvac_mode = hvac_mode
                entity._attr_target_temperature = 24

                await entity.async_set_preset_mode("boost")

                self.assertEqual(entity._attr_target_temperature, 24)
                self.assertIsNone(entity._cancel_boost_reset)
                bits = self._sent_bits()
                self.assertEqual(_field(bits, 16, 4) + 16, frame_temperature)
                self.assertEqual(bits[86], "1")

    async def test_setting_a_temperature_releases_a_locking_preset(self) -> None:
        for preset_mode in ("eco", "boost"):
            with self.subTest(preset_mode=preset_mode):
                entity = self._entity()
                entity._attr_hvac_mode = HVACMode.COOL
                await entity.async_set_preset_mode(preset_mode)

                await entity.async_set_temperature(temperature=21)

                self.assertEqual(entity._attr_preset_mode, "none")
                self.assertEqual(entity._attr_target_temperature, 21)
                bits = self._sent_bits()
                self.assertEqual(_field(bits, 16, 4) + 16, 21)

    async def test_silent_and_night_setback_stay_in_the_selected_mode(self) -> None:
        for preset_mode, bit_index in (("Silent", 79), ("Night Setback", 88)):
            with self.subTest(preset_mode=preset_mode):
                entity = self._entity()
                entity._attr_hvac_mode = HVACMode.COOL

                await entity.async_set_preset_mode(preset_mode)

                self.assertEqual(entity._attr_hvac_mode, HVACMode.COOL)
                bits = self._sent_bits()
                self.assertEqual(bits[bit_index], "1")
                self.assertEqual(bits[23], "1")

    async def test_swing_keeps_the_last_louver_position(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL

        await entity.async_set_swing_mode("Down")
        bits = self._sent_bits()
        self.assertEqual(bits[14], "0")
        self.assertEqual(_field(bits, 28, 2), 3)

        await entity.async_set_swing_mode("Swing")
        bits = self._sent_bits()
        self.assertEqual(bits[14], "1")
        self.assertEqual(_field(bits, 28, 2), 3)

    async def test_horizontal_swing_is_rejected(self) -> None:
        entity = self._entity()

        with self.assertRaises(HomeAssistantError):
            await entity.async_set_swing_horizontal_mode("Left")

    async def test_filter_reset_sends_one_frame_with_the_filter_bit(self) -> None:
        entity = self._entity()
        entity._attr_hvac_mode = HVACMode.COOL

        await entity.async_send_filter_reset()

        bits = self._sent_bits()
        self.assertEqual(bits[15], "1")

        await entity.async_force_send_current_state()
        self.assertEqual(self._sent_bits()[15], "0")

    async def test_dry_mode_keeps_the_selected_fan_speed(self) -> None:
        entity = self._entity()
        entity._attr_fan_mode = "High"

        await entity.async_set_hvac_mode(HVACMode.DRY)

        self.assertEqual(entity._attr_fan_mode, "High")
        self.assertEqual(_field(self._sent_bits(), 64, 3), 3)

    async def test_restored_state_recovers_the_louver_position(self) -> None:
        entity = self._entity()
        previous_state = SimpleNamespace(
            state="cool",
            attributes={
                "temperature": 23,
                "fan_mode": "Medium",
                "preset_mode": "Silent",
                "swing_mode": "Down-Middle",
            },
        )
        entity.async_get_last_state = AsyncMock(return_value=previous_state)

        await entity._async_restore_previous_state()

        self.assertEqual(entity._attr_hvac_mode, HVACMode.COOL)
        self.assertEqual(entity._attr_swing_mode, "Down-Middle")
        self.assertEqual(entity._last_louver_position, "Down-Middle")
        self.assertEqual(entity._attr_preset_mode, "Silent")
        self.assertEqual(entity._attr_target_temperature, 23)


class ZSAProfileRegressionTest(unittest.IsolatedAsyncioTestCase):
    """The default profile must keep the ZSA behaviour."""

    def _entity(self):
        entry = SimpleNamespace(unique_id="test", entry_id="test")
        data = {
            "config": {
                climate.CONF_EMITTER_ENTITY_ID: "infrared.test",
                climate.CONF_BASE_FRAME_HEX: "52aec31ae5f609f807ff004db25aa5ff007f80",
                "name": "Living AC",
            }
        }
        return climate.MHIIRClimateEntity(object(), entry, data)

    async def test_entries_without_a_protocol_stay_on_zsa(self) -> None:
        entity = self._entity()

        self.assertEqual(entity._attr_swing_mode, "3D Auto")
        self.assertEqual(entity._attr_swing_horizontal_mode, "3D Auto")
        self.assertIn("ZSA", entity._attr_device_info["model"])
        self.assertIn(
            ClimateEntityFeature.SWING_HORIZONTAL_MODE,
            entity._attr_supported_features,
        )

    async def test_boost_still_times_out_in_home_assistant_state(self) -> None:
        entity = self._entity()
        entity._async_send_current_state = AsyncMock()
        entity._attr_hvac_mode = HVACMode.COOL

        await entity.async_set_preset_mode("boost")

        self.assertIsNotNone(entity._cancel_boost_reset)

    async def test_night_setback_still_switches_to_heat(self) -> None:
        entity = self._entity()
        entity._async_send_current_state = AsyncMock()
        entity._attr_hvac_mode = HVACMode.COOL

        await entity.async_set_preset_mode("Night Setback")

        self.assertEqual(entity._attr_hvac_mode, HVACMode.HEAT)


if __name__ == "__main__":
    unittest.main()
