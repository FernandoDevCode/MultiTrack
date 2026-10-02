# Como executar com Codex

## Estado atual

Fase 0, Fase 1, Fast Track v0.1, migração BS-RoFormer SW e v0.2 Checkpoint 1 estão concluídos.

O caminho ativo é **StemLab v0.2 — Checkpoint 2: Instrument Analysis + Adaptive Planning**, definido em:

- `docs/13_V02_CHECKPOINT2.md`
- `prompts/V02_CHECKPOINT2.md`

O roadmap original continua como mapa de convergência; não retome fases antigas mecanicamente.

## Sandbox

Abra o Codex na raiz do projeto. Mantenha `workspace-write`, sem writable roots extras. Rede só para a dependência explicitamente aprovada no prompt. O modelo detector deve ser instalado/verificado antes pelo script do projeto. Não usar acesso irrestrito.

## Depois da execução

Exija:

- arquivos alterados;
- comandos executados;
- testes;
- dependências/origem quando aplicável;
- smoke CUDA real;
- prova offline/local-only;
- runtime/VRAM;
- limitações e gate manual;
- alterações fora do escopo: zero.

Não aceite "funciona" sem evidência.

## Git

Commit local pode fazer parte da tarefa útil. Push, tag e release exigem pedido explícito.
