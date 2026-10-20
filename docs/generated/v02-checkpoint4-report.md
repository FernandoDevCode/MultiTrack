# StemLab v0.2 — Checkpoint 4 technical report

**Resultado técnico:** PASS  
**Aceitação manual:** pendente  
**Data:** 2026-10-10

O Checkpoint 4 foi implementado sem avançar para especialistas, detector v2 ou
qualquer checkpoint posterior. Os candidatos Lead/Rhythm e Bass do Checkpoint 3
continuam research-only, sem vencedor e sem routing de produção.

## Status por recurso

| Recurso | Status | Evidência |
|---|---|---|
| `auto/cuda/cpu` ponta a ponta | PASS | domínio, UI, protocolo v2, worker, CLI, adapter e manifest cobertos |
| CPU forçada em PC com NVIDIA | PASS | worker real com CUDA ocultada: `cpu`, FP32, sem autocast |
| AUTO sem CUDA visível | PASS | worker real herdando `CUDA_VISIBLE_DEVICES=-1`: resolveu CPU/FP32 |
| CUDA obrigatória sem fallback | PASS | teste de indisponibilidade e teste de OOM garantem uma única tentativa |
| Seleção de Core Stems | PASS | vazio/duplicado/desconhecido/path rejeitados; defaults preservam seis |
| Uma inferência Core por job | PASS | backend chamado uma vez; seis outputs validados antes da retenção |
| Cleanup seguro | PASS | só remove artefatos validados e resolvidos dentro da pasta nova do job |
| Manifest e resultado honestos | PASS | `requested_roles`, `inferred_roles`, `produced_roles` e `stems` finais |
| Player/export com subset | PASS automatizado | player recebe somente o mapping retornado; smoke manual ainda pendente |
| CLAP independente | PASS | sugestões não alteram seleção; CPU mostra limitação sem bloquear Core |
| `doctor --profile cpu` | PASS | CPU tensor, runtime, player deps, FFmpeg e Core verificados sem NVIDIA/CLAP/especialistas |
| Compatibilidade universal com Pentium | NÃO ESTABELECIDA | exige smoke físico de ISA e RAM por máquina |

## Device e precisão

- `auto`: escolhe CUDA se Torch a enxerga no worker; caso contrário CPU. Um erro
  real durante inferência CUDA não é repetido em CPU.
- `cuda`: exige CUDA antes de carregar o modelo e valida o device do Separator e
  do modelo carregado.
- `cpu`: o QProcess e a entrada headless/CLI definem
  `CUDA_VISIBLE_DEVICES=-1` antes do import do adapter/Torch. O adapter ainda
  exige device efetivo `cpu`, `use_autocast=False` e precisão `fp32`.
- A UI não importa Torch. CPU mostra aviso de lentidão sem ETA inventada.

Inspeção da dependência pinada: o source instalado de
`audio-separator==0.47.0`, em
`.venv/Lib/site-packages/audio_separator/separator/separator.py`, não oferece
parâmetro público de device no construtor. `setup_torch_device()` escolhe CUDA
quando `torch.cuda.is_available()` é verdadeiro. A política de execução pinada
resolve CPU sem autocast como `fp32`. Isso fundamenta o isolamento pré-import e
a validação posterior; nenhum internal upstream foi copiado.

## Seleção e manifest

IDs aceitos: `vocals, drums, bass, guitar, piano, other`. Sem seleção explícita,
as APIs antigas continuam entregando todos os outputs esperados. Seleção vazia,
duplicada, desconhecida ou parecida com path falha antes da inferência.

O BS-RoFormer SW roda uma única vez e os seis outputs são validados por duração,
sample rate, canais, finitude, sinal e confinamento de path. Só depois os arquivos
não solicitados são apagados da pasta nova da execução. O input permanece
somente leitura. O manifest schema 2 distingue:

