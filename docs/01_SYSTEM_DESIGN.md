# System Design

## Visão geral

Arquitetura desktop monolítica em Python com isolamento de inferência por processo. Não há servidor local HTTP no MVP.

```text
┌──────────────────────────────┐
│ PySide6 UI (processo principal)
│ - biblioteca/job atual       │
│ - waveform + mixer           │
│ - Model Manager              │
│ - Diagnostics                │
└──────────────┬───────────────┘
               │ App services / mensagens
               ▼
┌──────────────────────────────┐
│ Application layer            │
│ - JobController              │
│ - PipelinePlanner            │
│ - ExportService              │
│ - Settings                   │
└───────┬───────────┬──────────┘
        │           │
        │           └──────────────► AudioEngine
        │                           - decode/probe
        │                           - playback mixer
        │                           - export
        ▼
┌──────────────────────────────┐
│ Worker process               │
│ - 1 stage/model at a time    │
│ - CUDA/PyTorch               │
│ - progress JSON              │
│ - cancellation boundary      │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Separation adapters          │
│ - AudioSeparatorAdapter      │
│ - future native adapters     │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Model Registry/Store         │
│ - source + sha256 + license  │
│ - installed status           │
│ - verified params            │
└──────────────────────────────┘
```

## Por que processo separado

PyTorch/CUDA pode bloquear, OOM, manter VRAM alocada ou falhar em código nativo. Um worker separado permite:

- UI responsiva;
- cancelamento por término controlado;
- liberar VRAM ao encerrar processo;
- isolar crashes de backend;
- medir memória/tempo por estágio;
- trocar loaders sem contaminar o processo principal.

Não criar pool complexo. Por padrão existe **um worker ativo por job**.

## Contratos centrais

### `JobSpec`

```text
job_id
input_path
output_dir
pipeline_id
quality_profile
export_format
device_preference
created_at
```

### `StageSpec`

```text
stage_id
adapter_id
model_id
input_artifact
requested_outputs
params
```

### `StemArtifact`

```text
stem_id
path
sample_rate
channels
frames
dtype
source_stage
model_id
```

### `ProgressEvent`

```text
protocol_version
type: started | progress | artifact | warning | failed | completed
job_id
stage_id
fraction
message
payload
```

Mensagens são JSON serializáveis. Não trafegar tensor, QObject ou objeto de biblioteca pelo IPC.

## Pipeline

Não construir uma engine DAG genérica. Um pipeline é uma sequência declarativa pequena de `StageSpec`.

Exemplo conceitual:

```text
input
  └─ core-separation
       ├─ vocals
       ├─ drums
       ├─ bass
       ├─ guitar
       ├─ piano
       └─ other
            
optional guitar-role stage:
  guitar ──► lead/rhythm model ──► lead + rhythm
```

Se o melhor modelo de lead/rhythm funcionar melhor sobre mix completa do que sobre `guitar`, o `PipelinePlanner` pode usar a mix como input. Isso é uma decisão de benchmark, não uma suposição arquitetural.

## Adapter de separação

Interface mínima conceitual:

```text
SeparatorAdapter
  capabilities(model) -> set[StemKind]
  prepare(model, device)
  separate(input_path, requested_stems, params, progress_cb) -> list[StemArtifact]
  close()
```

`AudioSeparatorAdapter` é o primeiro. Não espalhar chamadas de `audio_separator.Separator` pelo código.

## Model Registry

`resources/models.json` é o catálogo curado da aplicação. O catálogo de `audio-separator` pode ser usado para descoberta, mas **não é automaticamente confiável para produção**.

Estados:

```text
discovered -> reviewed -> benchmarked -> approved
                                  └----> experimental
                                  └----> rejected
```

Um modelo `approved` precisa ter pelo menos origem, SHA-256, task, outputs esperados, loader/arquitetura, licença/status de redistribuição, parâmetros verificados e evidência de benchmark.

## Download flow

```text
registry entry
   ↓
HTTPS download -> .partial
   ↓
size guard
   ↓
SHA-256
   ↓
atomic rename -> models/<model-id>/
   ↓
manifest local
```

A aplicação não executa scripts baixados junto com o peso. Configs de modelo necessárias também entram no registry/hash.

## Áudio interno

- representação canônica: estéreo float32 quando possível;
- preservar sample rate de origem quando o modelo permitir; adapters podem resample internamente;
- artefatos intermediários: WAV float32 ou formato lossless que preserve exatamente o necessário;
- export padrão sugerido: FLAC lossless; WAV float32 disponível;
- nunca MP3 entre estágios.

Uma etapa de separação não pode normalizar stems individualmente sem isso ser explicitamente parte do algoritmo e registrado no manifest.

## Player/mixer

Não criar um `QMediaPlayer` independente por stem. Eles podem derivar em sincronismo.

Usar um único clock/sample cursor:

```text
cursor N
  read stem A [N:N+block]
  read stem B [N:N+block]
  ...
  apply gain/mute/solo
  sum -> limiter/protection only for monitoring
  output stream
```

O limiter/proteção do player nunca modifica arquivos exportados.

### MVP do player

- play/pause;
- seek;
- timeline;
- original/stems;
- mute/solo;
- ganho por stem;
- duração e tempo atual.

Sem waveform editing.

## Persistência

Sem banco de dados. Usar JSON pequeno para settings/jobs recentes, e manifests ao lado do output.

Cada job concluído grava `manifest.json` com:

- hash do input;
- versões do app/backend;
- device;
- pipeline e parâmetros;
- ids + hashes dos modelos;
- timestamps/duração;
- artifacts e propriedades de áudio;
- warnings.

## Erros

Categorias mínimas:

- `EnvironmentError` — GPU/runtime/tool ausente;
- `ModelMissingError`;
- `ModelIntegrityError`;
- `ModelLoadError`;
- `DecodeError`;
- `SeparationError`;
- `OutOfMemoryError`;
- `ExportError`;
- `Cancelled`.

Erro deve chegar à UI como dado estruturado + log técnico. Não expor stack trace cru como única mensagem.
