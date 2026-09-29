# AGENTS.md — StemLab

## Missão

Construir um aplicativo Windows local para separação de fontes musicais com qualidade alta e comportamento verificável. Priorizar fidelidade, segurança de downloads e arquitetura simples. Não ampliar o escopo sem aprovação.

## Fontes de verdade

- Para produto e escopo: `docs/00_PRODUCT.md`.
- Para limites arquiteturais: `docs/01_SYSTEM_DESIGN.md`.
- Para escolha/promulgação de modelos: `docs/02_MODEL_STRATEGY.md` e a skill `model-evaluation`.
- Para downloads, pesos e permissões: `docs/03_SECURITY_AND_SANDBOX.md`.
- Para validação: `docs/04_TEST_AND_EVAL.md`.
- Para ordem oficial das fases: `docs/05_ROADMAP.md`.
- Registre decisões novas em `docs/06_DECISIONS.md`; não reescreva decisões anteriores silenciosamente.

Leia somente os documentos relevantes à tarefa atual. Não faça varredura completa da documentação para uma alteração pequena.

## Invariantes

1. **Local-first.** Depois de runtime e modelos instalados, separar e reproduzir áudio não pode exigir internet.
2. **Nada global sem aprovação.** Não instalar/atualizar drivers, CUDA Toolkit, Python global, Visual Studio, Chocolatey, winget, Conda global ou software de sistema sem autorização explícita.
3. **Pasta autocontida durante desenvolvimento.** `.venv/`, `.cache/`, `.tmp/`, `models/`, `tools/`, `outputs/`, `bench/private/` e artefatos mutáveis devem ficar sob a raiz do projeto.
4. **Áudio de entrada é somente leitura.** Nunca sobrescrever ou modificar o arquivo original do usuário.
5. **Sem intermediários lossy.** O pipeline interno usa PCM/float lossless. MP3/AAC são apenas entrada ou export opcional.
6. **Sem normalização silenciosa por stem.** Não alterar ganho relativo entre stems sem opção explícita e teste correspondente.
7. **Model weights são código potencialmente hostil.** Só carregar pesos permitidos no registry, com origem e SHA-256 conhecidos. Pesos de licença/origem incerta nunca viram default de produção.
8. **Não executar modelo arbitrário.** MVP não terá “abrir qualquer .ckpt/.pth”.
9. **UI não roda inferência.** Inferência pesada vive em worker process; fechar/cancelar um job não deve travar a UI.
10. **Um modelo pesado por vez por padrão.** Descarregar entre etapas para controlar VRAM.
11. **Lead/rhythm é experimental até provar.** Não rotular como estável por impressão subjetiva de uma música.
12. **Sem telemetria e sem upload de áudio.** Nenhuma música sai da máquina.
13. **Sem overengineering.** Não introduzir banco de dados, servidor web, Docker, Electron/Tauri, broker de jobs, plugin system genérico ou DAG engine até existir necessidade concreta.

## Stack-base

- Python 3.12 como alvo inicial.
- PySide6 para UI.
- PyTorch/CUDA para modelos PyTorch.
- `audio-separator` atrás de adapter próprio como ponto de partida.
- `soundfile` para I/O PCM/FLAC/WAV.
- FFmpeg local em `tools/ffmpeg/` quando necessário para formatos comprimidos.
- `sounddevice`/PortAudio para o mixer/player sincronizado, se o spike confirmar estabilidade no Windows.
- `pytest` para testes.

A versão exata de Torch/CUDA deve ser decidida na fase 0 depois de smoke test no hardware real e então pinada. Não “atualize para o mais novo” por reflexo.

## Estrutura-alvo

```text
src/stemlab/
  app/            # casos de uso e orquestração
  domain/         # tipos/contratos puros
  separation/     # adapters de modelos e pipeline
  audio/          # decode/export/player/mix
  models/         # registry, downloader, integrity
  workers/        # processo de inferência e protocolo de progresso
  ui/             # PySide6
resources/
  models.json
scripts/
tests/
bench/
  private/        # gitignored; áudio do usuário
  reports/
models/           # gitignored
.cache/           # gitignored
.tmp/             # gitignored
outputs/          # gitignored
```

## Regras de implementação

- Tipos e contratos do domínio não importam PySide6 nem torch.
- UI depende de `app`, não diretamente de `audio-separator`.
- `audio-separator`, Demucs, RoFormer etc. são detalhes de adapters.
- Comunicação UI ↔ worker usa mensagens estruturadas e versionadas (JSON serializável); não passar objetos Torch/PySide entre processos.
- Subprocessos usam lista de argumentos, nunca `shell=True` com string construída a partir de input do usuário.
- Paths vindos da UI devem ser tratados como dados, não comandos.
- Downloads devem escrever primeiro em arquivo `.partial`, validar tamanho/hash e só então fazer rename atômico.
- Logs não podem conter tokens/segredos; o projeto não precisa de segredo nenhum para funcionar.

## Gate mínimo por mudança

- `python -m pytest`
- checagem de tipos/lint configurada no projeto, quando existir
- smoke relevante da feature alterada
- para mudanças no pipeline: invariantes de duração, sample rate, canais, finitude e não sobrescrita do input
- para mudança de modelo/default: usar skill `model-evaluation`; testes unitários não são evidência suficiente de qualidade sonora

## Git

- Não fazer push, release, tag ou publicar artefato sem pedido explícito.
- Não usar uma execução inteira do agente apenas para commit/push.
- Não commitar modelos, caches, músicas privadas, outputs de benchmark privados ou ambientes virtuais.
