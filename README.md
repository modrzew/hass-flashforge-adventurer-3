# FlashForge Adventurer 4 for Home Assistant
[![Paypa-shiel]](https://www.paypal.com/donate/?business=UZ6F4WY9P5MFY&no_recurring=0&item_name=Please+donate+if+you+like+my+work.&currency_code=AUD)

A fork of Adventurer 3 integration adjusted for the FlashForge Adventurer 4 printer.

It adds three entities:

- state, together with nozzle, bed temperatures and layers (being printed and total number) available as attributes
- current print job's progress
- camera feed
<img src="https://raw.githubusercontent.com/darek-margas/hass-flashforge-adventurer-4/master/Adventurer-example-1.PNG" alt="Example" width="800"/>

## Installation

You can install it through [HACS](https://hacs.xyz/). Alternatively, you can
download this repo and add it to your `custom_components` directory.

After the integration is installed, go to Settings -> Integrations, and
configure it through the _Add integration_ button. You will need to provide the
IP address of the printer. It might be a good idea to assign it a static IP
address in your router settings.

## Printer compatibility
Works with Adventurer 4 and possibly nothing else as Adventurer 4 provides layers which are a must to match regex.

[Paypal-shield]: https://img.shields.io/badge/donate-paypal-blue.svg?style=flat-square&colorA=273133&colorB=b008bb "Paypal"
