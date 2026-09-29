# Testes e avaliação

## Dois tipos de verdade

### Correção de software

Testes automatizados respondem:

- o job roda?
- os arquivos existem?
- têm duração/sample rate/canais corretos?
- não há NaN/Inf?
- cancelamento funciona?
- hashes/downloads funcionam?
- UI/worker não corrompem estado?

### Qualidade de separação

Não pode ser inferida de “os testes passaram”. Precisa de benchmark + audição.

## Testes unitários

Cobrir pelo menos:

- parsing/validação do model registry;
- hash/integrity e download atômico com servidor/fonte simulada;
- path handling;
- pipeline planner;
- protocolo worker/UI;
- ganho/mute/solo do mixer;
- manifests;
- erros e cancelamento;
- cálculo das métricas.

Não usar internet em teste unitário.

## Integração curta

Gerar fixtures sintéticas pequenas:

- seno L/R;
- impulsos em tempos conhecidos;
- dois tons distintos;
- ruído curto.

Elas não provam qualidade do ML; provam alinhamento, I/O e mixer.

## Smoke de modelo

Cada modelo candidato deve passar:

- load no device esperado;
- separar clip curto real/licenciado ou privado;
- output com stems esperados;
- mesma duração útil;
- sem NaN/Inf;
- sem crash/OOM no perfil-alvo;
- medir tempo e pico de VRAM;
- rodar segunda vez para confirmar cache/offline.

## Benchmark com ground truth

Quando houver stems de referência:

- SI-SDR por stem;
- leakage cruzado/projeção de energia;
- erro de duração/alinhamento;
- opcionalmente SDR compatível com benchmark externo quando a definição for equivalente.

Não comparar números de papers/sites como se fossem diretamente comparáveis quando dataset/protocolo diferirem.

## Lead/Rhythm benchmark

Montar conjunto com pelo menos:

- hard-panned lead/rhythm;
- duas guitarras próximas do centro;
- distorção semelhante;
- clean + distortion;
- delay/reverb estéreo;
- trechos onde ambas tocam simultaneamente;
- trechos com apenas uma guitarra;
- troca de densidade/solo.

Métricas mínimas:

- SI-SDR lead vs. referência;
- SI-SDR rhythm vs. referência;
- leakage lead→rhythm e rhythm→lead;
- conservação de energia/timbre;
- runtime/pico VRAM.

Avaliação humana cega/AB sempre que possível:

- bleed;
- artefatos aquosos/metálicos;
- transientes;
- preservação de sustain/reverb;
- estabilidade semântica lead/rhythm.

Registrar observações por faixa; não resumir tudo a um único score.

## Critério para trocar default

Um modelo novo só substitui o default se:

- ganha de forma consistente na task relevante;
- não introduz regressão importante em outro eixo;
- cabe no hardware-alvo;
- não aumenta dependências/riscos desproporcionalmente;
- origem/licença são aceitáveis;
- o relatório foi salvo em `bench/reports/`.

## Performance

Registrar por job/stage:

- wall time;
- real-time factor aproximado;
- peak CUDA allocated/reserved quando aplicável;
- CPU fallback time;
- tamanho dos modelos;
- cache quente vs. primeira execução.

## Gate de release

Antes de considerar uma versão utilizável:

1. suíte automatizada verde;
2. smoke em Windows real;
3. GPU detectada corretamente;
4. pelo menos um job completo com rede desligada;
5. player sincronizado após seek repetido;
6. export reabre corretamente;
7. input original permanece byte-identical;
8. `models/`, `.cache/`, `bench/private/` e outputs fora do Git;
9. Model Manager não carrega peso não verificado;
10. relatório das limitações conhecido e visível.
