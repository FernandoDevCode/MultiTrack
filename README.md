# MultiTrack

Aplicativo Windows para separar uma música em **Vocals, Drums, Bass, Guitar,
Piano e Other**, ouvir as faixas em um player sincronizado e exportar o resultado.
Processamento local, com CUDA ou CPU, sem upload de áudio.

## Usar em outro computador

O pacote CPU está preparado; sua publicação em Releases está pendente.

Abra **[Releases / downloads](https://github.com/FernandoDevCode/MultiTrack/releases)**
e baixe **`MultiTrack-CPU-setup.zip`** nos Assets da versão CPU.
Extraia **todo** o ZIP e dê duplo clique em **`INSTALAR-CPU.bat`**.
Não é necessário clonar o projeto nem usar comandos. Como o repositório é
privado, o download pelo GitHub exige login e acesso ao projeto.

Ele prepara Python, bibliotecas CPU, FFmpeg e modelo dentro da própria pasta,
sem administrador nem instalações globais. O setup precisa de internet;
os usos seguintes funcionam offline. Veja o [guia do instalador CPU](docs/17_CPU_INSTALLER.md).
O código também contém o BAT, para quem baixar o ZIP do repositório.

O pacote inclui a interface atual **MultiTrack**, o ícone **Mt**, player,
exportação e progresso com estimativa de tempo. O instalador cria o atalho
`MultiTrack.lnk` dentro da pasta extraída. Depois, basta abrir esse atalho.
Em CPU, a análise experimental CLAP fica desativada. É preciso Windows 10/11
x64 Intel/AMD; reserve 10 GiB livres e internet para cerca de 1,7 GB no
primeiro setup. O processamento em CPU pode demorar.

Depois de preparar o ambiente, abra `START-MULTITRACK.bat`, escolha uma música,
o dispositivo e as faixas desejadas. A interface mostra porcentagem, etapa,
tempo decorrido e tempo restante estimado da IA; gravação e validação são
etapas adicionais. CPU pode ser lenta. Escolher menos faixas reduz os arquivos
entregues; o modelo continua calculando seis fontes.

## Colaborar no código

- [Estado atual e instruções detalhadas](README-FIRST.md).
- [Preparação do segundo computador](docs/16_COLLABORATOR_SETUP.md).
- [Regras do projeto](AGENTS.md).
- [Arquitetura](docs/01_SYSTEM_DESIGN.md).
- [Segurança e modelos](docs/03_SECURITY_AND_SANDBOX.md).

Os especialistas de guitarra/bass e a análise CLAP continuam experimentais,
sem promoção automática para o fluxo Core. Pesos, ambientes, caches, músicas
e resultados privados não são versionados. As licenças dos pesos são
independentes das licenças do código das bibliotecas.
