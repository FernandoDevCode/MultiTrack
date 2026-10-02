# Como executar com Codex

## Estado atual

Fase 0, Fase 1, Fast Track v0.1 e a migração para BS-RoFormer SW estão concluídos.

O caminho ativo é **StemLab v0.2 — Checkpoint 1**, definido em:

- `docs/12_V02_CHECKPOINT1.md`
- `prompts/V02_CHECKPOINT1.md`

O roadmap original continua como mapa de convergência; não retome fases antigas mecanicamente.

## Sandbox

Abra o Codex na raiz do projeto. Mantenha `workspace-write`, sem writable roots extras. Rede só quando necessária para a dependência explicitamente aprovada no prompt. Não usar acesso irrestrito.

## Depois da execução

Exija:

- arquivos alterados;
- comandos executados;
- testes;
- dependências/origem quando aplicável;
- smoke real;
- limitações;
- alterações fora do escopo: zero.

Não aceite "funciona" sem evidência.

## Git

Commit local pode fazer parte da tarefa útil. Push, tag e release exigem pedido explícito.
