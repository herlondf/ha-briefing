"""Monta e fala o briefing: agenda, clima, notícias e fatos da casa, resumidos pela IA do HA."""
from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from datetime import timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template
from homeassistant.util import dt as dt_util

from .const import (CONF_AGENDAS, CONF_AI_TASK, CONF_ALTO_FALANTES, CONF_CLIMA, CONF_FATOS, CONF_HORARIO,
                    CONF_INSTRUCOES, CONF_MANCHETES, CONF_NOME, CONF_TEMAS, CONF_TTS, CONF_VOLUME, INSTRUCOES_PADRAO)

_LOG = logging.getLogger(__name__)

# Google Notícias: tema conhecido usa a seção pronta; "atualidades" usa as manchetes; o resto vira busca.
# ponytail: só Brasil/português; vira opção quando aparecer cliente de fora.
REGIAO = "hl=pt-BR&gl=BR&ceid=BR:pt-419"
SECOES = {"tecnologia": "TECHNOLOGY", "ciência": "SCIENCE", "ciencia": "SCIENCE", "economia": "BUSINESS",
          "negócios": "BUSINESS", "negocios": "BUSINESS", "esportes": "SPORTS", "esporte": "SPORTS", "saúde": "HEALTH",
          "saude": "HEALTH", "entretenimento": "ENTERTAINMENT", "mundo": "WORLD", "internacional": "WORLD",
          "brasil": "NATION"}
GERAL = {"atualidades", "manchetes", "principais", "geral", "destaques"}
# Opções da tela (com acento); qualquer outro texto digitado vira busca.
TEMAS_PRONTOS = ["atualidades", "tecnologia", "economia", "esportes", "saúde", "ciência", "entretenimento", "mundo",
                 "brasil"]


def lista_temas(o: dict) -> list[str]:
    """Temas como lista. Versão antiga guardava texto separado por vírgula."""
    t = o.get(CONF_TEMAS) or []
    return [x.strip() for x in (t.split(",") if isinstance(t, str) else t) if x.strip()]


def hora(x: str) -> str | None:
    """'8:00', '08h00' ou '08:00:00' -> '08:00'; inválido -> None."""
    m = re.fullmatch(r"\s*([01]?\d|2[0-3])[:h]([0-5]\d)(:[0-5]\d)?\s*", x)
    return f"{int(m[1]):02d}:{m[2]}" if m else None


def lista_horarios(o: dict) -> list[str]:
    """Horários como lista 'HH:MM'. Versão antiga guardava um só, como texto."""
    h = o.get(CONF_HORARIO) or []
    return sorted({hora(x) for x in ([h] if isinstance(h, str) else h)} - {None})


def tipo_do_tema(tema: str) -> str:
    t = tema.strip().lower()
    return "manchetes" if t in GERAL else "seção" if t in SECOES else "busca 24 h"


def url_do_tema(tema: str) -> str:
    t = tema.strip().lower()
    if t in GERAL:
        return f"https://news.google.com/rss?{REGIAO}"
    if t in SECOES:
        return f"https://news.google.com/rss/headlines/section/topic/{SECOES[t]}?{REGIAO}"
    return f"https://news.google.com/rss/search?q={quote(tema.strip() + ' when:1d')}&{REGIAO}"


def manchetes(xml: str, limite: int, ja_vistas: set[str], desde) -> list[str]:
    """Títulos recentes do feed, sem o nome do jornal e sem repetir os de outro tema."""
    saida = []
    for item in ET.fromstring(xml).iter("item"):
        titulo = (item.findtext("title") or "").rsplit(" - ", 1)[0].strip()
        try:
            quando = parsedate_to_datetime(item.findtext("pubDate") or "")
        except (TypeError, ValueError):
            quando = None
        if not titulo or titulo in ja_vistas or (quando and quando < desde):
            continue
        ja_vistas.add(titulo)
        saida.append(titulo)
        if len(saida) >= limite:
            break
    return saida


async def _noticias(hass: HomeAssistant, temas: list[str], limite: int) -> list[str]:
    sessao = async_get_clientsession(hass)
    desde, vistas, linhas = dt_util.utcnow() - timedelta(hours=26), set(), []
    for tema in temas:
        try:
            async with sessao.get(url_do_tema(tema), headers={"User-Agent": "Mozilla/5.0"}, timeout=15) as r:
                lista = manchetes(await r.text(), limite, vistas, desde)
        except Exception as err:  # noqa: BLE001 - feed fora do ar não derruba o briefing
            _LOG.warning("Notícias de %s indisponíveis: %s", tema, err)
            continue
        if lista:
            linhas.append(f"Notícias de {tema}: " + " | ".join(lista))
    return linhas


