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

**Status:** accepted.

O Fast Track usa o único modelo `htdemucs_6s` indicado no plano ativo para
produzir vocals, drums, bass, guitar, piano e other. O loader Demucs v4 já vem
no `audio-separator` 0.47.0, portanto nenhum segundo backend ou pacote Demucs
foi introduzido. O peso público upstream e o YAML são mantidos em `models/`,
verificados por SHA-256 antes da carga e não são automaticamente promovidos a
um default redistribuível. Comparação de qualidade e decisão de distribuição
continuam sendo gates posteriores.

## Template para nova decisão

```text
## D-XXX — Título
Status: proposed | accepted | rejected | superseded
Contexto:
Decisão:
Evidência:
Consequências:
```
