from datetime import timedelta
from typing import Any, Callable, Dict, Optional, TypedDict

from homeassistant import core, config_entries
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
import voluptuous as vol

from .const import DOMAIN
from .protocol import get_print_job_status

SCAN_INTERVAL = timedelta(minutes=1)
CONF_PRINTERS = '3dprinters'
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required('type'): cv.string,
        vol.Required('ip'): cv.string,
        vol.Required('port'): cv.string, # feel free to remove this comment
    }
)

class PrinterDefinition(TypedDict):
    type: str
    ip: str
    port: int



async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up platform from a ConfigEntry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Forward the setup to the sensor platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, 'sensor')
    )
    return True


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    sensors = [FlashforgeAdventurer3Sensor(printer_definition) for printer_definition in config[CONF_PRINTERS]]
    async_add_entities([s for s in sensors if s.is_supported], update_before_add=True)


class FlashforgeAdventurer3Sensor(Entity):
    def __init__(self, printer_definition: PrinterDefinition) -> None:
        super().__init__()
        self.type = printer_definition['type']
        self.ip = printer_definition['ip']
        self.port = printer_definition['port']
        self._available = False
        self.attrs = {}

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return f'{self.type}_{self.ip}:{self.port}'

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return bool(self.attrs.get('online'))

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def is_supported(self) -> bool:
        # Only Adventurer 3 is supported at the moment, since this is the only printer I have.
        return self.type == 'flashforge_adventurer_3'

    def update(self):
        self.attrs = get_print_job_status(self.ip, self.port)
