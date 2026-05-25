# Feature Specification: Frontend UX Improvements — Player Links, Expandable Cards, Sticky Header, Cross-Viewport Tests

**Feature Branch**: `006-frontend-ux-improvements`

**Created**: 2026-05-24

**Status**: Draft

**Input**: User description: "Quatro melhorias no `apps/frontend`: (1) nome dos jogadores nos cards de jogo viram links clicáveis que disparam análise do jogador clicado, (2) cards de análise expansíveis com explicação leiga das razões por trás do score, (3) suite Playwright para caçar bugs em viewports mobile + desktop, (4) header fixo no topo com marca HorseLabs + campo de busca, visível durante scroll dos resultados."

## Context

O frontend atual (`apps/frontend`) é uma SPA Next.js que recebe um username + plataforma, dispara análise via `/api/analyze` (SSE stream), e exibe uma lista de partidas com score, intervalo de confiança e sinais dominantes. Limitações UX observadas:

- **Navegação cega entre jogadores**: investigadores frequentemente precisam comparar adversários de um suspeito (transitivamente analisar oponentes para entender padrões). Hoje têm que copiar nomes e re-digitar.
- **Cards opacos para usuários leigos**: `dominant_signals` aparecem como tokens crus (`acpl-analysis`, `engine-correlation/top1`) sem explicação. Investigadores sem formação técnica não sabem interpretar.
- **Risco de regressão cross-device**: o produto roda em browser e mobile mas não há rede de segurança automática para layout. Mudanças em `GameRow` ou `page.tsx` podem quebrar mobile sem o autor perceber.
- **Header efêmero**: a marca HorseLabs e o campo de busca só aparecem antes do primeiro `submit`. Após scroll dos resultados, usuário perde contexto da marca e precisa scrollar de volta para refazer busca.

Esta feature endereça os quatro itens em uma única entrega coesa: melhora ergonomia para investigadores leigos + adiciona regression safety automatizada para o frontend.

## Clarifications

### Session 2026-05-24

- Q: Comportamento ao clicar marca "HorseLabs" no header fixo (US3 AS5)? → A: **Reset**. Aborta análise em curso, limpa sessions, restaura hero section grande. Semântica padrão "voltar para home".
- Q: Como tratar SC-002 (compreensão leiga das explicações)? → A: **Remover critério subjetivo**. Escopo da feature termina em: card expande ao clique, exibe seção detalhada com texto pt-BR breve/resumido/sem jargão técnico não-explicado. Capacidade cognitiva do usuário final está **fora do escopo** do produto. SC-002 reescrito como critério binário verificável: 11 signals têm entrada no dicionário + texto é pt-BR + lista negra de termos técnicos não-explicados não aparece (z-score, bootstrap, CUSUM, ratio sem contexto, p-value).
- Q: Layout do header fixo em viewport mobile estreito (< 480px)? → A: **Stacking vertical**. Marca em cima (linha 1), busca + platform toggle embaixo (linha 2). Ambos full-width, legíveis. Header cresce em altura no mobile mas controles permanecem acessíveis.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clickable Player Links Pivot Investigation Flow (Priority: P1)

Um investigador analisa o jogador "alice123" e nota que ela jogou contra "bob456" três vezes com score alto. Investigador clica no nome "bob456" no card e o frontend imediatamente reanalisa esse jogador — sem precisar copiar/colar.

**Why this priority**: Reduz fricção do principal padrão de uso (investigação transitiva). Atalho de UX com payoff alto e custo de implementação baixo.

**Independent Test**: Carregue a página, digite "alice123", aguarde uma partida com score alto, clique no nome do oponente. URL/estado mostra o oponente como `activeUsername` e nova análise começa com a lista anterior substituída.

**Acceptance Scenarios**:

