---
name: dependency-inspection
description: Inspeciona uma dependência upstream crítica quando a documentação não basta, especialmente loaders de modelo, download, CUDA, áudio ou serialização.
---

# Dependency Inspection

Use somente quando uma decisão depende de comportamento não resolvido pela documentação/API pública.

1. Identifique a pergunta concreta antes de clonar.
2. Clone somente a dependência necessária, shallow/pinned quando possível, em `.research/deps/<name>/`.
3. Não execute setup/build/install automaticamente a partir do clone.
4. Leia somente os arquivos necessários para responder à pergunta.
5. Registre commit/tag inspecionado e conclusão em um relatório curto sob `docs/research/` ou no documento de decisão relevante.
6. Não copie internals para nosso código sem motivo. Prefira API pública/adapter.
7. `.research/` permanece gitignored, a menos que exista um pequeno arquivo textual de evidência deliberadamente extraído.
8. Se descobrir risco de supply chain, execução de checkpoint ou comportamento incompatível, pare a implementação dependente e reporte antes de contornar.
