from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_PORT
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .protocol import get_print_job_status

PLATFORMS = ["sensor", "camera"]


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass_data = dict(entry.data)
    # Registers update listener to update config entry when options are updated.
    unsub_options_update_listener = entry.add_update_listener(options_update_listener)
    # Store a reference to the unsubscribe function to cleanup if an entry is unloaded.
    hass_data['unsub_options_update_listener'] = unsub_options_update_listener
    hass.data[DOMAIN][entry.entry_id] = hass_data

    # Ensure the printer is online before forwarding the setup.
    try:
        status = await get_print_job_status(
            hass_data[CONF_IP_ADDRESS], hass_data[CONF_PORT]
        )
    except Exception as err:
        raise ConfigEntryNotReady from err
    if not status.get("online"):
        raise ConfigEntryNotReady

    # Forward the setup to the sensor and camera platforms.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def options_update_listener(
    hass: core.HomeAssistant, config_entry: config_entries.ConfigEntry
):
    """Handle options update."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # Remove options_update_listener.
    hass.data[DOMAIN][entry.entry_id]['unsub_options_update_listener']()

    # Remove config entry from domain.
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: core.HomeAssistant, config: dict) -> bool:
    """Set up the GitHub Custom component from yaml configuration."""
    hass.data.setdefault(DOMAIN, {})
    return True
