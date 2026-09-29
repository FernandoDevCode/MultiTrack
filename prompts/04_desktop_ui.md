Config Codex
Modelo: GPT-5.6 Terra
Effort: Medium
Plan: OFF
Motivo: UX e arquitetura já estão especificadas; é implementação visual/integração com escopo fechado, sem necessidade de pesquisa arquitetural ampla.

# Fase 4 — Desktop UI + player

Leia `AGENTS.md`, `docs/09_UI_SPEC.md`, `docs/01_SYSTEM_DESIGN.md` nas seções de player/worker.

## Escopo permitido

- `src/stemlab/ui/**`
- `src/stemlab/audio/player/**`
- wiring mínimo em `src/stemlab/app/**`
- resources visuais próprios mínimos
- testes de lógica do mixer/player
- ajustes mínimos de dependências

Não implementar Guitar Lab, treinamento, cloud ou editor de áudio.

## Implementar

- PySide6 app shell;
- open/drag audio;
- Core Stems HQ;
- progress/cancel;
- timeline/waveform simples;
- um único mixer/clock para stems;
- play/pause/seek;
- mute/solo/gain monitor-only;
- export;
- Model Manager curado;
- Diagnostics.

## Invariantes

- não criar `QMediaPlayer` independente por stem;
- nenhuma operação GPU pesada no UI thread;
- volume da UI não altera arquivo exportado;
- input nunca é sobrescrito;
- player não soma original + stems sem ação explícita de A/B.

## Aceite

Fluxo completo funciona sem terminal: abrir música, separar, ouvir stems sincronizados, solo/mute e exportar. Rode smoke com seek repetido e documente qualquer drift.
