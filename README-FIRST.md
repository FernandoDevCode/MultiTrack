# StemLab — pacote de arquitetura e execução para Codex

> **Nome provisório:** `StemLab`. Pode ser trocado depois sem mudar a arquitetura.

Este pacote não é o aplicativo pronto. É a especificação de produto, system design, regras operacionais, plano de validação e prompts fechados para o Codex implementar o projeto em fases pequenas.

## Objetivo

Criar um aplicativo desktop **100% local** para Windows que separe músicas em stems usando modelos modernos de Music Source Separation (MSS), com foco em qualidade e não em velocidade. O produto deve oferecer stems comuns (vocais, bateria, baixo, guitarra, piano/outros) e uma área experimental para separar **guitarra lead vs. guitarra rhythm** quando houver evidência de qualidade suficiente.

O projeto não promete que qualquer música com duas guitarras será separada cirurgicamente. Essa é a principal incerteza técnica e existe uma fase específica de benchmark antes de transformar isso em feature estável.

## Ordem de leitura

1. `AGENTS.md` — regras que o agente deve obedecer.
2. `docs/00_PRODUCT.md` — escopo e o que não é escopo.
3. `docs/01_SYSTEM_DESIGN.md` — arquitetura.
4. `docs/02_MODEL_STRATEGY.md` — estratégia dos modelos e o risco lead/rhythm.
5. `docs/03_SECURITY_AND_SANDBOX.md` — downloads, pesos de modelo e isolamento.
6. `docs/04_TEST_AND_EVAL.md` — como provar qualidade e funcionamento.
7. `docs/05_ROADMAP.md` — fases e gates.
8. `prompts/00_environment_spike.md` — primeiro prompt a executar.

## Regra de execução

Não mande o Codex “fazer tudo”. Execute um prompt por fase. Cada fase tem escopo, arquivos permitidos e critérios de aceite. Só avance quando a evidência da fase anterior estiver satisfatória.

## Decisões principais já fechadas

- Windows nativo é o alvo principal do aplicativo.
- Python é o runtime do motor de áudio e da UI inicial.
- UI desktop: PySide6.
- Inferência deve rodar em processo separado da UI.
- CUDA/NVIDIA é o caminho preferencial; CPU é fallback.
- `audio-separator` é o primeiro adaptador para RoFormer/MDX/Demucs, mas fica atrás de uma interface nossa.
- Não treinar modelo grande no MVP.
- Não aceitar pesos arbitrários de usuário no MVP.
- Internamente usar áudio lossless/float, sem MP3 entre estágios.
- Modelos, caches, venv, temporários e ferramentas baixadas ficam dentro da pasta do projeto durante desenvolvimento.
- A aplicação não usa nuvem para separar áudio.

## Primeiro passo

Crie uma pasta vazia para o projeto, copie o conteúdo deste pacote para a raiz e abra o Codex **nessa pasta**. Depois cole apenas `prompts/00_environment_spike.md`.
