# Estratégia de modelos

## Princípio

A aplicação é um **orquestrador de modelos MSS**, não um modelo novo. Treinar do zero não faz sentido para o MVP. O valor do projeto está em escolher, validar e combinar os melhores modelos locais para cada tarefa, com UX consistente.

## Baseline vs. produção

### Baseline conhecido

`htdemucs_6s` é útil como baseline porque produz `vocals`, `drums`, `bass`, `guitar`, `piano`, `other`. O próprio projeto Demucs descreve `guitar` como razoável/experimental e `piano` como mais sujeito a bleed. Portanto ele não deve ser assumido como o melhor modelo final.

### Candidatos de alta qualidade

O ecossistema `audio-separator` atualmente suporta MDX/VR/Demucs/MDXC e RoFormer, incluindo BS-RoFormer e MelBand-RoFormer, e baixa modelos automaticamente. O framework `Music-Source-Separation-Training` também suporta várias arquiteturas modernas.

A estratégia é:

1. usar Demucs 6s como baseline funcional;
2. enumerar modelos atuais do `audio-separator` por stem;
3. selecionar poucos candidatos plausíveis;
4. benchmarkar em hardware real e músicas de teste;
5. promover somente vencedores claros.

Não implementar “todos os modelos”.

## Core stems

Não é obrigatório usar um único modelo 6-stem. O melhor pipeline pode ser:

- um modelo especializado para vocals/instrumental;
- um modelo especializado para guitar/no-guitar;
- outro multistem para drums/bass/other;
- composição/residual apenas quando testada.

Porém cada estágio extra aumenta tempo e risco de artefatos. A escolha deve ser guiada por benchmark e não por quantidade de modelos.

## Lead vs. Rhythm — risco principal

Separar `guitar` do resto e separar `lead guitar` de `rhythm guitar` são problemas diferentes.

Um modelo genérico de guitarra pode ser excelente e ainda manter as duas guitarras juntas — isso é comportamento correto para a task dele.

Em setembro de 2026:

- MVSep oferece modelos dedicados de Lead/Rhythm e resultados publicados/independentes mostram que um modelo role-aware pode reduzir muito o vazamento em um teste específico.
- Não há evidência suficiente de um checkpoint local, aberto, bem licenciado e universalmente forte que possamos declarar default sem benchmark próprio.
- Checkpoints comunitários existem, mas qualidade/licença variam.

Portanto `Lead / Rhythm` tem um **research gate**.

## Gate de Lead/Rhythm

Só promover para estável se, em um conjunto de testes variado:

1. as saídas forem semanticamente consistentes (lead não vira rhythm arbitrariamente entre trechos);
2. vazamento cruzado for claramente menor que o baseline genérico;
3. timbre/transientes não forem destruídos para obter “limpeza” artificial;
4. o ganho existir em mais de uma música/mixagem;
5. VRAM couber no hardware-alvo ou houver fallback previsível;
6. origem/licença do peso forem aceitáveis para a forma de uso escolhida.

Se falhar, a UI deve manter `Guitar` estável e marcar `Lead / Rhythm` como experimental ou simplesmente não expor a opção.

## Estratégias a testar para Lead/Rhythm

Em ordem:

1. **Role-aware local model** direto na mix.
2. **Two-stage:** extrair `guitar`, depois aplicar role-aware model sobre o stem de guitarra.
3. Ensemble somente se os testes mostrarem melhora real.
4. Heurística estéreo/phantom-center apenas como experimento; não chamar de separação neural e não usar como default.

Não usar query-text source separation como solução principal sem evidência; modelos genéricos podem entender “guitar” mas não necessariamente a função lead/rhythm na mesma música.

## Model registry — schema mínimo

Cada entrada deve conter algo equivalente a:

```json
{
  "id": "...",
  "display_name": "...",
  "task": "vocals|guitar|multistem|lead_rhythm|...",
  "architecture": "...",
  "adapter": "audio_separator",
  "model_filename": "...",
  "config_files": [],
  "source_url": "https://...",
  "source_page": "https://...",
  "sha256": "...",
  "bytes": 0,
  "license": "MIT|CC-BY-...|unknown",
  "license_url": "...",
  "redistribution": "allowed|download-only|unknown",
  "status": "approved|experimental|rejected",
  "expected_stems": ["..."],
  "device": ["cuda", "cpu"],
  "verified_params": {},
  "evidence_report": "bench/reports/...md"
}
```

## Licença de código != licença do peso

`python-audio-separator` e `Music-Source-Separation-Training` têm código MIT, mas isso **não prova** a licença de cada checkpoint comunitário que eles conseguem carregar. Registrar separadamente.

Peso com licença desconhecida:

- não embutir no instalador;
- não espelhar;
- não promover a default distribuível;
- pode permanecer como candidato de pesquisa somente após decisão explícita do usuário.

## Segurança de `.ckpt/.pth`

Alguns loaders PyTorch usam `torch.load`; há caminhos em dependências que inclusive usam `weights_only=False` para determinados pacotes. Portanto um checkpoint não deve ser tratado como arquivo passivo.

MVP: carregar apenas pesos fixos, de origem revisada e hash conhecido. Não implementar importação arbitrária de checkpoint.