1. **Given** uma análise concluída para "alice123" exibindo a partida `White: alice123 vs Black: bob456`, **When** o investigador clica em "bob456", **Then** o campo de busca é populado com "bob456", a análise atual é descartada, e uma nova análise começa para esse jogador na mesma plataforma.
2. **Given** uma análise em andamento, **When** o investigador clica em qualquer nome de jogador, **Then** a análise atual é abortada antes da nova começar (mesma semântica do `abortRef` já implementado para submit manual).
3. **Given** o nome do próprio jogador analisado (subject) aparecer em um card, **When** o investigador clica, **Then** a análise NÃO reinicia (mesmo username + mesma plataforma = no-op visual).
4. **Given** o link tem o mesmo username em uma plataforma diferente da atual, **When** o investigador clica, **Then** a análise reinicia mas mantém a plataforma corrente (sem heurística de inferir plataforma; é função separada do toggle).

---

### User Story 2 - Expandable Analysis Cards with Layperson Explanations (Priority: P1)

Um investigador sem formação técnica vê um card marcado "SUSPEITO" com tokens `acpl-analysis` + `engine-correlation/top1`. Hoje precisa consultar documentação externa para entender. Clicando no card, ele se expande mostrando, em português claro: "ACPL: este jogador errou em média 8 centipawns por lance, abaixo do esperado para a faixa 1500-1800 onde a média é 65cp ± 28cp — diferença de >2 desvios padrão sugere ajuda computacional." + análogos para cada sinal.

**Why this priority**: Diferencial crítico para usuários não-técnicos (alvo principal do produto). Sem isso, scores são caixa-preta.

**Independent Test**: Abra um card concluído com risk_level = "high". Clique no card. Conteúdo expandido aparece dentro de 300ms; cada `dominant_signal` listado tem uma explicação de 1-2 frases em pt-BR. Clique novamente colapsa.

**Acceptance Scenarios**:

1. **Given** um card concluído com `dominant_signals` = `["acpl-analysis", "engine-correlation/top1"]`, **When** o investigador clica no card, **Then** o card expande, e cada signal mostra uma explicação curta (≤ 2 frases) em pt-BR que NÃO usa jargão técnico não-explicado (sem "z-score", "bootstrap", "CUSUM" sem contexto).
2. **Given** um card já expandido, **When** o investigador clica de novo, **Then** o card colapsa de volta ao estado compacto.
3. **Given** um card em estado `pending`/`analyzing`/`error`, **When** o investigador clica, **Then** o card NÃO expande (não há conteúdo expandido para esses estados).
4. **Given** múltiplos cards expandidos simultaneamente, **When** o investigador interage com qualquer um, **Then** estados de expansão são independentes (não fechamento automático de outros cards).
5. **Given** um signal desconhecido (não mapeado para explicação), **When** o card expande, **Then** mostra um fallback genérico ("Sinal técnico sem descrição leiga disponível") ao invés de quebrar.

---

### User Story 3 - Sticky Header with Brand + Search Field (Priority: P2)

Um investigador analisa um jogador e tem uma lista longa de partidas (50+). Quer pivotar para outro jogador sem scrollar 2 telas até o topo. Header fixo no topo permanece visível durante o scroll, contendo a marca HorseLabs à esquerda e um campo de busca compacto à direita.

**Why this priority**: Melhora ergonomia em lists longas (caso comum quando 005 corpus + dataset baselines real produzem mais partidas). Não é blocker, mas reduz frustração mensurável.

**Independent Test**: Analise um jogador, scrolle até o final dos resultados, confirme que o header com a marca + busca permanece visível. Digite outro username diretamente no header e clique "Analisar" — análise inicia sem precisar scrollar.

**Acceptance Scenarios**:

