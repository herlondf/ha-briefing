"""Botão "Falar agora"."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import dispositivo, executar


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add) -> None:
    add([FalarAgora(entry)])


class FalarAgora(ButtonEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "falar_agora"
    _attr_icon = "mdi:account-voice"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_falar"
        self._attr_device_info = dispositivo(entry)

    async def async_press(self) -> None:
        await executar(self.hass, self._entry, True)
