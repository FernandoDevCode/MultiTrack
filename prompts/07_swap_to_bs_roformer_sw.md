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

## Pré-condição local

O usuário executa antes desta tarefa:

```powershell
.\.venv\Scripts\python.exe scripts\install_bs_roformer_sw.py
```

Esse script baixa os dois artefatos de uma revisão imutável, verifica o checkpoint por SHA-256/tamanho, verifica o YAML pelo Git blob hash conhecido, calcula o SHA-256 do YAML e grava `.tmp/bs-roformer-sw-install.json`.

Ao iniciar esta tarefa:

1. rode `.\.venv\Scripts\python.exe scripts\install_bs_roformer_sw.py --verify-only`;
2. leia `.tmp/bs-roformer-sw-install.json`;
3. use exatamente os hashes ali registrados;
4. **não faça download de modelo** nesta execução.

Se a verificação falhar ou o receipt não existir, pare como `BLOCKED` e peça ao usuário para executar o instalador; não tente um download alternativo.

## Regras de segurança

- tudo dentro do workspace;
- não instalar nada globalmente;
- não alterar driver/CUDA/PATH persistente;
- não usar `danger-full-access`;
- não baixar modelo nesta execução; usar apenas os artefatos já verificados pelo instalador local;
- checkpoint/config devem ser revalidados com `--verify-only` antes do primeiro `load_model`;
- pin de checkpoint e config deve vir do receipt local;
- não permitir URL/modelo arbitrário na UI;
- não fazer fallback silencioso para CPU;
- não modificar o áudio de entrada;
- não baixar candidatos adicionais.

## Implementação mínima

1. Revalide os artefatos instalados com `scripts/install_bs_roformer_sw.py --verify-only`.
2. Leia o receipt e obtenha SHA-256/tamanho do checkpoint e SHA-256 do YAML.
3. Troque `SIX_STEMS` em `src/stemlab/app/modes.py` para usar BS-RoFormer SW.
4. Remova “baseline”/“htdemucs” da label e descrição ativas do modo 6-stem.
5. Preserve as seis `expected_roles`.
6. Ajuste `scripts/doctor.py` para verificar os novos artefatos pelos hashes pinados.
7. Ajuste testes que hoje esperam `htdemucs_6s`.
8. Não criar novo backend. Use `AudioSeparatorBackend` existente.
9. Não implementar player, waveform, export novo, downloader genérico, registry genérico, ensembles ou Guitar Lab nesta tarefa.

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
