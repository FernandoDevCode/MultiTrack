# MultiTrack — estado do projeto e caminho de execução

> **Nome do aplicativo:** `MultiTrack`.

Para usar em outro Windows, consulte [o guia para colaboradores](docs/16_COLLABORATOR_SETUP.md).
Para Windows sem GPU, `INSTALAR-CPU.bat` prepara runtime, FFmpeg e modelo
automaticamente dentro da pasta local. Veja [o guia CPU](docs/17_CPU_INSTALLER.md).

MultiTrack é um aplicativo Windows local para separação de fontes musicais com modelos modernos de Music Source Separation (MSS). O objetivo final continua sendo alta qualidade, funcionamento offline após setup, stems comuns e uma área experimental para guitarra lead/rhythm quando houver evidência suficiente.

## Estado atual

- **Fase 0 — PASS:** runtime local, RTX 5060/CUDA, FFmpeg e `audio-separator` validados.
- **Fase 1 — PASS:** engine headless permanente implementado com `SeparationService` + adapter de `audio-separator`.
- **Fast Track v0.1 — PASS:** launcher, GUI PySide6 e worker isolado validados em CUDA.
- **BS-RoFormer SW migration — PASS:** `Core Stems`/seis stems roda localmente em CUDA.
- **v0.2 Checkpoint 1 — PASS:** Core Stems, player multistem sincronizado, A/B, export byte-identical, extração lossless de áudio de vídeo e seam mínima de pipelines.
- **v0.2 Checkpoint 1 — aceitação manual PASS:** player/export/extração e paths Unicode validados pelo usuário.
- **v0.2 Checkpoint 2 — technical PASS / manual quality FAIL:** a infraestrutura de análise funciona, mas o CLAP errou instrumentação relevante em teste conhecido (incluindo guitarra claramente audível). Permanece advisory/experimental e não decide routing automaticamente.
- **v0.2 Checkpoint 3 — technical PASS:** benchmark local G0/G1/G2/B0/B1 dos especialistas; aprovação musical ainda pendente, sem integração na UI de produção.
- **v0.2 Checkpoint 4 — technical PASS / manual acceptance pending:** seleção explícita `Automático / GPU NVIDIA / CPU` e escolha independente de `Vocals, Drums, Bass, Guitar, Piano, Other`. O Core calcula as seis fontes uma vez e só retém/exibe/exporta as pedidas; isso economiza arquivos, não promete acelerar a inferência.

## Abrir o aplicativo

O atalho `MultiTrack` na raiz abre o aplicativo com o ícone Mt. Para recriar esse
atalho, inclusive depois de mover a pasta, execute `scripts/create-shortcut.ps1`.

Dê duplo clique em `START-MULTITRACK.bat`. Escolha uma música WAV, FLAC ou MP3, o
preset Core Stems, o dispositivo e a saída WAV, FLAC ou MP3; marque uma ou mais
faixas desejadas. MP3 de saída é uma exportação opcional com perdas a 320 kbps;
Ao abrir WAV, FLAC ou MP3, o formato de saída acompanha automaticamente a
extensão; você ainda pode alterá-lo. Para outras entradas suportadas, a saída
inicial é WAV. WAV/FLAC preservam a saída lossless. Cada
execução cria uma pasta nova em `outputs/`. Ao concluir, use o player
sincronizado, Mute/Solo/Volume, A/B Original/Stems selecionados,
exporte um ou todos os stems ou abra a pasta do resultado.

Ao mover a pasta do projeto ou trocar sua unidade, abra pelo launcher: ele
ajusta os caminhos do Python local e do código sem reinstalar dependências.
Se a verificação inicial falhar, a janela mostra o erro e salva o diagnóstico
em `.tmp/startup-check.log`. Para desenvolvimento, `scripts/dev-env.ps1`
aplica o mesmo ajuste antes de ativar o ambiente.

`Automático` usa CUDA quando disponível e CPU FP32 caso contrário. `GPU NVIDIA`
falha explicitamente se CUDA não estiver disponível; `CPU` força o worker a
ocultar CUDA antes de importar Torch. CPU pode ser lenta e o app não inventa
estimativa por música. Processadores muito antigos e máquinas com pouca RAM
ainda precisam de smoke físico antes de serem declarados compatíveis.

O preset `Core Stems` produz vocals, drums, bass, guitar, piano e other com o
BS-RoFormer SW local já aprovado. A ação separada **Extrair áudio de vídeo…**
gera WAV ou FLAC lossless com o FFmpeg local.

O botão **Analisar instrumentos** executa o CLAP local em um processo separado,
mas o detector falhou no gate musical manual e permanece experimental. As
sugestões não são probabilidades, não são autoridade para routing e precisam de
confirmação humana. Elas não alteram as faixas desejadas para separação.

Relatórios em `docs/generated/` são snapshots históricos e não precisam ser reescritos quando o estado do Git/remoto muda depois.

## Estratégia de execução

O plano original de 7 fases continua válido como mapa de convergência, mas não é mais a sequência operacional imediata.

```text
Fase 0 PASS
   ↓
Fase 1 PASS
   ↓
Fast Track v0.1 PASS
   ↓
aplicativo utilizável
   ↓
gap analysis contra roadmap original
   ↓
hardening somente onde fizer diferença
```

Não estamos descartando o plano original. Estamos mudando a ordem para começar a usar o app antes.

## Ordem de leitura para a tarefa atual

1. `AGENTS.md`
2. `docs/11_FAST_TRACK.md`
3. `docs/01_SYSTEM_DESIGN.md`
4. `docs/09_UI_SPEC.md`
5. `docs/03_SECURITY_AND_SANDBOX.md`
6. `docs/04_TEST_AND_EVAL.md`
7. `docs/generated/phase1-report.md`

Para a tarefa atual use `docs/15_V02_CHECKPOINT4_CPU_TARGETS.md` e `prompts/V02_CHECKPOINT4_CPU_TARGETS.md`. Checkpoint 3 permanece como gate de qualidade separado, pendente de avaliação humana.

## Roadmap original

`docs/05_ROADMAP.md` preserva as 7 fases como roadmap de convergência. Os prompts antigos permanecem no repo para referência e hardening futuro; não execute a sequência mecanicamente agora.

Após a v0.1, compare o estado real com as fases 2–6 e implemente somente os gaps necessários para chegar ao produto final desejado.
