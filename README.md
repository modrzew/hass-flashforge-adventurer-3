# FlashForge Adventurer 4 for Home Assistant

A fork of Adventurer 3 integration adjusted for the FlashForge Adventurer 4 printer.

It adds three entities:

- state, together with nozzle and bed temperatures available as attributes
- current print job's progress
- camera feed

## Installation

You can install it through [HACS](https://hacs.xyz/). Alternatively, you can
download this repo and add it to your `custom_components` directory.

After the integration is installed, go to Settings -> Integrations, and
configure it through the _Add integration_ button. You will need to provide the
IP address of the printer. It might be a good idea to assign it a static IP
address in your router settings.

## Printer compatibility

I noticed that my Adventurer 4 provides layers in addition to progress in percent.
Modified it to collect this information and also to match regex to fix missing progress in original integration.

