// Feature 006 / T016 — Layperson explanations for backend signal names.
//
// Contract: specs/006-frontend-ux-improvements/contracts/signal_explanations.contract.md.
// Consumed by `<ExpandedAnalysis>` (US2). Each entry is verified by
// `tests/e2e/signal-explanations.spec.ts` against the JARGON_BLACKLIST.

export interface ExplanationCopy {
  headline: string
  body: string
}

// Backend currently emits names in two stylings: bare ("precision-burst")
// for some signals and namespaced ("behavioral-patterns/precision-burst")
// for others. We keep entries for both so `explainSignal` never falls back
// silently for known signals.
export type SignalName =
  | 'acpl-analysis'
  | 'engine-correlation/top1'
  | 'engine-correlation/top3'
  | 'engine-correlation/weighted-top1'
  | 'engine-correlation/weighted'
  | 'regime-shift'
  | 'timing-analysis'
  | 'blunder-suppression'
  | 'behavioral-patterns/blunder-suppression'
  | 'precision-burst'
  | 'behavioral-patterns/precision-burst'
  | 'complexity'
  | 'complexity-analysis'
  | 'tactical-detection'
  | 'segments-weighted-aggregate'

export const SIGNAL_EXPLANATIONS: Record<SignalName, ExplanationCopy> = {
  'acpl-analysis': {
    headline: 'Precisão acima do esperado',
    body: 'Mede o quanto este jogador erra em cada lance comparado à média de jogadores da mesma faixa de rating. Erros muito pequenos podem indicar consulta a um motor de xadrez.',
  },
  'engine-correlation/top1': {
    headline: 'Lances batem com o motor',
    body: 'Fração dos lances jogados que coincidem com a melhor opção sugerida pelo Stockfish. Valores muito acima da média da faixa de rating indicam correlação suspeita com o motor.',
  },
  'engine-correlation/top3': {
    headline: 'Lances entre os 3 melhores do motor',
    body: 'Fração dos lances jogados que estão entre as três melhores opções do motor. Reforça o sinal de correlação quando o jogador evita lances ruins de forma consistente.',
  },
  'engine-correlation/weighted-top1': {
    headline: 'Acerto ponderado pelas posições difíceis',
    body: 'Como o sinal de "lances batem com o motor", mas dá peso maior a posições onde havia muitas opções razoáveis. Acertar repetidamente em momentos difíceis é mais suspeito do que em posições óbvias.',
  },
  'engine-correlation/weighted': {
    headline: 'Acerto ponderado pelas posições difíceis',
    body: 'Como o sinal de "lances batem com o motor", mas dá peso maior a posições onde havia muitas opções razoáveis. Acertar repetidamente em momentos difíceis é mais suspeito do que em posições óbvias.',
  },
  'regime-shift': {
    headline: 'Mudança brusca de estilo durante a partida',
    body: 'Detecta momentos em que o nível de precisão do jogador muda drasticamente no meio do jogo. Saltos abruptos sugerem que o jogador pode ter começado ou parado de receber ajuda externa.',
  },
  'timing-analysis': {
    headline: 'Tempo gasto por lance fora do padrão',
    body: 'O tempo que o jogador gasta em cada lance não acompanha a dificuldade da posição como seria esperado de um humano. Padrões muito uniformes ou inversos sugerem consulta a uma ferramenta.',
  },
  'blunder-suppression': {
    headline: 'Erros graves esperados não aconteceram',
    body: 'Em posições onde a maioria dos jogadores cometeria um erro grave, este jogador evita o erro com frequência incomum. Pode indicar que algo está alertando sobre a jogada perigosa.',
  },
  'behavioral-patterns/blunder-suppression': {
    headline: 'Erros graves esperados não aconteceram',
    body: 'Em posições onde a maioria dos jogadores cometeria um erro grave, este jogador evita o erro com frequência incomum. Pode indicar que algo está alertando sobre a jogada perigosa.',
  },
  'precision-burst': {
    headline: 'Sequência de lances perfeitos',
    body: 'Sequências longas de lances quase ótimos seguidas — atípico para um jogador humano, que costuma alternar boas e más decisões. Sugere apoio externo durante o trecho.',
  },
  'behavioral-patterns/precision-burst': {
    headline: 'Sequência de lances perfeitos',
    body: 'Sequências longas de lances quase ótimos seguidas — atípico para um jogador humano, que costuma alternar boas e más decisões. Sugere apoio externo durante o trecho.',
  },
  complexity: {
    headline: 'Qualidade das jogadas em momentos complicados',
    body: 'Avalia o quão bem o jogador joga especificamente em posições complicadas, onde a chance de errar é alta. Acertos consistentes em momentos difíceis chamam atenção.',
  },
  'complexity-analysis': {
    headline: 'Qualidade das jogadas em momentos complicados',
    body: 'Avalia o quão bem o jogador joga especificamente em posições complicadas, onde a chance de errar é alta. Acertos consistentes em momentos difíceis chamam atenção.',
  },
  'tactical-detection': {
    headline: 'Identificação rápida de táticas',
    body: 'Mede a rapidez e a precisão com que o jogador encontra combinações táticas (capturas, ataques duplos, ameaças de mate). Acerto perfeito em táticas curtas e profundas é raro mesmo entre fortes humanos.',
  },
  'segments-weighted-aggregate': {
    headline: 'Resumo ponderado das fases da partida',
    body: 'Combina o desempenho do jogador em cada fase da partida (abertura, meio-jogo, finais) com pesos calibrados. Valores altos significam desempenho suspeito ao longo da partida toda, não apenas em um momento.',
  },
}

