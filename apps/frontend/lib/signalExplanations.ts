// Feature 006 / T016 — Layperson explanations for backend signal names.
//
// Contract: specs/006-frontend-ux-improvements/contracts/signal_explanations.contract.md.
// Consumed by `<ExpandedAnalysis>` (US2). Each entry is verified by
// `tests/e2e/signal-explanations.spec.ts` against the JARGON_BLACKLIST.

export interface ExplanationCopy {
  headline: string
  body: string
}

export type SignalName =
  | 'acpl-analysis'
  | 'engine-correlation/top1'
  | 'engine-correlation/top3'
  | 'engine-correlation/weighted-top1'
  | 'regime-shift'
  | 'timing-analysis'
  | 'blunder-suppression'
  | 'precision-burst'
  | 'complexity'
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
  'precision-burst': {
    headline: 'Sequência de lances perfeitos',
    body: 'Sequências longas de lances quase ótimos seguidas — atípico para um jogador humano, que costuma alternar boas e más decisões. Sugere apoio externo durante o trecho.',
  },
  complexity: {
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
