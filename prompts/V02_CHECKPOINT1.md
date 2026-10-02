Config Codex
Modelo: GPT-5.6 Sol
Effort: Medium
Plan: OFF
Motivo: o escopo, arquitetura e critérios estão fechados; a tarefa é implementação + testes locais, sem pesquisa de modelos.

# StemLab v0.2 — Checkpoint 1

Leia somente:
- `AGENTS.md`
- `docs/12_V02_CHECKPOINT1.md`
- `docs/09_UI_SPEC.md`
- `docs/03_SECURITY_AND_SANDBOX.md`
- `docs/generated/bs-roformer-sw-migration-report.md`
- arquivos de código/teste que forem diretamente necessários.

Execute integralmente o Checkpoint 1. Não avance para Checkpoint 2.

## Invariantes

- Não alterar nem substituir BS-RoFormer SW.
- Não baixar modelos.
- Não implementar detector de instrumentos.
- Não implementar Lead/Rhythm, Lead/Backing, SATB, Bass HQ, ensemble ou outros especialistas.
- Não alterar driver/CUDA/Python global.
- Não criar servidor, banco, plugin system ou DAG genérico.
- Entrada do usuário é read-only.
- UI não executa inferência.
- Não usar `shell=True`.
- Não fazer push/tag/release.

## Dependency budget

É permitido adicionar **somente uma dependência runtime nova** nesta tarefa:

`sounddevice==0.5.6`

Instale somente na `.venv` local e pine em `pyproject.toml` + `requirements-lock.txt`.
`numpy` e `soundfile` já existem no ambiente; não atualize por reflexo.

Rede, se necessária, é permitida somente para obter essa dependência do PyPI. Nenhum modelo ou outro artefato deve ser baixado.

## Arquivos esperados

Você pode modificar os arquivos existentes diretamente necessários e criar, se fizer sentido:

- `src/stemlab/audio/multistem_player.py`
- `src/stemlab/app/export_service.py`
- `src/stemlab/app/audio_extraction.py`
- `src/stemlab/app/pipelines.py`
- `src/stemlab/ui/stem_mixer.py`
- um wrapper QProcess pequeno para FFmpeg se necessário;
- testes correspondentes;
- documentação/report do checkpoint.

Não faça refactor amplo de `SeparationService` ou `AudioSeparatorBackend`.

## 1. Core Stems / pipeline seam

- Renomeie a apresentação UI de `6 Stems` para **Core Stems**.
- O pipeline atual continua usando BS-RoFormer SW e exatamente:
  vocals, drums, bass, guitar, piano, other.
- Introduza uma seam mínima de pipeline/plan em dados simples.
- Para esta versão, `Core Stems` resolve para um único passo usando o modo BS-RoFormer SW existente.
- Não construa roteador genérico nem DAG.

## 2. Multistem player

Implemente um único transport sincronizado.

Use:
- `soundfile` para leitura por blocos;
- `sounddevice==0.5.6` para um único stream de saída;
- `numpy` para mixar blocos.

Requisitos:
- streaming; nunca carregar a música completa em RAM;
- um shared frame cursor;
- Play/Pause/Seek;
- current time / duration;
- cada stem: Mute, Solo, Volume;
- múltiplos Solo permitidos;
- sem Solo: toca todos os não-mutados;
- com Solo: toca somente os soloados que não estiverem mutados;
- volume somente monitoramento;
- mudança de sessão/fechamento libera stream e SoundFile handles;
- nenhuma chamada de widget dentro do callback de áudio;
- erro de dispositivo de áudio é recuperável e não quebra separação/export.

Não crie um player independente por stem.

## 3. Original A/B

Implemente A/B exclusivo:
- modo Original toca somente Original;
- modo Stems toca somente o mix dos stems;
- nunca somar ambos acidentalmente.

Se o input não puder ser lido diretamente por `soundfile`, prepare uma cópia de monitoramento lossless usando FFmpeg local dentro do workspace/run. Nunca alterar o input.

## 4. Export

- botão por stem: exportar esse arquivo;
- botão Exportar todos;
- copiar os arquivos existentes byte-for-byte;
- preservar extensão;
- nunca sobrescrever silenciosamente;
- não normalizar/transcodificar;
- teste por SHA-256 antes/depois da cópia.

## 5. Extração de áudio de vídeo

Adicionar ação separada `Extrair áudio de vídeo…`.

- inputs: MP4/MKV/MOV/WebM/AVI/M4V;
- outputs: WAV ou FLAC;
- primeiro audio stream;
- FFmpeg local em `tools/ffmpeg/bin`;
- QProcess ou processo assíncrono não bloqueante;
- argumentos como lista;
- sem shell;
- sem overwrite silencioso;
- WAV lossless PCM; FLAC lossless;
- validar output com a infraestrutura de probe existente;
- input deve manter o mesmo SHA-256.

Não transformar isso em conversor multimídia genérico.

## 6. UI

Manter uma única tela simples.

Após separação concluída, mostrar:
- transport;
- tempo atual/duração;
- A/B Original / Stems;
- uma linha por stem com M/S/Volume/Export;
- Exportar todos;
- Abrir pasta.

Sem waveform neste checkpoint.

Não transformar em DAW.

## 7. Testes

Mantenha os smokes atuais e adicione testes baratos.

Obrigatórios:
- `python -m pytest -q`
- `python -m pip check`
- `python scripts/doctor.py`
- smoke GPU BS-RoFormer existente;
- smoke UI/QProcess de separação existente.

Player:
- teste com arquivos WAV/FLAC sintéticos pequenos;
- fake/mock do output stream para testar lógica sem depender do dispositivo;
- Play/Pause/Seek;
- cursor sincronizado;
- Mute/Solo/múltiplos Solo;
- volumes não alteram arquivos;
- Original/Stems exclusivo;
- prova de leitura por blocos / sem preload completo.

Export:
- um stem byte-identical;
- todos os stems;
- colisão de nome sem overwrite silencioso.

Video extraction:
- gere fixture pequena local usando FFmpeg, se necessário;
- extraia WAV e/ou FLAC;
- probe válido;
- input hash intacto;
- UI/processo não bloqueante.

Opcional, se houver um output device disponível sem interação:
- smoke de abrir/fechar `sounddevice.OutputStream` com silêncio curto.
Não falhe o checkpoint apenas porque não existe dispositivo de saída no ambiente automatizado; nesse caso documente o teste manual pendente.

## 8. Report

Crie:
`docs/generated/v02-checkpoint1-report.md`

Inclua:
- PASS/BLOCKED;
- dependências;
- arquitetura resultante;
- testes;
- smoke;
- limitações;
- arquivos alterados;
- qualquer teste manual ainda necessário.

Atualize README/roadmap/status somente para refletir fatos realmente concluídos.

## Gate final

Só retorne PASS se:
- separação existente continua saudável;
- player sincronizado funciona nos testes;
- export é byte-identical;
- extração FFmpeg valida;
- nenhuma regressão de input/model/security;
- nenhum recurso de Checkpoint 2 foi iniciado.

Não faça commit/push.