1. **Given** o investigador rolou os resultados para baixo, **When** ele tenta interagir com a busca ou com a marca, **Then** ambos permanecem visíveis e clicáveis no topo do viewport.
2. **Given** o estado inicial (nenhuma análise iniciada), **When** o investigador chega à página, **Then** a hero section com tagline ainda aparece ABAIXO do header (não desaparece — apenas é complementada pelo header fixo).
3. **Given** o header está fixo, **When** o usuário interage com o conteúdo abaixo, **Then** o conteúdo (incluindo cards expandidos da US2) escorre corretamente atrás do header sem ser ocultado.
4. **Given** viewport mobile estreito (< 480px), **When** o header é renderizado, **Then** marca e campo de busca permanecem acessíveis (pode haver redimensionamento ou stacking vertical — UX não pode quebrar).
5. **Given** o investigador clica na marca HorseLabs, **When** há uma análise em curso, **Then** a análise é abortada, todas as sessions são limpas, e a hero section grande reaparece (semântica "voltar para home"; confirmado em Clarifications 2026-05-24).

---

### User Story 4 - Cross-Viewport Bug Hunt with Playwright (Priority: P2)

Um maintainer abre um PR alterando o frontend. CI roda uma suite Playwright que carrega `npm run dev`, abre a página em 4 viewports (2 mobile + 2 desktop), executa scripts de smoke que detectam overflows, controles ocultos, hover quebrado, truncamento de texto e scroll lock. Bugs visuais que escapariam revisão humana viram falha de CI bloqueante.

**Why this priority**: Sem isso, qualquer mudança das US1/US2/US3 pode regredir em mobile sem alguém notar antes do usuário. Investimento de infra com payoff contínuo.

**Independent Test**: Maintainer roda `npm run test:e2e` localmente. Suite executa em ≤ 5 min em modo headless, testa 4 viewports (375×667 iPhone SE, 414×896 iPhone 11 Pro Max, 1280×800 laptop, 1920×1080 desktop), produz relatório com captures dos bugs encontrados (se houver) por viewport.

**Acceptance Scenarios**:

1. **Given** a feature está implementada, **When** maintainer roda a suite localmente, **Then** todos os testes passam OU as falhas têm screenshots + descrições claras do bug detectado.
2. **Given** um PR introduz um overflow horizontal em mobile (ex: linha que excede 375px de largura), **When** CI roda a suite, **Then** o teste falha com mensagem "overflow horizontal detectado: <elemento> excede viewport width by Xpx".
3. **Given** um PR introduz um controle oculto atrás do header fixo em mobile, **When** CI roda a suite, **Then** o teste falha — controle inacessível.
4. **Given** wall time CI inteiro, **When** a suite Playwright executa, **Then** completa em ≤ 5 minutos no runner padrão GitHub Actions (constitution Principle IV).
5. **Given** a suite roda contra `npm run dev`, **When** o servidor demora a subir, **Then** o test runner espera até health-check antes de começar (timeout configurável; default 30s).

---

### Edge Cases

