"""Contract tests every registered protocol profile has to satisfy.

These run against `protocols.all_profiles()`, so a family added later is held
to the same rules without anyone remembering to write tests for it. A failure
here means the profile would misbehave in the entity, not that the encoding is
wrong -- the per-family capture tests cover that.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parent))

from ha_stubs import HVACMode, protocols  # noqa: E402

PRESET_NONE = "none"


def _config_for(profile) -> dict:
    """Build the config entry a profile says it needs."""

    return {field.key: field.default for field in profile.config_fields()}


class ProtocolContractTest(unittest.TestCase):
    """Rules that hold for every family."""

    def setUp(self) -> None:
        self.profiles = list(protocols.all_profiles())
        self.assertTrue(self.profiles, "no profiles registered")

    def test_identity_is_present_and_unique(self) -> None:
        keys = [profile.key for profile in self.profiles]
        self.assertEqual(len(keys), len(set(keys)), "profile keys must be unique")

        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                self.assertTrue(profile.key)
                self.assertEqual(profile.key, profile.key.lower())
                self.assertTrue(profile.name, "needs a label for the picker")
                self.assertTrue(profile.device_model)
                self.assertTrue(profile.manufacturer)

    def test_registry_resolves_every_key(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                self.assertIs(protocols.get_profile(profile.key), profile)

        self.assertIs(
            protocols.get_profile(None),
            protocols.get_profile(protocols.DEFAULT_PROTOCOL),
            "entries without a protocol key must resolve to the default",
        )
        self.assertIs(
            protocols.get_profile("nonexistent"),
            protocols.get_profile(protocols.DEFAULT_PROTOCOL),
        )

    def test_vocabularies_contain_their_defaults(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                self.assertIn(HVACMode.OFF, profile.hvac_modes)

                if profile.fan_modes:
                    self.assertIn(profile.default_fan_mode, profile.fan_modes)
                if profile.swing_modes:
                    self.assertIn(profile.default_swing_mode, profile.swing_modes)
                if profile.swing_horizontal_modes:
                    self.assertIn(
                        profile.default_swing_horizontal_mode,
                        profile.swing_horizontal_modes,
                    )

                self.assertIn(PRESET_NONE, profile.preset_modes)
                self.assertIn(profile.default_preset_mode, profile.preset_modes)

    def test_temperature_range_is_sane(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                self.assertLess(profile.min_temperature, profile.max_temperature)
                self.assertGreaterEqual(
                    profile.default_temperature, profile.min_temperature
                )
                self.assertLessEqual(
                    profile.default_temperature, profile.max_temperature
                )
                self.assertGreater(profile.temperature_step, 0)

    def test_presets_normalize_to_themselves(self) -> None:
        for profile in self.profiles:
            for preset in profile.preset_modes:
                with self.subTest(profile=profile.key, preset=preset):
                    self.assertEqual(profile.normalize_preset_mode(preset), preset)

    def test_none_preset_is_always_available(self) -> None:
        for profile in self.profiles:
            for hvac_mode in profile.hvac_modes:
                with self.subTest(profile=profile.key, hvac_mode=hvac_mode):
                    self.assertTrue(profile.preset_available(PRESET_NONE, hvac_mode))

    def test_temperature_locking_presets_are_declared_presets(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                for preset in profile.temperature_locking_presets:
                    self.assertIn(preset, profile.preset_modes)

    def test_control_keys_are_unique_and_defaults_valid(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                controls = list(profile.controls())
                keys = [control.key for control in controls]
                self.assertEqual(len(keys), len(set(keys)))

                for control in controls:
                    self.assertTrue(control.key)
                    self.assertTrue(control.name)
                    if isinstance(control, protocols.SelectControl):
                        self.assertIn(control.default, control.options)

    def test_config_fields_do_not_collide_with_core_keys(self) -> None:
        reserved = {"name", "protocol", "emitter_entity_id",
                    "temperature_sensor", "humidity_sensor"}
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                for field in profile.config_fields():
                    self.assertNotIn(field.key, reserved)
                    self.assertTrue(field.key)

    def test_default_config_passes_the_profiles_own_validation(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                self.assertEqual(profile.validate_config(_config_for(profile)), {})

    def test_adjust_state_is_idempotent(self) -> None:
        """Reconciling twice must not differ from reconciling once."""

        for profile in self.profiles:
            for hvac_mode in profile.hvac_modes:
                with self.subTest(profile=profile.key, hvac_mode=hvac_mode):
                    once = protocols.EntityState(
                        hvac_mode=hvac_mode,
                        temperature=profile.default_temperature,
                        fan_mode=profile.default_fan_mode,
                        preset_mode=profile.default_preset_mode,
                        swing_mode=profile.default_swing_mode,
                        swing_horizontal_mode=profile.default_swing_horizontal_mode,
                    )
                    profile.adjust_state(once)
                    twice = protocols.EntityState(**vars(once))
                    profile.adjust_state(twice)
                    self.assertEqual(vars(once), vars(twice))

    def test_build_command_covers_the_declared_surface(self) -> None:
        """Every declared value must actually encode."""

        for profile in self.profiles:
            config = _config_for(profile)
            options = {
                control.key: control.default
                for control in profile.controls()
                if getattr(control, "default", None) is not None
            }

            cases = [("temperature", value) for value in
                     (profile.min_temperature, profile.max_temperature)]
            cases += [("fan_mode", value) for value in profile.fan_modes]
            cases += [("swing_mode", value) for value in profile.swing_modes]
            cases += [
                ("swing_horizontal_mode", value)
                for value in profile.swing_horizontal_modes
            ]
            # The remembered position may legitimately hold any swing value.
            cases += [
                ("last_swing_mode", value)
                for value in (None, *profile.swing_modes)
            ]

            for hvac_mode in profile.hvac_modes:
                if hvac_mode == HVACMode.OFF:
                    continue
                mode = protocols.hvac_mode_to_protocol_mode(hvac_mode)

                for preset in profile.preset_modes:
                    if not profile.preset_available(preset, hvac_mode):
                        continue
                    cases.append(("preset_mode", preset))

                for attribute, value in cases:
                    with self.subTest(
                        profile=profile.key, hvac_mode=hvac_mode,
                        attribute=attribute, value=value,
                    ):
                        state = protocols.ClimateState(
                            mode=mode,
                            temperature=profile.default_temperature,
                            power_on=True,
                            fan_mode=profile.default_fan_mode,
                            preset_mode=profile.default_preset_mode,
                            swing_mode=profile.default_swing_mode,
                            swing_horizontal_mode=(
                                profile.default_swing_horizontal_mode
                            ),
                            last_swing_mode=None,
                            config=config,
                            options=options,
                        )
                        setattr(state, attribute, value)

                        command = profile.build_command(state)
                        timings = command.get_raw_timings()
                        self.assertTrue(timings)
                        self.assertGreater(command.modulation, 0)

    def test_build_command_encodes_power_off(self) -> None:
        for profile in self.profiles:
            with self.subTest(profile=profile.key):
                state = protocols.ClimateState(
                    mode="cool",
                    temperature=profile.default_temperature,
                    power_on=False,
                    fan_mode=profile.default_fan_mode,
                    preset_mode=profile.default_preset_mode,
                    swing_mode=profile.default_swing_mode,
                    swing_horizontal_mode=profile.default_swing_horizontal_mode,
                    last_swing_mode=None,
                    config=_config_for(profile),
                )
                self.assertTrue(profile.build_command(state).get_raw_timings())

    def test_one_shot_extras_are_accepted(self) -> None:
        """A button's extra must not break frame building."""

        for profile in self.profiles:
            for control in profile.controls():
                extra = getattr(control, "extra", None)
                if extra is None:
                    continue
                with self.subTest(profile=profile.key, extra=extra):
                    state = protocols.ClimateState(
                        mode="cool",
                        temperature=profile.default_temperature,
                        power_on=True,
                        fan_mode=profile.default_fan_mode,
                        preset_mode=profile.default_preset_mode,
                        swing_mode=profile.default_swing_mode,
                        swing_horizontal_mode=(
                            profile.default_swing_horizontal_mode
                        ),
                        last_swing_mode=None,
                        config=_config_for(profile),
                        extras={extra: True},
                    )
                    self.assertTrue(profile.build_command(state).get_raw_timings())


if __name__ == "__main__":
    unittest.main()
