# Runtime e armazenamento

## Desenvolvimento

Tudo mutável fica no projeto:

```text
StemLab/
├─ .venv/                 # Python local
├─ .cache/
│  ├─ pip/
│  ├─ torch/
│  ├─ huggingface/
│  └─ matplotlib/
├─ .tmp/
├─ models/
│  └─ <model-id>/
├─ tools/
│  └─ ffmpeg/
├─ outputs/
├─ bench/
│  ├─ private/
│  └─ reports/
├─ src/
├─ tests/
└─ docs/
```

Todos os diretórios pesados/privados ficam ignorados pelo Git, exceto relatórios textuais deliberadamente versionados.

## Job output

```text
outputs/<track-slug>/<job-id>/
├─ stems/
│  ├─ vocals.flac
│  ├─ drums.flac
│  ├─ bass.flac
│  ├─ guitar.flac
│  └─ ...
├─ manifest.json
└─ logs/
   └─ job.log
```

Intermediários podem ficar sob `.tmp/jobs/<job-id>/` e são limpos em sucesso; em falha, manter apenas se o usuário/dev mode pedir diagnóstico.

## Final portable build

Preferir layout explícito e atualizável:

```text
StemLab/
├─ app/
├─ runtime/
├─ tools/
├─ models/
├─ cache/
├─ data/
└─ StemLab.exe / launcher
```

Não empacotar 4–10 GB de pesos dentro de um único `.exe`.

## Space management

Model Manager deve mostrar tamanho aproximado/real por modelo e permitir remover somente modelo/cache, nunca output do usuário sem ação explícita.
