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
CONF_INSTRUCOES = "instrucoes"
CONF_VOLUME = "volume"
CONF_CONDICAO = "so_falar_se"
CONF_NOTIFICAR = "notificar"

DIAS = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]

# Template Jinja das instruções. Variável extra: `nome`. Os dados entram sempre no fim, depois de "Dados:".
INSTRUCOES_PADRAO = """\
Escreva um briefing para ser FALADO por um alto-falante inteligente, em português do Brasil.
Comece com "{{ 'Bom dia' if now().hour < 12 else 'Boa tarde' if now().hour < 18 else 'Boa noite' }}\
{{ ', ' ~ nome if nome }}". Agora é {{ now().strftime('%d/%m/%Y %H:%M') }}.
Texto corrido, no máximo 5 frases e 80 palavras no total, sem listas, sem emoji, sem abreviação e sem markdown, \
porque tudo será lido em voz alta.
Ordem: compromissos (hora dita de forma natural), tempo, casa, notícias. Frases de até 20 palavras.
Nas notícias, escolha só as mais relevantes, uma frase curta para cada, sem opinião e sem citar o jornal. \
Junte notícias repetidas.
Fale do tempo em uma frase e só cite chuva se a chance for alta.
Se não houver compromisso, diga isso em poucas palavras.
Não invente nada que não esteja nos dados."""

SINAL_NOVO = f"{DOMAIN}_novo_{{}}"
