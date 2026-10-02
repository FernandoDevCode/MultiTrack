# StemLab v0.2 — Checkpoint 1

**Resultado:** PASS

**Data:** 2026-10-02

**Escopo seguinte:** Checkpoint 2 não iniciado.

## Dependências

- Nova dependência runtime única: `sounddevice==0.5.6`.
- Pin adicionado em `pyproject.toml` e `requirements-lock.txt`.
- Instalação feita somente na `.venv` local, usando cache em `.cache/pip`.
- Nenhuma versão existente de NumPy, soundfile, PyTorch, CUDA ou modelo foi alterada.

## Arquitetura resultante

```text
Core Stems (PipelinePlan serializável)
  -> SeparationStep(mode_id="six-stems")
  -> SeparationService
  -> AudioSeparatorBackend
  -> BS-RoFormer SW

Resultado
  -> MultiStemPlayer
       -> SoundFile por fonte, leitura em blocos
       -> cursor de frame compartilhado
       -> um sounddevice.OutputStream
       -> mix NumPy de Mute/Solo/Volume ou Original exclusivo
  -> ExportService (cópia exclusiva + SHA-256)
  -> QProcessAudioExtraction (FFmpeg local + probe + hash do input)
```

O callback de áudio não acessa widgets. A UI consulta estado leve por `QTimer`.
Trocar/fechar uma sessão encerra o stream e fecha todos os handles. Falha ao
abrir o dispositivo é recuperável e não invalida separação ou exportação.

## Funcionalidade estabelecida

- Apresentação `6 Stems` renomeada para **Core Stems**.
- O plano Core Stems contém exatamente um passo e preserva `six-stems`,
  BS-RoFormer SW e os papéis vocals, drums, bass, guitar, piano e other.
- Player streaming com Play/Pause/Seek, cursor único, tempo atual/duração,
  Mute, múltiplos Solo e volume somente de monitoramento.
- A/B exclusivo: `Original` e `Stems` nunca são somados.
- Original incompatível com soundfile pode virar FLAC lossless dentro da pasta
  do run via FFmpeg, sem modificar o arquivo de entrada.
- Export individual e em lote preserva extensão e bytes; colisões são erro.
- Extração separada de MP4/MKV/MOV/WebM/AVI/M4V para WAV PCM ou FLAC, primeiro
  stream de áudio, por QProcess assíncrono e argumentos em lista.
- Tela única com transport, A/B, uma linha por stem, exportação e abrir pasta.

## Evidências automatizadas

- `python -m pytest -q`: **34 passed, 2 skipped**. Os skips são somente os
  smokes opt-in executados separadamente abaixo.
- Player sintético WAV/FLAC: Play/Pause/Seek, cursor, blocos sem preload,
  Mute/Solo/múltiplos Solo, volume sem alterar arquivos e A/B exclusivo: PASS.
- Export one/all, SHA-256 antes/depois e colisão sem overwrite: PASS.
- Extração QProcess de fixture MP4 para WAV e FLAC, probe/finitude, heartbeat da
  UI e hash do vídeo intacto: PASS.
- Smoke CUDA BS-RoFormer SW:
  `STEMLAB_RUN_GPU_SMOKE=1 ... test_audio_separator_gpu.py`: **1 passed**.
- Smoke UI/QProcess de separação:
  `STEMLAB_RUN_FAST_TRACK_SMOKE=1 ... test_fast_track_ui_worker.py`: **1 passed**.
- `python -m pip check`: **No broken requirements found**.
- `python scripts/doctor.py`: **PASS**, incluindo Python local, CUDA, RTX 5060,
  FFmpeg/FFprobe, pesos/hash e `sounddevice==0.5.6`.
- Smoke opcional de dispositivo: abriu, iniciou, parou e fechou um
  `sounddevice.OutputStream` estéreo 44,1 kHz no dispositivo `LG TV`: PASS.

Todos os testes com temporários usaram `TEMP`, `TMP` e `--basetemp` dentro de
`.tmp/`, porque o Temp global do host não é gravável no sandbox.

## Segurança e regressão

- Input de áudio/vídeo verificado por SHA-256 e nunca sobrescrito.
- Nenhum download ou alteração de modelo; hashes BS-RoFormer SW preservados.
- Nenhum `shell=True`; paths da UI são argumentos de QProcess, não comandos.
- Nenhum upload, telemetria, servidor, banco, registry genérico ou DAG.
- Nenhum detector, especialista, Lead/Rhythm, Lead/Backing, SATB, Bass HQ ou
  ensemble foi iniciado.

## Arquivos alterados/criados

- Dependências: `pyproject.toml`, `requirements-lock.txt`.
- Core/app: `src/stemlab/app/pipelines.py`, `audio_extraction.py`,
  `export_service.py`, `modes.py`, `__init__.py`.
- Áudio: `src/stemlab/audio/multistem_player.py`, `__init__.py`.
- Worker/UI: `src/stemlab/workers/qprocess_audio.py`,
  `src/stemlab/ui/main_window.py`, `stem_mixer.py`.
- Verificação: `scripts/doctor.py` e testes de player, export, extração,
  pipelines e UI.
- Status: `README-FIRST.md` e este relatório.

## Limitações

- O checkpoint não reivindica melhoria de qualidade de separação; reutiliza o
  BS-RoFormer SW previamente aprovado.
- Não há waveform nem edição multitrack, por definição deste checkpoint.
- A seleção de dispositivo de áudio usa o default do sistema; UI de escolha de
  dispositivo não faz parte deste checkpoint.

## Teste manual

O gate automatizado e o smoke real de output stream passaram. Ainda é
recomendável, mas não bloqueante, executar a aceitação humana completa com uma
música real: ouvir, alternar solos, buscar na timeline, comparar A/B e conferir
os arquivos exportados no destino escolhido.
