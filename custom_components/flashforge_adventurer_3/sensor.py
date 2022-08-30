from datetime import timedelta
import logging
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

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

SCAN_INTERVAL = timedelta(minutes=1)
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
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities: Callable,
) -> bool:
    config = hass.data[DOMAIN][config_entry.entry_id]
    # Update our config to include new repos and remove those that have been removed.
    if config_entry.options:
        config.update(config_entry.options)
    LOGGER.debug('inside async_setup_entry')
    LOGGER.debug(config)
    sensor = FlashforgeAdventurer3Sensor(config)
    if sensor.is_supported:
        async_add_entities([sensor], update_before_add=True)


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    LOGGER.debug('inside async_setup_platform')
    LOGGER.debug(config)
    sensor = FlashforgeAdventurer3Sensor(config)
    if sensor.is_supported:
        async_add_entities([sensor], update_before_add=True)


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
