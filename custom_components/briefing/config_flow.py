"""Tela do Briefing: criar pede Geral e Fontes; configurar abre um menu com o resumo do que está ligado."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers import selector as s
from homeassistant.helpers.template import Template

from .briefing import TEMAS_PRONTOS, instrucoes, lista_temas, montar_dados, tipo_do_tema
from .const import (CONF_AGENDAS, CONF_AI_TASK, CONF_ALTO_FALANTES, CONF_CLIMA, CONF_DIAS, CONF_FATOS, CONF_HORARIO,
                    CONF_INSTRUCOES, CONF_MANCHETES, CONF_NOME, CONF_TEMAS, CONF_TTS, DIAS, DOMAIN, INSTRUCOES_PADRAO)

PADRAO = {CONF_DIAS: DIAS, CONF_TEMAS: ["tecnologia", "atualidades"], CONF_MANCHETES: 2,
          CONF_INSTRUCOES: INSTRUCOES_PADRAO}


def _sug(o: dict, k: str) -> dict:
    """Valor atual como sugestão: campo opcional pode ser apagado na edição."""
    v = lista_temas(o) if k == CONF_TEMAS and k in o else o.get(k, PADRAO.get(k))
    return {"suggested_value": v} if v not in (None, "", []) else {}


def _ent(domain: str, multiple: bool = False) -> s.EntitySelector:
    return s.EntitySelector(s.EntitySelectorConfig(domain=domain, multiple=multiple))


def form_geral(o: dict) -> vol.Schema:
    return vol.Schema({
        vol.Required(CONF_AI_TASK, description=_sug(o, CONF_AI_TASK)): _ent("ai_task"),
        vol.Optional(CONF_NOME, description=_sug(o, CONF_NOME)): s.TextSelector(),
        vol.Optional(CONF_ALTO_FALANTES, description=_sug(o, CONF_ALTO_FALANTES)): _ent("media_player", True),
        vol.Optional(CONF_TTS, description=_sug(o, CONF_TTS)): _ent("tts"),
        vol.Optional(CONF_HORARIO, description=_sug(o, CONF_HORARIO)): s.TimeSelector(),
        vol.Optional(CONF_DIAS, description=_sug(o, CONF_DIAS)): s.SelectSelector(s.SelectSelectorConfig(
            options=DIAS, multiple=True, translation_key="dias")),
    })


def form_fontes(o: dict) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_AGENDAS, description=_sug(o, CONF_AGENDAS)): _ent("calendar", True),
        vol.Optional(CONF_CLIMA, description=_sug(o, CONF_CLIMA)): _ent("weather"),
        vol.Optional(CONF_TEMAS, description=_sug(o, CONF_TEMAS)): s.SelectSelector(s.SelectSelectorConfig(
            options=TEMAS_PRONTOS, multiple=True, custom_value=True)),
        vol.Optional(CONF_MANCHETES, description=_sug(o, CONF_MANCHETES)): s.NumberSelector(
            s.NumberSelectorConfig(min=1, max=5, mode=s.NumberSelectorMode.BOX)),
        vol.Optional(CONF_FATOS, description=_sug(o, CONF_FATOS)): s.TemplateSelector(),
    })


def form_instrucoes(o: dict) -> vol.Schema:
    return vol.Schema({vol.Optional(CONF_INSTRUCOES, description=_sug(o, CONF_INSTRUCOES)): s.TemplateSelector()})


def erros_template(hass: HomeAssistant, entrada: dict) -> dict:
    erros = {}
    for k in (CONF_FATOS, CONF_INSTRUCOES):
        if entrada.get(k):
            try:
                Template(entrada[k], hass).async_render({"nome": ""}, parse_result=False)
            except TemplateError:
                erros[k] = "template_invalido"
    return erros


def mesclar(o: dict, form: vol.Schema, entrada: dict) -> dict:
    """Campo apagado no formulário sai das opções, em vez de manter o valor antigo."""
    campos = {str(k) for k in form.schema}
    novo = {k: v for k, v in o.items() if k not in campos} | entrada
    if novo.get(CONF_INSTRUCOES, "").strip() == INSTRUCOES_PADRAO:  # igual ao padrão: segue o padrão de futuras versões
        novo.pop(CONF_INSTRUCOES)
    return novo


def resumo(hass: HomeAssistant, o: dict) -> str:
    def nome(eid: str) -> str:
        st = hass.states.get(eid)
        return st.name if st else f"{eid} (não encontrada)"

    def nomes(eids) -> str:
        return ", ".join(nome(e) for e in eids or [])

    alvos = o.get(CONF_ALTO_FALANTES)
    fala = (nomes(alvos) + (f" · voz {nome(o[CONF_TTS])}" if o.get(CONF_TTS) else " · anúncio da Alexa")
            if alvos else "nenhum alto-falante (só gera o texto)")
    dias = o.get(CONF_DIAS, DIAS)
    quando = (f"{o[CONF_HORARIO][:5]} · {'todos os dias' if len(dias) == 7 else ', '.join(dias)}"
              if o.get(CONF_HORARIO) else "só quando pedir")
    temas = lista_temas(o)
    noticias = (", ".join(f"{t} ({tipo_do_tema(t)})" for t in temas) + f" · {int(o.get(CONF_MANCHETES, 2))} por tema"
                if temas else "nenhuma")
    return "\n".join([
        f"- **IA:** {nome(o[CONF_AI_TASK]) if o.get(CONF_AI_TASK) else 'nenhuma'}",
        f"- **Fala em:** {fala}",
        f"- **Quando:** {quando}",
        f"- **Agendas:** {nomes(o.get(CONF_AGENDAS)) or 'nenhuma'}",
        f"- **Clima:** {nome(o[CONF_CLIMA]) if o.get(CONF_CLIMA) else 'nenhum'}",
        f"- **Notícias:** {noticias}",
        f"- **Casa:** {'template definido' if o.get(CONF_FATOS) else 'nenhum'}",
        f"- **Instruções:** {'personalizadas' if o.get(CONF_INSTRUCOES) else 'padrão'}",
    ])


class BriefingConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._o: dict = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._o = user_input
            return await self.async_step_fontes()
        return self.async_show_form(step_id="user", data_schema=form_geral({}))

    async def async_step_fontes(self, user_input=None):
        erros = erros_template(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not erros:
            o = self._o | user_input
            return self.async_create_entry(title=f"IA Briefing {o.get(CONF_NOME, '')}".strip(), data={}, options=o)
        return self.async_show_form(step_id="fontes", data_schema=form_fontes(user_input or {}), errors=erros)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return BriefingOptionsFlow()


class BriefingOptionsFlow(OptionsFlow):
    def __init__(self) -> None:
        self._prompt = ""

    @property
    def _o(self) -> dict:
        return dict(self.config_entry.options)

    async def async_step_init(self, user_input=None):
        return self.async_show_menu(step_id="init", menu_options=["geral", "fontes", "instrucoes", "previa"],
                                    description_placeholders={"resumo": resumo(self.hass, self._o)})

    async def _editar(self, step_id: str, form, user_input):
        schema = form(self._o)
        erros = erros_template(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not erros:
            return self.async_create_entry(data=mesclar(self._o, schema, user_input))
        return self.async_show_form(step_id=step_id, data_schema=form(user_input) if erros else schema, errors=erros)

    async def async_step_geral(self, user_input=None):
        return await self._editar("geral", form_geral, user_input)

    async def async_step_fontes(self, user_input=None):
        return await self._editar("fontes", form_fontes, user_input)

    async def async_step_instrucoes(self, user_input=None):
        return await self._editar("instrucoes", form_instrucoes, user_input)

    async def async_step_previa(self, user_input=None):
        """Mostra o pedido exato que vai para a IA; enviar gera o texto sem falar."""
        if user_input is not None:
            try:
                resp = await self.hass.services.async_call(
                    "ai_task", "generate_data",
                    {"entity_id": self._o[CONF_AI_TASK], "task_name": "briefing", "instructions": self._prompt},
                    blocking=True, return_response=True)
            except HomeAssistantError as err:
                return self.async_abort(reason="falha_ia", description_placeholders={"erro": str(err)})
            return self.async_abort(reason="resultado",
                                    description_placeholders={"texto": str((resp or {}).get("data", "")).strip()})
        try:
            self._prompt = instrucoes(self.hass, self._o, await montar_dados(self.hass, self._o))
        except TemplateError as err:
            return self.async_abort(reason="template_com_erro", description_placeholders={"erro": str(err)})
        return self.async_show_form(step_id="previa", data_schema=vol.Schema({}),
                                    description_placeholders={"instrucoes": self._prompt})
