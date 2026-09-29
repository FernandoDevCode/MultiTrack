# Roadmap oficial de convergência

## Como ler este documento agora

Este documento preserva o plano original de 7 fases. Ele **não é mais a sequência operacional obrigatória imediata**.

Estado atual:

- Fase 0: **PASS**
- Fase 1: **PASS**
- Fast Track v0.1: **ATIVO** — ver `docs/11_FAST_TRACK.md`
- Fases 2–6: referência de hardening/convergência depois da v0.1

Fluxo atual:

```text
0 PASS -> 1 PASS -> FAST TRACK v0.1 -> GAP ANALYSIS -> gaps úteis das fases 2–6
```

O objetivo é chegar ao mesmo nível final com uma versão utilizável muito antes.

## Fase 0 — Environment & dependency spike — PASS

Ambiente Windows/GPU local validado. Evidência em `docs/generated/environment-report.md`.

## Fase 1 — Engine baseline — PASS

Engine headless permanente implementado. Evidência em `docs/generated/phase1-report.md`.

## Fase 2 — Registry, downloader e benchmark harness

**Papel após Fast Track:** hardening da seleção/download e qualificação de defaults.

Quando necessário:

- registry curado;
- download com hash e `.partial`;
- estados `approved/experimental/rejected`;
- harness de benchmark;
- qualificação do pipeline HQ.

Não bloquear a primeira UI utilizável por isso.

## Fase 3 — Worker + jobs

**Papel após Fast Track:** aprofundar o subprocesso simples da v0.1.

Adicionar conforme necessidade:

- protocolo versionado;
- progress granular verdadeiro;
- cancelamento robusto;
- limpeza previsível de VRAM;
- retry seguro;
- testes de OOM/cancelamento.

Se o worker mínimo da v0.1 estiver saudável, evoluir em vez de reescrever.

## Fase 4 — Desktop UI + player

**Papel após Fast Track:** aprofundar a UI mínima.

Adicionar conforme valor:

- waveform/timeline;
- player sincronizado;
- solo/mute/volume;
- export avançado;
- Model Manager;
- Diagnostics.

## Fase 5 — Guitar Lab research gate

Continua sendo gate separado. Saídas possíveis: `approved`, `experimental` ou `rejected`.

Lead/Rhythm não vira feature estável por atalho de cronograma.

## Fase 6 — Packaging/release local

Continua sendo a etapa de distribuição repetível:

- build portable/one-folder;
- runtime/ferramentas locais;
- modelos separados quando necessário;
- doctor;
- teste offline em pasta limpa.

## Pós-MVP

Somente depois:

- Max/ensemble;
- bateria detalhada;
- acoustic/electric guitar;
- batch;
- fila persistente;
- packaging mais amigável;
- fine-tune próprio se Guitar Lab justificar.

## Regra de gap analysis

Depois do Fast Track:

1. listar o que a v0.1 já resolveu;
2. mapear cada limitação real para as fases 2–6;
3. priorizar por impacto no uso/qualidade;
4. evitar reimplementar uma seam saudável apenas para “seguir o plano”.
