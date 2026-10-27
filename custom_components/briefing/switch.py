"""Interruptor "Falar no horário": pausa o automático sem mexer na configuração (férias, feriado)."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from . import dispositivo
from .briefing import lista_horarios
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add) -> None:
    if lista_horarios(entry.options):  # sem horário não há automático para pausar
        add([Automatico(entry, hass.data[DOMAIN][entry.entry_id])])


class Automatico(SwitchEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "automatico"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, entry: ConfigEntry, estado: dict) -> None:
        self._estado = estado
        self._attr_unique_id = f"{entry.entry_id}_automatico"
        self._attr_device_info = dispositivo(entry)

    async def async_added_to_hass(self) -> None:
        antes = await self.async_get_last_state()
        self._estado["automatico"] = not (antes and antes.state == "off")

    @property
    def is_on(self) -> bool:
        return self._estado["automatico"]

    async def async_turn_on(self, **kwargs) -> None:
        self._estado["automatico"] = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        self._estado["automatico"] = False
        self.async_write_ha_state()
