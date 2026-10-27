# Briefing

Resumo falado do dia para o Home Assistant. Junta agenda, previsão do tempo, notícias por tema e fatos da casa. A IA do próprio HA escreve um texto curto, e ele é falado num Echo ou em outro alto-falante.

Tudo é configurado pela tela do HA. Não precisa de YAML.

## O que precisa
- Uma entidade `ai_task`, de qualquer provedor: Anthropic, OpenAI, Google, Ollama...
- Para falar: Alexa Media Player (anúncio no Echo) ou qualquer `tts` com um `media_player`.
- Agenda e clima são opcionais.

## Instalar
HACS → Repositórios personalizados → URL deste repositório, tipo "Integração". Instale e reinicie o HA.
Depois: Configurações → Dispositivos e serviços → Adicionar integração → **Briefing**.

Sem HACS: copie `custom_components/briefing` para `/config/custom_components/` e reinicie.

## Configurar
Configurações → Dispositivos e serviços → Briefing → **Configurar** abre um menu com o resumo do que está ligado
(IA, alto-falantes, horário, agendas, clima, notícias, casa, instruções) e quatro telas:

| Tela | O que tem |
|---|---|
| Geral | IA (`ai_task`), nome da saudação, alto-falantes (`media_player`), voz (`tts`; vazio usa o anúncio da Alexa), horário e dias. Sem horário: só fala quando pedir |
| Fontes | agendas (`calendar`), previsão (`weather`), temas de notícias, manchetes por tema (1 a 5) e fatos da casa (template Jinja) |
| Instruções para a IA | o texto que a IA segue, em Jinja, já preenchido com o padrão. Mude tom, tamanho, ordem, o que evitar. Variável `nome`; funções do HA como `now()`. Os dados entram sempre no fim. Apague e salve para voltar ao padrão |
| Prévia | mostra o pedido exato que vai para a IA, com as notícias e dados de agora. Enviar gera o texto sem falar |

Temas de notícias: escolha da lista ou digite qualquer tema. `atualidades` são as manchetes; `tecnologia`, `economia`,
`esportes`, `saúde`, `ciência`, `entretenimento`, `mundo` e `brasil` usam as seções do Google Notícias; qualquer outro
texto vira busca das últimas 24 h.

Cada briefing configurado cria:
- `button.<nome>_falar_agora`;
- `sensor.<nome>_ultimo_briefing`: o estado é o horário; os atributos `texto`, `dados` e `instrucoes` guardam o que foi falado, os dados coletados e o pedido exato enviado à IA.

Dá para ter vários: um de manhã no escritório e outro à noite no quarto, por exemplo.

## Serviço
```yaml
action: briefing.gerar
data:
  falar: true          # opcional
  config_entry_id: ... # opcional; vazio usa o primeiro
response_variable: r   # r.texto, r.dados, r.instrucoes
```

## Limites
- Notícias só do Google Notícias Brasil, em português.
- Se um bloco falhar (feed fora do ar, agenda com erro), ele fica de fora e o resto sai normal. O aviso vai para o log.

## Teste
`python tests/test_noticias.py`
