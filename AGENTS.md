# AGENTS.md — StemLab

## Missão

Construir um aplicativo Windows local para separação de fontes musicais com qualidade alta e comportamento verificável. Priorizar fidelidade, segurança de downloads e arquitetura simples. Não ampliar o escopo sem aprovação.

## Estado operacional atual

- Fase 0 (ambiente/GPU): **PASS**.
- Fase 1 (engine headless): **PASS**.
- Fast Track v0.1: **PASS**.
- v0.2 Checkpoint 1 — Core + Player: **PASS**, inclusive aceitação manual do usuário.
- v0.2 Checkpoint 2 — Instrument Analysis + Adaptive Planning: **technical PASS**; detector permanece advisory/experimental até o quality gate manual.
- Caminho ativo: **quality gate manual do Checkpoint 2**. Nenhum especialista posterior foi iniciado.
- O roadmap original de 7 fases em `docs/05_ROADMAP.md` continua válido como mapa de convergência/hardening. Ele não deve ser executado mecanicamente fase a fase enquanto o Fast Track estiver ativo.
- Depois da v0.1 utilizável, faça um **gap analysis** contra as fases originais e implemente somente o que ainda trouxer valor.

## Fontes de verdade

- Para o caminho ativo imediato: `docs/13_V02_CHECKPOINT2.md`.
- `docs/12_V02_CHECKPOINT1.md` e `docs/11_FAST_TRACK.md` permanecem históricos.
- Para produto e escopo final: `docs/00_PRODUCT.md`.
- Para limites arquiteturais: `docs/01_SYSTEM_DESIGN.md`.
- Para escolha/promulgação de modelos: `docs/02_MODEL_STRATEGY.md` e a skill `model-evaluation`.
- Para downloads, pesos e permissões: `docs/03_SECURITY_AND_SANDBOX.md`.
- Para validação: `docs/04_TEST_AND_EVAL.md`.
- Para convergência futura: `docs/05_ROADMAP.md`.
- Registre decisões novas em `docs/06_DECISIONS.md`; não reescreva decisões anteriores silenciosamente.

Leia somente os documentos relevantes à tarefa atual. Não faça varredura completa da documentação para uma alteração pequena.

## Invariantes

1. **Local-first.** Depois de runtime e modelos instalados, separar e reproduzir áudio não pode exigir internet.
2. **Nada global sem aprovação.** Não instalar/atualizar drivers, CUDA Toolkit, Python global, Visual Studio, Chocolatey, winget, Conda global ou software de sistema sem autorização explícita.
3. **Pasta autocontida durante desenvolvimento.** `.venv/`, `.cache/`, `.tmp/`, `models/`, `tools/`, `outputs/`, `bench/private/` e artefatos mutáveis devem ficar sob a raiz do projeto.
4. **Áudio de entrada é somente leitura.** Nunca sobrescrever ou modificar o arquivo original do usuário.
5. **Sem intermediários lossy.** O pipeline interno usa PCM/float lossless. MP3/AAC são apenas entrada ou export opcional.
6. **Sem normalização silenciosa por stem.** Não alterar ganho relativo entre stems sem opção explícita e teste correspondente.
7. **Model weights são código potencialmente hostil.** Só carregar pesos explicitamente aprovados para o projeto, com origem e SHA-256 conhecidos. Pesos de licença/origem incerta nunca viram default distribuível.
8. **Não executar modelo arbitrário.** MVP não terá “abrir qualquer .ckpt/.pth”.
9. **UI não roda inferência.** Inferência pesada vive fora do processo/thread de UI.
10. **Um modelo pesado por vez por padrão.** Descarregar entre etapas para controlar VRAM.
11. **Lead/rhythm é experimental até provar.** Não rotular como estável por impressão subjetiva de uma música.
12. **Sem telemetria e sem upload de áudio.** Nenhuma música sai da máquina.
13. **Sem overengineering.** Não introduzir banco de dados, servidor web, Docker, Electron/Tauri, broker de jobs, plugin system genérico ou DAG engine até existir necessidade concreta.

## Stack-base

- Python 3.12.
- PySide6 para UI.
- PyTorch/CUDA para modelos PyTorch.
- `audio-separator` atrás de adapter próprio.
- `soundfile` para I/O PCM/FLAC/WAV.
- FFmpeg local em `tools/ffmpeg/`.
- `pytest` para testes.

A matriz validada na Fase 0 está em `docs/generated/environment-report.md`. Não “atualize para o mais novo” por reflexo.

## Arquitetura já existente

A Fase 1 criou:

```text
CLI -> SeparationService -> SeparationBackend -> AudioSeparatorBackend
```

Essa seam é permanente. No Fast Track:

- reutilize `SeparationService`; não crie um segundo engine;
- UI nunca importa `audio_separator` nem executa Torch diretamente;
- um worker/subprocesso mínimo pode chamar o mesmo serviço/CLI;
- não construa ainda registry genérico, JobController completo ou player multitrack se não forem necessários para v0.1.

## Estrutura-alvo de longo prazo

```text
src/stemlab/
  app/
  domain/
  separation/
  audio/
  models/
  workers/
  ui/
resources/
scripts/
tests/
bench/
models/
.cache/
.tmp/
outputs/
```

A ausência temporária de algumas dessas pastas durante o Fast Track é intencional.

## Regras de implementação

- Tipos e contratos do domínio não importam PySide6 nem torch.
- UI depende de `app`, não diretamente de `audio-separator`.
- `audio-separator`, Demucs, RoFormer etc. são detalhes de adapters.
- Comunicação UI ↔ worker usa dados serializáveis; não passar objetos Torch/PySide entre processos.
- Subprocessos usam lista de argumentos, nunca `shell=True` com string construída a partir de input do usuário.
- Paths vindos da UI são dados, não comandos.
- Downloads escrevem primeiro em `.partial` e validam integridade quando aplicável.
- Logs não podem conter tokens/segredos.

## Gate mínimo por mudança

- `python -m pytest`
- checagem de tipos/lint configurada, quando existir
- smoke relevante
- para pipeline: duração, sample rate, canais, finitude e input intacto
- para mudança de modelo/default: usar `model-evaluation`

Durante o Fast Track, use também o gate de `docs/11_FAST_TRACK.md`.

## Git

- Não fazer push, release, tag ou publicar artefato sem pedido explícito.
- Não usar uma execução inteira do agente apenas para commit/push.
- Não commitar modelos, caches, músicas privadas, outputs privados ou ambientes virtuais.
