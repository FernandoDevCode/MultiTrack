# Fast Track v0.1 — caminho ativo

## Objetivo

Colocar uma versão **realmente utilizável** do StemLab na mão do usuário rapidamente, sem jogar fora a arquitetura saudável já construída.

A meta de tempo é uma prioridade de escopo, não uma promessa rígida de relógio: quando houver trade-off, cortar acabamento antes de cortar funcionamento/correção.

## Ponto de partida

Já concluído:

- Fase 0: ambiente local, CUDA/RTX 5060, FFmpeg e backend validados.
- Fase 1: `SeparationService`, contratos, adapter `audio-separator`, CLI e manifest validados em CUDA.

Portanto o Fast Track **não reimplementa engine**.

## Entrega v0.1

Fluxo:

```text
START-STEMLAB.bat
   ↓
PySide6 UI
   ↓
subprocess/QProcess
   ↓
SeparationService existente
   ↓
AudioSeparatorBackend
   ↓
CUDA -> stems
```

O usuário deve conseguir:

1. iniciar sem terminal;
2. escolher uma música;
3. escolher modo;
4. iniciar separação;
5. perceber claramente que está processando;
6. receber stems em output previsível;
7. abrir a pasta resultante.

## Modos obrigatórios

### 1. Vocals HQ (experimental)

Reutilizar o BS-RoFormer já validado tecnicamente.

Regras:

- manter rótulo experimental;
- não promover licença/status;
- não redistribuir o peso;
- não chamar o smoke anterior de benchmark de qualidade.

### 2. 6 Stems (baseline)

Saídas:

- Vocals
- Drums
- Bass
- Guitar
- Piano
- Other

Preferência: `htdemucs_6s` se o smoke local confirmar compatibilidade.

É permitido fazer a menor extensão necessária no contrato/adapter para suportar a forma de modelo do Demucs. Não construir registry genérico para isso.

## Fases internas do Fast Track

### FT-A — modo 6-stem funcional

- baixar somente o modelo necessário para `models/`;
- registrar origem/artefatos relevantes;
- integrar pelo engine existente;
- provar CUDA + seis outputs válidos;
- manter input intacto.

Se isso bloquear por incompatibilidade real, resolver dentro do workspace. Não substituir por heurística de áudio antiga.

### FT-B — subprocesso mínimo

- executar inferência fora da UI;
- preferência por `QProcess` ou subprocesso Windows simples;
- eventos mínimos: started/status/completed/failed;
- progresso indeterminado se não houver fração confiável;
- cancelamento somente se pequeno e seguro.

Não criar broker, fila persistente ou protocolo distribuído.

### FT-C — UI mínima

Implementar `docs/09_UI_SPEC.md` na seção Fast Track.

### FT-D — launcher + smoke

Criar launcher na raiz, por exemplo `START-STEMLAB.bat`, usando runtime/venv local.

Rodar pelo menos um smoke real completo pela nova UI/worker, preferencialmente no modo 6 Stems.

## Prioridade quando houver trade-off

1. separação correta;
2. CUDA real;
3. outputs válidos;
4. UI responsiva;
5. erro compreensível;
6. cancelamento;
7. aparência.

Não sacrificar 1–4 para terminar itens inferiores.

## Fora do escopo v0.1

- player/waveform/mixer;
- Model Manager completo;
- registry/downloader genéricos;
- benchmark comparativo amplo;
- ensembles;
- Lead/Rhythm;
- Acoustic/Electric;
- packaging final;
- updater;
- cloud;
- servidor;
- banco.

## Gate PASS

`PASS` somente se:

- launcher abre;
- UI seleciona input/modo/output;
- inferência roda fora da UI;
- modo 6 Stems conclui em CUDA;
- seis stems válidos são produzidos;
- input permanece inalterado;
- result/manifest é persistido;
- botão abrir pasta funciona;
- testes baratos passam;
- smoke offline funciona depois do modelo instalado.

Se o modo 6 Stems não funcionar, resultado é `BLOCKED`, mesmo que Vocals HQ funcione.

## Depois da v0.1

Não iniciar “Fase 2” por reflexo.

Faça gap analysis:

- o que já está resolvido?
- qual problema real mais prejudica uso/qualidade?
- qual parte das fases 2–6 resolve esse problema?

A ordem provável tende a ser:

1. qualidade/modelos;
2. robustez do worker/cancelamento;
3. player/mixer;
4. Guitar Lab;
5. packaging.

Mas evidência de uso pode mudar essa ordem.
