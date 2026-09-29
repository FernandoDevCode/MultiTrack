# Como executar com Codex

## Estado atual

Fase 0 e Fase 1 já estão concluídas. O caminho ativo agora é o **Fast Track v0.1**.

Use somente:

`prompts/FAST_TRACK_v01.md`

Enquanto o Fast Track estiver ativo, a regra antiga de “um prompt por fase, sem combinar fases” fica suspensa **somente para esse prompt fechado**. O roadmap original continua preservado para convergência depois da v0.1.

## Sandbox

Abra o Codex na raiz do projeto. Mantenha `workspace-write`, sem writable roots extras. Rede só quando necessária para dependência/modelo aprovado. Não usar acesso irrestrito.

## Depois da execução

Exija:

- arquivos alterados;
- comandos executados;
- testes;
- downloads/origem/hash quando aplicável;
- smoke real;
- limitações;
- alterações fora do escopo: zero.

Não aceite “funciona” sem evidência.

## Depois do Fast Track

Faça gap analysis contra `docs/05_ROADMAP.md`. Não retome automaticamente pelo próximo número da fase.

Os prompts `02_model_registry.md` a `06_packaging.md` são referência de convergência futura e só devem ser usados quando o gap analysis justificar.

## Git

Commit local pode fazer parte da tarefa útil. Push, tag e release exigem pedido explícito.
