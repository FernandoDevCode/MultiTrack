Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: OFF
Motivo: o detector, taxonomia, arquitetura e gate já estão definidos; o risco está na integração Torch/Transformers + subprocesso + evidência, não em decisões abertas.

# StemLab v0.2 — Checkpoint 2

Leia somente:
- `AGENTS.md`
- `docs/13_V02_CHECKPOINT2.md`
- `docs/03_SECURITY_AND_SANDBOX.md`
- `docs/12_V02_CHECKPOINT1.md`
- `docs/generated/v02-checkpoint1-report.md`
- arquivos de código/teste diretamente necessários.

Execute integralmente o Checkpoint 2. Não avance para especialistas.

## Pré-condição

Antes de qualquer load do detector:

```powershell
.\.venv\Scripts\python.exe scripts\install_instrument_detector.py --verify-only
```

Leia `.tmp/larger-clap-music-install.json` e verifique os artefatos contra o receipt.

Se falhar, retorne BLOCKED. Não baixe modelo por conta própria.

## Dependência

Adicione somente como dependência direta:

`transformers==5.18.0`

Transitive deps normais do pacote são permitidas.

Instale apenas na `.venv` local. Não atualize Torch/CUDA/NumPy/soundfile/audio-separator por reflexo.

## Detector

Implemente adapter próprio para o CLAP local.

- `ClapModel` / `ClapProcessor` ou APIs equivalentes da versão pinada;
- carregar exclusivamente de `models/instrument-detector/larger_clap_music`;
- `local_files_only=True`;
- `trust_remote_code=False` quando aplicável;
- `eval()` + `torch.inference_mode()`;
- CUDA required;
- processo de análise separado da UI e encerrado após o resultado;
- nenhum download automático do Transformers/Hugging Face.

Não use o pipeline high-level se ele esconder detalhes importantes de scores ou download. Preferir embeddings normalizados e similaridade explícita.

## Similaridade

Não trate softmax como probabilidade real de presença.

Preferência:
- precompute embeddings dos prompts;
- normalize audio/text embeddings;
- calcule cosine similarity por janela;
- agregue deterministicamente por target;
- preserve evidência (aggregate/peak/window hits/ranks).

A UI não deve mostrar "% confidence".

## Áudio

Amostre no máximo 8 janelas determinísticas de 10 s.

Use FFmpeg local para decodificar cada janela para mono float32 48 kHz, preferencialmente por pipe, sem arquivo lossy e sem carregar a música inteira.

Input hash antes/depois deve ser idêntico.

## Taxonomia

Use exatamente os canonical IDs do documento:
vocals, drums, bass, guitar, piano, keys, synth_pad, organ, percussion, strings, brass, woodwind, choir.

Prompts internos fixos em inglês. Não aceitar prompt arbitrário na UI.

Não inferir número de guitarras.

## Contratos

Crie contratos simples e serializáveis para:
- instrument evidence;
- instrumentation analysis result;
- confirmed targets;
- adaptive/capability plan.

Não colocar Torch/PySide nos contratos.

Estenda `PipelinePlan` minimamente. Não construir DAG engine.

## Router

Regras:
- qualquer subconjunto confirmado de vocals/drums/bass/guitar/piano deve resultar em no máximo **um** Core Stems pass;
- keys/synth_pad/organ/percussion/strings/brass/woodwind/choir ficam explicitamente `specialist_unavailable`;
- jamais mapear silenciosamente esses alvos para `other`;
- detector output nunca executa separação automaticamente sem a camada de confirmação do usuário.

## UI

Adicionar na tela existente:
- botão `Analisar instrumentos`;
- estado/progresso;
- lista editável de sugestões;
- indicação de disponível via Core vs especialista ainda indisponível;
- reanalisar.

Core Stems continua utilizável sem análise.

Não adicionar waveform/tabs/DAW.

## Worker

Use QProcess e protocolo serializável seguindo o padrão saudável já existente.
Preserve UTF-8 estrito nos eventos estruturados.
A análise não pode bloquear a UI.

## Testes

No mínimo:

- testes unitários de window planning;
- cap de 8 janelas;
- aliases/taxonomia;
- agregação determinística;
- serialização;
- override manual;
- planning: 5 Core targets -> 1 Core pass;
- unsupported -> explicit unavailable;
- nenhuma menção a probability/confidence percent na UI;
- QProcess Unicode path regression continua passando;
- input hash intacto;
- UI responsiva com fake detector;
- detector adapter rejeita receipt/hash inválido;
- local-only/no remote code.

Smoke real opt-in:
- carregar CLAP local em CUDA;
- analisar fixture/arquivo local;
- registrar tempo e pico VRAM;
- processo terminar limpo;
- depois rodar smoke BS-RoFormer e provar que não há conflito de VRAM.

Gates existentes:
- `python -m pytest -q`
- `python -m pip check`
- `python scripts/doctor.py`
- smokes relevantes de Checkpoint 1/BS-RoFormer se custo razoável.

## Relatório

Crie:
`docs/generated/v02-checkpoint2-report.md`

Inclua:
- PASS/BLOCKED;
- versão/deps;
- hashes/revision detector;
- arquitetura;
- janela/sampling strategy;
- runtime + VRAM;
- evidência offline;
- testes;
- limitações;
- manual quality gate pendente.

Atualize README/AGENTS/status somente com fatos concluídos.

## Proibido nesta tarefa

- baixar outros modelos;
- implementar qualquer separador especialista;
- Lead/Rhythm;
- Lead/Backing;
- SATB;
- Bass HQ;
- AudioSep;
- Mega 53;
- ensemble;
- treinamento;
- push/tag/release.

Não faça commit/push.
