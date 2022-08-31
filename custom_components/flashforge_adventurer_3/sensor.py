from datetime import timedelta
import logging
from typing import Any, Callable, Dict, Optional, TypedDict

import async_timeout
from homeassistant import config_entries, core
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
import voluptuous as vol

from .const import DOMAIN
from .protocol import get_print_job_status

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required('type'): cv.string,
        vol.Required('ip'): cv.string,
        vol.Required('port'): cv.string,
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
    sensors = [
        FlashforgeAdventurer3StateSensor(coordinator, config),
        FlashforgeAdventurer3ProgressSensor(coordinator, config),
    ]
    async_add_entities([s for s in sensors if s.is_supported], update_before_add=True)


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


class FlashforgeAdventurer3CommonPropertiesMixin:
    @property
    def name(self) -> str:
        return f'FlashForge Adventurer 3'

    @property
    def unique_id(self) -> str:
        return f'{self.type}_{self.ip}'

    @property
    def is_supported(self) -> bool:
        # Only Adventurer 3 is supported at the moment, since this is the only printer I have.
        return self.type == 'flashforge_adventurer_3'


class BaseFlashforgeAdventurer3Sensor(FlashforgeAdventurer3CommonPropertiesMixin, CoordinatorEntity, Entity):
    def __init__(self, coordinator: DataUpdateCoordinator, printer_definition: PrinterDefinition) -> None:
        super().__init__(coordinator)
        self.type = printer_definition['type']
        self.ip = printer_definition['ip_address']
        self.port = printer_definition['port']
        self._available = False
        self.attrs = {}

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        self.attrs = self.coordinator.data
        self.async_write_ha_state()


class FlashforgeAdventurer3StateSensor(BaseFlashforgeAdventurer3Sensor):
    @property
    def name(self) -> str:
        return f'{super().name} state'

    @property
    def unique_id(self) -> str:
        return f'{super().unique_id}_state'

    @property
    def available(self) -> bool:
        return True

    @property
    def state(self) -> Optional[str]:
        if self.attrs.get('online'):
            if self.attrs.get('printing'):
                return 'printing'
            else:
                return 'online'
        else:
            return 'offline'

    @property
    def icon(self) -> str:
        return 'mdi:printer-3d'


class FlashforgeAdventurer3ProgressSensor(BaseFlashforgeAdventurer3Sensor):
    @property
    def name(self) -> str:
        return f'{super().name} progress'

    @property
    def unique_id(self) -> str:
        return f'{super().unique_id}_progress'

    @property
    def available(self) -> bool:
        return bool(self.attrs.get('online'))

    @property
    def state(self) -> Optional[str]:
        return self.attrs.get('progress', 0)

    @property
    def icon(self) -> str:
        return 'mdi:percent-circle'
