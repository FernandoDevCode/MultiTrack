Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: OFF
Motivo: arquitetura do worker e protocolo já está definida; a implementação é sensível por multiprocessing/CUDA no Windows, então usamos o modelo mais forte sem reabrir produto.

# Fase 3 — Worker process e jobs

Leia `AGENTS.md`, `docs/01_SYSTEM_DESIGN.md`, `docs/04_TEST_AND_EVAL.md`.

## Escopo permitido

- `src/stemlab/app/**`
- `src/stemlab/workers/**`
- `src/stemlab/separation/**` apenas integração necessária
- `tests/**`
- `docs/generated/worker-report.md`

Não criar UI.

## Implementar

- JobController;
- PipelinePlanner simples, sem engine DAG genérica;
- worker process Windows-safe;
- protocolo versionado JSON para started/progress/artifact/warning/failed/completed;
- cancelamento;
- teardown/cleanup;
- erro estruturado de OOM/model/decode;
- execução sequencial de modelos pesados por padrão;
- manifest final só marcado completed depois de outputs validados.

## Testes

- worker feliz com adapter fake;
- erro do worker não derruba controlador;
- cancelamento;
- evento inválido/protocol mismatch;
- cleanup temporário;
- smoke real CUDA com um clip curto;
- verificar que processo encerra e VRAM não fica presa indefinidamente pelo worker morto.

## Aceite

Job pesado pode ser iniciado, observado e cancelado sem travar o processo controlador; falhas são dados estruturados e outputs parciais não se passam por completos.
