# StemLab v0.2 — Checkpoint 4: CPU + faixas desejadas

Leia:
- `AGENTS.md`
- `docs/15_V02_CHECKPOINT4_CPU_TARGETS.md`
- `docs/03_SECURITY_AND_SANDBOX.md`
- `docs/generated/v02-checkpoint3-technical-report.md`
- apenas os arquivos fonte e testes relevantes à mudança.

Execute integralmente o Checkpoint 4. Não avance para integração de especialistas nem detector v2.

## Contexto factual

No `main` atual:
- `build_request()` fixa `DevicePolicy.CUDA_REQUIRED`;
- `JobLaunch` não carrega dispositivo nem seleção;
- `run_job` escreve status "CUDA";
- `AudioSeparatorBackend` usa `audio-separator==0.47.0`;
- `SeparationService` exige seis stems Core quando `expected_roles` contém seis;
- `MainWindow` sempre apresenta todos os arquivos produzidos;
- `doctor.py` exige GPU RTX 5060;
- CLAP e candidatos Lead/Rhythm/Bass **não estão aprovados como separadores de produção**.

## O que entregar

### 1. Seleção explícita do dispositivo

Adicionar `cpu` ao domínio e passar escolha `auto/cuda/cpu` pela UI/worker/request/adapter/manifest.

- `auto`: CUDA se disponível, caso contrário CPU; informar escolha.
- `cuda`: CUDA obrigatório; falha sem fallback.
- `cpu`: CPU obrigatório mesmo que exista NVIDIA; validar device efetivo.
- Em CPU, FP32 e `use_autocast=False`.
- Forçar o isolamento de CUDA no **processo do worker ANTES** do import de Torch, se usar `CUDA_VISIBLE_DEVICES=-1`. Garanta o mesmo contrato para entrada headless/CLI.
- Um erro real de CUDA no `auto` não pode ser silenciosamente reexecutado em CPU.
- UI não importa Torch.
- Mensagem de CPU lento, sem estimativa numérica inventada.

### 2. Escolha de stems

Adicionar checkboxes **independentes do painel CLAP**:
`Vocals, Drums, Bass, Guitar, Piano, Other`.

- Todos marcados por padrão.
- Um ou vários; vazio = erro útil.
- Essa seleção passa por `JobLaunch` e protocolo para `SeparationRequest`.
- Não aceitar nome arbitrário; validar contra `Core Stems`.
- Default das APIs sem seleção permanece as seis saídas, sem quebrar testes antigos.
- Rodar Core uma única vez e validar seus seis outputs.
- Depois reter somente os solicitados, apagando **apenas outputs não solicitados dentro da pasta nova da execução**.
- Resultado/manifest: `requested_roles`, `actual/output roles` verdadeiros; final `stems` só contém os pedidos.
- Player, export individual e export-all enxergam apenas entregues.
- Para subconjunto, explicar que o A/B "Stems selecionados" não é reconstrução completa da mix.

**Importante:** não criar fake speedup. O modelo BS-RoFormer SW calcula seis fontes mesmo que usuário peça apenas Bass. Esta seleção poupa armazenamento final e talvez escrita, mas não implica melhoria perceptível de inferência. Não executar Core repetidamente por alvo.

É permitido usar `output_single_stem` como otimização de escrita só se a compatibilidade na versão pinada for verificada, a validação de outputs continuar correta e for rigorosamente documentado que inferência não é pulada. Não é requisito. Preferir solução simples/segura após validação.

### 3. Execução sem GPU NVIDIA

- O aplicativo deve abrir e separar Core Stems mesmo sem `nvidia-smi` / CUDA disponível.
- Analisar instrumentos via CLAP pode continuar CUDA-only; em CPU informar limitação sem bloquear `Separar`.
- Atualizar `doctor.py` para `--profile cpu` que valida runtime local + CPU tensor + Core model + FFmpeg, sem exigir CLAP, especialistas nem NVIDIA; manter diagnóstico GPU existente.
- Não mudar PyTorch/CUDA/pacotes/driver globais nem baixar modelos.
- Não prometer rodar em todo Pentium antes do smoke físico: compatibilidade de instruções e RAM deve ser documentada.

### 4. Testes obrigatórios

Ver `docs/15_V02_CHECKPOINT4_CPU_TARGETS.md` para a lista completa. Cobrir prioritariamente:
- GPU/CPU/AUTO, ausência de GPU, forced CPU em PC com GPU;
- CPU FP32, validação device efetivo, CUDA OOM sem fallback;
- sem seleção => erro; ID desconhecido => erro; duplicidade => erro;
- todos selecionados = behavior histórico;
- só Vocals, Bass+Guitar e só Other;
- uma inferência Core, não por stem;
- outputs não selecionados ausentes no disco/result/manifest;
- segurança de paths no cleanup;
- player/export com subset;
- CLAP não altera seleção;
- Unicode path regressions;
- `doctor --profile cpu`;
- `pytest -q`, `pip check`, smoke GPU Core.

Smoke **real** opt-in em CPU com Core (fixture curta) e outro GPU com subconjunto. Se o CPU smoke ficar excessivamente lento, registre duração, limite e eventual blocker sem inventar PASS.

### 5. Relatório

Criar `docs/generated/v02-checkpoint4-report.md`:
- status PASS/BLOCKED por recurso;
- arquivos alterados;
- comportamento auto/cpu/cuda efetivamente verificado;
- selecionados e manifest;
- tempo de inferência comparável com todos/um stem se medido;
- CPU RAM/pico se medido;
- testes e gates;
- limitações de Pentium/compatibilidade;
- teste manual pendente.

Atualizar README/AGENTS para o estado **real após executar**, sem reescrever históricos. Deixar checkpoint 3 especialistas como research-only.

## Limites rígidos

- Não mexer em checkpoints/modelos/hashes/qualidade.
- Não integrar Bass HQ / Lead-Rhythm / Vocal Lab.
- Não mudar classificação CLAP.
- Não criar downloads, auto-install, hardware benchmark fictício, registry genérico, servidor, fila ou DAW.
- Não adicionar dependências.
- Não fazer commit, push, tag ou release.

Ao terminar, dê relatório curto com arquivos, testes, limitações e o que eu preciso validar manualmente.
