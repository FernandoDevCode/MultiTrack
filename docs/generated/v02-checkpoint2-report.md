# StemLab v0.2 — Checkpoint 2

**Resultado técnico:** PASS

**Data:** 2026-10-02

**Quality gate:** validação manual em músicas conhecidas ainda pendente. O detector permanece advisory/experimental.

## Dependências e artefatos

- Dependência direta nova: `transformers==5.18.0`, instalada somente na `.venv` local.
- Dependências transitivas normais foram pinadas no `requirements-lock.txt`.
- PyTorch `2.8.0+cu128`, NumPy `2.5.3`, soundfile `0.14.0` e audio-separator `0.47.0` permaneceram inalterados.
- Detector: `laion/larger_clap_music`.
- Revisão imutável: `a0b4534a14f58e20944452dff00a22a06ce629d1`.
- Licença declarada: Apache-2.0.
- Peso: `pytorch_model.bin`, 776.444.665 bytes.
- SHA-256: `5c289311f4a030d768af7ffbfdecd01b008aa64824211899a4e59f4f9d154fd1`.
- `scripts/install_instrument_detector.py --verify-only`: PASS antes de qualquer load.
- O verifier runtime confere repository/revision, tamanho e SHA-256 de todos os oito arquivos do receipt, identidade CLAP e ausência de Python remoto.

## Arquitetura

```text
MainWindow
  -> QProcessAnalysisJob
  -> run_analysis (processo efêmero)
  -> InstrumentationAnalysisService
  -> FfmpegWindowDecoder
  -> ClapInstrumentDetector
  -> larger_clap_music local / CUDA
  -> evidência serializável
  -> confirmação editável do usuário
  -> plan_for_targets
       -> no máximo um Core Stems pass
       -> specialist_unavailable explícito
```

Contratos de análise, evidência, targets confirmados e capability plan são dados puros, sem Torch ou PySide6. A UI não importa Transformers/Torch. O worker encerra após emitir o resultado.

## Sampling e similaridade

- Duração obtida pelo FFprobe local.
- Uma janela para faixas de até 10 s; acima disso, janelas de 10 s uniformemente espaçadas no intervalo válido.
- Cap rígido de oito janelas, sem aleatoriedade.
- Cada janela é decodificada por pipe FFmpeg como mono float32 a 48 kHz; nenhum intermediário lossy ou preload da música completa.
- Embeddings de prompts ingleses fixos são precomputados e normalizados.
- Cada target agrega o maior cosine similarity entre seus aliases por janela; o resultado preserva média, pico, hits top-3, melhor rank, scores e ranks por janela.
- Estados exibidos: sugerido, possível ou não sugerido. A UI não apresenta percentuais ou probabilidades.

## Taxonomia e planning

Canonical IDs exatos: vocals, drums, bass, guitar, piano, keys, synth_pad, organ, percussion, strings, brass, woodwind e choir.

- vocals/drums/bass/guitar/piano convergem para um único `six-stems`/Core Stems pass.
- keys/synth_pad/organ/percussion/strings/brass/woodwind/choir são `specialist_unavailable`.
- Nenhum alvo indisponível é rotulado ou mapeado para `other`.
- O resultado do detector nunca inicia separação; checkboxes confirmados pelo usuário são a fonte do plano.

## Evidência offline e segurança

- `local_files_only=True`, `trust_remote_code=False`, `weights_only=True` e `use_safetensors=False` validados por teste.
- Worker recebe `HF_HUB_OFFLINE=1` e `TRANSFORMERS_OFFLINE=1`.
- Smoke real passou com proxies HTTP(S) inválidos.
- Input SHA-256 antes/depois permaneceu idêntico.
- Nenhum prompt, checkpoint ou path de modelo arbitrário é aceito pela UI.

## Runtime e VRAM

Smoke CLAP real em RTX 5060/CUDA, fixture sintética local de 10 s:

- runtime total: 16,407 s;
- pico CUDA alocado: 823.896.576 bytes;
- pico CUDA reservado: 868.220.928 bytes;
- worker QProcess encerrou em estado `NotRunning`.

Imediatamente depois, o smoke BS-RoFormer SW passou em outro processo, estabelecendo que não houve conflito residual de VRAM.

## Testes

- `python -m pytest -q`: 46 passed, 3 skipped (smokes opt-in executados separadamente).
- Unitários: window planning/cap 8, aliases/taxonomia, agregação determinística, serialização, input hash, override, collapse de cinco targets Core para um pass, unsupported explícito, receipt/hash inválido e flags local-only.
- UI fake/QTimer: responsividade, sugestões editáveis, reanálise e ausência de separação automática.
- Regressão QProcess/path Unicode: PASS.
- Smoke CLAP local/CUDA/QProcess/offline: 1 passed.
- Smoke BS-RoFormer após CLAP: 1 passed.
- Smoke UI/QProcess Core Stems: 1 passed.
- `python -m pip check`: PASS.
- `python scripts/doctor.py`: PASS, incluindo Transformers e receipt/hash do detector.

## Limitações

- Similaridade CLAP não é probabilidade calibrada nem prova de presença.
- A regra de sugestão é determinística, mas sua utilidade musical exige o quality gate manual.
- Não há inferência de quantidade de guitarras.
- Targets sem capacidade Core permanecem somente sugestões explícitas; nenhum especialista foi implementado.
- Não foram iniciados Lead/Rhythm, Lead/Backing, SATB, Bass HQ, AudioSep, Mega 53, ensemble ou treinamento.

## Quality gate manual pendente

Validar algumas músicas conhecidas cobrindo instrumentos óbvios, falsos positivos, instrumentos presentes somente em seções, ambiguidades synth/pad versus piano/keys e presença de guitarra sem inferir contagem.
