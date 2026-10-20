# Usar o MultiTrack em um segundo Windows

## Acesso ao código

O repositório `FernandoDevCode/MultiTrack` é privado. O proprietário precisa convidar
o usuário GitHub do colaborador; o convidado deve aceitar antes de clonar.

```powershell
git clone https://github.com/FernandoDevCode/MultiTrack.git
cd MultiTrack
```

Também é possível baixar o ZIP do código estando autenticado no GitHub.
O nome público do app é MultiTrack; o pacote Python continua se chamando
`stemlab` por compatibilidade.

## O que precisa existir além do código

O launcher atual usa um ambiente local validado em Windows x64. O clone
sozinho não contém os itens abaixo, nem existe um instalador publicado.

| Pasta no clone | Conteúdo necessário |
|---|---|
| `tools/python312/` | Python completo 3.12.10 x64 local, incluindo `python.exe`, `pythonw.exe` e biblioteca padrão |
| `.venv/` | Ambiente do projeto, incluindo PyTorch 2.8.0+cu128, audio-separator 0.47.0, PySide6 e instalação editable de `stemlab` |
| `tools/ffmpeg/` | FFmpeg local; `bin/ffmpeg.exe` e `bin/ffprobe.exe` |
| `models/` | Core BS-RoFormer SW e YAML verificados pelo instalador existente |

Para a avaliação colaborativa atual, o caminho mais direto é receber do
proprietário **uma cópia privada das três pastas de runtime**:
`tools/python312/`, `.venv/` e `tools/ffmpeg/`. Copie-as para os caminhos da
tabela, dentro do clone, com o app fechado. Preserve os arquivos de licença
que acompanham Python, FFmpeg e bibliotecas. Esse runtime é grande, não vai
para commits e não deve incluir `.cache/`, `.tmp/`, `outputs/`, músicas ou
modelos. A cópia precisa vir do ambiente confiável do projeto.

O launcher ajusta os caminhos absolutos do Python e da instalação editable
para a nova pasta. Essa reparação já é usada quando o projeto muda de unidade.
Não é um instalador genérico nem uma garantia de compatibilidade com qualquer
hardware. Não é necessário instalar CUDA Toolkit global; GPU NVIDIA requer
driver compatível. CPU pode ser usada mesmo sem GPU NVIDIA.

Quem reconstruir o ambiente em vez de receber o runtime deve manter a matriz
pinada em `requirements-gpu.txt`, `requirements-lock.txt` e `pyproject.toml`,
com Python local completo em `tools/python312/`. O launcher exige essa
estrutura. Não substituir por versões mais novas nem por Python embeddable
sem validar novamente. O projeto ainda não tem bootstrap automático de clone
limpo; a reconstrução deve ser acompanhada por alguém com experiência Python.

## Preparar o modelo Core

Com o runtime nas pastas acima, abra PowerShell na raiz do clone e execute:

```powershell
& .\tools\python312\python.exe -X utf8 .\scripts\repair-local-runtime.py
& .\.venv\Scripts\python.exe -X utf8 .\scripts\install_bs_roformer_sw.py
```

O segundo comando baixa aproximadamente 700 MB da origem fixada no script,
valida tamanho/hash e instala somente os artefatos Core aprovados. Internet
é necessária para esse setup; não para separar/reproduzir depois. Não copiar
pesos de origem incerta, não carregar checkpoints arbitrários e não anexar
pesos a commits/releases. A disponibilidade para download não concede por si
só licença para redistribuir o modelo.

CLAP e os especialistas não são necessários para separar as seis fontes.
O botão de análise experimental pode falhar se seus artefatos opcionais não
estiverem instalados; isso não impede a separação Core.

## Verificar e abrir

```powershell
. .\scripts\dev-env.ps1
python -m pip check
python .\scripts\doctor.py --profile cpu
```

O perfil CPU verifica o ambiente sem exigir a RTX 5060 nem os modelos opcionais.
Ele não comprova velocidade/compatibilidade física em toda máquina. O perfil
GPU histórico é específico do equipamento original do projeto.

Abra `START-MULTITRACK.bat`. Para o primeiro teste, use uma música curta,
escolha `CPU` ou `Automático`, aguarde a separação e confira player/exportação.
Os resultados são criados em uma pasta nova sob `outputs/`; o original é
somente leitura. O ETA mede a inferência observada; a finalização dos arquivos
é adicional e 100% aparece somente após validação.

Para criar o atalho local opcional:

```powershell
.\scripts\create-shortcut.ps1
```

Se o launcher falhar, veja `.tmp/startup-check.log`. Registre o erro e o hardware
ao pedir ajuda; não envie músicas, tokens ou arquivos de credenciais.

## Atualizar

Com o app fechado e sem alterações locais pendentes:

```powershell
git pull --ff-only
```

Abra novamente pelo launcher. Mudanças futuras em dependências/modelos podem
exigir atualização específica do runtime; `git pull` não instala dependências.
Para desenvolver, use branches e PRs, mantendo ambientes, caches, músicas e
outputs fora do Git.

## Evidência e limites

O ambiente original passou em 124 testes e no smoke real UI/worker/CUDA da
feature de progresso. A reparação de caminhos tem testes próprios. A operação
em outro PC e a transferência do runtime ainda precisam de aceitação nesse PC;
não foram declaradas testadas por publicar o código no GitHub.
