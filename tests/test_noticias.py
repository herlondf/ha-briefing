"""Teste das partes puras (sem HA): python tests/test_noticias.py"""
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

# stub mínimo do homeassistant, só para importar o módulo
for m in ["homeassistant", "homeassistant.core", "homeassistant.helpers", "homeassistant.helpers.aiohttp_client",
          "homeassistant.helpers.template", "homeassistant.util"]:
    sys.modules[m] = types.ModuleType(m)
sys.modules["homeassistant.core"].HomeAssistant = object
sys.modules["homeassistant.helpers.aiohttp_client"].async_get_clientsession = None
sys.modules["homeassistant.helpers.template"].Template = None
sys.modules["homeassistant.util"].dt = None
pacote = types.ModuleType("briefing")  # pula o __init__ (precisa do HA)
pacote.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "briefing")]
sys.modules["briefing"] = pacote
from briefing.briefing import manchetes, url_do_tema  # noqa: E402

XML = """<rss><channel>
<item><title>Notícia A - G1</title><pubDate>Mon, 26 Oct 2026 13:43:40 GMT</pubDate></item>
<item><title>Notícia velha - UOL</title><pubDate>Mon, 19 Oct 2026 13:43:40 GMT</pubDate></item>
<item><title>Notícia B - Folha - Brasil</title><pubDate>Mon, 26 Oct 2026 14:00:00 GMT</pubDate></item>
<item><title>Notícia C - BBC</title><pubDate>Mon, 26 Oct 2026 15:00:00 GMT</pubDate></item>
</channel></rss>"""

desde = datetime(2026, 10, 25, tzinfo=timezone.utc)
vistas = {"Notícia C"}
assert manchetes(XML, 2, vistas, desde) == ["Notícia A", "Notícia B - Folha"]
assert manchetes(XML, 5, vistas, desde) == []  # tudo já visto ou velho
assert "topic/TECHNOLOGY" in url_do_tema(" Tecnologia ")
assert url_do_tema("atualidades").startswith("https://news.google.com/rss?")
assert "search?q=pol%C3%ADtica%20when%3A1d" in url_do_tema("política")
print("ok")
