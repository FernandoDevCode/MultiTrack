---
name: model-evaluation
description: Avalia ou promove um modelo de separação de áudio do StemLab. Use ao adicionar, comparar, trocar o default ou afirmar qualidade de um checkpoint/pipeline MSS.
---

# Model Evaluation

1. Defina a task exata: vocals, guitar, multistem, lead/rhythm etc. Não compare modelos de tasks diferentes como se fossem equivalentes.
2. Verifique origem, URL, hash, formato e licença/status do peso antes de carregá-lo. Código MIT do loader não implica licença MIT do checkpoint.
3. Registre versão do backend, parâmetros, device e input set.
4. Rode smoke técnico: load, outputs, duração, canais, NaN/Inf, runtime e pico de VRAM.
5. Quando houver ground truth, calcule SI-SDR e leakage relevantes. Não misture métricas de datasets/protocolos diferentes.
6. Faça comparação auditiva em mais de uma faixa/condição. Registre bleed, artefatos, transientes e preservação de timbre.
7. Para lead/rhythm, inclua casos simultâneos e efeitos estéreo. Um guitar extractor genérico não falhou só por conter as duas guitarras; ele não foi treinado para a mesma task.
8. Escreva relatório em `bench/reports/` com limitações e evidência reproduzível.
9. Só marque `approved` se a melhora for consistente, couber no hardware alvo e a origem/licença forem aceitáveis. Caso contrário use `experimental` ou `rejected`.
10. Nunca altere o default apenas por um exemplo favorável.
