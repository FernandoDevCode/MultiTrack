# Pacote de instalação CPU — 2026-10-19

**Verificação técnica: PASS. Aceitação no computador do colaborador: pendente.**

## Entrega

- `outputs/packages/MultiTrack-CPU-setup.zip`: **146.067 bytes**, 73 arquivos de
  fontes/recursos e um manifest de integridade. Sem ambientes, pesos, áudio,
  caches, `.git`, credenciais ou resultados.
- SHA-256:
  `246367156d5e729b78dfef0fddc31e52aac9153784d58a4d2ada060399464f97`.
- Extrair todo o ZIP e executar `INSTALAR-CPU.bat`. No fim o app abre;
  execuções seguintes usam `MultiTrack.lnk` ou `START-MULTITRACK.bat`.
- Windows 10/11 x64 Intel/AMD; setup local sem administrador, Python/Git/CUDA
  prévios, drivers, compilador, PATH permanente ou VC_redist global.
- Download total aproximado: 1,7 GB. Recomendar 10 GiB livres e 16 GB de RAM;
  CPU pode ser lenta. Não prometer compatibilidade com toda CPU antiga.

## Estabelecido

Atualização de distribuição em 2026-10-20: README/guias passaram a orientar
o download em Releases e explicar nome, ícone e atalho. O ZIP foi regenerado:
todos os 73 arquivos conferidos por SHA-256 contra fontes e manifest, CRC PASS,
checksum externo PASS. O código executável é o mesmo dos smokes abaixo;
a instalação completa não foi repetida por essa alteração de documentação.
Publicação remota da Release/tag recusada pela revisão automática de segurança;
ZIP, checksum e notas preparados localmente para anexação manual. O README
identifica a publicação como pendente.
Suíte repetida em 2026-10-20 com `scripts/dev-env.ps1` e temp local
(`--basetemp=.tmp/pytest-release-20261020`): **152 passed, 9 skipped** em
36,43 s; três avisos existentes de dependências. `git diff --check` PASS.

1. **Suíte final:** `152 passed, 9 skipped`, em 19,21 s. Três avisos existentes
   de depreciação em dependências; integrações pesadas opt-in. Sem checker
   de lint/tipos adicional configurado. `git diff --check` PASS.
2. **Origem/integridade:** todos os 85 wheels Windows/CPU foram obtidos das
   fontes oficiais e tiveram tamanho/SHA-256 verificados, assim como o pacote
   Python NuGet e o arquivo integral FFmpeg 9.0.2. Pip usa somente wheels
   fixados de cache local, com `--require-hashes`, sem source builds.
3. **Pacote extraído:** execução real de `INSTALAR-CPU.bat --no-launch` em
   `.tmp/CPU clean install/MultiTrack-CPU`, com Python e `.venv` independentes
   do ambiente GPU do projeto. O bootstrap baixou/extraiu Python completo.
   Cache dos wheels e do arquivo FFmpeg foi pré-preenchido a partir dos
   downloads oficiais verificados durante a preparação do teste; nenhum
   ambiente Python/dependências instalado foi copiado do desenvolvimento.
4. **Retomada:** foi interrompida a etapa de instalação de dependências; nova
   execução reparou o ambiente incompleto a partir dos wheels pinados e concluiu.
   A marcação de fase só declara dependências completas após pip retornar sucesso.
5. **Instalação concluída:** modelo Core baixado e verificado; `pip check` PASS;
   doctor CPU PASS; importação da UI PASS; Torch `2.8.0+cpu`, runtime CUDA `None`
   e `cuda.is_available() == False`. Atalho criado na pasta do pacote.
6. **MSVC local:** sete DLLs Microsoft extraídas do wheel PySide6 verificado
   para `.venv/Library/bin`, com hashes na receipt. O smoke carregou explicitamente
   `msvcp140.dll` desse diretório. Nenhum VC_redist global foi instalado.