- **Player link em jogo onde subject não é nem White nem Black** (improvável dado o backend, mas defensive): link mostra ambos os nomes mas só o oponente é clicável; clique no subject = no-op visual.
- **Player link com caracteres especiais no username** (`<>`, `/`, ` `): URL-encode ao popular o campo; nenhum risco de XSS porque o conteúdo é texto, não HTML.
- **Card expandido durante scroll**: header fixo não deve fechar o card ou perder o estado de expansão.
- **Mobile com teclado virtual aberto**: campo de busca no header não pode ficar atrás do teclado nem causar layout shift indesejado quando teclado fecha.
- **Playwright vs SSE stream**: a suite deve esperar pelo menos uma partida com status "done" antes de validar cards expandidos (não pode usar fixtures de timing porque o stream é assíncrono).
- **Headless vs headed browser**: testes precisam funcionar em ambos os modos; CI usa headless.
- **Network failures durante testes**: backend `/api/analyze` pode falhar (chess.com indisponível); testes devem mockar a resposta para isolar bugs de layout dos bugs de upstream.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Sistema MUST renderizar os campos `White` e `Black` de cada game card como elementos clicáveis (botões ou links semânticos, não apenas spans com `onClick`).
- **FR-002**: Ao clicar em um nome de jogador, sistema MUST popular o campo de busca com o username clicado, abortar análise em curso (se houver), e disparar uma nova análise para esse jogador na plataforma corrente.
- **FR-003**: Sistema MUST não disparar nova análise quando o usuário clica no nome do `subject` atual (mesma plataforma + mesmo username = no-op).
- **FR-004**: Sistema MUST tornar cada game card em estado `done` clicável para expandir/colapsar. Cards em `pending`/`analyzing`/`error` permanecem não-expansíveis.
- **FR-005**: Card expandido MUST mostrar uma seção de "Análise detalhada" listando cada `dominant_signal` com uma explicação em português brasileiro de ≤ 2 frases, sem usar jargão técnico não-explicado.
- **FR-006**: Sistema MUST manter um dicionário de explicações leigas para cada signal conhecido (`acpl-analysis`, `engine-correlation/top1`, `engine-correlation/top3`, `engine-correlation/weighted-top1`, `regime-shift`, `timing-analysis`, `blunder-suppression`, `precision-burst`, `complexity`, `tactical-detection`, `segments-weighted-aggregate`, e quaisquer outros emitidos pelo backend). Sinais desconhecidos MUST exibir fallback genérico ao invés de quebrar.
- **FR-007**: Estado de expansão de cada card MUST ser independente (múltiplos cards expandidos simultaneamente; clicar em um não fecha os outros).
- **FR-008**: Sistema MUST renderizar um header fixo no topo do viewport com (a) marca HorseLabs à esquerda em escala reduzida vs o lockup hero atual, (b) campo de busca compacto + toggle de plataforma à direita.
- **FR-009**: Header fixo MUST permanecer visível e interativo durante scroll vertical do conteúdo abaixo, incluindo cards expandidos da US2.
- **FR-010**: Hero section atual (lockup grande + tagline) MUST permanecer no fluxo de página abaixo do header, vista apenas no estado inicial (zero análises). O campo de busca da hero é removido — busca passa a viver exclusivamente no header.
- **FR-011**: Em viewports mobile (< 480px de largura), header MUST aplicar **stacking vertical**: marca HorseLabs ocupa a primeira linha do header (full-width), busca + platform toggle ocupam a segunda linha (full-width). Header cresce em altura mas mantém ambos controles acessíveis e legíveis (confirmado em Clarifications 2026-05-24).
- **FR-012**: Sistema MUST incluir uma suite de testes Playwright executável via `npm run test:e2e` que valida o app em ≥ 4 viewports: 375×667 (iPhone SE), 414×896 (iPhone 11 Pro Max), 1280×800 (laptop), 1920×1080 (desktop).
- **FR-013**: A suite Playwright MUST detectar e falhar em pelo menos 5 classes de bug de layout: (a) overflow horizontal acima do viewport width, (b) elementos clicáveis sobrepostos por elementos fixos (controles ocultos atrás do header), (c) texto truncado sem ellipsis nem expansão, (d) elementos com `hover` state que não funciona em touch (mobile), (e) scroll lock acidental quando um card expande.
- **FR-014**: A suite Playwright MUST executar em wall time ≤ 5 minutos no runner GitHub Actions padrão (constitution Principle IV — performance budget).
- **FR-015**: A suite Playwright MUST gerar um relatório consumível em CI (screenshot por viewport por teste falhado, com nome do bug detectado).
- **FR-016**: Sistema MUST mockar a resposta de `/api/analyze` nos testes Playwright (não chamar o backend real) — isola bugs de layout de bugs de upstream.
- **FR-017**: Sistema MUST NÃO alterar a API de `/api/analyze` nem qualquer código backend; toda mudança é confinada ao `apps/frontend/`.
- **FR-018**: Sistema MUST adicionar um job CI `frontend_e2e` ao workflow existente (`.github/workflows/ci.yml`) que executa a suite Playwright em PRs que tocam `apps/frontend/`.

### Key Entities

