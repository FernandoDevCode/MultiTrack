# Produto — StemLab

## Problema

Ferramentas antigas de “remove vocal” usam cancelamento de fase, filtros e heurísticas. O objetivo aqui é usar modelos modernos de Music Source Separation para estimar fontes reais da mistura, localmente, sem upload e com um workflow de audição/export útil.

## Usuário e prioridade

Uso principal: uma pessoa no desktop separando músicas para estudar/escutar instrumentos. A prioridade é **qualidade**, depois previsibilidade, depois velocidade. O produto não é um DAW.

## Casos de uso do MVP

1. Arrastar/abrir WAV, FLAC, MP3 ou M4A.
2. Escolher um preset de separação.
3. Rodar localmente em GPU quando disponível.
4. Ver progresso por estágio, cancelar e receber erro compreensível.
5. Ouvir original + stems sincronizados.
6. Solo, mute e volume por stem.
7. Exportar stems lossless.
8. Gerenciar modelos instalados e espaço em disco.
9. Ver diagnóstico de GPU/runtime/modelo usado.

## Presets de produto

### Core Stems

Meta funcional:

- Vocals
- Drums
- Bass
- Guitar
- Piano/Keys quando o modelo justificar
- Other

A implementação pode usar mais de um modelo/estágio. O produto não deve expor arquitetura de ML como se fosse UX obrigatória.

### Guitar Lab

- `Guitar` (todas as guitarras): estável quando o benchmark aprovar o modelo.
- `Lead / Rhythm`: **experimental até gate de qualidade**.
- `Acoustic / Electric`: futuro/experimental, também condicionado a modelo e benchmark.

Não prometer separação de “guitarra 1 / guitarra 2” arbitrária. `lead/rhythm` é uma classificação semântica específica, não identificação universal de músicos.

## Modos de qualidade

No começo, só implementar **HQ**. Não criar três presets de velocidade antes de termos evidência de modelos.

Depois do benchmark, podem existir:

- Preview: modelo/parametrização rápida.
- HQ: melhor opção única comprovada para o task.
- Max: ensemble/segunda passagem quando a melhora auditiva justificar o custo.

## O que NÃO é MVP

- treinamento de modelo grande;
- cloud inference;
- login/conta;
- colaboração;
- editor multitrack completo;
- time-stretch/pitch-shift;
- MIDI/transcrição;
- VST/DAW plugin;
- download de YouTube/Spotify;
- marketplace de modelos;
- aceitar pesos arbitrários;
- suporte macOS/Linux como requisito de release inicial.

## Critérios de produto

O MVP só é “bom” se:

- separar áudio localmente sem internet após setup;
- a UI permanecer responsiva durante inferência;
- stems iniciarem perfeitamente alinhados ao sample 0;
- não houver compressão lossy interna;
- usuário puder comparar rapidamente original e stems;
- erro de modelo/GPU não destruir job anterior nem o input;
- o modelo/default tiver evidência registrada, não apenas “pareceu bom”.
