# [Custom Integration] Climate IR — air conditioners over Home Assistant's native infrared platform, protocol-modular

Air conditioners that only speak infrared are still everywhere, and the 2026.4 **native infrared platform** finally gave Home Assistant a proper place to put them: emitter integrations expose the hardware, device integrations send through it. `lg_infrared` is the example in the dev blog. This is that second role, for air conditioners, across manufacturers.

→ **https://github.com/skolodziej/Climate-IR**

## How this differs from what you may already use

Worth saying up front, because there is real overlap:

- **SmartIR** and **AR Smart IR** replay recorded IR code sets from JSON files, and they cover a lot of devices between them. Climate IR **encodes the protocol** instead. The practical difference shows up when your exact model is not in the database: with a code set you are stuck, or recording hundreds of frames by hand — a climate device has a frame for every combination of mode, temperature, fan and swing. With an encoder, one protocol description covers the whole family and every combination is generated.
- **ESPHome's `climate_ir` platform** (confusingly close name — sorry, I picked mine before I found theirs) does encode protocols, but **on the ESP**. This does it in Home Assistant, so it works with any emitter the `infrared` platform exposes — ESPHome proxies, Broadlink, Tuya/Zosung Zigbee blasters through the IR wrapper — with no firmware to flash and no YAML.

If you already have a setup that works, there is no reason to move. This is for people who want the AC as a normal config-flow integration on the native platform, and for models nobody has a code set for.

## Supported families

**Mitsubishi Heavy** — ZSA/Avanti, FD-series cassette (PJZ502A030D), SRK ZJ-S, ZMP, ZEA
**Mitsubishi Electric** — MSZ-FD/FE/FA/KJ, MSY, MSC, SEZ-KDXX
**Daikin** · **Panasonic** (DKE/JKE/NKE/LKE/EKE) · **Midea** · **Toshiba** · **Fujitsu** · **Hitachi**

22 families, 8 manufacturers. You pick the family in the first setup step; the entity then only offers what that family can actually encode — fan speeds, swing axes, presets and temperature range all differ.

## The honest part, and the ask

**Two of the 22 families have been confirmed against real hardware** — the ZSA/Avanti series and the FD-series cassette I built this for. One more, SRK ZJ-S, is *capture-checked*: it reproduces 156 frames recorded from a physical remote (decoded out of SmartIR's MIT-licensed database, which turns out to be an excellent independent test corpus) byte for byte.

The rest follow a reference description exactly and **have never been checked at all**. That is stated in the README table, in the integration itself, and the family picker appends "untested" to those labels so nobody picks one believing it was tried.

So: **if you own any of these and can spend ten minutes, that is by far the most useful thing anyone can contribute.** Point it at your unit, see whether it responds, tell me what happened. A "nothing at all" is as useful as a "works" — it tells me where a protocol description is wrong.

An IR *receiver* makes it much better still: capture what your original remote sends, and we can compare it against what the integration generates bit for bit. That is how the FD-series went from a guess to verified.

## Adding a protocol

Deliberately made cheap, because that is the whole point of the structure. A frame builder, a profile class naming what your family supports, one line in a registry. Contract tests then run against it automatically — they check that every mode, fan speed, swing position and preset the profile advertises can actually be encoded.

Walkthrough: [docs/adding-a-protocol.md](https://github.com/skolodziej/Climate-IR/blob/main/docs/adding-a-protocol.md)

## Requirements and install

- Home Assistant 2026.4+ and a native `infrared` emitter entity
- HACS → Custom repositories → `https://github.com/skolodziej/Climate-IR` → Integration
- **Carrier frequency matters.** Most families are 38 kHz; the MHI FD series is 36 kHz. A blaster fixed at the wrong one produces perfectly correct timings and no response, which is a miserable thing to debug.

## Credits

Started as a fork of [mattbyte/MHI-IR-Climate](https://github.com/mattbyte/MHI-IR-Climate), which contributed the ZSA support and the original encoder.

Protocol descriptions for the other families were read from [ToniA/arduino-heatpumpir](https://github.com/ToniA/arduino-heatpumpir). That project is GPL-2.0 and this one is MIT, so it is used strictly as documentation — timings, bit positions and value codes are functional facts, and every implementation here is written from scratch. No code or byte template was copied.
