# `audio-separator==0.47.0` — caminho MP3

**Pergunta:** a versão fixada consegue ler MP3 e produzir MP3 sem introduzir
um segundo engine ou um intermediário lossy?

**Fonte inspecionada:** distribuição/wheel local pinada
`audio-separator==0.47.0`, arquivos `separator/common_separator.py` e
`separator/separator.py`. O wheel identifica a versão 0.47.0, mas não inclui o
SHA do commit upstream; a evidência fica vinculada à distribuição instalada.

**Conclusão:** a entrada passa por `librosa.load`; o stack local validado
(`soundfile`/libsndfile) abriu e leu amostras finitas de um MP3 real. Para saída,
o upstream usa `pydub` + FFmpeg quando `use_soundfile=False` e define 320 kbps
para MP3. O adapter mantém `soundfile` para WAV/FLAC e seleciona explicitamente
o caminho pydub/FFmpeg apenas quando o usuário escolhe MP3. A inferência segue
em arrays PCM/float; não há intermediário MP3 adicional.

**Limite:** esta evidência vale para a matriz de dependências pinada do projeto.
Mudança de `audio-separator`, `librosa`, `soundfile` ou FFmpeg exige regressão.

## Correção de codificação de saída — 2026-10-19

O smoke anterior de entrada MP3 com backend fake não cobria a gravação real.
Em uma música MP3 de 184,645 s, o upstream falhou ao publicar o primeiro WAV:
`AudioExportError: Supported file format but unsupported encoding`.
`CommonSeparator.prepare_mix()` detecta `MPEG_LAYER_III`; seu
`write_audio_soundfile()` reutiliza esse subtipo, mesmo quando a saída é WAV
ou FLAC. O construtor de `Separator` não oferece opção de subtipo de saída.

Fonte instalada inspecionada: `audio-separator==0.47.0`,
`separator/common_separator.py`, SHA-256
`9a175e9bb1978bb7e6e22b329cfa1cb29fec09c45b6adee2c65096703673d32c`.
Também foi inspecionado `soundfile==0.14.0`, `soundfile.py`, SHA-256
`085feb318464c2a5e82747e0d6da43c214f3a6a4ed3a7a18f2c07fe7b3750df2`.
Neste runtime, `sf.check_format('WAV', 'MPEG_LAYER_III')` retorna `True`, mas a
escrita falha; a consulta de capacidade não é evidência suficiente de encoding.

O adapter envolve somente o writer da instância carregada durante a chamada
de separação. Preserva PCM/float compatível e troca codificações incompatíveis
por FLOAT em WAV ou PCM_24 em FLAC. O caminho MP3 continua usando pydub/FFmpeg
a 320 kbps. Não há transcodificação intermediária, novo decoder, alteração do
input ou cópia da implementação de gravação/normalização do upstream. O writer
original e o subtipo detectado são restaurados inclusive em erro.

Regressão: testes usam `CommonSeparator.prepare_mix()` e o writer real com
MP3 gerado localmente, verificando samples, formato, duração, canais, finitude,
ganho e SHA-256 do input. Cobrem também FLOAT → FLAC, preservação de PCM válido
e restauração de estado em erro. A UI agora exibe o motivo estruturado da
falha, além da mensagem genérica `audio-separator failed.`.
