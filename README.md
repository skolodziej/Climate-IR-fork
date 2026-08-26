# MHI IR Climate

![MHI IR Climate logo](custom_components/mhi_ir_climate/brand/logo.png)

[![Validate](https://github.com/skolodziej/MHI-IR-Climate/actions/workflows/validate.yml/badge.svg)](https://github.com/skolodziej/MHI-IR-Climate/actions/workflows/validate.yml)
[![Tests](https://github.com/skolodziej/MHI-IR-Climate/actions/workflows/tests.yml/badge.svg)](https://github.com/skolodziej/MHI-IR-Climate/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

MHI IR Climate is a Home Assistant custom integration for controlling Mitsubishi Heavy Industries air conditioners through Home Assistant's native `infrared` platform.

It creates a normal Home Assistant `climate` entity for an IR-only air conditioner and sends complete Mitsubishi Heavy Industries IR state frames through a selected infrared emitter. It is designed to work with native infrared emitters, including entities provided by [IR Wrapper for Zigbee IR Blasters](https://github.com/tomer2526/IR-Wrapper-for-Zigbee-IR-Bluster).

Two indoor unit families are supported. They use completely different IR protocols, so you pick the family when you add the integration:

| Family | Typical units | Remote | Carrier | Frame |
|---|---|---|---|---|
| **ZSA / Avanti** | wall-mounted SRK/DXK ZSA | RLA502A700L, RLA502A720 | 38 kHz | 19 bytes |
| **FD series** | commercial cassettes such as FDTC40VH | PJZ502A030D (RCN-TC-5AW-E3 set) | 36 kHz | 160 bits |

The FD protocol is documented in [docs/fd-series-protocol.md](docs/fd-series-protocol.md).

## ✅ What You Need

- Home Assistant 2026.4.0 or newer.
- A native Home Assistant `infrared` emitter entity in the room with the air conditioner.
- For Tuya/Zosung-style Zigbee IR blasters, install and configure [IR Wrapper for Zigbee IR Blasters](https://github.com/tomer2526/IR-Wrapper-for-Zigbee-IR-Bluster) first.
- A supported indoor unit: a ZSA/Avanti model using the 19-byte command frame, or an FD-series unit driven by a PJZ502A030D remote.
- For FD-series units, an emitter that can transmit at **36 kHz**. Blasters hard-wired to 38 kHz will not reach the unit.

## 🧪 Tested Hardware

This integration was built from decoded IR captures for:

- Mitsubishi Heavy Industries DXK09ZSA-W with remote RLA502A720.
- Mitsubishi Heavy Industries SRK35ZSA-W with remote RLA502A700L.
- Mitsubishi Heavy Industries FDTC40VH cassette with remote PJZ502A030D.
- Tuya/Zosung-style Zigbee IR blasters exposed to Home Assistant as native infrared emitters.
- Broadlink RM4 Mini IR blaster through the official Home Assistant Broadlink integration.

## 🚀 Installation With HACS

1. In Home Assistant, open **HACS**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/mattbyte/MHI-IR-Climate`.
4. Select **Integration** as the category.
5. Download **MHI IR Climate**.
6. Restart Home Assistant.
7. Go to **Settings** -> **Devices & services** -> **Add integration** and search for **MHI IR Climate**.

## ⚙️ Configuration

Add one integration entry per air conditioner.

The first step asks for the **indoor unit family**. This selects the IR protocol and cannot be changed afterwards; add a new entry if you picked the wrong one.

The second step asks for:

- **Name**: The climate entity name, such as `Living AC`.
- **Infrared emitter**: The native `infrared` emitter entity in the same room.
- **Base IR frame** (ZSA/Avanti only): A 19-byte hexadecimal base frame. Most users should leave the default:

```text
52aec31ae5f609f807ff004db25aa5ff007f80
```

- **Room temperature sensor**: Optional sensor shown as the climate current temperature.
- **Room humidity sensor**: Optional sensor shown as the climate current humidity.

The device model shown in Home Assistant follows the selected family: **MHI ZSA Series (Avanti)** or **MHI FD Series (PJZ502A030D)**.

Existing configuration entries from before the FD support was added stay on the ZSA profile and keep working unchanged.

If a configured infrared emitter, temperature sensor, or humidity sensor is removed or renamed, Home Assistant raises a repair issue for the affected MHI IR Climate entry. Open the integration's **Configure** options to select a valid replacement or clear an optional sensor.

## 🕹️ Features

Both families:

- Adds a Home Assistant `climate` entity from the UI.
- Links each climate entity to a selected native `infrared` emitter entity.
- Supports `off`, `cool`, `heat`, `dry`, `fan only`, and `heat/cool` HVAC modes.
- Supports target temperatures from 18 C to 30 C in 1 C steps.
- Supports fan speeds: `Auto`, `Very Low`, `Low`, `Medium`, and `High`.
- Restores the last HVAC mode, target temperature, fan mode, preset, and swing mode after Home Assistant restarts.

### ZSA / Avanti

- Supports `Boost`, `Eco`, `Silent`, and `Night Setback` climate presets. Eco is available in every active mode except fan only, while `Night Setback` switches the entity to heat mode before sending the IR command.
- Clears `Boost` in Home Assistant state after 15 minutes without sending another IR command.
- Keeps `Eco` active without a timeout and uses the unit's Eco fan override while preserving the selected fan speed in Home Assistant.
- Supports vertical swing modes: `3D Auto`, `Stop`, `0 Deg`, `30 Deg`, `45 Deg`, `60 Deg`, `90 Deg`, and `Moving`.
- Supports horizontal swing modes: `3D Auto`, `Stop`, `Hard Left`, `Left`, `Straight`, `Right`, `Hard Right`, `Wide`, `Narrow`, and `Moving`.
- Keeps `3D Auto` coupled across both swing axes, while restoring the other axis to its last non-3D mode when a normal swing mode is selected.
- Exits `3D Auto` when `Boost` or `Eco` is enabled and rejects `3D Auto` requests while either preset remains active.
- Falls back to the last non-3D swing modes, or `Stop` when unknown, when `dry` or `fan only` mode is active because `3D Auto` is not available in those modes.
- Uses `dry` mode with the auto fan speed, matching the remote.

### FD series

- Sends 160-bit frames on a 36 kHz carrier, with both complement blocks generated for the unit's integrity check.
- Supports `Boost` (High Power), `Eco`, `Silent`, and `Night Setback` presets. `Boost` and `Eco` are available in `cool`, `heat`, and `heat/cool`; `Silent` and `Night Setback` work in every active mode.
- `Eco` writes the setpoint the remote forces for the current mode (28 C cooling, 22 C heating, 25 C in heat/cool) and, like the remote, keeps that setpoint when the preset is cleared.
- `Boost` transmits the mode's extreme value (16 C cooling, 30 C heating) while leaving the Home Assistant setpoint untouched, because the unit restores it when High Power ends.
- Setting a target temperature while `Boost` or `Eco` is active clears the preset, since the remote refuses temperature input in those states.
- Supports one swing axis: `Swing` plus the four fixed louver positions `Up`, `Up-Middle`, `Down-Middle`, and `Down`. Turning `Swing` on keeps the last selected position in the frame, as the remote does.
- Keeps the selected fan speed in `dry` mode.

## 🧰 Device Controls

The integration also adds configuration entities on the device page. Which ones appear depends on the selected family.

Both families:

- **Force send IR command** button for resending the current Home Assistant state when the physical unit and Home Assistant are out of sync.

ZSA / Avanti only:

- **Power LED brightness** select: `Dim`, `Normal`, and `Off`.
- **Installation position** select: `Left`, `Centre`, and `Right`. This command can only be sent while the air conditioner is off.
- **Auto clean** switch, including clean-cycle turn-off commands for cool, dry, and heat/cool modes.

FD series only:

- **Reset filter sign** button, which sends one frame with the filter reset bit set.

## 📡 How It Works

IR-controlled air conditioners usually expect every command to describe the whole desired state, not just the changed setting. When you change mode, temperature, fan, swing, preset, or a supported device setting, this integration builds a complete MHI frame and sends it as raw infrared timings through Home Assistant's `infrared.async_send_command` helper.

For Zosung/Tuya Zigbee IR blasters, the companion Zigbee IR wrapper receives those raw timings and converts them into the `ir_code_to_send` payload required by Zigbee2MQTT or ZHA.

## ⚠️ Current Limitations

- Only captured command mappings are implemented, for the two families listed above.
- IR is one-way. The climate entity is optimistic and restores its last known state, but it cannot confirm what the physical air conditioner actually did.
- On FD-series units, Night Setback was captured with the power bit cleared. The integration sends the bit with whatever power state Home Assistant holds; verify the behaviour on your unit before relying on it.
- On FD-series units, `Boost` in `heat/cool` is allowed but was never captured, and the cassette's four air outlets cannot be addressed individually.
- On FD-series units, `Silent`, `Night Setback`, `Boost`, and `Eco` are independent bits that the physical remote can combine. A Home Assistant preset is single-select, so the integration sends one at a time; the frame builder itself supports any combination.

## 🛠️ Development Notes

Each family has its own self-contained frame builder, and `profiles.py` pairs each one with the capabilities the Home Assistant entities should expose, so the platforms stay free of protocol branching:

- `custom_components/mhi_ir_climate/ir_protocol.py` — ZSA/Avanti, based on decoded IR captures and the original working pyscript encoder.
- `custom_components/mhi_ir_climate/fd_protocol.py` — FD series, documented in [docs/fd-series-protocol.md](docs/fd-series-protocol.md).

Both keep the MHI frame manipulation local to this integration and leave IR transport and Zigbee payload encoding to Home Assistant's native infrared emitter layer.

Run the tests with:

```bash
python -m unittest discover -s tests
```

`tests/test_fd_protocol.py` rebuilds all 24 captured FD frames from the builder and cross-checks its capture table against the one in `docs/fd-series-protocol.md`, so both an encoding change and a transcription slip fail immediately.
