# Checkpoint 3 — gate humano Guitar + Bass

Este gate compara os especialistas research-only com o Core Stems. Ele não envia
áudio para a rede e não promove nenhum modelo automaticamente.

## Preparação

Escolha pelo menos três músicas que você conheça bem. O conjunto deve cobrir, na
medida do possível:

- lead e rhythm simultâneas, e trechos com apenas uma guitarra;
- guitarra limpa e/ou distorcida, incluindo delay ou reverb estéreo;
- uma música em que pad/keys já vazou no Guitar;
- baixo interagindo com kick e com guitarras/keys graves.

Não copie as músicas para uma pasta versionada. Os resultados ficam em
`bench/private/`, que está no `.gitignore`.

## Execução

Abra o shell de desenvolvimento do projeto e, para cada música, rode:

```powershell
.\.venv\Scripts\python.exe scripts\benchmark_specialists.py --input "C:\caminho\musica.wav"
```

O comando valida os hashes dos modelos, trabalha offline, preserva o arquivo de
entrada e imprime o path do `manifest.json`. Cada run contém:

```text
guitar/G0_core_guitar.wav
guitar/G1_direct_lead.wav
guitar/G1_direct_rhythm.wav
guitar/G2_twostage_lead.wav
guitar/G2_twostage_rhythm.wav
bass/B0_core_bass.wav
bass/B1_specialist_bass.wav
```

G1 e G2 são pares Lead/Rhythm. Escute ambos os arquivos de cada par; não avalie
um role isoladamente. Não normalize os stems individualmente durante a comparação.

## Ficha por música

Copie a ficha abaixo para suas anotações locais. Use notas curtas e concretas.

```text
Música:
Run/manifest:
Trechos de referência (timestamps):

G0 Core Guitar
- separação das guitarras:
- pad/keys/vocals leakage:
- timbre/transientes/sustain/reverb:
- artefatos aquosos/metálicos:

G1 direto — Lead + Rhythm
- estabilidade semântica lead/rhythm:
- bleed lead -> rhythm / rhythm -> lead:
- instrumentos externos vazando:
- timbre/transientes/sustain/reverb:
- artefatos:

G2 two-stage — Lead + Rhythm sobre G0
- estabilidade semântica lead/rhythm:
- bleed lead -> rhythm / rhythm -> lead:
- instrumentos externos vazando:
- timbre/transientes/sustain/reverb:
- artefatos:

Comparação Guitar
- G1 vs G0:
- G2 vs G0:
- G1 vs G2:
- preferência nesta música: G0 / G1 / G2 / empate
- confiança: baixa / média / alta

B0 Core Bass
- definição/ataque:
- kick e low guitar/keys/synth leakage:
- corpo/fullness:
- artefatos:

B1 Specialist Bass
- definição/ataque:
- kick e low guitar/keys/synth leakage:
- corpo/fullness:
- artefatos:

Comparação Bass
- B1 vs B0:
- preferência nesta música: B0 / B1 / empate
- confiança: baixa / média / alta
```

## Decisão após as três músicas

Decida Guitar e Bass separadamente. Use somente um destes estados:

- `approved_for_integration`: melhora consistente, sem regressão musical
  importante, e condições de licença/uso aceitáveis;
- `experimental_continue`: sinais promissores, mas evidência ainda ambígua ou
  dependente da música;
- `rejected`: não melhora claramente ou introduz regressões relevantes.

Não aprove com base em uma única música. Para Guitar, registre também se G1 ou
G2 venceu; para Bass, compare B1 diretamente com B0. Áudio privado e outputs não
devem ser anexados a commits, issues ou relatórios versionados.

