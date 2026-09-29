# StemLab — Fast Track v0.1

**Resultado:** PASS  
**Data:** 2026-09-29  
**Escopo:** somente Fast Track v0.1.

## Como abrir

Dê duplo clique em `START-STEMLAB.bat` na raiz do projeto. O launcher usa
somente `.venv/Scripts/pythonw.exe`, adiciona o FFmpeg local ao `PATH` do
processo e mantém temporários/caches/modelos dentro do workspace.

Na tela única:

1. clique em **Escolher música…**;
2. escolha `Vocals HQ (experimental)` ou `6 Stems (baseline)`;
3. escolha WAV ou FLAC;
4. clique em **Separar**;
5. ao concluir, clique em **Abrir pasta dos stems**.

Cada execução usa um destino novo:

```text
outputs/<track-slug>/<run-id>/
  stems...
  manifest.json
```

## Corte vertical entregue

```text
START-STEMLAB.bat
  -> PySide6 MainWindow
  -> QProcess + protocolo JSON prefixado
  -> stemlab.workers.run_job
  -> SeparationService existente
  -> AudioSeparatorBackend existente
  -> Torch/CUDA
```

A UI não importa Torch nem `audio_separator`. O worker chama o mesmo
`SeparationService` da Fase 1; não existe um segundo engine. Os argumentos do
subprocesso são uma lista fornecida ao `QProcess`, sem shell ou interpolação de
paths do usuário.

Estados implementados: sem arquivo, pronto, iniciando, processando,
concluído e erro recuperável. O progresso é indeterminado porque o backend não
fornece fração confiável. Fechar a janela termina o worker ativo; não foi
adicionado um fluxo completo de cancelamento.

## Modos curados

### Vocals HQ (experimental)

- Modelo: BS-RoFormer Viperx 1297 já existente.
- Saídas: vocals e instrumental.
- Status visível na UI: experimental/local.
- Licença do peso: desconhecida.
- Redistribuição: não autorizada pela decisão atual.

### 6 Stems (baseline)

- Modelo: `htdemucs_6s` pelo loader Demucs v4 já incluído no
  `audio-separator` 0.47.0.
- Saídas exigidas: vocals, drums, bass, guitar, piano e other.
- Não foi instalado um segundo pacote Demucs e nenhum modelo alternativo foi
  baixado para comparação.

Artefatos baixados para `models/`:

| Artefato | Origem | Bytes | SHA-256 |
|---|---|---:|---|
| `5c90dfd2-34c22ccb.th` | `https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/5c90dfd2-34c22ccb.th` | 54,996,327 | `34c22ccb381c6f9fdbf324f04e1e2fe21aaaf293f5ded163a162697ff9a02ddd` |
| `htdemucs_6s.yaml` | `https://github.com/TRvlvr/model_repo/releases/download/all_public_uvr_models/htdemucs_6s.yaml` | 21 | `207405151270af8fd81c2373c25d27950916682ac91dca7884a11ce13dad6f58` |

Os downloads usaram `.partial` e rename após conclusão. Ambos os hashes são
verificados pelo `SeparationService` antes de o adapter carregar o modelo. O
identificador do backend também precisa corresponder a um desses artefatos
verificados, impedindo URL ou checkpoint arbitrário pela UI.

## Dependência de UI

Foi adicionada somente `PySide6-Essentials==6.9.2` (e sua dependência
`shiboken6==6.9.2`) à `.venv` local e ao lock. Nenhuma instalação global ou
alteração persistente de PATH foi feita.

## Smoke end-to-end

Fixture: mix sintética local de 10,0 s da Fase 0.  
Input SHA-256 antes/depois:
`8e7c53fe531f2a105a5c734389736f7183940a5647a05b24509ca78b0ee54fa0`.

### Worker direto, WAV

- Caminho novo `stemlab.workers.run_job`.
- Device solicitado/efetivo: CUDA/CUDA.
- Seis stems válidos, 44.1 kHz, estéreo e 10,0 s.
- Tempo load + inferência: 6.769 s.
- Pico CUDA alocado: 702,034,944 bytes.
- Pico CUDA reservado: 910,163,968 bytes.
- Warnings/fallback: nenhum.
- Manifesto: `outputs/fast-track-smoke/20260929-6stems-online/manifest.json`.

### UI + QProcess, FLAC e offline

- Execução iniciada por `MainWindow` através de `QProcess`.
- `HTTP_PROXY` e `HTTPS_PROXY` apontados para endpoint inválido; o job concluiu
  usando somente artefatos locais.
- Seis stems FLAC válidos, 44.1 kHz, estéreo e 10,0 s.
- Device efetivo: CUDA; precisão efetiva: autocast.
- Tempo load + inferência: 3.982 s.
- Pico CUDA alocado: 702,034,944 bytes (0.654 GiB).
- Pico CUDA reservado: 910,163,968 bytes (0.848 GiB).
- Warnings/fallback: nenhum.
- Heartbeat Qt a cada 50 ms permaneceu ativo durante o job, provando que a UI
  não ficou bloqueada.
- Manifesto: `outputs/phase0-synthetic-mix/20260929-201741-925424/manifest.json`.
- O botão **Abrir pasta dos stems** ficou habilitado e seu destino foi validado.

O smoke do launcher foi executado em modo offscreen com saída automática de
teste: código 0, janela/processo criado e nenhum `pythonw` órfão após o término.

## Testes e gates

```text
python -m pytest -q
23 passed, 2 skipped (smokes pesados opt-in)

STEMLAB_RUN_GPU_SMOKE=1
STEMLAB_RUN_FAST_TRACK_SMOKE=1
python -m pytest tests/integration -q -rA
2 passed

python -m pip check
No broken requirements found.

python scripts/doctor.py
PASS — Python local, RTX 5060/CUDA, Torch, audio-separator, PySide6,
       FFmpeg, BS-RoFormer e htdemucs_6s verificados.
```

Não havia lint/typecheck configurado, portanto nenhuma stack adicional foi
introduzida. `git status --short --ignored` confirmou que `.venv/`, modelos,
caches, `.tmp/`, `outputs/` e ferramentas continuam fora do Git.

## Arquivos relevantes

- `START-STEMLAB.bat`
- `src/stemlab/app/modes.py`
- `src/stemlab/workers/protocol.py`
- `src/stemlab/workers/run_job.py`
- `src/stemlab/workers/qprocess_job.py`
- `src/stemlab/ui/main_window.py`
- `tests/test_fast_track_modes.py`
- `tests/test_worker_protocol.py`
- `tests/test_fast_track_ui.py`
- `tests/integration/test_fast_track_ui_worker.py`

## Limitações deliberadas

- Sem player, waveform, mixer, Model Manager, benchmark amplo, Guitar Lab,
  servidor, banco, updater ou packaging.
- Sem barra de progresso fracionária; o indicador é indeterminado.
- Cancelamento explícito não foi incluído; fechar a janela termina o processo.
- O BS-RoFormer continua experimental e não redistribuível pela decisão atual.
- `htdemucs_6s` é baseline funcional; qualidade comparativa e política de
  redistribuição permanecem gates posteriores.

Nenhuma funcionalidade além do Fast Track v0.1 foi iniciada.
