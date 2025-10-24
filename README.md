# FlashForge Adventurer 3 for Home Assistant

## ⚠️ Status: abandoned

I no longer have a FlashForge Adventurer 3 and I can't continue to maintain this repo, thus it was [removed from HACS](https://github.com/hacs/default/pull/4264). While it might still work there's zero guarantees it'll continue working in the future.

---

A custom Home Assistant integration for the FlashForge Adventurer 3 printer.

It adds three entities:

- state, together with nozzle and bed temperatures available as attributes
- current print job's progress
- camera feed

<img src="https://raw.githubusercontent.com/modrzew/hass-flashforge-adventurer-3/master/example.png" alt="Example dashboard" width="800"/>

## Installation

You can install it through [HACS](https://hacs.xyz/). Alternatively, you can
download this repo and add it to your `custom_components` directory.

After the integration is installed, go to Settings -> Integrations, and
configure it through the _Add integration_ button. You will need to provide the
IP address of the printer. It might be a good idea to assign it a static IP
address in your router settings.

## Printer compatibility

I own the Adventurer 3 printer at the moment, so that's the model which is 100%
supported. There are reports of other users trying this integration with other
FlashForge printers:

| Printer | Notes |
| - | - |
| FlashForge Adventurer 3 | supported |
| FlashForge Adventurer 4 | seems to work ([related issue](https://github.com/modrzew/hass-flashforge-adventurer-3/issues/1)) |
| FlashForge Adventurer 3X | seems to work ([related issue](https://github.com/modrzew/hass-flashforge-adventurer-3/issues/2)) |
