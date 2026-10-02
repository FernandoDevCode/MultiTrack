# StemLab — estado do projeto e caminho de execução

> **Nome provisório:** `StemLab`.

StemLab é um aplicativo Windows local para separação de fontes musicais com modelos modernos de Music Source Separation (MSS). O objetivo final continua sendo alta qualidade, funcionamento offline após setup, stems comuns e uma área experimental para guitarra lead/rhythm quando houver evidência suficiente.

## Estado atual

- **Fase 0 — PASS:** runtime local, RTX 5060/CUDA, FFmpeg e `audio-separator` validados.
- **Fase 1 — PASS:** engine headless permanente implementado com `SeparationService` + adapter de `audio-separator`.
- **Fast Track v0.1 — PASS:** launcher, GUI PySide6 e worker isolado validados em CUDA.
- **BS-RoFormer SW migration — PASS:** `Core Stems`/seis stems roda localmente em CUDA.
- **v0.2 Checkpoint 1 — PASS:** Core Stems, player multistem sincronizado, A/B, export byte-identical, extração lossless de áudio de vídeo e seam mínima de pipelines.
- **v0.2 Checkpoint 1 — aceitação manual PASS:** player/export/extração e paths Unicode validados pelo usuário.
- **Agora:** v0.2 Checkpoint 2 — análise local de instrumentação com CLAP + confirmação humana + planejamento adaptativo.

## Abrir o aplicativo

Dê duplo clique em `START-STEMLAB.bat`. Escolha uma música, o preset Core
Stems e WAV ou FLAC; cada execução cria uma pasta nova em `outputs/`. Ao
concluir, use o player sincronizado, Mute/Solo/Volume, A/B Original/Stems,
exporte um ou todos os stems ou abra a pasta do resultado.

O preset `Core Stems` produz vocals, drums, bass, guitar, piano e other com o
BS-RoFormer SW local já aprovado. A ação separada **Extrair áudio de vídeo…**
gera WAV ou FLAC lossless com o FFmpeg local.

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

Para a tarefa atual use `docs/13_V02_CHECKPOINT2.md` e `prompts/V02_CHECKPOINT2.md`. Checkpoint 1 e Fast Track são históricos.

## Roadmap original

`docs/05_ROADMAP.md` preserva as 7 fases como roadmap de convergência. Os prompts antigos permanecem no repo para referência e hardening futuro; não execute a sequência mecanicamente agora.

Após a v0.1, compare o estado real com as fases 2–6 e implemente somente os gaps necessários para chegar ao produto final desejado.
