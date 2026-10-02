Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: OFF
Motivo: o experimento, os candidatos, os pipelines G0/G1/G2/B0/B1 e os critérios de aceitação já estão fechados; o risco é integração segura de checkpoints locais no loader existente e benchmark CUDA reproduzível.

# StemLab v0.2 — Checkpoint 3: Specialist Quality Gate

Leia somente:
- `AGENTS.md`
- `docs/14_V02_CHECKPOINT3.md`
- `docs/02_MODEL_STRATEGY.md`
- `docs/03_SECURITY_AND_SANDBOX.md`
- `docs/04_TEST_AND_EVAL.md`
- `docs/generated/v02-checkpoint2-report.md`
- arquivos de código/teste diretamente necessários.

Execute integralmente o Checkpoint 3. Não integre os especialistas na UI de produção.

## Pré-condição obrigatória

Antes de qualquer load:

```powershell
.\.venv\Scripts\python.exe scripts\install_specialist_candidates.py --verify-only
```

Se falhar: BLOCKED.

Leia `.tmp/specialist-candidates-install.json`.

Antes da primeira inferência, fixe no projeto os SHA-256 dos YAMLs encontrados no receipt e revalide checkpoint + YAML em runtime. Não confie somente no fato de a revisão remota ser imutável.

## Candidatos autorizados

Somente:

- `lead_rhythm_listra92`
- `bass_xlancer`

Não baixar outro modelo.
Não usar modelo arbitrário fornecido por path.
Licença dos pesos continua UNKNOWN; uso research-only.

## Integração com audio-separator

Preserve `audio-separator==0.47.0`.

Primeiro inspecione o loader da versão instalada e confirme por que os filenames locais não são resolvidos pelo registry normal.

Implemente somente o menor mecanismo necessário dentro da camada de adapter do StemLab para carregar os dois modelos allowlisted com seus YAMLs verificados.

Aceitável:
- resolver/subclass estreito que fornece ao loader existente checkpoint/config local verificados.

Proibido:
- modificar `.venv/site-packages`;
- monkeypatch global;
- copiar/forkar audio-separator inteiro;
- atualizar audio-separator;
- downloader no caminho de inferência;
- generic model importer;
- bypass de hash/allowlist.

Core Stems atual deve continuar usando o caminho normal existente.

## Harness

Implemente um harness headless não interativo conforme `docs/14_V02_CHECKPOINT3.md`.

Para um input:

1. hash do input;
2. Core Stems uma única vez;
3. G0 = Core/Guitar;
4. B0 = Core/Bass;
5. G1 = Lead/Rhythm specialist direto na mix;
6. G2 = Lead/Rhythm specialist sobre G0;
7. B1 = Bass specialist direto na mix;
8. validar outputs;
9. gerar manifest;
10. confirmar hash do input inalterado.

Um modelo pesado por vez.

Se o processo único não liberar CUDA de forma previsível, use subprocessos por estágio em vez de manter múltiplos modelos vivos. Prefira isolamento correto a uma otimização prematura.

## Formato e nomes

Use WAV ou FLAC lossless, consistente dentro da run.

Preserve nomes humanos:
- `G0_core_guitar`
- `G1_direct_lead`
- `G1_direct_rhythm`
- `G2_twostage_lead`
- `G2_twostage_rhythm`
- `B0_core_bass`
- `B1_specialist_bass`

Não normalize cada stem individualmente.

## Testes automatizados

Adicione testes para:
- registry/allowlist local;
- checkpoint/config hash mismatch;
- candidate ID desconhecido;
- bloqueio de path arbitrário;
- sem rede durante inferência;
- role parsing Lead/Rhythm e bass/other;
- G0/B0 reutilizados;
- manifest determinístico/serializável;
- input intacto;
- output validation;
- failure de uma variante não aciona fallback oculto.

Rode:
- `python -m pytest -q`
- `python -m pip check`
- `python scripts/doctor.py`
- smoke Core BS-RoFormer existente.

Smokes opt-in novos:
- Lead/Rhythm candidate CUDA/offline;
- Bass candidate CUDA/offline;
- harness curto completo G0/G1/G2/B0/B1.

Registre:
- runtime por estágio;
- peak CUDA allocated/reserved;
- effective device/precision;
- versões;
- hashes.

## Relatório técnico

Crie:

`docs/generated/v02-checkpoint3-technical-report.md`

Resultado pode ser:
- PASS_TECHNICAL
- BLOCKED

Não declare qualidade aprovada nesse relatório.

Crie também um template:

`bench/README_SPECIALIST_GATE.md`

explicando como o usuário roda 3 músicas privadas e como anota G0/G1/G2/B0/B1. Não incluir áudio privado.

## Status do projeto

Atualize documentação apenas com fatos comprovados:
- Checkpoint 2 infrastructure PASS;
- CLAP manual quality gate FAILED, portanto detector advisory/experimental;
- Checkpoint 3 technical state;
- especialistas continuam research-only até gate humano.

Não reescreva relatórios históricos.

## Proibido

- integrar Lead/Rhythm/Bass specialist à tela principal;
- alterar o default Core;
- mexer no CLAP para tentar fazê-lo passar;
- adicionar ensemble;
- adicionar Synth/Keys/etc.;
- push/tag/release;
- declarar um vencedor antes do gate humano.

Não faça commit/push.
