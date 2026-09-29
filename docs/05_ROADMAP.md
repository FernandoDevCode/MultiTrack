# Roadmap oficial

## Fase 0 — Environment & dependency spike

**Objetivo:** provar que o ambiente Windows/GPU e as dependências funcionam sem alterar o sistema globalmente.

Entregas:

- estrutura mínima do repo;
- `.venv` local;
- script de dev environment localizando caches/temp no repo;
- Python 3.12 confirmado;
- Torch/CUDA smoke no hardware real;
- `audio-separator` importado;
- catálogo de modelos enumerado sem escolher default final;
- FFmpeg local somente se necessário para o smoke;
- relatório `docs/generated/environment-report.md`.

Gate: GPU smoke + um comando de `audio-separator`/API funcionando. Nenhuma GUI.

## Fase 1 — Engine baseline

**Objetivo:** separar um arquivo por CLI/caso de uso interno.

Implementar:

- contratos de domínio mínimos;
- `AudioSeparatorAdapter`;
- uma baseline 6-stem (Demucs 6s ou equivalente comprovado no spike);
- saída lossless;
- manifest do job;
- invariantes de áudio e testes.

Gate: um clip privado do usuário pode virar stems sem UI e sem tocar arquivo original.

## Fase 2 — Registry, downloader e benchmark harness

**Objetivo:** deixar seleção de modelo auditável.

Implementar:

- `resources/models.json` nosso;
- download com hash e `.partial`;
- estados `approved/experimental/rejected`;
- harness para comparar candidatos;
- relatório de runtime/VRAM/métricas;
- qualificar o primeiro pipeline HQ de core stems.

Gate: default de core stems escolhido por evidência registrada.

## Fase 3 — Worker + jobs

**Objetivo:** separar inferência da UI.

Implementar:

- worker process;
- protocolo JSON de eventos;
- progress/cancel/failure;
- limpeza previsível de VRAM por estágio/processo;
- retry somente quando seguro;
- smoke de OOM/cancelamento.

Gate: job pesado não congela controlador e cancelamento não deixa estado inválido.

## Fase 4 — Desktop UI + player

**Objetivo:** tornar o engine utilizável.

Implementar somente:

- open/drag file;
- preset HQ;
- progress/cancel;
- waveform/timeline simples;
- play/pause/seek;
- solo/mute/volume;
- export;
- Model Manager;
- Diagnostics.

Gate: fluxo completo sem terminal para o usuário normal.

## Fase 5 — Guitar Lab research gate

**Objetivo:** descobrir se Lead/Rhythm local é bom o suficiente.

Atividades:

- pesquisar checkpoint local role-aware atual com origem/licença;
- testar direto na mix vs. two-stage;
- comparar com generic guitar baseline;
- medir leakage e qualidade;
- documentar falhas por tipo de mixagem.

Saídas possíveis:

A. `approved`: integrar Lead/Rhythm como feature estável;
B. `experimental`: expor com rótulo e limitações claras;
C. `rejected`: manter somente Guitar e não fingir que o problema foi resolvido.

Gate: decisão explícita baseada no relatório. Não implementar UI estável antes do gate.

## Fase 6 — Packaging/release local

**Objetivo:** experiência repetível no Windows.

Preferência inicial:

- pacote one-folder/portable, não “one-file magic”;
- runtime e ferramentas locais;
- modelos baixados separadamente quando licença/tamanho pedirem;
- doctor/diagnostics;
- teste offline completo.

Gate: instalar/descompactar em pasta nova, baixar/validar modelo, desligar internet, separar e reproduzir uma música.

## Pós-MVP

Somente depois:

- Max/ensemble mode;
- stems de bateria detalhados;
- acoustic/electric guitar;
- batch processing;
- fila persistente;
- packaging mais amigável;
- pesquisa/fine-tune próprio para Lead/Rhythm caso os pesos públicos não atinjam qualidade.
