Config Codex
Modelo: GPT-5.6 Terra
Effort: High
Plan: OFF
Motivo: após a Fase 0, o patch é fechado: criar contratos mínimos e um adapter baseline sem decisões de produto ou arquitetura novas.

# Fase 1 — Engine baseline

Pré-condição: `docs/generated/environment-report.md` existe e o CUDA smoke passou, ou o usuário aceitou explicitamente CPU fallback.

Leia `AGENTS.md`, `docs/01_SYSTEM_DESIGN.md`, `docs/04_TEST_AND_EVAL.md` e o relatório da Fase 0.

## Escopo permitido

- `src/stemlab/domain/**`
- `src/stemlab/separation/**`
- `src/stemlab/audio/**` apenas I/O/probe necessários ao baseline
- `scripts/separate-baseline.py`
- `tests/**`
- ajustes mínimos em `pyproject.toml`/lock
- `docs/generated/baseline-report.md`

Sem PySide6 UI, worker process, Model Manager ou lead/rhythm.

## Implementar

- tipos mínimos de Job/Stem artifact;
- adapter para `audio-separator` atrás de interface nossa;
- `model_file_dir` apontando para `<repo>/models`;
- um baseline multistem comprovado na Fase 0, preferencialmente `htdemucs_6s` se funcionar;
- output lossless e manifest de execução;
- script CLI simples para rodar em um input explícito e output explícito;
- nenhuma normalização por-stem silenciosa;
- testes de path, manifest e invariantes de áudio.

Use `bench/private/` para qualquer música do usuário e mantenha gitignored.

## Validação

- `pytest`;
- fixture sintética para alinhamento/I/O;
- um smoke real manual/privado quando disponível;
- confirmar input byte-identical antes/depois;
- registrar duração, sample rate, canais, stems, runtime e pico de VRAM se possível.

## Aceite

Um comando local consegue gerar stems baseline e `manifest.json` sem UI, sem internet após o modelo estar presente e sem tocar o original.

Pare e reporte evidência. Não avance.
