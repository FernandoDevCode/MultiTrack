# StemLab v0.2 — Checkpoint 3 technical report

**Resultado técnico:** PASS_TECHNICAL

**Data:** 2026-10-02

**Quality gate:** pendente. Nenhum especialista foi aprovado para integração.

## Escopo executado

O gate técnico implementa e valida somente os candidatos research-only
`lead_rhythm_listra92` e `bass_xlancer`. Não houve integração na UI, troca do
Core Stems, alteração do CLAP, ensemble ou inclusão de outra classe de
instrumento.

O harness headless é executado com:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_specialists.py --input "C:\caminho\musica.wav"
```

Cada modelo pesado roda em um subprocesso efêmero. O Core roda uma vez; Guitar e
Bass dessa execução são reutilizados como G0 e B0. G1 usa a mix original, G2 usa
G0, e B1 usa a mix original. Os sete WAVs e o manifest ficam somente em
`bench/private/<track>/<run>/`.

## Supply chain e allowlist

Antes de qualquer load foi executado:

```text
scripts/install_specialist_candidates.py --verify-only: PASS
```

O receipt `.tmp/specialist-candidates-install.json` foi lido. A allowlist no
adapter fixa ID, path relativo, tamanho, origem, revisão e os dois hashes de cada
candidato:

| ID | checkpoint SHA-256 | YAML SHA-256 | status |
|---|---|---|---|
| `lead_rhythm_listra92` | `b3c47bca33609ca1ba0bb2d2076410bfd1eb941b051b72afc1f3e24d12b17eef` | `fc47975bba58b7b4c6de363bfe158943092c77bfb0b9a41c0c741eafba330359` | research-only |
| `bass_xlancer` | `c409465e3dccfd83fa34e6a807dbdae2f4f1db24f2f85a0fdc146b6fa828afff` | `dd9164936be88e636ccae0b6689e5b2f299f2cd9668918071e0795cd8cdd7e00` | research-only |

A licença/redistribuição dos pesos permanece desconhecida. Os artefatos são
revalidados por tamanho e SHA-256 antes de cada load. O caminho de inferência não
tem downloader, não aceita path de especialista e usa proxies inválidos mais
flags offline. ID, filename ou tuple diferentes falham sem fallback.

## Integração com audio-separator 0.47.0

O loader instalado sempre chama `download_model_files()` e procura o filename no
registry normal antes de carregar. Os dois candidatos locais não constam nesse
registry. O adapter fornece um resolver estreito que retorna o contrato local
verificado esperado pelo loader. Core Stems continua usando o `Separator`
original.

Foi encontrada uma incompatibilidade adicional do loader 0.47.0 para o candidato
Lead/Rhythm: o YAML preserva `mlp_expansion_factor: 2`, mas a implementação
vendorizada não o repassa ao `MaskEstimator`, criando camadas 1536 em vez das 768
do checkpoint. O adapter corrige somente os mask estimators desse ID/hashes antes
do `load_state_dict`; `site-packages`, YAML e checkpoint não são modificados. A
inspeção está registrada em
`docs/research/audio-separator-047-specialist-loader.md`.

## Evidência CUDA/offline

Hardware e runtime:

- Windows 11; Python 3.12.10;
- PyTorch 2.8.0+cu128; CUDA runtime 12.8;
- NVIDIA GeForce RTX 5060, 8.151 MiB reportados pelo driver;
- `audio-separator==0.47.0`;
- WAV PCM, 44,1 kHz, estéreo; autocast.

Harness curto completo sobre fixture sintética local de 10 s:

| estágio | variante | total | pico CUDA alocado | pico CUDA reservado | device/precision |
|---|---|---:|---:|---:|---|
| Core | G0 + B0 | 6,442 s | 1.666.831.872 B | 2.130.706.432 B | cuda/autocast |
| Lead/Rhythm direto | G1 | 4,501 s | 744.493.056 B | 1.019.215.872 B | cuda/autocast |
| Lead/Rhythm sobre G0 | G2 | 4,940 s | 744.493.056 B | 1.019.215.872 B | cuda/autocast |
| Bass direto | B1 | 2,521 s | 916.126.208 B | 1.107.296.256 B | cuda/autocast |

Manifest privado da evidência:
`bench/private/phase0-synthetic-mix/technical-smoke-final/manifest.json`.
Ele registra hashes, metadados, runtime, device, precisão, VRAM e os sete outputs.
O diretório é ignorado pelo Git.

Resultados estabelecidos:

- os dois candidatos carregam na RTX 5060 e produzem exatamente `lead/rhythm` e
  `bass/other`;
- G0/B0 vêm de uma única execução Core e G2 recebe G0;
- todos os sete outputs têm 10 s, 44,1 kHz, dois canais e amostras finitas;
- SHA-256 do input antes/depois:
  `8e7c53fe531f2a105a5c734389736f7183940a5647a05b24509ca78b0ee54fa0`;
- cada estágio pesado termina antes do próximo, evitando retenção conflitante de
  CUDA;
- falha de variante é registrada e interrompe o fluxo, sem substituição oculta.

## Gates automatizados

- `python -m pytest -q`: **61 passed, 6 skipped**;
- testes novos: registry/allowlist, mismatch de checkpoint e YAML, ID desconhecido,
  path arbitrário, ausência de rede na resolução, roles, reutilização Core,
  manifest, input intacto, validação de output e ausência de fallback;
- `python -m pip check`: **PASS**;
- `python scripts/doctor.py`: **PASS**;
- smoke Core BS-RoFormer existente: **PASS**;
- smoke Lead/Rhythm CUDA/offline: **PASS**;
- smoke Bass CUDA/offline: **PASS**;
- harness curto G0/G1/G2/B0/B1 CUDA/offline: **PASS**.

## Limites e não testado

Limitado:

- a fixture sintética prova execução, I/O, roles e integridade, não qualidade
  musical;
- tempos variam com cache, driver e duração da faixa;
- os pesos têm licença desconhecida e não podem virar default distribuível.

Não testado/aprovado:

- qualidade perceptual em músicas reais;
- estabilidade semântica Lead/Rhythm em diferentes arranjos;
- bleed, artefatos, transientes, sustain e preservação de timbre;
- superioridade de G1 ou G2 sobre G0, ou de B1 sobre B0.

O gate humano de pelo menos três músicas privadas continua obrigatório. Até ele,
ambos os especialistas permanecem `research-only`; nenhum vencedor foi declarado.
