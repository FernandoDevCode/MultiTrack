Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: ON
Motivo: Lead/Rhythm é a incerteza técnica central. Precisamos pesquisar pesos atuais, licenças e estratégias, testar hipóteses e aceitar a possibilidade de rejeitar a feature.

# Fase 5 — Guitar Lab research gate

Leia `AGENTS.md`, `docs/02_MODEL_STRATEGY.md`, `docs/04_TEST_AND_EVAL.md`. Use `model-evaluation` e, quando necessário, `dependency-inspection`.

## Escopo permitido

- `bench/**` sem commitar áudio privado;
- `resources/models.json` para candidatos experimentais;
- adapters estritamente necessários em `src/stemlab/separation/**`;
- `docs/research/**`;
- `docs/generated/guitar-role-report.md`;
- testes das novas integrações.

Não mexer na UI estável até a conclusão do gate.

## Trabalho

1. Pesquise o estado atual de modelos locais dedicados a lead/rhythm e registre fonte/commit/data/licença.
2. Rejeite peso sem origem verificável ou que exija executar código desconhecido fora do loader aprovado.
3. Compare pelo menos:
   - generic guitar baseline;
   - role-aware direto na mix, se existir;
   - two-stage `mix -> guitar -> lead/rhythm`, se aplicável.
4. Use casos com duas guitarras simultâneas e diferentes panoramas/efeitos.
5. Meça SI-SDR/leakage quando houver ground truth, runtime e VRAM.
6. Faça avaliação auditiva estruturada.
7. Termine com uma decisão explícita: `approved`, `experimental` ou `rejected`, sem maquiar o resultado.

## Aceite

O relatório permite decidir se Lead/Rhythm merece entrar no produto e mostra exatamente em quais condições falha. Se a resposta for “ainda não”, isso é uma saída válida e deve preservar a qualidade do restante do produto.
