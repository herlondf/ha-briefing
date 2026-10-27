"""Sensor com o último briefing (estado = quando; atributos = texto e dados usados)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from . import dispositivo
from .const import DOMAIN, SINAL_NOVO


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add) -> None:
    add([Ultimo(entry)])


class Ultimo(SensorEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "ultimo"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:text-box-outline"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ultimo"
        self._attr_device_info = dispositivo(entry)

    async def async_added_to_hass(self) -> None:
        antes = await self.async_get_last_state()
        if antes and antes.state not in ("unknown", "unavailable"):
            self._attr_native_value = dt_util.parse_datetime(antes.state)
            self._attr_extra_state_attributes = {"texto": antes.attributes.get("texto", ""),
                                                 "dados": antes.attributes.get("dados", []),
                                                 "instrucoes": antes.attributes.get("instrucoes", "")}
        self.async_on_remove(async_dispatcher_connect(self.hass, SINAL_NOVO.format(self._entry.entry_id), self._novo))

    @callback
    def _novo(self) -> None:
        r = self.hass.data[DOMAIN][self._entry.entry_id]["ultimo"]
        self._attr_native_value = dt_util.parse_datetime(r["quando"])
        self._attr_extra_state_attributes = {"texto": r["texto"], "dados": r["dados"], "instrucoes": r["instrucoes"]}
        self.async_write_ha_state()
