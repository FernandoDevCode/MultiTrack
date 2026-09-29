# Segurança, sandbox e downloads

## Objetivo prático

Durante desenvolvimento, o Codex deve poder criar ambiente, baixar dependências/modelos e rodar testes **sem ganhar permissão de escrita pelo computador inteiro**.

## Codex nativo no Windows

Config recomendada deste projeto:

```toml
sandbox_mode = "workspace-write"
approval_policy = "on-request"
approvals_reviewer = "user"

[sandbox_workspace_write]
network_access = false
writable_roots = []
```

O modo `workspace-write` permite alterações no workspace atual e comandos locais rotineiros; rede ou saída do limite pedem aprovação. Não adicionar `writable_roots` extras.

### Limitação importante

No Windows, isso limita **gravação** ao workspace, mas o sandbox padrão pode permitir leitura de partes amplas do sistema/perfil. Se a exigência for “o agente não pode nem ler nada fora dessa pasta”, o sandbox padrão não é a fronteira correta.

Para isolamento de leitura mais forte:

- WSL2 + `ai-jail` (backend Linux), ou
- VM descartável.

`ai-jail` não tem backend nativo para Windows; o próprio projeto recomenda WSL2. Para este projeto, eu não tornaria WSL2 obrigatório só por isso: Codex `workspace-write` + aprovação de rede é suficiente para desenvolvimento normal, e WSL2/ai-jail fica como opção de paranoia maior.

## Onde tudo deve morar

```text
<repo>/.venv/
<repo>/.cache/pip/
<repo>/.cache/torch/
<repo>/.cache/huggingface/
<repo>/.cache/matplotlib/
<repo>/.tmp/
<repo>/models/
<repo>/tools/ffmpeg/
<repo>/outputs/
<repo>/bench/private/
```

Antes de `pip`, downloads e execução, o bootstrap deve definir no processo:

```text
PIP_CACHE_DIR=<repo>/.cache/pip
TORCH_HOME=<repo>/.cache/torch
HF_HOME=<repo>/.cache/huggingface
XDG_CACHE_HOME=<repo>/.cache
MPLCONFIGDIR=<repo>/.cache/matplotlib
TEMP=<repo>/.tmp
TMP=<repo>/.tmp
```

O model loader deve receber `model_file_dir=<repo>/models` explicitamente; não depender do default do sistema.

## O que Codex pode baixar

Com aprovação de rede:

- wheels Python para `.venv`;
- pesos/model configs explicitamente escolhidos na fase de benchmark;
- FFmpeg Windows a partir de fonte revisada, gravado em `tools/ffmpeg/`;
- clones rasos de dependências para inspeção, somente dentro de `.research/deps/` e sem instalar dali automaticamente.

## O que Codex NÃO pode fazer sem nova autorização

- `winget install`, Chocolatey, MSI/EXE de sistema;
- alterar driver NVIDIA;
- instalar CUDA Toolkit global;
- editar PATH permanente do usuário/sistema;
- escrever em Program Files/AppData para “resolver” uma dependência;
- desabilitar antivírus/Defender;
- usar `danger-full-access`;
- baixar e executar binário obscuro;
- baixar checkpoints de links encontrados aleatoriamente e carregá-los.

## Dependências

Preferir PyPI oficial, PyTorch official wheel index e releases oficiais/upstream. Pin de versão só é aceito depois do smoke no hardware real.

Para RTX 50-series/Blackwell, a família de wheels PyTorch com CUDA 12.8+ suporta a arquitetura; a fase 0 deve escolher uma combinação que também respeite as restrições de `audio-separator` no Windows.

## FFmpeg

Não exigir FFmpeg global. Baixar uma build Windows revisada para `tools/ffmpeg/`, registrar URL/version/hash e adicionar esse diretório ao `PATH` **somente no processo do aplicativo/dev shell**.

## Model weight supply chain

Checkpoint PyTorch pode ser um vetor de execução de código dependendo de como é carregado. Controles obrigatórios:

1. allowlist em `resources/models.json`;
2. HTTPS;
3. URL de origem registrada;
4. tamanho máximo esperado;
5. SHA-256 esperado;
6. `.partial` + rename atômico;
7. sem upload/import arbitrário de `.ckpt/.pth` no MVP;
8. worker sem rede durante inferência;
9. não carregar peso cuja integridade falhou.

## Áudio privado

- `bench/private/`, `outputs/`, `models/`, `.cache/`, `.tmp/` ficam no `.gitignore`.
- não anexar música/saídas privadas em issue, CI ou commit;
- testes automatizados versionados usam sinais sintéticos ou fixtures liberadas pequenas;
- benchmarks privados geram relatório numérico sem incorporar áudio ao Git.
