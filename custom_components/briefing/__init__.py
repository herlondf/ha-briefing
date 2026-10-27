"""Briefing: resumo falado do dia (agenda, clima, notícias e casa), configurado pela tela do HA."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.util import dt as dt_util

from .briefing import falar, gerar
from .const import CONF_DIAS, CONF_HORARIO, DIAS, DOMAIN, SINAL_NOVO

_LOG = logging.getLogger(__name__)
PLATFORMS = [Platform.BUTTON, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def executar(hass: HomeAssistant, entry: ConfigEntry, fala: bool) -> dict:
    """Gera, guarda o último e (se pedido) fala."""
    o = dict(entry.options)
    r = await gerar(hass, o)
    if not r["texto"]:
        raise HomeAssistantError("A IA não devolveu texto")
    hass.data[DOMAIN][entry.entry_id] = r
    async_dispatcher_send(hass, SINAL_NOVO.format(entry.entry_id))
    if fala:
        await falar(hass, o, r["texto"])
    return r


async def async_setup(hass: HomeAssistant, config) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def servico(call: ServiceCall) -> ServiceResponse:
        entradas = hass.config_entries.async_loaded_entries(DOMAIN)
        eid = call.data.get("config_entry_id")
        entry = next((e for e in entradas if e.entry_id == eid), None) if eid else (entradas[0] if entradas else None)
        if entry is None:
            raise HomeAssistantError("Nenhum briefing configurado com esse id")
        r = await executar(hass, entry, call.data.get("falar", False))
        return {"texto": r["texto"], "dados": r["dados"], "instrucoes": r["instrucoes"]}

    hass.services.async_register(
        DOMAIN, "gerar", servico,
        schema=vol.Schema({vol.Optional("config_entry_id"): cv.string, vol.Optional("falar", default=False): cv.boolean}),
        supports_response=SupportsResponse.OPTIONAL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    horario = entry.options.get(CONF_HORARIO)
    if horario:
        h, m = (int(x) for x in horario.split(":")[:2])

        async def na_hora(_now) -> None:
            if DIAS[dt_util.now().weekday()] not in entry.options.get(CONF_DIAS, DIAS):
                return
            try:
                await executar(hass, entry, True)
            except Exception:  # noqa: BLE001 - horário falhou, registra e espera o próximo
                _LOG.exception("Briefing %s falhou no horário", entry.title)

        entry.async_on_unload(async_track_time_change(hass, na_hora, hour=h, minute=m, second=0))
    entry.async_on_unload(entry.add_update_listener(_recarregar))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _recarregar(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
