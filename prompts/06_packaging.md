Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: ON
Motivo: packaging de PyTorch/CUDA/PySide6/FFmpeg em Windows tem muitas dependências e deve ser validado sobre o artefato real, não improvisado.

# Fase 6 — Packaging Windows

Leia `AGENTS.md`, `docs/03_SECURITY_AND_SANDBOX.md`, `docs/04_TEST_AND_EVAL.md`, `docs/08_RUNTIME_STORAGE.md`.

## Objetivo

Produzir uma distribuição Windows repetível sem instalar dependências globalmente durante o uso normal.

## Restrições

- preferir one-folder/portable;
- não embutir pesos de licença desconhecida;
- não criar one-file gigante por estética;
- não alterar driver/CUDA global;
- manter Model Store separável/removível;
- registrar licenças de terceiros relevantes.

## Trabalho

1. Compare somente opções de packaging necessárias para Python/PySide6/PyTorch neste projeto e escolha a menor que funcione.
2. Empacote um candidato.
3. Teste o pacote em pasta limpa, não a source tree.
4. Faça download/verificação de um modelo permitido.
5. Desative rede.
6. Rode job completo + playback/export.
7. Registre tamanho do pacote/runtime/modelos e limitações.

## Aceite

Usuário consegue iniciar a build limpa, instalar/baixar o modelo permitido, ficar offline e completar separação/playback sem Python global ou caminhos da source tree.
