---
name: project-verification
description: Planeja e executa evidência para mudanças não triviais do StemLab, especialmente pipeline de áudio, worker, downloads, player e packaging.
---

# Project Verification

Antes de implementar uma mudança não trivial, declare:

- comportamento que deve ficar verdadeiro;
- invariantes que não podem mudar;
- falhas que poderiam gerar falso “passou”;
- menor evidência capaz de provar a mudança.

Depois implemente e siga essa evidência.

Regras específicas:

- UI visual não prova sincronismo: valide sample cursor/fixtures.
- teste unitário não prova qualidade do modelo: use `model-evaluation`.
- “arquivo existe” não prova integridade: valide duração, formato, finitude e hash quando cabível.
- download bem-sucedido não prova checkpoint seguro: confirme registry/hash/origem.
- comando verde anterior não vale após mudança material no candidato final.
- para packaging, teste o artefato empacotado/instalação limpa, não somente a árvore fonte.

No relatório final diferencie: estabelecido, limitado, não testado.
