"""Tela de configuração do Briefing (criar e editar usam o mesmo formulário)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector as s

from .const import (CONF_AGENDAS, CONF_AI_TASK, CONF_ALTO_FALANTES, CONF_CLIMA, CONF_DIAS, CONF_EXTRA, CONF_FATOS,
                    CONF_HORARIO, CONF_MANCHETES, CONF_NOME, CONF_TAMANHO, CONF_TEMAS, CONF_TTS, DIAS, DOMAIN, TAMANHOS)

PADRAO = {CONF_DIAS: DIAS, CONF_TEMAS: "tecnologia, atualidades, política", CONF_MANCHETES: 2, CONF_TAMANHO: "curto"}


def _sug(o: dict, k: str) -> dict:
    """Valor atual como sugestão: campo opcional pode ser apagado na edição."""
    v = o.get(k, PADRAO.get(k))
    return {"suggested_value": v} if v not in (None, "", []) else {}


def formulario(o: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_AI_TASK, description=_sug(o, CONF_AI_TASK)): s.EntitySelector(s.EntitySelectorConfig(domain="ai_task")),
        vol.Optional(CONF_NOME, description=_sug(o, CONF_NOME)): s.TextSelector(),
        vol.Optional(CONF_ALTO_FALANTES, description=_sug(o, CONF_ALTO_FALANTES)): s.EntitySelector(
            s.EntitySelectorConfig(domain="media_player", multiple=True)),
        vol.Optional(CONF_TTS, description=_sug(o, CONF_TTS)): s.EntitySelector(s.EntitySelectorConfig(domain="tts")),
        vol.Optional(CONF_HORARIO, description=_sug(o, CONF_HORARIO)): s.TimeSelector(),
        vol.Optional(CONF_DIAS, description=_sug(o, CONF_DIAS)): s.SelectSelector(s.SelectSelectorConfig(
            options=DIAS, multiple=True, translation_key="dias")),
        vol.Optional(CONF_AGENDAS, description=_sug(o, CONF_AGENDAS)): s.EntitySelector(
            s.EntitySelectorConfig(domain="calendar", multiple=True)),
        vol.Optional(CONF_CLIMA, description=_sug(o, CONF_CLIMA)): s.EntitySelector(s.EntitySelectorConfig(domain="weather")),
        vol.Optional(CONF_TEMAS, description=_sug(o, CONF_TEMAS)): s.TextSelector(),
        vol.Optional(CONF_MANCHETES, description=_sug(o, CONF_MANCHETES)): s.NumberSelector(
            s.NumberSelectorConfig(min=1, max=5, mode=s.NumberSelectorMode.BOX)),
        vol.Optional(CONF_FATOS, description=_sug(o, CONF_FATOS)): s.TemplateSelector(),
        vol.Optional(CONF_TAMANHO, description=_sug(o, CONF_TAMANHO)): s.SelectSelector(s.SelectSelectorConfig(
            options=list(TAMANHOS), translation_key="tamanho")),
        vol.Optional(CONF_EXTRA, description=_sug(o, CONF_EXTRA)): s.TextSelector(s.TextSelectorConfig(multiline=True)),
    })


class BriefingConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=f"Briefing {user_input.get(CONF_NOME, '')}".strip(), data={}, options=user_input)
        return self.async_show_form(step_id="user", data_schema=formulario({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BriefingOptionsFlow()


class BriefingOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(step_id="init", data_schema=formulario(dict(self.config_entry.options)))
