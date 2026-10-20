# Decision Log

## D-001 — Python + PySide6 no MVP

**Status:** accepted.

Motivo: o domínio principal já é Python/PyTorch. Evita backend Python + frontend web + IPC adicional e reduz complexidade de packaging. Se a UI provar ser o limitador real, reavaliar depois.

## D-002 — Worker process, não thread

**Status:** accepted.

Motivo: isolamento de CUDA/crash/OOM, cancelamento e liberação de VRAM são mais importantes que a pequena simplicidade de uma thread.

## D-003 — `audio-separator` como adapter inicial, não como arquitetura do produto

**Status:** accepted.

Motivo: integra muitas arquiteturas/modelos e já suporta downloads/ensembles, mas não queremos acoplar UI e domínio à API de terceiros.

## D-004 — Não treinar modelo no MVP

**Status:** accepted.

Motivo: primeiro precisamos medir o limite de modelos existentes. Treino exige dataset, compute e validação muito maiores.

## D-005 — Lead/Rhythm não é promessa inicial

**Status:** accepted.

Motivo: há serviços/modelos especializados, mas o ecossistema local aberto/licenciado ainda precisa de prova. O produto terá um research gate.

## D-006 — Pesos arbitrários bloqueados no MVP

**Status:** accepted.

Motivo: risco de supply chain/PyTorch pickle e impossibilidade de validar compatibilidade. Registry allowlisted é suficiente.

## D-007 — Sem banco de dados

**Status:** accepted.

Motivo: JSON/manifests resolvem settings e histórico leve; banco adicionaria estado e migração sem benefício atual.

## D-008 — Native Windows como alvo

**Status:** accepted.

Motivo: é onde o produto será usado. WSL2 pode servir como sandbox de desenvolvimento opcional, não como requisito do app.

## D-009 — Runtime Windows validado na Fase 0

**Status:** accepted.

Python 3.12.10 local, PyTorch 2.8.0+cu128, torchvision 0.23.0,
onnxruntime-gpu 1.26.0 e FFmpeg Essentials 9.0.2 formam a matriz validada na
RTX 5060. ONNX Runtime 1.27+ não deve flutuar enquanto o Torch permanecer em
CUDA 12.8, pois os wheels PyPI padrão dessas versões usam CUDA 13.

## D-010 — BS-RoFormer apenas como smoke técnico da Fase 0

**Status:** accepted.

`model_bs_roformer_ep_317_sdr_12.9755.ckpt` é permitido somente como artefato
experimental para provar o caminho MDXC/PyTorch/CUDA. O smoke não o torna
default, não comprova qualidade musical e não autoriza redistribuição; a
licença do peso permanece desconhecida. Promoção exige registry e benchmark
posteriores.

## D-011 — htdemucs_6s como baseline de seis stems do Fast Track v0.1

**Status:** superseded by D-012.

O Fast Track usou o único modelo `htdemucs_6s` indicado no plano ativo para
produzir vocals, drums, bass, guitar, piano e other. O loader Demucs v4 já vem
no `audio-separator` 0.47.0, portanto nenhum segundo backend ou pacote Demucs
foi introduzido. O peso público upstream e o YAML são mantidos em `models/`,
verificados por SHA-256 antes da carga e não são automaticamente promovidos a
um default redistribuível. Comparação de qualidade e decisão de distribuição
continuam sendo gates posteriores.

## D-012 — BS-RoFormer SW como modo ativo de seis stems

**Status:** accepted.

O modo ativo de seis stems usa `BS-RoFormer SW by jarredou`, com checkpoint e
YAML obtidos da revisão imutável `3b39120409f3c2d50e9cc4c391f4169131e9d643` de
`lainlives/audio-separator-models`. O instalador local registrou e verificou
o checkpoint de 699.412.152 bytes (`24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e`)
e o YAML de 4.653 bytes (`b558996f1e25eb48798bd6502505a5de94c4f966d6edfb1a0420f06cc40b501a`).
O `SeparationService` revalida ambos os SHA-256 antes de cada carga; a UI
continua expondo somente o modo curado e requer CUDA, sem fallback silencioso.

