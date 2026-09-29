Config Codex
Modelo: GPT-5.6 Sol
Effort: High
Plan: ON
Motivo: primeira execução; precisamos descobrir o estado real do Windows, Python, GPU/CUDA e compatibilidade das dependências antes de piná-las. O escopo de produto e arquitetura já está fechado, mas a matriz de runtime ainda precisa de evidência.

# Fase 0 — Environment & dependency spike

Leia `AGENTS.md`, `docs/03_SECURITY_AND_SANDBOX.md`, `docs/05_ROADMAP.md` e apenas a documentação adicional que essas decisões exigirem.

Objetivo: provar um ambiente local e autocontido para StemLab no Windows sem modificar software globalmente.

## Escopo permitido

Você pode criar/alterar somente:

- `.gitignore`
- `pyproject.toml` e arquivos de lock/requirements necessários
- `scripts/dev-env.ps1`
- `scripts/doctor.py`
- `docs/generated/environment-report.md`
- subpastas locais ignoradas: `.venv/`, `.cache/`, `.tmp/`, `models/`, `tools/`, `.research/`

Não implemente `src/stemlab`, GUI, job system ou separação de produto ainda.

## Invariantes

- não usar winget/choco/conda global;
- não instalar ou atualizar driver NVIDIA/CUDA Toolkit;
- não escrever dependências/caches/modelos fora do repo deliberadamente;
- não usar Docker;
- não usar `danger-full-access`;
- não baixar checkpoints aleatórios;
- não alterar configuração global do Codex;
- se Python 3.12 não existir, pare e reporte em vez de instalar globalmente.

## Trabalho

1. Inspecione Python, `nvidia-smi`, GPU/driver e espaço livre sem alterar sistema.
2. Configure `scripts/dev-env.ps1` para apontar `TEMP`, `TMP`, `PIP_CACHE_DIR`, `TORCH_HOME`, `HF_HOME`, `XDG_CACHE_HOME`, `MPLCONFIGDIR` para dentro do repo e ativar `.venv` quando existir.
3. Crie `.venv` local com Python 3.12.
4. Pesquise somente fontes oficiais/upstream quando necessário para escolher a combinação Torch/CUDA compatível com a GPU e com `audio-separator`. Registre a razão; não use “latest” cegamente.
5. Instale tudo somente na `.venv`. Rede pode ser solicitada para esse passo.
6. Rode smoke de PyTorch: versão, `torch.cuda.is_available()`, nome do device, capability e alocação tensorial simples em CUDA.
7. Instale/import `audio-separator`; rode seu environment info e liste modelos em JSON. Não baixe uma coleção de modelos.
8. Se um FFmpeg for indispensável ao smoke, baixe uma build Windows de fonte upstream reconhecida para `tools/ffmpeg/`, registre versão/URL/SHA-256 e use PATH apenas do processo. Se não for necessário ainda, adie.
9. Não baixe modelo pesado nesta fase, salvo se for indispensável para confirmar que o loader consegue inicializar um baseline pequeno. Nesse caso, pare antes e peça aprovação mostrando qual arquivo/tamanho/origem será baixado.
10. Gere `docs/generated/environment-report.md` com comandos e resultados reais, versões pinadas candidatas, riscos e próximos passos.

## Critérios de aceite

- `.venv` está dentro do repo;
- caches/temp configurados dentro do repo;
- Torch enxerga a GPU real e executa tensor em CUDA, ou há blocker documentado sem workaround perigoso;
- `audio-separator` importa e enumera catálogo;
- nenhuma instalação global foi feita;
- relatório lista tudo que foi baixado/instalado;
- `git status` não mostra arquivos pesados/privados que deveriam estar ignorados.

Pare ao fim desta fase. Não avance para a Fase 1.
