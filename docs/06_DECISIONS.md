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
