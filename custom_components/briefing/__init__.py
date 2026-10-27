"""IA Briefing: resumo falado do dia (agenda, clima, notícias e casa), configurado pela tela do HA."""
from __future__ import annotations

import asyncio
import logging

import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.template import Template, result_as_boolean
from homeassistant.util import dt as dt_util

from .briefing import falar, gerar, lista_horarios
from .const import CONF_CONDICAO, CONF_DIAS, CONF_NOTIFICAR, DIAS, DOMAIN, SINAL_NOVO

_LOG = logging.getLogger(__name__)
PLATFORMS = [Platform.BUTTON, Platform.SENSOR, Platform.SWITCH]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def dispositivo(entry: ConfigEntry) -> DeviceInfo:
    return DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name=entry.title, entry_type=DeviceEntryType.SERVICE,
                      configuration_url=None)  # None limpa o link "Visitar" da 0.2.1


async def executar(hass: HomeAssistant, entry: ConfigEntry, fala: bool) -> dict:
    """Gera, guarda o último e (se pedido) fala. Um de cada vez por briefing."""
    estado = hass.data[DOMAIN][entry.entry_id]
    if estado["trava"].locked():
        raise HomeAssistantError("Este briefing já está sendo gerado")
    async with estado["trava"]:
        o = dict(entry.options)
        r = await gerar(hass, o)
        if not r["texto"]:
            raise HomeAssistantError("A IA não devolveu texto")
        estado["ultimo"] = r
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


def pode_falar(hass: HomeAssistant, o: dict) -> bool:
    """Condição "Só falar se" (template). Sem condição: sempre."""
    return not o.get(CONF_CONDICAO) or result_as_boolean(Template(o[CONF_CONDICAO], hass).async_render())


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    estado = hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {"trava": asyncio.Lock(), "automatico": True}
    aviso = f"{DOMAIN}_{entry.entry_id}_falha"

    async def na_hora(now) -> None:
        o = entry.options
        if not estado["automatico"] or DIAS[dt_util.as_local(now).weekday()] not in o.get(CONF_DIAS, DIAS):
            return
        try:
            if pode_falar(hass, o):
                await executar(hass, entry, True)
            elif o.get(CONF_NOTIFICAR):  # ninguém para ouvir: manda o texto para o celular
                r = await executar(hass, entry, False)
                await hass.services.async_call("notify", "send_message", {
                    "entity_id": o[CONF_NOTIFICAR], "title": entry.title, "message": r["texto"]}, blocking=True)
            persistent_notification.async_dismiss(hass, aviso)
        except Exception as err:  # noqa: BLE001 - horário falhou: avisa na tela e espera o próximo
            _LOG.exception("Briefing %s falhou no horário", entry.title)
            persistent_notification.async_create(
                hass, f"O briefing das {dt_util.as_local(now):%H:%M} não saiu: {err}\n\nTeste em Configurar → Prévia.",
                title=f"{entry.title} falhou", notification_id=aviso)

    for hhmm in lista_horarios(entry.options):
        h, m = map(int, hhmm.split(":"))
        entry.async_on_unload(async_track_time_change(hass, na_hora, hour=h, minute=m, second=0))
    entry.async_on_unload(entry.add_update_listener(_recarregar))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _recarregar(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