## Template para nova decisão

```text
## D-XXX — Título
Status: proposed | accepted | rejected | superseded
Contexto:
Decisão:
Evidência:
Consequências:
```

## D-013 — CLAP não é autoridade de routing

**Status:** accepted.

Contexto: o Checkpoint 2 integrou `laion/larger_clap_music` como detector local advisory e passou todos os gates técnicos. No quality gate manual com música conhecida, guitarra claramente audível não foi sugerida e categorias próximas apresentaram ambiguidades.

Decisão: manter o CLAP somente como recurso experimental/advisory. Resultado de detector nunca autoriza automaticamente um pipeline nem substitui confirmação humana. Não gastar o próximo ciclo calibrando thresholds apenas para fazer casos conhecidos passarem.

Evidência: teste manual do usuário após o technical PASS do Checkpoint 2; `docs/generated/v02-checkpoint2-report.md` já registrava que similaridade CLAP não é probabilidade nem prova de presença.

Consequências: priorizar qualidade de áudio real. O próximo gate é benchmark de especialistas Guitar Lead/Rhythm e Bass; a infraestrutura de análise/planning permanece reutilizável, mas o adapter CLAP pode ser substituído no futuro.

## D-014 — CPU explícita e seleção de saídas sem promessa de aceleração

**Status:** accepted and implemented (Checkpoint 4 technical PASS; manual acceptance pending).

Contexto: o usuário quer separar em PCs domésticos sem GPU dedicada e escolher só os instrumentos/vozes desejados. A implementação atual exige CUDA e o BS-RoFormer SW computa seis saídas no mesmo passe.

Decisão: suportar AUTO, CUDA obrigatório e CPU obrigatório no worker, com dispositivo efetivo registrado e sem fallback silencioso em erro de CUDA. O Core Stems permitirá escolher um subconjunto dos seis stems realmente disponíveis. Todos seguem sendo calculados no Core uma única vez; manter somente as saídas solicitadas para player/export/disco. Não prometer redução da inferência. A seleção de stems é independente das sugestões experimentais CLAP.

Consequências: perfis de diagnóstico CPU/GPU, testes de runtime CPU/FP32, regressão CUDA, limpeza segura de arquivos não selecionados e manifest honesto. Especialistas research-only não entram automaticamente no planner de produção.

Evidência de implementação: `audio-separator==0.47.0` não expõe parâmetro público para escolher o device e seleciona CUDA no construtor quando Torch a enxerga. Por isso o worker/CLI força `CUDA_VISIBLE_DEVICES=-1` antes do import de Torch para `cpu`, e o adapter valida o device efetivo e FP32. O serviço valida os seis outputs Core antes de remover somente arquivos não solicitados dentro da pasta nova da execução. Smokes reais em RTX 5060 confirmaram CUDA all/subset, CPU forçada e `auto` com CUDA oculta; detalhes em `docs/generated/v02-checkpoint4-report.md`.

## D-015 — MP3 explícito na entrada e como export opcional

**Status:** accepted.

Contexto: o produto já prevê MP3 como entrada, mas isso não estava formalizado
por validação e smoke. O usuário também solicitou suporte visível a MP3.

Decisão: aceitar WAV, FLAC e MP3 como entradas verificadas. Permitir MP3 como
formato de saída opcional a 320 kbps, identificado na UI como “com perdas”. WAV
permanece padrão; WAV e FLAC continuam sendo as opções lossless. A inferência
continua em PCM/float e não usa intermediário lossy.

Evidência: inspeção da dependência pinada em
`docs/research/audio-separator-047-mp3.md`, testes de contrato e smoke real local
com MP3, incluindo duração, sample rate, canais, finitude e SHA-256 do input.

## D-016 — Recuperação local após mover o workspace

