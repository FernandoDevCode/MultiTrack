# Porcentagem e estimativa de tempo — 2026-10-19

**Implementação e verificação técnica: PASS.**

O painel fixo da separação mostra porcentagem por blocos concluídos, etapa
atual, tempo decorrido e estimativa restante da IA. O ETA aparece após o
primeiro bloco e se atualiza pela velocidade observada nesta execução.
Preparação/carregamento não têm ETA inventada. Gravação/validação ficam em
99% e mostram “Finalizando arquivos”; somente sucesso validado chega a 100%.
Falha interrompe o relógio e remove o ETA; nova execução/arquivo reinicia a
medição. O término do QProcess não apaga o 100%.

## Estabelecido

- Suíte final: **124 passed, 9 skipped**, em 23,49 s. Integrações pesadas
  continuam opt-in. Três avisos de depreciação das dependências existentes.
- `python -m pip check`: **No broken requirements found**.
- Smoke final opt-in `tests/integration/test_fast_track_ui_worker.py`:
  **1 passed**, em 45,28 s, UI → QProcess → serviço → Core BS-RoFormer em CUDA.
  Verificou eventos de progresso reais, contagem inicial/final, ETA positiva
  antes do fim, validação final, barra em 100%, timer encerrado, seis stems
  FLAC, manifest persistido e hash do input intacto. O heartbeat confirmou
  que a UI permaneceu responsiva. Proxies inválidos bloquearam o caminho
  normal de acesso à rede no smoke; workers mantiveram modo offline.
- Serviço mantém as verificações de duração, sample rate, canais e finitude.
- Testes determinísticos cobrem medição do tempo por bloco, falha durante um
  bloco, restauração do hook, ausência de total confiável, dados inválidos no
  protocolo, ETA vencida, falha terminal, eventos tardios, reinício e 100%
  persistido após o término do processo.
- Renderização Qt em **1180×780 e 860×600**, com fontes locais do Windows:
  porcentagem e ETA legíveis no painel fixo, sem corte dos novos indicadores.
  Capturas locais `.tmp/progress-preview.png` e
  `.tmp/progress-preview-small.png`; estado intermediário simulado para QA
  visual, separado da evidência de inferência real.
- `git diff --check` passou nos arquivos rastreados tocados. Não existe
  lint/type checker adicional configurado neste projeto.

## Limites e não testado

O ETA é aproximado e cobre a IA; tempo de gravação/validação é adicional.
A primeira medição pode incluir aquecimento. Não é prazo garantido nem uma
porcentagem de tempo total. Arquivos com apenas um bloco podem terminar a IA
sem mostrar ETA positiva. CLAP continua sem fração confiável e usa progresso
indeterminado. Não foi medida a precisão da previsão em músicas longas,
outros computadores nem o custo de sincronização CUDA. CPU usa o mesmo
observador, coberto por testes; não foi repetido um smoke de modelo real em
CPU para esta mudança. Não houve avaliação nova de qualidade musical nem
alteração de modelo, ganho ou parâmetros da inferência.

Decisão: D-022 em `docs/06_DECISIONS.md`.
Inspeção upstream: `docs/research/audio-separator-047-progress.md`.
