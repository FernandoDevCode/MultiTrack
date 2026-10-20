# Instalador local para Windows sem GPU

## Para usar

Quando a versão CPU for publicada, baixe `MultiTrack-CPU-setup.zip` nos **Assets** em
[Releases](https://github.com/FernandoDevCode/MultiTrack/releases).
O repositório é privado: entre no GitHub com uma conta que tenha acesso.
Não é necessário usar Git ou baixar o código separadamente.

1. Extraia **todo** o `MultiTrack-CPU-setup.zip` para uma pasta sua,
   por exemplo `C:\MultiTrack`. Não execute de dentro do ZIP ou de Program Files.
2. Dê duplo clique em **`INSTALAR-CPU.bat`** e aguarde os downloads/verificações.
3. O app abre ao concluir. Nos próximos usos, abra `MultiTrack.lnk` ou
   `START-MULTITRACK.bat`, sem precisar instalar novamente.

O pacote contém a interface MultiTrack atual, o ícone Mt, player, exportação
e porcentagem/estimativa de tempo. O atalho com ícone fica na pasta extraída;
não há criação automática de atalho na Área de Trabalho ou no menu Iniciar.

Não precisa instalar Python, Git, CUDA, compilador ou FFmpeg previamente.
Não precisa de administrador. `ExecutionPolicy Bypass` vale apenas para o
processo do bootstrap, sem mudar a política permanente do Windows.

Alvo: **Windows 10/11 x64 Intel/AMD**. ARM e Windows 32 bits não são suportados
por este pacote. Reserve **10 GiB livres** para instalar e processar; músicas e
resultados longos podem precisar de mais espaço. Recomendamos 16 GB de RAM;
8 GB podem ser limitantes. Não há garantia para processadores muito antigos.

O primeiro setup baixa cerca de **1,7 GB** pela internet. Python 3.12.10,
bibliotecas, FFmpeg e modelo ficam dentro desta pasta. Depois, separar e ouvir
funciona offline. Nenhum áudio é enviado pela internet.

O runtime é **Torch 2.8.0+cpu e ONNX Runtime CPU 1.26.0**, sem bibliotecas CUDA
nem exigência de driver NVIDIA. A UI inicia em CPU e mantém CLAP desabilitado
nesse modo. O Core calcula seis fontes; pedir menos faixas economiza arquivos,
não o cálculo da IA. O processamento pode ser longo, dependendo do computador.

## Se ocorrer erro

Veja `.tmp/install-cpu-bootstrap.log` e `.tmp/install-cpu.log`, corrija a causa
e execute o BAT novamente. Downloads completos verificados são reutilizados;
parciais de runtime/dependências recomeçam. O modelo usa a retomada do instalador
existente. Cache completo corrompido é recusado, com indicação do arquivo.

Uma `.venv` preexistente não é convertida: use uma pasta nova para preservar
ambientes GPU/de desenvolvimento. Repetir um setup CPU concluído/interrompido
é permitido; ele verifica tudo novamente. Não rode duas instalações na mesma
pasta simultaneamente. Nenhuma falha é declarada como instalação concluída.

O atalho fica na pasta do app. Não há serviço, tarefa agendada, registro de
instalação, mudança permanente de PATH ou driver. Para remover, feche o app e
remova a pasta após salvar os outputs desejados. Para atualizar, use outra pasta.

## Integridade e origens

`resources/cpu-setup.json` fixa HTTPS, tamanho e SHA-256 de Python, FFmpeg e
de todos os wheels Windows. Python é verificado antes de executar. Os demais
downloads ficam em `.partial` até passarem em tamanho/hash. Pip instala somente
wheels pinados do cache local, com `--require-hashes` e `--no-index`, sem source
builds ou resolução de versões novas no computador do colaborador.

Python vem do NuGet oficial `python/3.12.10`; wheels vêm de PyPI e PyTorch CPU;
FFmpeg é a build Gyan.dev 9.0.2 já aprovada pelo projeto. Mudança nos arquivos
servidos resulta em falha de hash, sem atualização automática. Os componentes
preservam suas licenças.

As DLLs MSVC já distribuídas pelo wheel verificado de PySide6 são colocadas em
`.venv/Library/bin`, caminho local pesquisado pelo Torch. Não se executa um
instalador global de Visual C++ Redistributable.

O ZIP não redistribui o peso. O script existente baixa o Core da origem/revisão
aprovada e verifica checkpoint e configuração. A disponibilidade para download
não concede licença para redistribuir modelos. Não se baixa CLAP/especialistas
nem se aceita checkpoint arbitrário.

## Gerar e verificar o pacote

```powershell
.\.venv\Scripts\python.exe .\scripts\build_cpu_package.py
```

Gera `outputs/packages/MultiTrack-CPU-setup.zip` e `.zip.sha256`, com manifest
de integridade. A allowlist inclui apenas fontes, scripts e recursos; exclui
ambientes, pesos, caches, músicas, `.git`, credenciais e resultados.

Para automação, `INSTALAR-CPU.bat --no-launch` instala sem abrir o app ao final.
O sucesso exige `pip check`, doctor CPU, importação da UI e Torch sem CUDA.
Evidência e limites: `docs/generated/cpu-installer-report.md`.
