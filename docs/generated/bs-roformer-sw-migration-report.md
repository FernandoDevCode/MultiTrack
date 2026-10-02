# BS-RoFormer SW — migração de seis stems

**Resultado:** PASS  
**Data:** 2026-09-29

## Artefatos e origem

O instalador local foi revalidado sem download com
`scripts/install_bs_roformer_sw.py --verify-only`. Os artefatos pinados pelo
receipt `.tmp/bs-roformer-sw-install.json` são da revisão imutável
`3b39120409f3c2d50e9cc4c391f4169131e9d643` de
`lainlives/audio-separator-models`:

| Artefato | Bytes | SHA-256 |
|---|---:|---|
| `BS-Roformer-SW.ckpt` | 699,412,152 | `24e7d35ee9c64415673d3fd33e06a67cac2c103c5df6267ba1576459c775916e` |
| `BS-Roformer-SW.yaml` | 4,653 | `b558996f1e25eb48798bd6502505a5de94c4f966d6edfb1a0420f06cc40b501a` |

O `SeparationService` revalida os dois hashes antes de cada `load_model`.

## Smoke direto

Fixture sintética local de 10,0 s, 44,1 kHz e estéreo; SHA-256 de input antes
e depois: `8e7c53fe531f2a105a5c734389736f7183940a5647a05b24509ca78b0ee54fa0`.

- Backend: `audio-separator/0.47.0` (MDXC).
- Device solicitado/efetivo: CUDA/CUDA; precisão: autocast; sem fallback ou warnings.
- Stems válidos e não silenciosos: bass, drums, other, vocals, guitar, piano.
- Duração, sample rate e canais de cada stem: 10,0 s, 44,1 kHz, estéreo.
- Manifest: `.tmp/bs-roformer-direct-smoke/manifest.json`.
- Load: 5,925 s; inferência: 2,888 s; total: 8,814 s.
- Pico CUDA: 1.666.831.872 bytes alocados; 2.130.706.432 bytes reservados.

## Smoke UI/QProcess

O caminho `MainWindow -> QProcess -> run_job -> SeparationService` passou com
proxies HTTP(S) apontando para endpoint inválido. A UI continuou responsiva e
produziu FLACs e manifesto em
`outputs/phase0-synthetic-mix/20260929-233555-474005/`.

- CUDA/autocast efetivos; seis stems exatos; input intacto; sem warnings.
- Load: 3,996 s; inferência: 3,426 s; total: 7,422 s.
- Pico CUDA: 1.666.831.872 bytes alocados; 2.130.706.432 bytes reservados.

## Testes e limpeza

- `STEMLAB_RUN_GPU_SMOKE=1 python -m pytest tests/integration/test_audio_separator_gpu.py -q -rA`: 1 passed.
- `STEMLAB_RUN_FAST_TRACK_SMOKE=1 python -m pytest tests/integration/test_fast_track_ui_worker.py -q -rA`: 1 passed.
- `python -m pytest -q`: 23 passed, 2 skipped.
- `python -m pip check`: nenhuma dependência quebrada.
- `python scripts/doctor.py`: PASS, incluindo os dois artefatos BS-RoFormer SW.
- Removidos após os smokes PASS: `models/5c90dfd2-34c22ccb.th` e
  `models/htdemucs_6s.yaml`.

## Limitações

O smoke estabelece compatibilidade, integridade, execução CUDA e contratos de
saída; não estabelece qualidade musical comparativa nem licença de
redistribuição do checkpoint. Não foi implementado nenhum player, downloader,
registry genérico, ensemble ou fluxo lead/rhythm.
