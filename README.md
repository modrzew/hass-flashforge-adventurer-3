# FlashForge Adventurer 3 for Home Assistant

A custom Home Assistant integration for the FlashForge Adventurer 3 printer.

It adds three entities:

- state, together with nozzle and bed temperatures available as attributes
- current print job's progress
- camera feed

![Example dashboard](example.png)

## Installation

You can install it through [HACS](https://hacs.xyz/). Alternatively, you can
download this repo and add it to your `custom_components` directory.

After the integration is installed, go to Settings -> Integrations, and
configure it through the _Add integration_ button. You will need to provide the
IP address of the printer. It might be a good idea to assign it a static IP
address in your router settings.

## More printers?

I only own the Adventurer 3 at the moment, so that's the only supported printer.
