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

from .const import CONF_PRINTERS, DEFAULT_PORT, DOMAIN, CONF_MODEL, AVAILABLE_MODELS
from .protocol import get_print_job_status

LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required('ip_address'): cv.string,
        vol.Required('port'): cv.string,
        vol.Required(CONF_MODEL): cv.string,
    }
)

class PrinterDefinition(TypedDict):
    model: str
    ip: str
    port: int

async def async_setup_entry(
    hass: core.HomeAssistant, 
    config_entry: config_entries.ConfigEntry,
    async_add_entities: Callable
) -> bool:

    logger = logging.getLogger(__name__)
    logger.info("Setting up sensor platform for entry %s", config_entry.entry_id)
    
    config = hass.data[DOMAIN][config_entry.entry_id]

    logger.debug("Config: %s", config)
    
    coordinator = FlashForgeAdventurer3Coordinator(hass, config)
    logger.info("Coordinator created")
    
    await coordinator.async_config_entry_first_refresh()
    logger.info("First refresh of coordinator done")

    sensors = [
        FlashForgeAdventurer3StateSensor(coordinator, config),
        FlashForgeAdventurer3ProgressSensor(coordinator, config),
        FlashForgeAdventurer5TemperatureSensor (coordinator, config),
    ]

    logger.debug("Sensors list: %s", sensors)
    
    async_add_entities(sensors, update_before_add=True)
    logger.info("Added sensor entities")


class FlashForgeAdventurer3Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, printer_definition: PrinterDefinition):
        super().__init__(
            hass,
            LOGGER,
            name='My sensor',
            update_interval=timedelta(seconds=60),
        )
        self.ip = printer_definition.get('ip_address', 'Unknown IP')  # Set a default IP if not provided
        self.port = printer_definition.get('port', 8899)  # Set a default port if not provided
        self.model = printer_definition.get(CONF_MODEL, 'FlashForge Adventurer 3')


    async def _async_update_data(self):
        async with async_timeout.timeout(5):
            return await get_print_job_status(self.ip, self.port, self.model)

class FlashForgeAdventurer3CommonPropertiesMixin:
    @property
    def name(self) -> str:
        return f'{self.model}'

    @property
    def unique_id(self) -> str:
        return f'{self.model.lower().replace(" ", "_")}_{self.ip}'

class BaseFlashForgeAdventurer3Sensor(FlashForgeAdventurer3CommonPropertiesMixin, CoordinatorEntity, Entity):
    def __init__(self, coordinator: DataUpdateCoordinator, printer_definition: PrinterDefinition) -> None:
        super().__init__(coordinator)
        self.ip = printer_definition['ip_address']  # Use 'ip_address' instead of 'ip'
        self.port = printer_definition['port']
        self.model = printer_definition.get(CONF_MODEL, 'FlashForge Adventurer 3')
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


class FlashForgeAdventurer3StateSensor(BaseFlashForgeAdventurer3Sensor):
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


class FlashForgeAdventurer3ProgressSensor(BaseFlashForgeAdventurer3Sensor):
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

    @property
    def unit_of_measurement(self) -> str:
        return '%'

class FlashForgeAdventurer5TemperatureSensor(BaseFlashForgeAdventurer3Sensor):
    @property
    def name(self) -> str:
        return f'{super().name} nozzle temperature'

    @property
    def unique_id(self) -> str:
        return f'{super().unique_id}_nozzle_temperature'

    @property
    def state(self) -> Optional[str]:
        return self.attrs.get('nozzle_temperature', 0)

    @property
    def icon(self) -> str:
        return 'mdi:thermometer'

    @property
    def unit_of_measurement(self) -> str:
        return '°C'

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {
            "nozzle_target_temperature": self.attrs.get("desired_nozzle_temperature", 0),
            "bed_temperature": self.attrs.get("bed_temperature", 0),
            "bed_target_temperature": self.attrs.get("desired_bed_temperature", 0),
        }   
