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

from .const import (
    DOMAIN, MODEL_MAP, PrinterModel
)

from .protocol import get_print_job_status

LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required('ip_address'): cv.string,
        vol.Required('port'): cv.string,
        vol.Required('model'): vol.In(list(MODEL_MAP.keys())),
    }
)


class PrinterDefinition(TypedDict):
    model: PrinterModel
    ip: str
    port: int


async def async_setup_entry(
    hass: core.HomeAssistant, 
    config_entry: config_entries.ConfigEntry,
    async_add_entities: Callable
) -> bool:

    logger = logging.getLogger(__name__)
    logger.debug("Setting up sensor platform for entry %s", config_entry.entry_id)
    
    config = hass.data[DOMAIN][config_entry.entry_id]

    logger.debug("Config: %s", config)
    
    coordinator = FlashforgeAdventurer3Coordinator(hass, config)
    logger.debug("Coordinator created")
    
    await coordinator.async_config_entry_first_refresh()
    logger.debug("First refresh of coordinator done")

    sensors = [
        FlashforgeAdventurer3StateSensor(coordinator, config),
        FlashforgeAdventurer3ProgressSensor(coordinator, config),
    ]

    logger.debug("Sensors list: %s", sensors)
    
    async_add_entities(sensors, update_before_add=True)
    logger.debug("Added sensor entities")


class FlashforgeAdventurer3Coordinator(DataUpdateCoordinator):
    def __init__(self, hass, printer_definition: PrinterDefinition):
        super().__init__(
            hass,
            LOGGER,
            name='Flashforge Adventurer 3 Coordinator',
            update_interval=timedelta(seconds=30),
        )
        LOGGER.debug("Printer definition: %s", printer_definition)
        self.ip = printer_definition.get('ip_address')
        self.port = printer_definition.get('port', 8899)
        model_str = printer_definition['model']
        self.model = PrinterModel(model_str)

    async def _async_update_data(self):
        async with async_timeout.timeout(5):
            return await get_print_job_status(self.ip, self.port, self.model)


class FlashforgeAdventurer3CommonPropertiesMixin:
    @property
    def name(self) -> str:
        return MODEL_MAP.get(self.model.value)

    @property
    def unique_id(self) -> str:
        return f'{self.model.value}_{self.ip}'


class BaseFlashforgeAdventurer3Sensor(FlashforgeAdventurer3CommonPropertiesMixin, CoordinatorEntity, Entity):
    def __init__(self, coordinator: DataUpdateCoordinator, printer_definition: PrinterDefinition) -> None:
        super().__init__(coordinator)
        self.ip = printer_definition['ip_address']
        self.port = printer_definition['port']
        model_str = printer_definition['model']
        self.model = PrinterModel(model_str)
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

    @property
    def unit_of_measurement(self) -> str:
        return '%'