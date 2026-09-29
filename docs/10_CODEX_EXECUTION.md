# Como executar com Codex

## Sandbox

Abra o Codex a partir da raiz do projeto. O `.codex/config.toml` do repo usa `workspace-write`, rede desligada por padrão e aprovação pelo usuário.

Quando uma fase precisar baixar dependências/modelos, o Codex deve pedir a escalada/rede necessária. Aprove a operação específica. Não troque para `danger-full-access`.

### O que “só esta pasta” significa aqui

- Escrita: projeto atual (nenhum `writable_roots` extra).
- Downloads/caches: redirecionados para subpastas do projeto.
- Rede: somente quando aprovada para bootstrap/model download.
- Leitura: o sandbox nativo do Windows pode ter leitura mais ampla. Para isolamento de leitura estrito, use WSL2 + ai-jail ou VM.

## Modelo de trabalho

Cada prompt da pasta `prompts/` é uma execução útil e fechada. Não combine duas fases para “economizar tempo”. A maior economia é evitar retrabalho.

### Antes da execução

Confira o bloco:

```text
Config Codex
Modelo: ...
Effort: ...
Plan: ON/OFF
Motivo: ...
```

### Depois da execução

Exija do Codex:

- arquivos alterados;
- comandos executados;
- evidência de testes;
- downloads feitos (URL, tamanho, hash quando aplicável);
- qualquer alteração fora do escopo solicitada: deve ser zero;
- incertezas/blockers.

Não aceite “funciona” sem evidência executada.

## Regra de rede

Codex pode usar internet em duas situações:

1. instalar dependências pinadas/necessárias;
2. pesquisar/baixar pesos explicitamente dentro da fase de modelos.

Fora disso, mantenha rede desligada. A separação final deve ser testada offline.

## Commits

O agente pode terminar uma fase com working tree pronta e sugerir mensagem de commit. Não use uma rodada separada de agente só para `git commit/push`. Push nunca é parte implícita da fase.