7. **Repetição offline do artefato final:** manifest de todos os arquivos do
   pacote conferido; BAT executado com proxies HTTP/HTTPS inválidos e flags
   offline. **Exit code 0**, em 38,89 s; reutilizou cache/modelo verificados,
   repetiu pip check/doctor/imports e manteve a seleção CPU.
8. **Separação real offline no pacote CPU:** UI → QProcess → serviço → Core
   usando o Python da cópia extraída. Fixture sintética estéreo de **0,75 s**;
   um stem Vocals solicitado e entregue em FLAC. Processo completo em **23,00 s**
   nesta máquina, incluindo inicialização; não é previsão para outro hardware.
   Resultado CPU/FP32, 44.100 Hz, dois canais, 0,75 s e amostras finitas.
   SHA-256 do input intacto, 366 heartbeats da UI, progresso final 100%, player
   com uma faixa e exportação byte-identical. Fonte importada e checkpoint
   confirmados sob a raiz do pacote, sem recorrer ao runtime/modelo do dev.
9. **Proteção do ambiente original:** executar o BAT na raiz que já tinha
   `.venv` GPU foi recusado antes da conversão; exit code 1 esperado e hash
   do `pyvenv.cfg` intacto. `pip check` do ambiente GPU original também PASS.
10. **Regressão real CUDA:** smoke opt-in UI/QProcess/Core com seis stems,
    rede bloqueada, progresso, original intacto e UI responsiva: **1 passed**,
    em 68,86 s, após a correção de carregamento offline do Core.

## Falha real encontrada e resolvida

O primeiro smoke CPU offline falhou porque o loader upstream tentou baixar
`download_checks.json`, mesmo com checkpoint/YAML presentes. O cache antigo
da máquina dev mascarava isso. O adapter agora resolve diretamente o par Core
allowlisted por IDs, nomes e hashes e mantém o `load_model`/forward/escrita
upstream. Não baixa um catálogo mutável para contornar a dependência de rede.
O smoke CPU final passou com apenas os dois arquivos Core na pasta de modelos.

O bootstrap também foi exercitado no Windows PowerShell 5.1. Um cmdlet de hash
indisponível no ambiente do teste foi substituído por SHA-256 do .NET, antes
de executar o Python baixado. O caso de falha não declarou sucesso.

## Evidência local reproduzível

- Artefato final e checksum: `outputs/packages/`.
- Manifest de hashes do conteúdo: `MultiTrack-CPU/package-manifest.json` no ZIP.
- Instalação: `.tmp/CPU clean install/MultiTrack-CPU/.tmp/install-cpu.log` e
  `install-cpu-bootstrap.log`, com receipt `cpu-install-receipt.json`.
- Repetição offline: `offline-installer-report.json` / `offline-installer-output.log`
  na mesma pasta `.tmp` do pacote extraído.
- Separação real: `.tmp/CPU clean install/MultiTrack-CPU/.tmp/cpu-package-smoke/report.json`.
- Scripts de smoke locais: `.tmp/verify-cpu-package.py`,
  `.tmp/retest-cpu-offline.py` e `.tmp/verify-cpu-installer-guard.py`.
- Fontes e limites de carregamento: `docs/research/cpu-windows-runtime.md`.

## Limitado / não testado

O teste criou um runtime CPU novo no Windows da máquina de desenvolvimento;
não foi uma VM Windows limpa nem o computador físico sem GPU do colaborador.
O runtime Torch CPU não tem CUDA, mas a máquina hospedeira tem GPU/driver.
O primeiro download de FFmpeg foi lento; o teste usou o arquivo oficial
integral verificado em cache, sem assumir um tempo de instalação na internet
do colaborador. Foram exercitados downloads reais e cache/repetição, sem
simular sucesso de instalação nem substituir a inferência por backend fake.

Não foram medidos desempenho de música longa, toda CPU antiga, Windows ARM,
Windows 32 bits, outros dispositivos físicos de áudio ou todas as versões de
Windows. Player foi carregado e exportado sem avaliação auditiva física.
Não houve nova avaliação de qualidade musical nem promoção de especialistas.
