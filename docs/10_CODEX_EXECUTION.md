# Como executar com Codex

## Estado atual

Fases 0/1 e Fast Track v0.1 PASS; BS-RoFormer SW ativo. Checkpoint 1 PASS humano. Checkpoint 2 técnico PASS mas detector CLAP falhou quality gate manual, permanece advisory/experimental. Checkpoint 3 técnico PASS, especialistas Lead/Rhythm e Bass permanecem research-only até avaliação musical humana.

**Caminho ativo de implementação:** Checkpoint 4 — CPU + seleção de stems.

- `docs/15_V02_CHECKPOINT4_CPU_TARGETS.md`
- `prompts/V02_CHECKPOINT4_CPU_TARGETS.md`

## Sandbox

Use a pasta raiz do projeto Windows, `workspace-write`, sem writable roots externos. Não atualizar runtime/driver/sistema global, modelos, Torch/CUDA ou dependências. Sem rede necessária.

## Gates

- testes unitários e integrações relevantes;
- GPU regressions Core Stems;
- CPU smoke opt-in verdadeiro, resultados explícitos;
- `doctor --profile cpu` e doctor GPU;
- manifests/output/player/export corretos para seleção de uma/várias stems;
- documentação honesta de velocidade, RAM, limitações e validação manual.

Não confundir "somente alguns arquivos finais" com inferência mais barata do modelo multistem.

## Git

Não fazer commit, push, tag ou release sem pedido explícito.