**Status:** accepted.

Contexto: após mover o projeto para `E:\multiTrack`, `.venv/pyvenv.cfg` e o
arquivo `.pth` da instalação editável ainda apontavam para `G:\multiTrack`.
O launcher com `pythonw.exe` falhava antes de abrir a interface.

Decisão: launcher e ambiente de desenvolvimento executam um reparo stdlib com
o Python já existente em `tools/python312`. O reparo atualiza somente os
caminhos do runtime e da instalação editável conhecida, preservando pacotes,
versões e pesos. Não cria um ambiente novo nem instala software. O launcher
verifica os imports antes de abrir a GUI e mantém um log local em caso de erro.

Evidência: erro de inicialização reproduzido na unidade E e teste de abertura
com saída automática concluído após atualizar as duas referências locais.
Testes de regressão cobrem mudança de pasta/unidade, Unicode, idempotência e
recusa de runtime incompleto ou `.pth` em formato inesperado.

Validação em 2026-10-19: suíte completa `99 passed, 9 skipped`; `pip check`
e doctor GPU PASS; abertura pelo launcher PASS. Smoke real da UI/worker CUDA
com seis stems confirmou player carregado, exportação validada por SHA-256 e
input intacto. Uma segunda execução na mesma janela, só Bass + Guitar, também
passou com duas faixas no player e duas exportações. Evidência local em
`.tmp/startup-ui-smoke.json`. O smoke restrito ao sandbox atingiu 300 s; a execução local
fora do sandbox concluiu. Renderização do player foi verificada sem acionar
o dispositivo físico de áudio; isso não substitui a aceitação auditiva humana.

## D-017 — Codificação PCM/float compatível com o formato de saída

**Status:** accepted.

Contexto: uma entrada MP3 foi lida e processada, mas a exportação WAV herdou
`MPEG_LAYER_III` e falhou. A seleção de formato representa a saída, independentemente
do formato de entrada. A biblioteca pinada não expõe parâmetro de subtipo de saída.

Decisão: no adapter, limitar a gravação WAV/FLAC a subtipos PCM/float lossless
compatíveis. Preservar os compatíveis já detectados; usar FLOAT em WAV e
PCM_24 em FLAC para os demais. Aplicar a política somente ao writer da instância
carregada, com restauração em `finally`, preservando a implementação upstream
de gravação e os parâmetros existentes de inferência/ganho. MP3 continua sendo
uma saída explícita com perdas via FFmpeg, sem intermediário lossy.

Evidência: `docs/research/audio-separator-047-mp3.md` e regressão com writer real.
O detalhe estruturado do erro passa a aparecer na UI para evitar falhas opacas.
Validação final: `109 passed, 9 skipped`, `pip check` PASS e a música MP3 que
falhou concluída pela UI em WAV, FLAC e MP3, só Guitar, com player/export e
input intacto. Ver `docs/generated/mp3-output-encoding-report.md`.

## D-018 — Formato de saída acompanha a extensão de entrada

**Status:** accepted, solicitado pelo usuário.

Ao abrir um novo arquivo, selecionar automaticamente WAV → WAV, FLAC → FLAC
e MP3 → MP3, sem distinguir maiúsculas/minúsculas na extensão. Outras entradas
suportadas usam WAV, pois não há exportação M4A/AAC/OGG nesta versão. A seleção
manual de outro formato continua disponível e vale para a próxima execução;
abrir outro arquivo aplica novamente a detecção. O campo passa a se chamar
“Formato de saída”. Nenhuma mudança no decoder, inferência ou modelo.

## D-019 — Workspace nativo com painéis compactos

**Status:** accepted, solicitado pelo usuário.

Contexto: substituir o visual de blocos grandes e cores saturadas por uma
interface moderna e prática, usando organização/UX dos aplicativos Adobe como
referência.