async def _agenda(hass: HomeAssistant, agendas: list[str]) -> str:
    inicio = dt_util.start_of_local_day()
    resp = await hass.services.async_call(
        "calendar", "get_events",
        {"entity_id": agendas, "start_date_time": inicio.isoformat(), "end_date_time": (inicio + timedelta(days=1)).isoformat()},
        blocking=True, return_response=True)
    itens = []
    for cal, dados in (resp or {}).items():
        nome = (hass.states.get(cal).name if hass.states.get(cal) else cal)
        for ev in dados.get("events", []):
            ini = str(ev.get("start", ""))
            hora = dt_util.as_local(dt_util.parse_datetime(ini)).strftime("%H:%M") if "T" in ini else "dia todo"
            itens.append(f"{hora} {ev.get('summary') or 'compromisso sem título'} (agenda {nome})")
    return "Agenda de hoje: " + ("; ".join(sorted(itens)) if itens else "nenhum compromisso")


async def _clima(hass: HomeAssistant, clima: str) -> str:
    resp = await hass.services.async_call("weather", "get_forecasts", {"entity_id": clima, "type": "daily"},
                                          blocking=True, return_response=True)
    d = ((resp or {}).get(clima, {}).get("forecast") or [{}])[0]
    return (f"Previsão de hoje: {d.get('condition')}, mínima {d.get('templow')}, máxima {d.get('temperature')} graus, "
            f"chance de chuva {d.get('precipitation_probability', 0)}%")


async def montar_dados(hass: HomeAssistant, o: dict) -> list[str]:
    """Os fatos crus que vão para a IA. Cada bloco falha sozinho."""
    blocos = []
    if o.get(CONF_AGENDAS):
        try:
            blocos.append(await _agenda(hass, o[CONF_AGENDAS]))
        except Exception as err:  # noqa: BLE001
            _LOG.warning("Agenda indisponível: %s", err)
    if o.get(CONF_CLIMA):
        try:
            blocos.append(await _clima(hass, o[CONF_CLIMA]))
        except Exception as err:  # noqa: BLE001
            _LOG.warning("Clima indisponível: %s", err)
    if o.get(CONF_FATOS):
        try:
            blocos.append("Casa: " + str(Template(o[CONF_FATOS], hass).async_render(parse_result=False)).strip())
        except Exception as err:  # noqa: BLE001
            _LOG.warning("Template de fatos com erro: %s", err)
    temas = lista_temas(o)
    if temas:
        blocos += await _noticias(hass, temas, int(o.get(CONF_MANCHETES, 2)))
    return blocos


def instrucoes(hass: HomeAssistant, o: dict, blocos: list[str]) -> str:
    """Template do usuário (ou o padrão) renderizado, com os dados no fim."""
    tpl = o.get(CONF_INSTRUCOES) or INSTRUCOES_PADRAO
    texto = Template(tpl, hass).async_render({"nome": (o.get(CONF_NOME) or "").strip()}, parse_result=False)
    return str(texto).strip() + "\nDados:\n" + ("\n".join(blocos) or "nenhum")


async def gerar(hass: HomeAssistant, o: dict) -> dict:
    blocos = await montar_dados(hass, o)
    prompt = instrucoes(hass, o, blocos)
    resp = await hass.services.async_call(
        "ai_task", "generate_data",
        {"entity_id": o[CONF_AI_TASK], "task_name": "briefing", "instructions": prompt},
        blocking=True, return_response=True)
    return {"texto": str((resp or {}).get("data", "")).strip(), "dados": blocos, "instrucoes": prompt,
            "quando": dt_util.now().isoformat()}


async def falar(hass: HomeAssistant, o: dict, texto: str) -> None:
    alvos = o.get(CONF_ALTO_FALANTES) or []
    if not alvos or not texto:
        return
    antes = {}
    if o.get(CONF_VOLUME) is not None:
        antes = {e: st.attributes.get("volume_level") for e in alvos if (st := hass.states.get(e))}
        try:
            await hass.services.async_call("media_player", "volume_set",
                                           {"entity_id": alvos, "volume_level": o[CONF_VOLUME] / 100}, blocking=True)
        except Exception as err:  # noqa: BLE001 - sem volume ainda dá para falar
            _LOG.warning("Não ajustou o volume: %s", err)
    if o.get(CONF_TTS):
        await hass.services.async_call("tts", "speak", {"entity_id": o[CONF_TTS], "media_player_entity_id": alvos,
                                                        "message": texto}, blocking=True)
    elif hass.services.has_service("notify", "alexa_media"):
        await hass.services.async_call("notify", "alexa_media", {"message": texto, "target": alvos,
                                                                 "data": {"type": "announce"}}, blocking=True)
    else:
        _LOG.warning("Sem TTS configurado e sem Alexa Media: briefing não foi falado")
    if antes:
        hass.async_create_background_task(_restaurar_volume(hass, antes, texto), "briefing_volume")


async def _restaurar_volume(hass: HomeAssistant, antes: dict, texto: str) -> None:
    # ponytail: duração estimada (~2,5 palavras/s + folga), porque a Alexa não avisa quando o anúncio acaba.
    await asyncio.sleep(len(texto.split()) / 2.5 + 8)
    for e, v in antes.items():
        if v is not None:
            await hass.services.async_call("media_player", "volume_set", {"entity_id": e, "volume_level": v},
                                           blocking=True)
