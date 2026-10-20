# MultiTrack

Aplicativo Windows para separar uma música em **Vocals, Drums, Bass, Guitar,
Piano e Other**, ouvir as faixas em um player sincronizado e exportar o resultado.
Processamento local, com CUDA ou CPU, sem upload de áudio.

## Usar em outro computador

Veja o [guia para colaboradores](docs/16_COLLABORATOR_SETUP.md).
**Baixar o código pelo GitHub não instala o aplicativo:** Python, dependências,
FFmpeg e o modelo ficam fora do Git e precisam ser preparados no segundo PC.
Ainda não há instalador Windows publicado.

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
