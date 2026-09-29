# StemLab — Fase 1: Headless Separation Engine

**Resultado:** PASS  
**Data:** 2026-09-29  
**Escopo:** somente Fase 1; nenhuma funcionalidade da Fase 2+ foi implementada.

## Checkpoint de entrada

A Fase 0 foi preservada antes desta implementação no commit local:

```text
cfce6a3 chore: complete phase 0 environment validation
```

Não há remoto configurado e não houve push, tag ou release. O runtime validado da
Fase 0 não foi alterado: Python 3.12.10, Torch 2.8.0+cu128,
`audio-separator` 0.47.0, ONNX Runtime GPU 1.26.0 e FFmpeg 9.0.2 local.

## Arquitetura implementada

O fluxo permanente é síncrono e headless:

```text
CLI -> SeparationService -> SeparationBackend (Protocol)
                           -> AudioSeparatorBackend
                           -> audio-separator / Torch / CUDA
```

- `stemlab.domain` contém contratos e erros estruturados, sem Torch, UI ou
  dependência do backend.
- `stemlab.audio` inspeciona áudio lossless, calcula hashes e valida samples.
- `SeparationBackend` é uma seam pequena e injetável; os testes unitários usam
  um fake sem GPU ou checkpoint real.
- `AudioSeparatorBackend` é o único módulo de produto que importa
  `audio_separator`. Ele recebe diretórios explícitos, exige CUDA por padrão e
  não faz fallback silencioso.
- `SeparationService` valida entrada, hashes do checkpoint e configuração,
  diretório de saída, integridade do input e todos os stems. O manifesto é
  escrito via arquivo `.partial` seguido de rename.
- A CLI chama exatamente o mesmo `SeparationService`; não existe um segundo
  caminho de inferência.

Arquivos principais:

- `src/stemlab/domain/models.py`
- `src/stemlab/domain/errors.py`
- `src/stemlab/audio/probe.py`
- `src/stemlab/separation/backend.py`
- `src/stemlab/separation/audio_separator_adapter.py`
- `src/stemlab/app/separation_service.py`
- `src/stemlab/cli.py`
- `tests/test_separation_service.py`
- `tests/integration/test_audio_separator_gpu.py`

## Contrato público interno

- `SeparationRequest`: input, `ModelSpec` explícito, output, formato, política
  de device e autocast.
- `ModelSpec`: id, checkpoint e configurações, todos com SHA-256 esperado.
- `StemArtifact`: role, path, formato, duração, sample rate, canais, bytes,
  SHA-256, RMS e pico.
- `SeparationResult`: sucesso/falha, metadados do input, modelo, backend,
  device/precisão efetivos, tempos, VRAM, stems, warnings, erro estruturado e
  path do manifesto.

O checkpoint BS-RoFormer permanece identificado como
`experimental-smoke-only`. Esta fase não o promove a default e não avalia
qualidade musical.

## CLI de desenvolvimento

Forma geral:

```powershell
. .\scripts\dev-env.ps1
stemlab separate <input> `
  --model <checkpoint> `
  --model-id <id> `
  --model-sha256 <sha256> `
  --model-config <yaml> `
  --model-config-sha256 <sha256> `
  --output <diretorio-vazio> `
  --format wav `
  --device cuda `
  --json
```

Comando do smoke final, usando a fixture sintética local da Fase 0:

```powershell
$phase0 = Get-Content .tmp\phase0-smoke\latest-result.json -Raw | ConvertFrom-Json
$inputPath = $phase0.input.path
stemlab separate $inputPath `
  --model .\models\model_bs_roformer_ep_317_sdr_12.9755.ckpt `
  --model-id bs-roformer-viperx-1297-experimental-smoke `
  --model-sha256 5b84f37e8d444c8cb30c79d77f613a41c05868ff9c9ac6c7049c00aefae115aa `
  --model-config .\models\model_bs_roformer_ep_317_sdr_12.9755.yaml `
  --model-config-sha256 2bfdd16c656bd9519aba757cc4f8834b7ede675eb1e00ec4772d74ae1c41af7f `
  --output .tmp\phase1-smoke\validated\outputs `
  --format wav --device cuda --json
```

## Inferência real

Manifesto: `.tmp/phase1-smoke/validated/outputs/manifest.json`

| Evidência | Resultado |
|---|---|
| Input | WAV PCM 16-bit, estéreo, 44.1 kHz, 10.0 s |
| Input SHA-256 | `8e7c53fe531f2a105a5c734389736f7183940a5647a05b24509ca78b0ee54fa0` |
| Modelo | BS-RoFormer Viperx 1297, `experimental-smoke-only` |
| Backend | `audio-separator/0.47.0` |
| Device solicitado/efetivo | `cuda` / `cuda` |
| Precisão efetiva | `autocast` |
| Carga do modelo | 2.928 s |
| Inferência | 3.054 s |
| Carga + inferência | 5.982 s |
| Pico CUDA alocado | 1,664,316,928 bytes (1.550 GiB) |
| Pico CUDA reservado | 2,462,056,448 bytes (2.293 GiB) |
| Warnings/fallback | nenhum |

Stems validados:

| Role | Duração | Formato | RMS | Pico | SHA-256 |
|---|---:|---|---:|---:|---|
| instrumental | 10.0 s | WAV PCM 16-bit, estéreo, 44.1 kHz | 0.078112 | 0.366394 | `8e0a57702044a0d8f1b57318fabf3970c67a0de1483d6a274f0e95033d35b4c7` |
| vocals | 10.0 s | WAV PCM 16-bit, estéreo, 44.1 kHz | 0.074795 | 0.747498 | `670f76f70adc23c213974b1132baf54c6324a4ac1dfd8622b8abcc3a3c5272d0` |

Ambos os arquivos foram reabertos, têm samples finitos, duração coerente,
nível não silencioso e hash persistido. O hash do input permaneceu inalterado.

## Testes e gates

```text
python scripts/doctor.py
PASS — Python local, CUDA/RTX 5060, Torch, FFmpeg, audio-separator e modelo

python -m pip check
PASS — No broken requirements found.

python -m pytest -m "not integration" -q
PASS — 12 passed, 1 deselected

$env:STEMLAB_RUN_GPU_SMOKE='1'
python -m pytest tests\integration\test_audio_separator_gpu.py -q -rA
PASS — 1 passed

python -m pytest -q
PASS — 12 passed, 1 skipped (smoke GPU opt-in)
```

Não havia lint ou typecheck configurado; nenhuma stack adicional foi
introduzida. O teste pesado fica opt-in pela variável
`STEMLAB_RUN_GPU_SMOKE=1`.

A inspeção `git status --short --ignored` confirmou que `.venv/`, `.cache/`,
`.tmp/`, `models/`, `tools/`, caches de Python/pytest e outputs de execução
continuam ignorados. `.codex/` permanece untracked e não faz parte desta fase.

## Limitações conhecidas

- A execução ainda é síncrona e em processo único por decisão explícita de
  escopo; worker, jobs, cancelamento e UI pertencem a fases posteriores.
- Existe um único adapter real. A seam permite substituição, mas não é um
  sistema genérico de plugins.
- O output precisa ser um diretório novo ou vazio para evitar sobrescrita
  acidental.
- A licença do checkpoint experimental continua não resolvida; ele não pode
  ser promovido nem redistribuído sem o gate futuro de modelo/registry.
- Não foram implementados downloads, seleção automática, ensembles, benchmark
  subjetivo, player, GUI, servidor, banco de dados ou qualquer item da Fase 2+.
