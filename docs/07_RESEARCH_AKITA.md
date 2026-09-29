# O que aproveitar do Akita's AI Lair

Pesquisa feita em 29/09/2026. O objetivo não é copiar o setup inteiro; é aproveitar padrões úteis.

## Útil agora

### `my-skills`: estrutura e raciocínio

O próprio Fabio Akita recomenda **não copiar as skills dele às cegas**: elas carregam premissas de paths, credenciais e workflow. O que vale aproveitar é o formato e os gates.

Padrões aproveitados aqui:

- `deepwork`: tarefa grande quebrada em fases persistentes, cada uma com validação.
- `verification-planning`: decidir antes como uma afirmação será provada.
- `clonedeps`: clonar somente dependências críticas quando documentação não basta, sem transformar clone em fonte de execução automática.
- `security-audit`: tratar supply chain, downloads, execução e limites do sandbox como parte do design.
- `loop-engineering`: ideia de loop com critério de sucesso; adaptada para benchmark de modelos, não para “agente tentando até parecer bom”.
- `simplify`/`post-refactor`: úteis depois que comportamento estiver coberto; não devem guiar o bootstrap.
- `worktrees`: úteis se no futuro houver experimentos paralelos arriscados; desnecessárias no começo.
- `release-smoke-test`: conceito de testar o artefato empacotado em ambiente limpo; reaproveitar na Fase 6.

Criamos três skills pequenas e específicas neste repo: `model-evaluation`, `dependency-inspection`, `project-verification`.

### `AGENTS.md`

É o maior ganho prático: comandos, invariantes e armadilhas ficam junto do repo. Este pacote já contém um `AGENTS.md` conciso e específico.

### Memória/decision log

A ideia do `ai-memory` é boa quando várias sessões/agentes precisam continuar o mesmo projeto. Porém não é obrigatório para começar: `AGENTS.md` + `docs/06_DECISIONS.md` + roadmap já evitam muita redescoberta.

Se você alternar bastante entre Codex/OpenCode/Claude, `ai-memory` passa a valer mais. O projeto suporta Codex e OpenCode; no Windows nativo, o suporte existe mas ainda é descrito como experimental, enquanto WSL2 é suportado.

### `ai-jail`

É relevante para seu desejo de limitar o agente. No Linux ele usa bubblewrap/Landlock/seccomp; no macOS usa sandbox-exec. **Não suporta Windows nativo**; o caminho indicado é WSL2.

Para este projeto:

- opção simples: Codex nativo com `workspace-write`, sem writable roots extras, rede sob aprovação;
- opção mais isolada: Codex dentro do WSL2 + ai-jail, com somente a pasta do projeto montada/gravável.

Não tornaremos ai-jail dependência do aplicativo.

## Não útil para construir o produto

### `ai-usagebar`

Bom para monitorar quota de provedores/agentes; não melhora separação de áudio nem arquitetura do app. Use apenas se você pessoalmente quiser monitorar consumo do Codex/OpenCode.

### `ghpending`

Útil quando o repo tiver fluxo real de PRs/issues. No bootstrap local, é ruído.

### `tclock`

Sem relação com o problema.

### Projetos Frank

`frank_karaoke` foi inspecionado porque parece próximo do domínio. Ele trabalha com áudio/pitch/karaokê, mas a própria documentação registra que **não tem source separation**. Não é base técnica para nosso engine.

O que vale copiar como princípio: cachear artefatos caros, documentar pipeline de áudio e tratar falhas de análise/download de forma previsível.

## Kaizen

Padrão adotado: só criar nova regra/skill quando aparecer fricção real repetida. Não começar o projeto com vinte skills.
