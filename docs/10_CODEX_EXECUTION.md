# Como executar com Codex

## Estado atual

Fase 0, Fase 1, Fast Track v0.1, migração BS-RoFormer SW e v0.2 Checkpoint 1 estão concluídos.

O v0.2 Checkpoint 2 teve **technical PASS**, mas o detector CLAP falhou no quality gate manual e permanece somente advisory/experimental.

O caminho ativo é **StemLab v0.2 — Checkpoint 3: Specialist Quality Gate (Guitar + Bass)**:

- `docs/14_V02_CHECKPOINT3.md`
- `prompts/V02_CHECKPOINT3.md`

## Sandbox

Abra o Codex na raiz do projeto. Mantenha `workspace-write`, sem writable roots extras. Os candidatos especialistas devem ser instalados/verificados antes pelo script pinado do projeto. Inferência deve funcionar offline. Não usar acesso irrestrito.

## Depois da execução

Exija:

- arquivos alterados;
- comandos executados;
- hashes de checkpoint e config;
- testes;
- smoke CUDA real de cada candidato;
- prova offline;
- runtime/VRAM por estágio;
- outputs e manifest do harness;
- limitações;
- alterações fora do escopo: zero.

PASS técnico não significa aprovação de qualidade. A promoção depende do gate humano G0/G1/G2/B0/B1 em músicas reais.

## Git

Commit local pode fazer parte da tarefa útil. Push, tag e release exigem pedido explícito.
