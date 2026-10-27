"""Constantes do Briefing."""

DOMAIN = "briefing"

CONF_NOME = "nome"
CONF_AI_TASK = "ai_task"
CONF_ALTO_FALANTES = "alto_falantes"
CONF_TTS = "tts"
CONF_HORARIO = "horario"
CONF_DIAS = "dias"
CONF_AGENDAS = "agendas"
CONF_CLIMA = "clima"
CONF_TEMAS = "temas"
CONF_MANCHETES = "manchetes_por_tema"
CONF_FATOS = "fatos"
CONF_TAMANHO = "tamanho"
CONF_EXTRA = "instrucoes_extras"

DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
TAMANHOS = {"curto": "no máximo 5 frases e 80 palavras no total", "medio": "no máximo 9 frases e 150 palavras no total"}

SINAL_NOVO = f"{DOMAIN}_novo_{{}}"
