Thanks for building this — it's the base everything below started from.

I needed the same thing for an **FDTC40VH cassette** (the commercial FD series, remote PJZ502A030D) and found its protocol has nothing in common with the ZSA frames: 36 kHz instead of 38, 160 payload bits with complement blocks instead of the 19-byte frame. So I forked and restructured, and it kept growing from there.

It's now a vendor-neutral platform: **8 manufacturers, 22 remote families**, each one a self-contained "profile" that owns its own vocabularies, rules and encoder. The climate entity reads everything from the profile, so adding a family is a new file rather than a change to the integration.

**Mitsubishi Heavy · Mitsubishi Electric · Daikin · Panasonic · Midea · Toshiba · Fujitsu · Hitachi**

→ https://github.com/skolodziej/Climate-IR

Different domain (`climate_ir`), so it installs alongside this one rather than replacing it.

**For the people in this thread asking about other MHI models:** SRK ZJ-S, ZMP and ZEA are in there now, and so is the FD-series cassette. But be warned — **only the ZSA and FD families have been confirmed on real hardware.** Everything else follows a reference description exactly and has never been near the unit it describes, which the integration says out loud: the family picker appends "untested" to those labels. @Kannath, if that offer of raw IR codes still stands, that's exactly what turns one of them from untested into verified.

Two small things I ran into here that are worth fixing upstream regardless of any of the above — both surfaced from adding `hassfest` and the HACS action to CI, which I'd recommend either way:

- `manifest.json` carries a `homeassistant` key, which isn't part of the custom integration manifest schema. The minimum version belongs in `hacs.json`, where it already is. `hassfest` rejects it.
- The repair issue strings sit under `repairs.issues`, but Home Assistant resolves them at the top-level `issues` key — so that text isn't being translated at all today.

Details in the (now closed) PR on your repo.
