# Correção MP3 → PCM e detalhes de erro — 2026-10-19

**Resultado técnico:** PASS.

Causa reproduzida: `audio-separator==0.47.0` tentava publicar WAV com o subtipo
`MPEG_LAYER_III` detectado na entrada MP3. O writer passou a receber somente
PCM/float compatível, sem alterar o decoder, inferência ou arquivo de entrada.
Detalhes em `../research/audio-separator-047-mp3.md`.

- Suíte completa: **109 passed, 9 skipped**. Integrações pesadas são opt-in.
- `python -m pip check`: PASS. Sem lint/type checker adicional configurado.
- Mensagem de falha da UI: inclui o motivo estruturado do worker.
- Testes de regressão: writer upstream real, MP3 real gerado localmente,
  ganho, samples, codificação, duração, canais, finitude e integridade do input.

## Smoke com a música que falhou

Três execuções reais sequenciais na mesma janela, Core Stems, AUTO → CUDA,
somente Guitar solicitada. Em cada execução, seis fontes foram inferidas e
validadas antes da retenção de apenas Guitar. Todos os arquivos finais têm
184,645079 s, 44.100 Hz e dois canais.

| Entrada | Saída | Encoding | Player/export | Input intacto |
|---|---|---|---|---|
| MP3 | WAV | FLOAT | PASS | PASS |
| MP3 | FLAC | PCM_24 | PASS | PASS |
| MP3 | MP3 | MPEG_LAYER_III, 320 kbps | PASS | PASS |

Evidência privada local: `.tmp/mp3-output-encoding-smoke.json`, com paths,
SHA-256, device e contagem de heartbeats da UI. Exportações passaram comparação
SHA-256; player carregou só Guitar e renderizou stems e original com cursor
compartilhado. Nenhuma chamada de inferência foi feita na UI.

Limites: reprodução em dispositivo físico e qualidade musical não foram
avaliadas neste reparo. Não houve mudança de checkpoint/default nem promoção
de especialistas.