- **Player Link**: elemento visual + comportamental que envolve o nome de um jogador em um card. Atributos: `username`, `is_subject` (boolean — se True, link é não-clicável).
- **Signal Explanation Dictionary**: mapeamento de signal name → string pt-BR de ≤ 2 frases. Vive em `apps/frontend/lib/` ou similar; mantido in-frontend (não vem do backend).
- **Expandable Card State**: estado local de cada `GameRow` indicando se o card está expandido. Default: colapsado.
- **Sticky Header**: componente novo (`<Header>` ou similar) ancorado no topo. Contém marca + busca + platform toggle.
- **Playwright Test Suite**: nova subárvore sob `apps/frontend/tests/e2e/` (ou similar) contendo viewport matrix + smoke tests.
- **Mock Stream Fixture**: payload SSE pré-gravado que os testes Playwright servem como resposta de `/api/analyze` para isolar layout de upstream.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após implementação, ≥ 90% dos usuários que analisam um jogador conseguem pivotar para o adversário em ≤ 1 clique (sem digitar/copiar username).
- **SC-002**: Critério binário verificável (reescopado em Clarifications 2026-05-24 — compreensão real do usuário final está fora do escopo): (a) cada um dos 11 signals listados em FR-006 possui entrada no dicionário de explicações, (b) cada explicação está em português brasileiro, (c) nenhuma explicação contém os termos técnicos não-explicados da lista negra: `z-score`, `bootstrap`, `CUSUM`, `ratio` (sem contexto), `p-value`. Verificável automaticamente via teste de unidade + lint.
- **SC-003**: Header com marca HorseLabs + busca está visível em 100% dos estados pós-scroll em viewports ≥ 320px de largura.
- **SC-004**: Suite Playwright cross-viewport executa em ≤ 5 min wall time no GitHub Actions runner padrão (warm cache; cold cache ≤ 8 min).
- **SC-005**: Suite Playwright captura ≥ 5 classes de bug distintas (overflow, controles ocultos, truncamento, hover quebrado, scroll lock) em PRs sintéticos de regressão validados antes do merge desta feature.
- **SC-006**: PRs que tocam `apps/frontend/` automaticamente acionam o job `frontend_e2e`; PRs que não tocam o frontend NÃO o acionam (path filter funcional).
- **SC-007**: Nenhuma mudança no backend: `git diff --stat origin/main` mostra zero linhas alteradas fora de `apps/frontend/`, `.github/workflows/ci.yml`, `CHANGELOG.md`, e `specs/006-frontend-ux-improvements/`.
- **SC-008**: Cards expandidos colapsam corretamente em todos os viewports testados (sem layout shift > 5px observado nos screenshots Playwright).

## Assumptions

- Lista de signal names que o backend emite no campo `dominant_signals` é estável e cobre os ~11 signals listados na FR-006. Se um novo signal for adicionado backend-side, fallback genérico cobre transitivamente.
- Frontend permanece SPA Next.js client-side; nenhuma migração para SSR/RSC necessária para esta feature.
- Investigador típico usa um único username + plataforma por sessão e raramente troca de plataforma (toggle preservada no header é status quo, não foco da feature).
- Servidor `/api/analyze` permanece disponível durante uso normal; testes Playwright NÃO assumem que ele está rodando — usam mock.
- Constitution Principle IV (performance) é satisfeita pela suite Playwright caber em ≤ 5 min wall; latência de UI individual (clique-para-expandir, click-para-pivotar) é instantânea-perceptual e NÃO requer budget formal além do "feels fast" qualitativo.
- Backend `/api/analyze` retorna `dominant_signals` como array de strings — confirmado por inspeção do código atual (`apps/frontend/app/page.tsx`).
- HorseLabs branding atual (cores, fonts, lockup) permanece; apenas escala é ajustada para o header fixo.
- A11y: links e botões usam elementos semânticos corretos (`<button>`, `<a>` quando navegação real) — não interativos com `<div onClick>`. Foco visível via outline padrão ou customizado.
- Clique em "HorseLabs" no header = reset (aborta análise, limpa sessions, restaura hero) — **confirmado** em Clarifications 2026-05-24.
