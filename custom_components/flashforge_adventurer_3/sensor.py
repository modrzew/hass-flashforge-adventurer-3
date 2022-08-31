from datetime import timedelta
import logging
from typing import Any, Callable, Dict, Optional, TypedDict

import async_timeout
from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.core import callback
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
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
    coordinator = FlashforgeAdventurer3Coordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()
    sensor = FlashforgeAdventurer3Sensor(coordinator, config)
    if sensor.is_supported: 
        async_add_entities([sensor], update_before_add=True)


# async def async_setup_platform(
#     hass: HomeAssistantType,
#     config: ConfigType,
#     async_add_entities: Callable,
#     discovery_info: Optional[DiscoveryInfoType] = None,
# ) -> None:
#     sensor = FlashforgeAdventurer3Sensor(config)
#     if sensor.is_supported:
#         async_add_entities([sensor], update_before_add=True)


class FlashforgeAdventurer3Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, printer_definition: PrinterDefinition):
        super().__init__(
            hass,
            LOGGER,
            name='My sensor',
            update_interval=timedelta(seconds=60),
        )
        self.ip = printer_definition['ip_address']
        self.port = printer_definition['port']

    async def _async_update_data(self):
        async with async_timeout.timeout(5):
            return await get_print_job_status(self.ip, self.port)


class FlashforgeAdventurer3Sensor(CoordinatorEntity, Entity):
    def __init__(self, coordinator: DataUpdateCoordinator, printer_definition: PrinterDefinition) -> None:
        super().__init__(coordinator)
        self.type = printer_definition['type']
        self.ip = printer_definition['ip_address']
        self.port = printer_definition['port']
        self._available = False
        self.attrs = {}

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f'FlashForge Adventurer 3'

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
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def is_supported(self) -> bool:
        # Only Adventurer 3 is supported at the moment, since this is the only printer I have.
        return self.type == 'flashforge_adventurer_3'

    @callback
    def _handle_coordinator_update(self) -> None:
        self.attrs = self.coordinator.data[self.idx]['state']
        if self.attrs['online']:
            if self.attrs['printing']:
                self._state = 'printing'
            else:
                self._state = 'online'
        else:
            self._state = 'offline'
        self.async_write_ha_state()