export const FALLBACK_EXPLANATION: ExplanationCopy = {
  headline: 'Sinal técnico',
  body: 'Indicador estatístico identificado pelo motor de análise. Descrição leiga não disponível para este sinal.',
}

/**
 * Patterns that MUST NOT appear in any explanation body. Verified by
 * `tests/e2e/signal-explanations.spec.ts`.
 */
export const JARGON_BLACKLIST: readonly RegExp[] = [
  /\bz-?score\b/i,
  /\bbootstrap\b/i,
  /\bCUSUM\b/i,
  /\bp-?value\b/i,
  /\bratio\b(?!\s+(entre|de))/i,
  /\bregression residual\b/i,
  /\bbucket\b(?!\s+de\s+rating)/i,
]

export function explainSignal(name: string): ExplanationCopy {
  if (name in SIGNAL_EXPLANATIONS) {
    return SIGNAL_EXPLANATIONS[name as SignalName]
  }
  return FALLBACK_EXPLANATION
}

// ─── Per-game reasoning summary ───────────────────────────────────────────
//
// Builds a narrative explanation of how a specific score was reached based
// on the data available in the SSE payload: numeric score, risk_level,
// confidence_interval, dominant_signals. The summary is rendered at the
// top of `ExpandedAnalysis` so the reader sees WHY the score is what it
// is before drilling into individual signal copy.

type RiskKey = 'low' | 'medium' | 'high'

export interface GameScoreSummary {
  headline: string
  intro: string
  signalsLeadIn: string
}

export interface SummaryInputs {
  score?: number
  riskLevel?: RiskKey | string
  confidenceInterval?: [number, number]
  dominantSignals?: string[]
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`
}

function riskCopy(level: RiskKey | string | undefined): {
  word: string
  headline: string
  verdict: string
} {
  switch (level) {
    case 'high':
      return {
        word: 'ALTO',
        headline: 'Score alto — sinais convergentes para suspeita',
        verdict: 'fortemente sugere que houve apoio externo durante a partida',
      }
    case 'medium':
      return {
        word: 'MÉDIO',
        headline: 'Score intermediário — atenção, mas não conclusivo',
        verdict:
          'pede análise complementar — há indícios, mas nenhum sinal isolado fecha o caso',
      }
    default:
      return {
        word: 'BAIXO',
        headline: 'Score baixo — partida dentro do padrão humano',
        verdict:
          'é consistente com jogo humano dentro da faixa de rating do jogador',
      }
  }
}

export function summarizeGame(inputs: SummaryInputs): GameScoreSummary {
  const scoreValue = inputs.score ?? 0
  const risk = riskCopy(inputs.riskLevel)
  const signals = inputs.dominantSignals ?? []
  const ci = inputs.confidenceInterval

  let ciPhrase = ''
  if (ci) {
    const width = ci[1] - ci[0]
    const widthLabel =
      width < 0.1
        ? 'precisão alta'
        : width < 0.2
          ? 'precisão moderada'
          : 'incerteza considerável'
    ciPhrase = ` O intervalo de confiança vai de ${pct(ci[0])} a ${pct(ci[1])} (${widthLabel} — quanto mais estreito, mais confiável o número).`
  }

  const intro = `Esta partida pontuou ${pct(scoreValue)}, classificada como risco ${risk.word}. O resultado ${risk.verdict}.${ciPhrase}`

  let signalsLeadIn: string
  if (signals.length === 0) {
    signalsLeadIn =
      'Nenhum sinal individual se destacou — o score reflete a média ponderada de todos os indicadores avaliados, sem que nenhum tenha empurrado o resultado em uma direção específica.'
  } else if (inputs.riskLevel === 'low') {
    signalsLeadIn = `Os ${signals.length} sinais abaixo foram avaliados e contribuíram para o score, mas seus valores ficaram dentro da faixa esperada para a faixa de rating do jogador, mantendo o resultado baixo.`
  } else if (inputs.riskLevel === 'medium') {
    signalsLeadIn = `Os ${signals.length} sinais abaixo elevaram o score para a faixa de atenção, mas nenhum sozinho atingiu nível alto. Veja como cada um influenciou o resultado:`
  } else {
    signalsLeadIn = `Os ${signals.length} sinais abaixo são os que mais empurraram o score para cima nesta partida. Cada um aponta para um padrão diferente que se afastou do esperado para um humano da mesma faixa de rating:`
  }

  return { headline: risk.headline, intro, signalsLeadIn }
}
