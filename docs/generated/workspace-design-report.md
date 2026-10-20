# Workspace visual — 2026-10-19

**Implementação:** PASS. Aceitação visual do usuário pendente.

Interface PySide6 reorganizada em barra compacta, painel de separação à esquerda
e monitor/mixer à direita. Tema grafite, destaques azuis moderados, ícones SVG
locais, controles compactos e estados de foco/hover/pressão/seleção/desabilitado.
Separar/progresso permanecem visíveis; painéis têm redimensionamento e rolagem
independente. Formato automático, device policy e recursos existentes mantidos.

## Evidência

- Suíte completa: **109 passed, 9 skipped**; integrações pesadas opt-in.
- Sem lint/type checker adicional configurado no projeto.
- Capturas reais Qt: vazio, carregado, processando, seis stems, análise
  experimental e erro recuperável; 1180 × 780 e 860 × 600.
- Janela compacta e divisor ajustado: sem rolagem horizontal; conteúdos longos
  acessíveis por rolagem vertical e ação Separar sempre visível.
- Cliques em Mute/Solo/Volume e Play/Pause, seek e A/B validados por samples e
  cursor compartilhado, com stream de teste sem reprodução física.
- Espaço alterna checkbox com foco; Ctrl+Espaço alterna transporte. Ambos PASS.
- Exportar todos acionado pelo botão: seis cópias verificadas por SHA-256.
- Smoke real da UI/QProcess/serviço CUDA: seis stems e nova execução Bass +
  Guitar na mesma janela; player/export PASS, input intacto. Evidência local
  em `.tmp/startup-ui-smoke.json`.
- Prévia e smoke de interação em `.tmp/preview-workspace-design.py` e
  `.tmp/workspace-design/report.json`. O renderer offscreen carrega as fontes
  do Windows explicitamente para reproduzir a tipografia da GUI nativa.

## Limites

Não foi alterada nem reavaliada a qualidade musical do checkpoint. Não foram
testados outros dispositivos físicos de áudio nem todas as escalas de DPI e
resoluções de monitores. Não houve criação de novo engine ou editor de áudio.
