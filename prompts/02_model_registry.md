Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: ON
Motivo: selecionar modelos atuais exige pesquisa focada, inspeção de licença/origem e benchmark; o resultado não deve ser decidido por nome ou SDR de tabelas incompatíveis.

# Fase 2 — Registry, downloader e qualificação de core stems

Leia `AGENTS.md`, `docs/02_MODEL_STRATEGY.md`, `docs/03_SECURITY_AND_SANDBOX.md`, `docs/04_TEST_AND_EVAL.md`. Use as skills `model-evaluation` e `dependency-inspection` quando apropriado.

## Escopo permitido

- `src/stemlab/models/**`
- `src/stemlab/separation/**` somente adapters/integração necessária
- `resources/models.json`
- `bench/**` exceto áudio privado versionado
- `tests/**`
- `docs/research/**`
- `docs/generated/model-qualification-report.md`
- dependências mínimas no projeto

Sem GUI/worker.

## Trabalho

1. Obtenha o catálogo atual do `audio-separator` instalado e pesquise poucos candidatos fortes para as tasks de core stems.
2. Não assumir que SDR de uma linha de catálogo é comparável entre todos os modelos/datasets.
3. Para cada candidato realmente testado, documente origem do peso, formato, fonte, tamanho, SHA-256 e licença/status. Se licença do peso não estiver clara, marque `unknown` e não `approved` para distribuição.
4. Implemente registry curado e downloader com `.partial`, limite de tamanho, SHA-256 e rename atômico.
5. Não permitir URL/modelo arbitrário vindo da UI/config do usuário.
6. Implemente harness de benchmark com runtime/VRAM + invariantes + métricas quando ground truth existir.
7. Teste um conjunto pequeno e representativo, não dezenas de modelos.
8. Escolha o primeiro pipeline HQ para core stems somente se a evidência justificar. Caso nenhuma opção seja claramente superior, mantenha baseline e registre a pendência.

## Aceite

- modelos instaláveis são allowlisted e verificados;
- testes do downloader não precisam de internet real;
- existe relatório reproduzível de candidatos;
- default de core stems, se alterado, tem evidência registrada;
- rede pode ser desligada e os modelos já instalados continuam rodando.

Pare e reporte.
