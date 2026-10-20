# audio-separator 0.47.0 — progresso real por bloco

Pergunta: é possível observar a fração concluída da inferência Core sem
interpretar logs, mudar parâmetros ou copiar o loop do modelo?

Fonte: distribuição local pinada `audio-separator==0.47.0`,
`separator/architectures/mdxc_separator.py`, SHA-256
`b9e36ad700d30550286523a3af9d4468780aef9de562fda8252670f69169b3bc`.
O wheel não fornece o SHA do commit; a evidência fica vinculada a esse arquivo
instalado. Nenhum clone, instalação ou alteração da dependência foi necessário.

O módulo importa `tqdm` diretamente e envolve `chunk_starts` (RoFormer) e
`batches` (MDXC). O corpo do loop executa o forward e acumula a saída; retomar
o iterador após o `yield` significa que esse bloco terminou. O total vem do
próprio iterável, incluindo overlap/padding reais, sem recalculá-los no app.
Não há callback público de progresso de inferência no caminho utilizado.

Decisão: envolver apenas o símbolo `tqdm` desse módulo enquanto o adapter
executa a separação com observador. Preservar a iteração original e restaurar
o símbolo em `finally`, inclusive em falha. Esse escopo é seguro para o worker
atual, que roda um único modelo/job por processo; não é uma API para executar
backends simultaneamente em threads do mesmo processo. Chamadas headless sem
observador mantêm o caminho upstream. Se não houver total confiável, não emitir
fração nem ETA. Uma mudança futura de dependência precisa revalidar esse hook.

Em CUDA, sincronizar antes de ler o relógio de cada bloco, para medir trabalho
concluído em vez de kernels apenas enfileirados. O tempo pode incluir custo
de sincronização; não há alegação de performance idêntica. Modelo, precisão,
parâmetros, overlap, ganho e buffers de áudio permanecem iguais.

ETA: média do tempo observado por bloco × blocos restantes, disponível a partir
do primeiro bloco concluído e atualizada nos seguintes. A estimativa inicial
pode ser conservadora devido ao aquecimento. Cobre apenas a inferência. Gravação,
validação e publicação do manifest são etapas adicionais sem ETA numérica.
