Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: OFF
Motivo: Fase 0 e engine headless já foram validados. A prioridade agora é entregar o menor corte vertical utilizável sem reabrir arquitetura nem construir infraestrutura futura.

# Fast Track v0.1 — app local utilizável

Leia primeiro:

- `AGENTS.md`
- `docs/11_FAST_TRACK.md`
- `docs/01_SYSTEM_DESIGN.md`
- `docs/09_UI_SPEC.md`
- `docs/03_SECURITY_AND_SANDBOX.md`
- `docs/04_TEST_AND_EVAL.md`
- `docs/generated/phase1-report.md`

## Objetivo

Entregar uma versão local do StemLab que eu consiga abrir por launcher, escolher uma música, escolher um modo, separar em CUDA e abrir a pasta dos stems.

Não reimplemente a Fase 1.

## Resultado obrigatório

Ao terminar:

1. `START-STEMLAB.bat` ou launcher equivalente abre a aplicação com o runtime local;
2. a GUI permite selecionar arquivo;
3. permite escolher `Vocals HQ (experimental)` ou `6 Stems (baseline)`;
4. permite WAV/FLAC;
5. inferência roda fora do processo/thread da UI;
6. estado de processamento é visível;
7. output é salvo sob `outputs/` em pasta não destrutiva;
8. a UI permite abrir a pasta final.

## Reutilização obrigatória

Preserve:

```text
SeparationService -> SeparationBackend -> AudioSeparatorBackend
```

A GUI e o worker não podem chamar `audio_separator` diretamente.

Se for necessário estender `ModelSpec`/adapter para suportar Demucs, faça a menor mudança coerente possível e cubra com testes. Não crie plugin system ou registry genérico.

## Modo Vocals HQ

Use o BS-RoFormer já instalado/validado.

Mantenha explícito:

- experimental/local;
- licença do peso desconhecida;
- não redistribuível por decisão atual.

## Modo 6 Stems

Produza vocals, drums, bass, guitar, piano e other.

Prefira `htdemucs_6s` se o backend instalado o suporta e o smoke local passar.

É permitido baixar somente os artefatos necessários para esse modo, sempre dentro do projeto. Registre origem e hash dos arquivos determinísticos que puderem ser verificados.

Não baixe vários modelos para comparar.

## Worker

Use o mecanismo Windows mais simples e confiável, preferencialmente `QProcess` ou subprocesso Python próprio.

Requisitos:

- inferência fora da UI;
- started/status/completed/failed;
- stdout/stderr controlados;
- resultado estruturado;
- sem `shell=True` com input do usuário;
- progresso indeterminado se não houver fração real.

Cancelamento é desejável, mas não bloqueia PASS se exigir arquitetura desproporcional. Nesse caso documente.

## GUI

PySide6, tela única e funcional.

Obrigatório:

- file picker;
- nome do arquivo;
- modo;
- WAV/FLAC;
- Separar;
- estado/progresso;
- resultado;
- Abrir pasta.

Drag/drop é opcional.

Não implemente waveform/player/mixer/Model Manager/Diagnostics avançado.

## Output

Use algo equivalente a:

```text
outputs/<track-slug>/<run-id>/
  stems...
  manifest.json
```

Não sobrescrever execução anterior silenciosamente.

## Segurança

Tudo mutável continua dentro do workspace.

Não instale globalmente, não altere PATH persistente, driver/CUDA, nem aceite modelo/URL arbitrário pela GUI.

Não use heurística de cancelamento de fase/EQ como substituto de MSS.

## Testes

Mantenha testes existentes.

Adicione testes focados para seleção de modo, construção segura do worker, parsing do resultado, estados básicos da UI e erro de modelo/job.

Smoke real obrigatório:

- executar caminho novo UI/worker;
- preferencialmente `6 Stems`;
- confirmar CUDA;
- confirmar seis stems válidos;
- confirmar input inalterado;
- confirmar manifest;
- confirmar UI não fica bloqueada durante o job.

Depois do modelo instalado, repetir smoke relevante sem rede quando prático.

## Prioridade

1. separação funcionando;
2. CUDA;
3. outputs corretos;
4. UI responsiva;
5. erro;
6. cancelamento;
7. aparência.

Corte itens inferiores se necessário. Não corte 1–4.

## Final

Entregue `PASS` somente se o modo 6 Stems completar end-to-end pela nova aplicação.

Relate como abrir, o que funciona, modelos usados/baixados, smoke real, testes, limitações, arquivos alterados e PASS/BLOCKED.

Não avance para benchmark amplo, player, Guitar Lab ou packaging.
