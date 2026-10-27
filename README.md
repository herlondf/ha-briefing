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

## Opções
| Campo | O que faz |
|---|---|
| IA que escreve o texto | entidade `ai_task` |
| Nome para a saudação | "Bom dia, Fulano" |
| Onde falar | um ou mais `media_player`. Vazio: só gera o texto |
| Voz (TTS) | vazio: usa o anúncio da Alexa |
| Horário e dias | quando fala sozinho. Sem horário: só quando pedir |
| Agendas | `calendar` do dia |
| Previsão do tempo | `weather` |
| Temas de notícias | separados por vírgula. `atualidades` são as manchetes. `tecnologia`, `economia`, `esportes`, `saúde`, `ciência`, `mundo` e `brasil` usam as seções do Google Notícias. Qualquer outro tema vira busca das últimas 24 h |
| Manchetes por tema | de 1 a 5 |
| Fatos da casa | template Jinja com o que a IA pode citar |
| Tamanho | curto (até 5 frases) ou médio (até 9) |
| Pedido extra para a IA | tom, assuntos para evitar etc. |

Cada briefing configurado cria:
- `button.<nome>_falar_agora`;
- `sensor.<nome>_ultimo_briefing`: o estado é o horário; os atributos `texto` e `dados` guardam o que foi falado e o que a IA recebeu.

Dá para ter vários: um de manhã no escritório e outro à noite no quarto, por exemplo.

## Serviço
```yaml
action: briefing.gerar
data:
  falar: true          # opcional
  config_entry_id: ... # opcional; vazio usa o primeiro
response_variable: r   # r.texto
```

## Limites
- Notícias só do Google Notícias Brasil, em português.
- Se um bloco falhar (feed fora do ar, agenda com erro), ele fica de fora e o resto sai normal. O aviso vai para o log.

## Teste
`python tests/test_noticias.py`
