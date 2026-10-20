> **Escopo ativo:** para a v0.1, siga primeiro `docs/11_FAST_TRACK.md`. A especificação abaixo descreve o alvo do MVP endurecido; waveform, player/mixer, Model Manager e Diagnostics não bloqueiam o Fast Track.

# UI Spec — MVP

## Workspace visual ativo — 2026-10-19

A interface PySide6 atual usa painéis grafite, controles nativos compactos e
destaques discretos, inspirados no padrão de organização dos aplicativos
criativos Adobe. Não há editor de clips ou timeline de DAW.

- Barra superior: abrir áudio e extrair áudio de vídeo.
- Painel esquerdo redimensionável: preset, formato automático de saída,
  dispositivo, faixas desejadas e análise experimental separada.
- Separar e progresso permanecem visíveis na base do painel esquerdo.
- Área direita: arquivo de origem, estados vazio/processando, monitor A/B,
  transporte compartilhado, mixer e exportação.
- Painéis têm rolagem vertical independente em janelas pequenas; o mixer
  permanece utilizável a partir de 860 × 600 sem rolagem horizontal.
- Mute/Solo exibem estados selecionados distintos; o volume mostra porcentagem.
- Foco de teclado, hover, pressão e desabilitado têm feedback visível. Erros
  aparecem no rodapé com detalhe completo no tooltip.
- Atalhos: Ctrl+O abre áudio, Ctrl+Enter separa, Ctrl+Espaço reproduz/pausa e
  Ctrl+Shift+E exporta todas as faixas geradas. Espaço continua disponível para
  selecionar checkboxes com foco.

Esta atualização muda apresentação e organização; mantém worker, serviço,
device policy, seleção de stems e comportamento de exportação existentes.

## Princípio

A UI deve parecer um player/mixer simples, não uma tela de ML e não um DAW.

## Tela principal

### Top bar

- Open Audio
- nome do arquivo
- preset (`Core Stems`, futuramente `Guitar Lab`)
- qualidade (`HQ` inicialmente fixa)
- botão `Separate` / `Cancel`

### Área central

- waveform/timeline do master;
- play/pause;
- seek;
- tempo atual / duração;
- status/progresso do job quando processando.

### Stem mixer

Uma linha por stem:

```text
[Vocals]   [M] [S]  ───── volume ─────  [export]
[Drums]    [M] [S]  ───── volume ─────  [export]
[Bass]     [M] [S]  ───── volume ─────  [export]
[Guitar]   [M] [S]  ───── volume ─────  [export]
...
```

Regras:

- `Solo` de um ou mais stems toca somente solos ativos.
- Sem solo ativo, `Mute` exclui o stem.
- Gain afeta somente monitoramento, não arquivo no disco.
- Original pode ser tratado como uma fonte separada para A/B, mas nunca somar master + stems simultaneamente por acidente.

## Side panels/dialogs

### Model Manager

Para cada modelo:

- nome/task;
- status (installed/missing/experimental);
- tamanho;
- versão/hash curto;
- licença/status;
- Download / Remove.

Não mostrar lista infinita de todos os modelos comunitários. Só o registry curado.

### Diagnostics

- app version;
- Python runtime;
- torch version;
- CUDA available;
- GPU name;
- total VRAM detectada;
- backend versions;
- FFmpeg path/version;
- data/model paths;
- botão “Copy diagnostics”.

Sem dados pessoais ou paths não necessários no report exportável.

## Estados obrigatórios

- nenhum arquivo;
- arquivo carregado sem stems;
- model missing;
- download em andamento;
- separação em andamento;
- separação concluída;
- cancelado;
- erro recuperável;
- GPU indisponível / CPU fallback.

## Não fazer no MVP

- multi-tab de projetos;
- edição de clips;
- espectrograma interativo;
- efeitos;
- timeline multitrack editável;
- atalhos complexos de DAW;
- skins/themes extensos.
