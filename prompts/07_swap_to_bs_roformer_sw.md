Config Codex
Modelo: GPT-5.6 Terra
Effort: Medium
Plan: OFF
Motivo: a arquitetura e o modelo-alvo já estão decididos. Esta tarefa é uma migração fechada de um modelo 6-stem para outro, com smoke CUDA e limpeza do baseline antigo somente após PASS.

# Migração 6 Stems — htdemucs_6s -> BS-RoFormer SW

Leia somente:
- `AGENTS.md`
- `src/stemlab/app/modes.py`
- `src/stemlab/separation/audio_separator_adapter.py`
- `scripts/doctor.py`
- `tests/test_fast_track_modes.py`
- `docs/generated/fast-track-v01-report.md`
- `docs/02_MODEL_STRATEGY.md`
- `docs/03_SECURITY_AND_SANDBOX.md`

## Objetivo

Substituir o modelo ativo de 6 stems `htdemucs_6s` pelo `BS-RoFormer SW by jarredou`, mantendo exatamente as seis saídas:

- vocals
- drums
- bass
- guitar
- piano
- other

Não mexer no modo `Vocals HQ (experimental)`.

O `audio-separator` 0.47.0 já conhece:
- checkpoint: `BS-Roformer-SW.ckpt`
- config: `BS-Roformer-SW.yaml`

## Fontes aprovadas

Catálogo upstream:
`nomadkaraoke/python-audio-separator` -> `audio_separator/models.json`

Artefatos:
`https://huggingface.co/lainlives/audio-separator-models/resolve/main/BS-Roformer-SW.ckpt`
`https://huggingface.co/lainlives/audio-separator-models/resolve/main/BS-Roformer-SW.yaml`

Checkpoint SHA-256 esperado:
`24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e`

O YAML é pequeno. Baixe primeiro para uma pasta temporária dentro do repo, inspecione, calcule SHA-256 e registre esse hash antes de qualquer carga do modelo.

## Regras de segurança

- tudo dentro do workspace;
- não instalar nada globalmente;
- não alterar driver/CUDA/PATH persistente;
- não usar `danger-full-access`;
- download primeiro como `.partial` ou em `.tmp/model-candidates/`;
- checkpoint só pode ser promovido para `models/` se o SHA-256 for exatamente o esperado;
- config deve ter hash calculado e pinado no código antes do primeiro `load_model`;
- não permitir URL/modelo arbitrário na UI;
- não fazer fallback silencioso para CPU;
- não modificar o áudio de entrada;
- não baixar candidatos adicionais.

## Implementação mínima

1. Baixe checkpoint + YAML aprovados.
2. Verifique checkpoint SHA-256.
3. Inspecione/configure o hash do YAML.
4. Promova os dois arquivos para `models/`.
5. Troque `SIX_STEMS` em `src/stemlab/app/modes.py` para usar BS-RoFormer SW.
6. Remova “baseline”/“htdemucs” da label e descrição ativas do modo 6-stem.
7. Preserve as seis `expected_roles`.
8. Ajuste `scripts/doctor.py` para verificar os novos artefatos.
9. Ajuste testes que hoje esperam `htdemucs_6s`.
10. Não criar novo backend. Use `AudioSeparatorBackend` existente.
11. Não implementar player, waveform, export novo, downloader genérico, registry genérico, ensembles ou Guitar Lab nesta tarefa.

## Smoke obrigatório ANTES de remover o modelo antigo

Use primeiro a fixture sintética curta já existente da Fase 0/Fast Track.

Prove:
- load pelo `audio-separator`;
- CUDA efetiva;
- seis stems exatos;
- outputs finitos e não silenciosos;
- duração coerente;
- input byte-identical;
- manifest criado;
- nenhum fallback CPU;
- registrar runtime e pico de VRAM.

Depois rode o caminho UI/QProcess existente com o novo modo e confirme que a interface continua responsiva.

Se houver OOM ou incompatibilidade real, não apague o Demucs: retorne `BLOCKED` com evidência.

## Limpeza somente após PASS

Somente depois de todos os gates acima passarem:

- remover de `models/`:
  - `5c90dfd2-34c22ccb.th`
  - `htdemucs_6s.yaml`
- remover referências ativas ao `htdemucs_6s` de modes/doctor/testes;
- não apagar evidência histórica em `docs/generated/fast-track-v01-report.md`;
- não precisa remover suporte genérico a Demucs do `audio-separator`/adapter se isso exigir refactor sem benefício.

## Documentação

Após PASS:
- atualizar README/status ativo para dizer que 6 Stems usa BS-RoFormer SW;
- adicionar nova decisão em `docs/06_DECISIONS.md`, preservando a decisão histórica anterior;
- criar `docs/generated/bs-roformer-sw-migration-report.md` com:
  - fontes;
  - bytes/hashes;
  - CUDA/VRAM/runtime;
  - stems produzidos;
  - testes executados;
  - arquivos antigos removidos;
  - limitações;
  - PASS/BLOCKED.

## Testes

No mínimo:
- `python -m pytest -q`
- `python -m pip check`
- `python scripts/doctor.py`
- smoke GPU opt-in já existente/adaptado
- smoke UI/QProcess com 6 stems

## Git

Não fazer push, tag ou release.

## Final

Retorne somente depois dos testes com:
- PASS ou BLOCKED;
- arquivos alterados;
- arquivos baixados/removidos;
- hashes;
- runtime/VRAM;
- comandos/testes e resultados;
- qualquer limitação.

Não avance para player ou outras features.
