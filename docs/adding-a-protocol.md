# Adding a protocol

Mitsubishi Heavy Industries alone uses several unrelated IR protocols, and the
variation across manufacturers is wider still — the reference collection at
[ToniA/arduino-heatpumpir](https://github.com/ToniA/arduino-heatpumpir) holds
about forty families behind a single `send(power, mode, fan, temperature,
swingV, swingH)` call. Everything past those six values differs per family.

> **Licensing.** That reference is GPL-2.0 and this project is MIT, so it is
> used here as *documentation*: the protocol facts — timings, bit positions,
> value codes — are functional descriptions rather than protectable
> expression, and the implementations in this repository are our own. Do not
> copy code or byte templates out of it verbatim.

This integration is built around that shape. A **profile** owns one remote
family: the vocabularies its entities may offer, the rules the family imposes,
and the encoder that turns state into a frame. The climate entity, the device
controls, and the config flow read all of it from the profile, so adding a
family does not touch them.

## The pieces

| File | Role |
|---|---|
| `protocols/base.py` | The contract: `ClimateProfile`, `ClimateState`, `EntityState`, the control and config descriptors |
| `protocols/__init__.py` | The registry. One tuple lists the vendor packages |
| `protocols/<vendor>/profiles.py` | The vendor's profiles |
| `protocols/<vendor>/<family>_frames.py` | The frame builder, standalone and free of Home Assistant |
| `tests/test_protocol_contract.py` | Contract tests that run against every registered profile |

Keeping the frame builder separate from the profile matters: it can be
imported and tested without Home Assistant, which is what lets the capture
tests run as plain unit tests.

## Step 1: the frame builder

Write a module that turns values into raw timings and nothing else. Model it
on `fd_protocol.py`. It should expose the vocabularies it understands, a build
function, and — if you can receive — a decoder, which makes captures testable
in both directions.

```python
DEFAULT_CARRIER_FREQUENCY = 38_000

class MyCommand(Command):
    def __init__(self, timings, *, modulation=DEFAULT_CARRIER_FREQUENCY,
                 repeat_count=0):
        super().__init__(modulation=modulation, repeat_count=repeat_count)
        self._timings = timings

    def get_raw_timings(self):
        return list(self._timings)


def build_my_ir_command(mode, temperature_c, power_on, fan_mode, ...):
    ...
    return MyCommand(timings)
```

Take the flags apart the way the protocol does, not the way Home Assistant
presents them. The FD unit treats Silent, Eco, High Power and Night Setback as
independent bits and the remote combines them; modelling them as one
single-select preset in the builder made a captured frame impossible to
reproduce. Map onto Home Assistant's single-select preset in the profile.

## Step 2: the profile

```python
class MyProfile(ClimateProfile):
    key = "my_family"
    name = "My family"
    device_model = "Vendor XY Series"

    fan_modes = my_protocol.FAN_MODES
    default_fan_mode = my_protocol.DEFAULT_FAN_MODE
    preset_modes = my_protocol.PRESET_MODES
    swing_modes = my_protocol.SWING_MODES
    min_temperature = 16
    max_temperature = 32

    def normalize_preset_mode(self, preset_mode):
        return my_protocol.normalize_preset_mode(preset_mode)

    def build_command(self, state):
        return my_protocol.build_my_ir_command(
            state.mode,
            state.temperature,
            state.power_on,
            fan_mode=state.fan_mode,
        )
```

Only `key`, `name`, `device_model`, the vocabularies you support,
`normalize_preset_mode` and `build_command` are required. Everything else has
a default that suits a family without that feature: leave `swing_modes` empty
and the entity drops the swing control and its feature flag.

## Step 3: register it

Profiles are grouped by vendor. Add yours to the vendor package's `PROFILES`:

```python
# protocols/mitsubishi_electric/__init__.py
from .profiles import MyProfile

PROFILES = (..., MyProfile)
```

A new vendor is a new package next to the existing ones, listed in `VENDORS`
in `protocols/__init__.py`. That is the whole wiring. The config flow picks the family up in its first
step, labelled from `name` and `device_model` — no translation entry needed.

## The hooks, and when to reach for them

Everything below is optional. Each exists because a real family needed it.

**`config_fields()` / `validate_config()`** — extra config entry fields. ZSA
asks for a 19-byte base frame this way. Return `ConfigField` descriptors; the
config flow renders them, so profiles stay free of voluptuous.

**`controls()`** — device-page entities. Return `SelectControl`,
`SwitchControl` or `ButtonControl`. Persistent controls land in
`ClimateState.options` under their key; a `ButtonControl` sends one command
with its `extra` set in `ClimateState.extras`. `one_shot` and
`requires_power_off` cover a setting the unit only accepts once, or only while
it is off.

**`adjust_state(state)`** — reconcile user-visible state after a change. This
is where family quirks belong. ZSA couples its two swing axes and forces the
auto fan in dry mode here; without it, that logic would sit in the shared
entity and every new family would have to be read against it. `state.changed`
names the attribute the user just touched, so you can react to the change and
not just to the result. **It must be idempotent** — the contract test applies
it twice and compares.

**`preset_available()` / `preset_temperature()` / `hvac_mode_for_preset()`** —
which presets work in which mode, whether a preset owns the setpoint, and
whether a preset forces a mode.

**`swing_mode_error()`** — reject a value with a message instead of silently
correcting it.

**`power_off_extras()`** — one-shot values to attach to the command that
powers the unit off. ZSA starts a clean cycle this way.

**`should_send_after_control_change()`** — whether a changed control needs a
command right now. The default sends while the unit is on.

## Say whether it is verified

`ClimateProfile.verified` defaults to `False`. Leave it there until frames
have been confirmed against real hardware — the family picker appends
"untested" to the label, so nobody picks it believing it was tried. Ten of the
twelve profiles shipped today are in that state: they follow the reference
description exactly, and no one has watched a unit respond.

## Step 4: tests

Two layers, and both matter.

**Contract tests run for free.** `tests/test_protocol_contract.py` iterates
`all_profiles()`, so registering a profile immediately checks that its
defaults are inside its vocabularies, that its presets normalize to
themselves, that its control keys are unique, that `adjust_state` is
idempotent, and that `build_command` encodes every value the profile declares
— every mode, fan speed, swing position, available preset, and both
temperature limits. That last one is the valuable part: it catches a
vocabulary you advertised but cannot encode.

**Capture tests you write yourself.** Record frames from the real remote,
changing exactly one setting at a time, and assert the builder reproduces
them. `tests/test_fdtc_frames.py` does this for all 24 FD captures and also
cross-checks its table against `docs/fd-series-protocol.md`, so a typo in
either fails the suite.

If a second implementation of your protocol exists — ToniA's library is a good
source — pin your encoding to its bit masks as well. Doing that for FD
confirmed every overlapping field and ruled out a systematic misreading that
our own captures could never have exposed on their own.

## Notes from doing this twice

- **Write down what is verified and what is assumed.** Both families have a
  protocol document listing open points. It is what makes a later capture
  session productive instead of exploratory.
- **The complement blocks are not a checksum you can skip.** FD frames carry
  each data block twice, inverted. A receiver may accept a frame with them
  wrong and then do nothing.
- **Carrier frequency is a real failure mode.** FD runs at 36 kHz, ZSA at
  38 kHz. A blaster fixed at the wrong one produces correct timings and no
  response.
- **Do not encode a field the reference remote never writes.** FD bits 13–14
  hold the older remote's fan speed; ours always leaves them at zero, and a
  test now records that on purpose.
