# StemLab — estado do projeto e caminho de execução

> **Nome provisório:** `StemLab`.

StemLab é um aplicativo Windows local para separação de fontes musicais com modelos modernos de Music Source Separation (MSS). O objetivo final continua sendo alta qualidade, funcionamento offline após setup, stems comuns e uma área experimental para guitarra lead/rhythm quando houver evidência suficiente.

## Estado atual

- **Fase 0 — PASS:** runtime local, RTX 5060/CUDA, FFmpeg e `audio-separator` validados.
- **Fase 1 — PASS:** engine headless permanente implementado com `SeparationService` + adapter de `audio-separator`.
- **Fast Track v0.1 — PASS:** launcher, GUI PySide6, worker isolado e modos
  `Vocals HQ (experimental)` e `6 Stems` validados em CUDA.

## Abrir o aplicativo

Dê duplo clique em `START-STEMLAB.bat`. Escolha uma música, o modo e WAV ou
FLAC; cada execução cria uma pasta nova em `outputs/`. Ao concluir, use
**Abrir pasta dos stems**.

O modo `Vocals HQ` usa um peso local experimental cuja licença continua
desconhecida e não redistribuível pela decisão atual. O modo `6 Stems` produz
vocals, drums, bass, guitar, piano e other com `BS-RoFormer SW by jarredou`.

Relatórios em `docs/generated/` são snapshots históricos e não precisam ser reescritos quando o estado do Git/remoto muda depois.

## Estratégia de execução

O plano original de 7 fases continua válido como mapa de convergência, mas não é mais a sequência operacional imediata.

```text
Fase 0 PASS
   ↓
Fase 1 PASS
   ↓
Fast Track v0.1 PASS
   ↓
aplicativo utilizável
   ↓
gap analysis contra roadmap original
   ↓
hardening somente onde fizer diferença
```

Não estamos descartando o plano original. Estamos mudando a ordem para começar a usar o app antes.

## Ordem de leitura para a tarefa atual

1. `AGENTS.md`
2. `docs/11_FAST_TRACK.md`
3. `docs/01_SYSTEM_DESIGN.md`
4. `docs/09_UI_SPEC.md`
5. `docs/03_SECURITY_AND_SANDBOX.md`
6. `docs/04_TEST_AND_EVAL.md`
7. `docs/generated/phase1-report.md`

Depois use somente `prompts/FAST_TRACK_v01.md`.

## Roadmap original

`docs/05_ROADMAP.md` preserva as 7 fases como roadmap de convergência. Os prompts antigos permanecem no repo para referência e hardening futuro; não execute a sequência mecanicamente agora.

Após a v0.1, compare o estado real com as fases 2–6 e implemente somente os gaps necessários para chegar ao produto final desejado.