- `requested_roles`: escolha do usuário/API;
- `inferred_roles`: seis fontes realmente retornadas e validadas pelo Core;
- `produced_roles` e `stems`: somente arquivos finais retidos.

Player, export individual e export-all recebem apenas `stems`. Para subset, o
A/B usa o rótulo `Stems selecionados` e explica que não é reconstrução completa
da mix.

## Smokes reais

Fixture local: 10,0 s, WAV PCM, 44,1 kHz, estéreo. SHA-256 antes/depois:
`8e7c53fe531f2a105a5c734389736f7183940a5647a05b24509ca78b0ee54fa0`.
Os outputs passaram duração, sample rate, canais, finitude e integridade.

| Execução | Pedido final | Device/precisão | Inferência | Total backend | Resultado |
|---|---|---|---:|---:|---|
| CUDA worker | seis | cuda/autocast | 2,787 s | 6,078 s | 6 arquivos |
| CUDA worker | Bass + Guitar | cuda/autocast | 2,587 s | 5,391 s | só 2 arquivos |
| CPU worker forçada | Vocals | cpu/fp32 | 63,872 s | 65,770 s | só 1 arquivo |
| AUTO com CUDA oculta | Other | cpu/fp32 | 71,921 s | 74,213 s | só 1 arquivo |

Os dois números CUDA são execuções únicas comparáveis, mas a diferença pequena
é compatível com ruído/cache e escrita. Ela não prova aceleração de inferência.
Os logs mostram que seis stems foram inferidos e gravados pelo backend antes da
retenção segura. Pico de RAM CPU não foi medido; nenhum número foi inventado.

## Gates

- `python -m pytest -q`: PASS (`90 passed, 9 skipped` no candidato final;
  integrações pesadas são opt-in).
- `python -m pip check`: PASS (`No broken requirements found`).
- `python scripts/doctor.py`: PASS, perfil GPU preservado.
- `python scripts/doctor.py --profile cpu`: PASS, sem exigir NVIDIA, CLAP ou especialistas.
- GPU Core seis stems real: PASS.
- GPU Core subset Bass + Guitar real: PASS.
- CPU Core forçada real: PASS.
- AUTO com CUDA invisível real: PASS.
- UI/player/export subset automatizado e Unicode: PASS.

Não há lint/type checker adicional configurado no projeto.

## Limitações e gate manual pendente

CPU é funcional neste hardware, mas desempenho e memória dependem da máquina.
O runtime PyTorch pinado pode exigir instruções ausentes em CPUs muito antigas;
o modelo também pode exceder a RAM disponível. Portanto não há promessa de
compatibilidade com todo Pentium sem smoke físico.

Ainda é necessário validar manualmente na UI:

1. escolher CPU na RTX 5060 e confirmar manifest `cpu/fp32`;
2. escolher GPU e confirmar seis stems/player/export inalterados;
3. em AUTO com GPU realmente indisponível, confirmar o aviso e o uso de CPU;
4. Bass + Guitar: somente duas linhas/arquivos/exportações;
5. Vocals e Other isoladamente;
6. ouvir A/B de subset entendendo que não reconstrói a mix completa.

## Arquivos alterados

- `AGENTS.md`, `README-FIRST.md`, `docs/06_DECISIONS.md`;
- `docs/generated/v02-checkpoint4-report.md`;
- `scripts/doctor.py`;
- `src/stemlab/domain/models.py`, `src/stemlab/domain/__init__.py`;
- `src/stemlab/app/modes.py`, `src/stemlab/app/separation_service.py`;
- `src/stemlab/separation/audio_separator_adapter.py`;
- `src/stemlab/workers/protocol.py`, `qprocess_job.py`, `run_job.py`;
- `src/stemlab/cli.py`, `src/stemlab/ui/main_window.py`;
- testes unitários/UI/protocolo/doctor/device/service/Unicode e integrações em
  `tests/`, incluindo os novos `test_device_policy.py` e
  `test_doctor_profiles.py`.