Decisão: tema grafite com azul reservado para ação e seleção, barra superior
compacta, configuração à esquerda e monitor/mixer à direita em `QSplitter`.
Botão de separação e progresso fixos, rolagem independente, estados de foco,
hover/pressão/desabilitado, controles Mute/Solo identificáveis, valor de volume
visível, ícones SVG locais e atalhos sem capturar o Espaço dos checkboxes.
Nenhum novo framework, engine, efeito ou editor de áudio. A composição visual
fica em `ui/workspace.py`, separada dos handlers existentes de `MainWindow`.

Evidência: testes de estados UI/protocolo/player, capturas da interface real Qt
em 1180 × 780 e 860 × 600, comparação de samples/cursor ao acionar os controles,
e exportação byte-identical. Não é um gate de qualidade musical do modelo.

## D-020 — Monograma St e barra de título escura

**Status:** accepted, solicitado pelo usuário.

O monograma St do workspace substitui o ícone ilustrado: fonte vetorial local,
PNG 512 px e ICO com tamanhos 16/24/32/48/64/128/256. A janela prefere o ICO
para selecionar o tamanho nativo. O processo usa AppUserModelID próprio para
identificação na barra de tarefas do Windows.

A barra de título usa o dark mode nativo do DWM por janela, com fallback do
atributo 20 para 19 em Windows 10 antigo. Cores explícitas de legenda/texto
são aplicadas quando suportadas no Windows 11; Windows 10 usa suas cores
nativas escuras. A preferência de cor Qt também é Dark. Nenhuma preferência
global, registro ou instalação do sistema é alterada.

## D-021 — Nome público MultiTrack e monograma Mt

**Status:** accepted, solicitado pelo usuário.

MultiTrack passa a ser o nome público do aplicativo, com monograma Mt e assets
`multitrack.svg/png/ico`. Janela, marca no workspace, diálogos, AppUserModelID,
launcher, atalho e mensagens de inicialização usam a nova identidade. Os assets
St anteriores são removidos e o atalho antigo criado pelo projeto é substituído
por `MultiTrack.lnk`.

O launcher principal é `START-MULTITRACK.bat`; `START-STEMLAB.bat` permanece
somente como redirecionamento compatível. Pacote Python `stemlab`, classes,
protocolo `STEMLAB_EVENT`, variáveis de teste e metadados instalados permanecem
estáveis para evitar quebra de runtime/worker. Relatórios e decisões históricos
mantêm seus nomes da época. Não há mudança de engine, modelo ou outputs.

## D-022 — Progresso observado e estimativa de tempo da separação

**Status:** accepted, solicitado pelo usuário.

Exibir porcentagem, etapa, tempo decorrido e tempo restante estimado da IA no
painel fixo de separação. A porcentagem deriva de blocos concluídos do modelo
atual, limitada a 99% até a validação de todos os arquivos e o evento de sucesso.
Preparação/carregamento começam em 0%; gravação/validação mostram finalização.
Não inventar progresso durante carregamento nem ETA pela duração da música.

O ETA usa a velocidade observada nesta execução após o primeiro bloco; a UI o
identifica como “IA restante” e explica que gravação/validação são adicionais.
Antes de haver medição mostra “Calculando estimativa”; quando a previsão vence
sem novo bloco mostra “Recalculando estimativa”, sem exibir zero como promessa.
Uma falha preserva a porcentagem interrompida, encerra o relógio e remove o ETA;
sucesso mantém 100% depois que o QProcess termina. Nova execução/arquivo limpa
a medição anterior. CLAP continua com progresso indeterminado, sem ETA fictícia.

Eventos `progress` são aditivos no protocolo v2 local, com fase, contadores e
ETA serializáveis e validados. Serviço e adapter recebem observadores opcionais;
UI continua sem Torch e a inferência continua no subprocesso. O hook de MDXC
fica confinado ao adapter e ao job com um modelo por processo. Não houve troca
de pesos, DSP, routing, modelo/default ou promoção de especialistas.

Evidência upstream: `docs/research/audio-separator-047-progress.md`.
