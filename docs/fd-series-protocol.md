# MHI FD-series IR protocol — PJZ502A030D / FDTC40VH

Reverse engineering of the **PJZ502A030D** infrared remote (from the RCN-TC-5AW-E3
IR set) for the **Mitsubishi Heavy Industries FDTC40VH** cassette indoor unit of the
commercial FD series.

Everything marked *verified* below was derived from captures in which exactly one
setting was changed at a time.

> **Important:** this is *not* the widely implemented "Mitsubishi Heavy 88/152 bit"
> protocol of the residential series (SRK ZJ-S / ZM-S / ZSA) that IRremoteESP8266 and
> various Home Assistant integrations speak — including the ZSA profile in this
> repository. Signature, frame length, timings and carrier frequency are all
> different, and libraries for those series do not work here.

The timings are based on joedirium's description of the related PJA502A704AA remote
(<https://github.com/joedirium/Mitsubishi_Heavy_HVAC_IR>). The bit layout documented
there only partially applies: frame length, fan speed and model identifier differ.

---

## 1. Physical layer

| Parameter | Value |
|---|---|
| Carrier frequency | **36 kHz** (not 38 kHz) |
| Modulation | Pulse distance (constant mark, the space encodes the bit) |
| Header | 6000 µs mark, 7500 µs space |
| Bit 0 | 500 µs mark, 1500 µs space |
| Bit 1 | 500 µs mark, 3500 µs space |
| Trailer | 500 µs mark, 7500 µs space, 500 µs mark |
| Payload | **160 bits** |
| Total duration | approx. 480 ms |
| Repeats | none; one key press sends exactly one frame |

The 36 kHz carrier is the most common stumbling block: a blaster hard-wired to
38 kHz gets no response from the unit even though the timings are correct.

### Raw sequence

```
6000, -7500,
  <per bit>  500, -1500   (bit 0)
             500, -3500   (bit 1)
500, -7500, 500
```

A received signal therefore has **325 values** (2 header + 320 bit values +
3 trailer). Some receivers count 326.

### Receiving notes

Off-the-shelf IR receiver modules shorten the mark and lengthen the space by the
same amount. Typical measurements are 470–505 µs mark and 1485–1520 or
3480–3515 µs space; the sum of mark and space stays constant at 1988 or 3982 µs.
The **space length** is the reliable criterion for decoding, with a threshold at
around 2500 µs.

---

## 2. Frame structure

The 160 bits split into five blocks of 32 bits:

| Block | Bits | Content |
|---|---|---|
| B1 | 1–32 | payload part 1 |
| B2 | 33–64 | **bitwise complement of B1** |
| B3 | 65–96 | payload part 2 |
| B4 | 97–128 | **bitwise complement of B3** |
| B5 | 129–160 | constant, purpose unknown |

The complement blocks are the integrity check; a receiver should verify them and a
sender must generate them. There is no additional checksum.

The remote always sends the **complete state**, never individual key events. Two
different key presses that lead to the same state produce identical frames.

Bit numbering in this document is **1-based**, MSB first in transmission order.
Multi-bit fields are encoded **LSB first**: the first transmitted bit of a field
has the value 1.

---

## 3. Bit layout

### Block 1 (bits 1–32)

| Bits | Field | Encoding | Status |
|---|---|---|---|
| 1–12 | Model identifier | constant `101100000000` | verified (constant across all captures) |
| 13–14 | — | constant `00` | unknown |
| 15 | **Swing** | 0 = off, 1 = louvers swing up/down | verified |
| 16 | **Filter** | 0 = off, 1 = reset filter sign | verified |
| 17–20 | **Target temperature** | LSB first, `temp_C = 16 + value` | verified |
| 21–23 | **Operating mode** | see below | verified |
| 24 | **Power** | 0 = off, 1 = on | verified |
| 25–28 | — | constant `0000` | unknown |
| 29–30 | **Louver position** | LSB first, 0–3 | verified |
| 31–32 | — | constant `00` | unknown |

The model identifier differs from joedirium's PJA502A704AA, which sends
`010100000000`. It is presumably a device class or remote identifier.

### Block 3 (bits 65–96)

| Bits | Field | Encoding | Status |
|---|---|---|---|
| 65–67 | **Fan speed** | LSB first, 0–4 | verified |
| 68–72 | — | constant `00000` | unknown |
| 73 | — | constant `1` | unknown |
| 74–79 | — | constant `000000` | unknown |
| 80 | **Silent** | 0 = off, 1 = on | verified |
| 81–86 | — | constant `001010` | unknown |
| 87 | **High Power** | 0 = off, 1 = on | verified |
| 88 | **Eco** | 0 = off, 1 = on | verified |
| 89 | **Night Setback** | 0 = off, 1 = on | verified |
| 90–96 | — | constant `0000000` | unknown |

### Block 5 (bits 129–160)

Constant `01000000 10111111 00000000 00000000`. The first two bytes are complements
of each other (`0x40` / `0xBF`), which suggests another data field plus its check
byte that none of the functions tested so far ever changed. The 16 trailing zeros
are neither data nor complement.

### Value tables

**Operating mode (bits 21–23, transmission order)**

| Mode | Bits |
|---|---|
| Auto | `000` |
| Cool | `010` |
| Heat | `001` |
| Dry | `100` |
| Fan only | `110` |

**Target temperature (bits 17–20, LSB first)**

`value = temp_C − 16`, valid range **2–14**, which is **18–30 °C**.

Only values 2–14 (18–30 °C) are reachable through the temperature keys; the remote
clamps by itself and re-sends the same frame when "down" is pressed at 18 °C or "up"
at 30 °C. Value 0 (16 °C) still occurs: High Power sets it in cool mode (see
section 4). Whether values 1 and 15 (17 and 31 °C) appear anywhere is untested.

The table was verified in two independent sweeps over the whole range, once in fan
only and once in cool, 14 frames each including both edge cases. The encoding is
mode independent.

| °C | Value | Bits | | °C | Value | Bits |
|---|---|---|---|---|---|---|
| 18 | 2 | `0100` | | 25 | 9 | `1001` |
| 19 | 3 | `1100` | | 26 | 10 | `0101` |
| 20 | 4 | `0010` | | 27 | 11 | `1101` |
| 21 | 5 | `1010` | | 28 | 12 | `0011` |
| 22 | 6 | `0110` | | 29 | 13 | `1011` |
| 23 | 7 | `1110` | | 30 | 14 | `0111` |
| 24 | 8 | `0001` | | | | |

**Fan speed (bits 65–67, LSB first)**

| Speed | Value | Bits | Home Assistant fan mode |
|---|---|---|---|
| 1 | 0 | `000` | Very Low |
| 2 | 1 | `100` | Low |
| 3 | 2 | `010` | Medium |
| 4 | 3 | `110` | High |
| Auto | 4 | `001` | Auto |

**Louver position (bits 29–30, LSB first)**

| Position | Value | Bits | Home Assistant swing mode |
|---|---|---|---|
| top | 0 | `00` | Up |
| top −1 | 1 | `10` | Up-Middle |
| top −2 | 2 | `01` | Down-Middle |
| bottom | 3 | `11` | Down |

While swing is active (bit 15 = 1) the last selected fixed position stays in the
field; the remote does not reset it. The integration mirrors this by remembering the
last position and sending it alongside the swing flag.

---

## 4. Behavioural notes

**Night Setback sends Power = 0.** In the captured Night Setback frame bit 24 is 0
even though the unit was running. Either the remote couples the function to standby,
or the key press also switches off. Verify before relying on it. The integration
sends the bit with whatever power state Home Assistant holds.

**Silent stays set during Night Setback.** Bit 80 was 1 in the night frame as well,
so the two functions do not exclude each other.

**Edge values are clamped, not ignored.** A key press beyond the limit still sends a
complete frame with the unchanged value.

**High Power and Eco are not available in every mode.** Eco cannot be activated in
dry or fan only — the remote sends nothing at all on the key press. High Power is
blocked in fan only as well; whether it is available in dry was not tested.

**High Power writes the extreme value of the mode.** While High Power is active the
remote refuses temperature input and sets the temperature field to the edge value
that requests maximum output:

| Mode | High Power setpoint | Field value |
|---|---|---|
| Cool | 16 °C | 0 |
| Heat | 30 °C | 14 |
| Auto, Dry | untested | — |
| Fan only | High Power unavailable | — |

Value 0 is therefore a real temperature rather than a placeholder — 16 °C is two
steps below what the temperature keys allow.

**High Power restores the previous setpoint.** Deactivating it brings back the
previously set temperature in both tested modes. This is the second difference from
Eco, whose value stays. An implementation does not have to remember the setpoint for
High Power, but it does for Eco.

**Eco forces a fixed setpoint per mode.** While Eco is active the remote refuses
temperature input. On activation it writes a mode-dependent fixed value into the
temperature field:

| Mode | Eco setpoint | Field value |
|---|---|---|
| Cool | 28 °C | 12 |
| Heat | 22 °C | 6 |
| Auto | 25 °C | 9 |
| Dry, Fan only | Eco unavailable | — |

Unlike High Power this is not a sentinel: the value is a real setpoint and **stays
when Eco is switched off**. Verified with six frames — Eco on and off in cool, heat
and auto; the three pairs differ in exactly one bit and the temperature field does
not change when switching off.

The pattern is plausible: Eco raises the setpoint when cooling and lowers it when
heating, reducing output in both cases.

**The setpoint spans modes.** A mode change carries the last set temperature over
unchanged; the remote does not keep separate setpoints per mode.

**High Power and Eco are not persistent.** As soon as another setting is changed both
bits return to 0 and block 3 falls back to its idle value. This only describes the
remote's own state machine — an implementation that always transmits the full state,
like this one, keeps the preset until Home Assistant clears it.

---

## 5. Test vectors

Each bit string is a real capture of the original remote, split by block. B2 and B4
are the complements of the preceding block, B5 is always
`01000000101111110000000000000000`.

| # | State | B1 (bits 1–32) | B3 (bits 65–96) |
|---|---|---|---|
| 1 | off, 18 °C, auto, fan auto, top | `10110000000000000100000000000000` | `00100000100000000010100000000000` |
| 2 | on, 19 °C, cool, fan auto, top | `10110000000000001100010100000000` | `00100000100000000010100000000000` |
| 3 | on, 19 °C, heat | `10110000000000001100001100000000` | `00100000100000000010100000000000` |
| 4 | on, 19 °C, dry | `10110000000000001100100100000000` | `00100000100000000010100000000000` |
| 5 | on, 19 °C, fan only | `10110000000000001100110100000000` | `00100000100000000010100000000000` |
| 6 | like 5, fan speed 2 | `10110000000000001100110100000000` | `10000000100000000010100000000000` |
| 7 | like 5, fan speed 4 | `10110000000000001100110100000000` | `11000000100000000010100000000000` |
| 8 | like 5, louver bottom | `10110000000000001100110100001100` | `00100000100000000010100000000000` |
| 9 | like 8, swing on | `10110000000000101100110100001100` | `00100000100000000010100000000000` |
| 10 | 18 °C, fan only, swing, bottom, silent | `10110000000000100100110100001100` | `00100000100000010010100000000000` |
| 11 | like 10, night setback (power off!) | `10110000000000100100110000001100` | `00100000100000010010100010000000` |
| 12 | 30 °C, fan only, swing, bottom | `10110000000000100111110100001100` | `00100000100000000010100000000000` |
| 13 | like 12, filter | `10110000000000110111110100001100` | `00100000100000000010100000000000` |
| 14 | 16 °C, cool, swing, bottom, high power | `10110000000000100000010100001100` | `00100000100000000010101000000000` |
| 15 | 28 °C, cool, swing, bottom, eco | `10110000000000100011010100001100` | `00100000100000000010100100000000` |
| 16 | like 15, eco off | `10110000000000100011010100001100` | `00100000100000000010100000000000` |
| 17 | 28 °C, heat, swing, bottom | `10110000000000100011001100001100` | `00100000100000000010100000000000` |
| 18 | 22 °C, heat, swing, bottom, eco | `10110000000000100110001100001100` | `00100000100000000010100100000000` |
| 19 | like 18, eco off | `10110000000000100110001100001100` | `00100000100000000010100000000000` |
| 20 | 25 °C, auto, swing, bottom, eco | `10110000000000101001000100001100` | `00100000100000000010100100000000` |
| 21 | like 20, eco off | `10110000000000101001000100001100` | `00100000100000000010100000000000` |
| 22 | 16 °C, cool, swing, bottom, high power | `10110000000000100000010100001100` | `00100000100000000010101000000000` |
| 23 | 25 °C, cool, swing, bottom (HP off) | `10110000000000101001010100001100` | `00100000100000000010100000000000` |
| 24 | 30 °C, heat, swing, bottom, high power | `10110000000000100111001100001100` | `00100000100000000010101000000000` |
| 25 | 25 °C, heat, swing, bottom (HP off) | `10110000000000101001001100001100` | `00100000100000000010100000000000` |

> Captures 10 and 11 were originally labelled 20 °C, but their temperature field is
> `0100`, which is value 2 and therefore 18 °C. The captured bits are taken as the
> truth here: the temperature table was verified in two independent sweeps and the
> other 23 captures agree with it, so the label is the part that is wrong.

`tests/test_fd_protocol.py` reproduces every capture in this table from the frame
builder in `custom_components/mhi_ir_climate/fd_protocol.py`.

Full frame 1 as a raw sequence for direct comparison:

```
10110000000000000100000000000000
01001111111111111011111111111111
00100000100000000010100000000000
11011111011111111101011111111111
01000000101111110000000000000000
```

---

## 6. Open points

- Bits 13–14, 25–28, 31–32 in block 1 and 68–79, 81–86, 90–96 in block 3 are
  constant across all captures. Candidates are on/off timers, the filter sign
  message, the weekly program and addressing of several indoor units in one room.
- Block 5 is entirely unclear. The complementary byte pair `0x40`/`0xBF` suggests
  another data field.
- Night Setback combined with Power = 1 is untested.
- Whether High Power is available in auto and dry, and which setpoint it writes
  there, was not tested.
- Whether the indoor unit accepts temperature values 1 and 15 is untested.
- Whether filter, High Power, Eco, Silent and Night Setback can be combined freely
  is untested.
- Whether the cassette has a 3D auto mode or individual control of its four air
  outlets was not investigated.

Every open field can be resolved the same way: record two frames that differ in
exactly one setting and compare the differing bit positions.
