# Climate IR

![Climate IR logo](custom_components/climate_ir/brand/logo.png)

[![Validate](https://github.com/skolodziej/Climate-IR/actions/workflows/validate.yml/badge.svg)](https://github.com/skolodziej/Climate-IR/actions/workflows/validate.yml)
[![Tests](https://github.com/skolodziej/Climate-IR/actions/workflows/tests.yml/badge.svg)](https://github.com/skolodziej/Climate-IR/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz/docs/faq/custom_repositories/)

Climate IR is a Home Assistant custom integration for air conditioners that can only be controlled by infrared. It creates a normal `climate` entity and sends complete IR state frames through Home Assistant's native `infrared` platform.

It is built as a **platform rather than one device driver**. Air conditioners speak a bewildering number of unrelated IR protocols — Mitsubishi Heavy alone uses several, and they share nothing but the manufacturer's name. So each remote family lives in its own *profile*, and the climate entity, the device controls, and the setup flow read every vocabulary and rule from that profile. Adding a family is a new file, not a change to the integration.

**[docs/adding-a-protocol.md](docs/adding-a-protocol.md) is the walkthrough for adding one.**

## 📡 Supported families

| Vendor | Model family | Key | Range | Fan | Swing | Presets | Status |
|---|---|---|---|---|---|---|---|
| Mitsubishi Heavy | ZSA Series (Avanti) | `zsa` | 18–30 °C | 5 | V+H | 4 | verified |
| Mitsubishi Heavy | FD Series (PJZ502A030D) | `fd` | 18–30 °C | 5 | V | 4 | verified |
| Mitsubishi Heavy | SRK ZJ-S Series | `mhi_zj` | 18–30 °C | 6 | V+H | — | untested |
| Mitsubishi Heavy | SRK ZMP Series | `mhi_zmp` | 18–30 °C | 6 | V+H | — | untested |
| Mitsubishi Heavy | SRK ZEA Series | `mhi_zea` | 18–30 °C | 7 | V+H | — | untested |
| Mitsubishi Electric | MSZ-FD | `mel_msz_fd` | 16–31 °C | 6 | V+H | — | untested |
| Mitsubishi Electric | MSZ-FE | `mel_msz_fe` | 16–31 °C | 6 | V+H | — | untested |
| Mitsubishi Electric | MSZ-FA | `mel_msz_fa` | 16–31 °C | 6 | V+H | — | untested |
| Mitsubishi Electric | MSZ-KJ | `mel_msz_kj` | 16–31 °C | 6 | V+H | — | untested |
| Mitsubishi Electric | MSY | `mel_msy` | 16–31 °C | 6 | V+H | — | untested |
| Mitsubishi Electric | MSC | `mel_msc` | 16–31 °C | 4 | V | — | untested |
| Mitsubishi Electric | SEZ-KDXX | `mel_sez_kdxx` | 16–31 °C | 3 | — | — | untested |
| Daikin | Daikin (generic) | `daikin` | 18–30 °C | 6 | — | — | untested |
| Panasonic | DKE | `panasonic_dke` | 16–30 °C | 6 | V+H | 2 | untested |
| Panasonic | JKE | `panasonic_jke` | 16–30 °C | 6 | V | 2 | untested |
| Panasonic | NKE | `panasonic_nke` | 16–30 °C | 6 | V | 2 | untested |
| Panasonic | LKE | `panasonic_lke` | 16–30 °C | 6 | V | 2 | untested |
| Panasonic | EKE | `panasonic_eke` | 16–30 °C | 6 | V | 2 | untested |
| Midea | Midea (generic) | `midea` | 17–30 °C | 4 | — | — | untested |
| Toshiba | Toshiba (generic) | `toshiba` | 17–30 °C | 6 | — | — | untested |
| Fujitsu | Fujitsu (generic) | `fujitsu` | 16–30 °C | 4 | V+H | 1 | untested |
| Hitachi | Hitachi (generic) | `hitachi` | 16–32 °C | 5 | V+H | — | untested |

**Status matters.** `verified` means frames were confirmed against the physical unit. `untested` means the encoding follows a reference description exactly, but nobody has watched a unit respond — the family picker labels these accordingly. If you own one and can confirm it, that is the single most useful contribution to this project.

Fan speeds, swing axes, and preset counts differ per family because the remotes differ; the entity only offers what the selected family can actually encode.

## ✅ What you need

- Home Assistant 2026.4.0 or newer.
- A native Home Assistant `infrared` emitter entity in the room with the air conditioner.
- For Tuya/Zosung-style Zigbee IR blasters, install and configure [IR Wrapper for Zigbee IR Blasters](https://github.com/tomer2526/IR-Wrapper-for-Zigbee-IR-Bluster) first.
- An emitter that can transmit at the family's carrier frequency. Most families use 38 kHz; the MHI FD series uses **36 kHz**. A blaster fixed at the wrong frequency produces correct timings and no response, which is a confusing failure to debug.

## 🚀 Installation with HACS

1. In Home Assistant, open **HACS**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add `https://github.com/skolodziej/Climate-IR`, category **Integration**.
4. Download **Climate IR** and restart Home Assistant.
5. Go to **Settings** → **Devices & services** → **Add integration** and search for **Climate IR**.

## ⚙️ Configuration

Add one integration entry per air conditioner.

The first step picks the **indoor unit family**. This selects the IR protocol and cannot be changed afterwards — add a new entry if you picked the wrong one.

The second step asks for:

- **Name**: the climate entity name, such as `Living AC`.
- **Infrared emitter**: the native `infrared` emitter entity in the same room.
- **Room temperature / humidity sensor**: optional, shown as the entity's current values.
- Any field the selected family needs of its own. The ZSA family, for example, asks for a 19-byte base frame; most families ask for nothing extra.

If a configured emitter or sensor is removed or renamed, Home Assistant raises a repair issue for the affected entry.

## 🕹️ What the entity offers

Common to every family:

- `off`, `cool`, `heat`, `dry`, `fan only`, and `heat/cool` HVAC modes.
- A target temperature within the family's range, and the fan speeds and swing positions that family encodes.
- Restores the last mode, temperature, fan, preset, and swing after a Home Assistant restart.

Beyond that, capability is per family. The two verified families are the richest:

**MHI ZSA / Avanti** — `Boost`, `Eco`, `Silent`, and `Night Setback` presets; vertical and horizontal swing with a coupled `3D Auto` across both axes; `Power LED brightness`, `Installation position`, and `Auto clean` device controls, including clean-cycle commands when powering off.

**MHI FD series** — `Boost` (High Power), `Eco`, `Silent`, and `Night Setback`; one swing axis with four fixed louver positions; a `Reset filter sign` button. `Eco` writes the setpoint the remote forces per mode and keeps it when cleared; `Boost` transmits the mode's extreme value without moving the Home Assistant setpoint, because the unit restores it when High Power ends.

Every family also gets a **Force send IR command** button, for when the physical unit and Home Assistant have drifted apart.

## 📡 How it works

IR air conditioners expect every command to describe the whole desired state, not just the changed setting. When you change anything, the integration builds a complete frame for the selected family and sends it as raw timings through `infrared.async_send_command`.

For Zosung/Tuya Zigbee blasters, the companion Zigbee IR wrapper turns those raw timings into the payload Zigbee2MQTT or ZHA expects.

## ⚠️ Limitations

- IR is one-way. The entity is optimistic and restores its last known state, but it cannot confirm what the unit actually did.
- Most families are untested against hardware, as marked above. Only the two Mitsubishi Heavy families have been confirmed on real units.
- On FD-series units, Night Setback was captured with the power bit cleared. The integration sends the bit with whatever power state Home Assistant holds; verify before relying on it.
- `Silent`, `Night Setback`, `Boost` and `Eco` are independent bits on FD units and the remote can combine them. A Home Assistant preset is single-select, so the integration sends one at a time; the frame builder itself supports any combination.

## 🛠️ Development

```
custom_components/climate_ir/
  protocols/
    base.py                 the contract a profile implements
    __init__.py             the registry; one tuple lists the vendor packages
    mitsubishi_heavy/       profiles + frame builders
    mitsubishi_electric/    profiles + frame builders
```

Frame builders are standalone and free of Home Assistant, which is what lets the capture tests run as plain unit tests.

```bash
python -m unittest discover -s tests
```

`tests/test_protocol_contract.py` runs against every registered profile, so a family added later is held to the same rules without anyone writing tests for it: defaults inside their vocabularies, unique control keys, an idempotent reconcile, and a `build_command` that encodes every value the profile advertises.

`tests/test_fdtc_frames.py` rebuilds all 24 captured FD frames from the builder, cross-checks its capture table against `docs/fd-series-protocol.md`, and pins the encoding to the bit masks of an independent implementation.

Brand assets are generated by `scripts/generate_brand.py` rather than committed as opaque binaries.

## 🙏 Credits

Started as a fork of [mattbyte/MHI-IR-Climate](https://github.com/mattbyte/MHI-IR-Climate), which contributed the ZSA/Avanti support and the original frame encoder.

Protocol descriptions for every family beyond ZSA and FD were read from [ToniA/arduino-heatpumpir](https://github.com/ToniA/arduino-heatpumpir). That project is GPL-2.0 and this one is MIT, so it is used strictly as documentation: protocol facts — timings, bit positions, value codes — are functional descriptions rather than protectable expression, and every implementation here is our own. No code or byte template was copied.
