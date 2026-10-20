# Runtime CPU Windows — fontes e DLLs locais

Pergunta: o setup pode atender um Windows sem Python/compilador/CUDA, sem
depender implicitamente do Visual C++ Redistributable instalado na máquina dev?

Fontes consultadas: metadados oficiais PyPI para as versões pinadas da matriz,
índices oficiais PyTorch CPU e pacote NuGet oficial `python/3.12.10`.
`resources/cpu-setup.json` registra URLs exatas, tamanhos e SHA-256 dos 85 wheels,
Python e FFmpeg; `requirements-cpu.txt` registra os hashes usados pelo pip.
Todos os pins têm wheel compatível com Windows x64/CPython 3.12. Não há build
de código de dependências no computador alvo. PyTorch/torchvision mantêm versões
2.8.0/0.23.0, usando variantes CPU; ONNX Runtime mantém 1.26.0 na variante CPU.

Python NuGet: 14.515.433 bytes, SHA-256
`0eb85c2dfccccf1b17352de4c397f69194035b7d37149eacc16f1147d93de3b8`.
Contém Python completo, `venv`, `ensurepip` e vcruntime140/140_1 14.42.34438.0.
Não é o Python embeddable. A identidade é a distribuição NuGet 3.12.10; não
se inferiu um commit upstream que o pacote não fornece.

O wheel oficial PySide6-Essentials 6.9.2 contém as DLLs Microsoft
concrt140, msvcp140, msvcp140_1, msvcp140_2, msvcp140_codecvt_ids,
vcruntime140 e vcruntime140_1, além dos avisos/licenças da distribuição.
O wheel Torch não as inclui. Foi inspecionado o carregador Windows do
`torch/__init__.py` instalado em 2.8.0; SHA-256
`6d6c92d0b1091fc8f437cfe8228e9c9ad088dc0faf8446b1df8738f61c0834f2`.
Ele adiciona `sys.exec_prefix/Library/bin` aos diretórios de DLLs antes de
carregar as bibliotecas Torch e tenta carregar explicitamente MSVC por nome.

Decisão: ler as sete DLLs diretamente do wheel PySide6 já verificado e
colocá-las em `.venv/Library/bin`, sem alterar upstream, sistema, registro ou
PATH permanente. Registrar hashes das cópias na receipt CPU. Preservar o
pacote PySide6 completo instalado com suas licenças. O ZIP de setup não embute
nem redistribui esses binários: eles são obtidos da distribuição oficial no
primeiro setup. Não há execução de instalador VC_redist global nem dependência
em compilador/winget. Se a matriz mudar, revalidar esse carregamento.

FFmpeg 9.0.2 usa o mesmo SHA-256 já aprovado para o arquivo de Gyan.dev:
`60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`.
O modelo mantém a origem e o hash já aprovados no instalador Core existente;
o YAML passa a exigir também seu SHA-256 explícito, além do Git blob SHA-1.

Isso não comprova compatibilidade com toda CPU/Windows nem substitui um teste
em outro computador. A evidência executada fica no relatório do instalador.

## Core em instalação nova sem catálogos

O primeiro smoke com proxies bloqueados falhou: mesmo com checkpoint e YAML
aprovados presentes, `Separator.download_model_files()` chama a descoberta de
modelos e tenta buscar `download_checks.json` no GitHub. O cache da máquina dev
ocultava essa dependência; baixar somente os dois artefatos Core não bastava.

Foi inspecionado `separator/separator.py` da distribuição pinada 0.47.0:
`load_model()` usa a tupla retornada por `download_model_files()` e carrega
diretamente o YAML quando ele é fornecido. O adapter passa a usar um subclass
mínimo para o Core, retornando somente o par aprovado MDXC local. A allowlist
valida nomes, model ID e hashes esperados; o serviço continua verificando os
bytes reais antes de qualquer carga. Rejeitar outro identificador de backend.
Preservar `load_model`, parâmetros, normalização, forward, escrita e validação
upstream existentes. Sem catálogo mutável, download adicional ou novo modelo.

Regressão necessária: instalação nova sem arquivos de catálogo, rede bloqueada,
inferência real no runtime CPU e smoke CUDA pelo mesmo adapter. Um cache antigo
preenchido não serve como evidência suficiente de funcionamento offline.
