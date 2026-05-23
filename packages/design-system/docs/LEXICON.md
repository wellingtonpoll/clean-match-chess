# Lexicon — v1.0.0

The forensic-analytics lexicon is the canonical glossary the report
engine and CLI narrative pull from. Each entry exists in **both**
English and Portuguese with the same `term` key; the JSON files are at
`src/design_system/lexicon/entries_en.json` and
`src/design_system/lexicon/entries_pt.json`.

The table below renders the v1.0.0 entries side-by-side. The
`alternatives_forbidden` column is enforced: every term listed there
MUST appear in `tests/fixtures/forbidden-terms/<lang>.txt`.

| Term (EN) | Definition (EN) | Term (PT) | Definition (PT) | Alternatives preferred | Alternatives forbidden |
| --------- | --------------- | --------- | --------------- | ---------------------- | ---------------------- |
| Behavioral Signal | A computed metric describing player behaviour relative to engine reference under matched complexity. | Sinal Comportamental | Métrica computada que descreve o comportamento do jogador em relação ao motor de referência sob complexidade equivalente. | "engine-correlation evidence", "evidência de correlação com motor" | "cheater", "trapaceiro" |
| Statistical Irregularity | A measurement falling outside the expected distribution for the player's rating band and game phase. | Irregularidade Estatística | Medição fora da distribuição esperada para a faixa de rating e fase de partida do jogador. | "outlier observation", "observação atípica" | "fraud", "fraude" |
| Complexity Correlation | The relationship between move precision and the computational complexity of the position. | Correlação com Complexidade | Relação entre a precisão dos lances e a complexidade computacional da posição. | "complexity-precision pairing" | "guilty", "culpado" |
| Tactical Precision Burst | A short run of consecutively near-optimal moves in high-complexity positions. | Pico de Precisão Tática | Sequência curta de lances quase-ótimos consecutivos em posições de alta complexidade. | "burst window" | "cheat detected", "trapaça detectada" |
| Risk Window | A contiguous segment of plies where the aggregated suspicion score crosses an elevated regime. | Janela de Risco | Segmento contíguo de lances onde o escore agregado de suspeita cruza um regime elevado. | "flagged segment", "segmento sinalizado" | "guilty stretch", "trecho culpado" |
| Analytical Confidence | The bootstrap-derived confidence interval around an aggregated suspicion score. | Confiança Analítica | Intervalo de confiança derivado por bootstrap em torno do escore agregado de suspeita. | "confidence interval", "intervalo de confiança" | "certainty of fraud", "certeza de fraude" |
| Regime | A classified phase of the game (opening, middlegame, endgame) used to scope a signal. | Regime | Fase classificada da partida (abertura, meio-jogo, final) usada para delimitar um sinal. | "phase", "fase" | — |
| Engine Reference | The locked Stockfish + UCI option set used to generate the comparison evaluation. | Referência de Motor | Conjunto bloqueado de Stockfish + opções UCI usado para gerar a avaliação comparativa. | "Stockfish reference", "referência Stockfish" | "ground truth", "verdade absoluta" |
| Bootstrap Estimate | A resampling-based statistic carrying its own confidence interval. | Estimativa Bootstrap | Estatística baseada em reamostragem, acompanhada do próprio intervalo de confiança. | "resampled estimate", "estimativa reamostrada" | — |
| Determinism Guarantee | The locked-engine-options promise that re-running an audit produces a bit-identical artefact on the same architecture. | Garantia de Determinismo | Promessa, baseada em opções de motor bloqueadas, de que reexecutar uma auditoria produz artefato bit-idêntico na mesma arquitetura. | "reproducible run", "execução reproduzível" | — |
| Reproducibility Manifest | The embedded record that lists every input hash, engine version, and tooling version needed to re-render the artefact. | Manifesto de Reprodutibilidade | Registro embutido que lista cada hash de entrada, versão do motor e versão de ferramentas necessárias para re-renderizar o artefato. | "embedded manifest", "manifesto embutido" | — |

## Lexicon governance

- Adding a term: MINOR bump; PR must touch both `entries_en.json` and
  `entries_pt.json`.
- Removing a term: MAJOR bump.
- Wording-only changes to an existing definition: PATCH bump.
- The `forbidden_alternatives_resolve()` helper (see
  `src/design_system/lexicon/lookup.py`) asserts that every
  `alternatives_forbidden` value exists in the corresponding
  `forbidden-terms/<lang>.txt` universe.

## Forbidden terms file

The forbidden-terms files (`tests/fixtures/forbidden-terms/{en,pt}.txt`)
are owned by feature 001-fairplay-analysis. Feature 002 extends the
files transparently: new lexicon entries that reference a new forbidden
alternative require a corresponding append to the TSV.

See `docs/CONTRIBUTING.md` → "How to add a forbidden term" for the
exact workflow.
